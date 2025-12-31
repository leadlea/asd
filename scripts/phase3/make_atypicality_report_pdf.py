# scripts/phase3/make_atypicality_report_pdf.py
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


def is_s3(path: str) -> bool:
    return path.startswith("s3://")


def aws_s3_cp(local_path: str, s3_path: str, kms_key_arn: Optional[str]) -> None:
    cmd = ["aws", "s3", "cp", local_path, s3_path]
    if kms_key_arn:
        cmd += ["--sse", "aws:kms", "--sse-kms-key-id", kms_key_arn]
    subprocess.run(cmd, check=True)


def read_any(path: str) -> pd.DataFrame:
    if is_s3(path):
        with tempfile.TemporaryDirectory() as td:
            local = str(Path(td) / "in.parquet")
            subprocess.run(["aws", "s3", "cp", path, local], check=True)
            return pd.read_parquet(local)
    return pd.read_parquet(path)


def a4_fig():
    # A4 portrait inches
    fig = plt.figure(figsize=(8.27, 11.69))
    return fig


def page_title(fig, text: str, y=0.97):
    fig.text(0.5, y, text, ha="center", va="top", fontsize=18, fontweight="bold")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", required=True, help="atypicality_v0.parquet (s3:// or local)")
    ap.add_argument("--out_pdf", required=True, help="output pdf (local path recommended: docs/report/...)")
    ap.add_argument("--topn", type=int, default=30)
    ap.add_argument("--also_upload_s3", default=None, help="optional s3://... to upload pdf")
    args = ap.parse_args()

    df = read_any(args.scores)

    out_pdf = Path(args.out_pdf)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    with PdfPages(out_pdf) as pdf:
        # Page 1: Overview
        fig = a4_fig()
        page_title(fig, "Atypicality score v0 (speaker×dataset)")

        txt = [
            f"- rows: {len(df):,}",
            f"- datasets: {', '.join([str(x) for x in df['dataset'].unique().tolist()])}",
            "- score: RMS(z) within dataset",
            "- scaler: robust_z (median/MAD) if generated as default",
            "",
            "Output columns:",
            "  dataset, speaker_id, role, n_rows, atypicality_v0, top_contrib_json, is_outlier_p99",
        ]
        fig.text(0.08, 0.90, "\n".join(txt), ha="left", va="top", fontsize=11)

        fig.text(0.08, 0.10,
                 "Note: v0 is a deviation score for pragmatic feature distribution, not a diagnosis.",
                 ha="left", va="bottom", fontsize=9)

        pdf.savefig(fig)
        plt.close(fig)

        # Page 2..: distribution per dataset
        for dataset, g in df.groupby("dataset", dropna=False):
            fig = a4_fig()
            page_title(fig, f"Distribution: {dataset}")

            ax = fig.add_axes([0.12, 0.58, 0.78, 0.30])
            x = g["atypicality_v0"].to_numpy(dtype=float)
            ax.hist(x[np.isfinite(x)], bins=50)
            ax.set_xlabel("atypicality_v0")
            ax.set_ylabel("count")

            stats = {
                "n": int(len(g)),
                "mean": float(np.nanmean(x)),
                "std": float(np.nanstd(x)),
                "p50": float(np.nanpercentile(x, 50)),
                "p90": float(np.nanpercentile(x, 90)),
                "p95": float(np.nanpercentile(x, 95)),
                "p99": float(np.nanpercentile(x, 99)),
                "max": float(np.nanmax(x)),
            }
            fig.text(0.12, 0.52, json.dumps(stats, ensure_ascii=False, indent=2),
                     ha="left", va="top", fontsize=10, family="monospace")

            # TopN table
            top = g.sort_values("atypicality_v0", ascending=False).head(args.topn).copy()
            top["speaker_id"] = top["speaker_id"].astype(str)
            cols = ["speaker_id", "role", "n_rows", "atypicality_v0", "is_outlier_p99"]
            cols = [c for c in cols if c in top.columns]

            ax2 = fig.add_axes([0.12, 0.10, 0.78, 0.35])
            ax2.axis("off")
            table = ax2.table(
                cellText=top[cols].values.tolist(),
                colLabels=cols,
                loc="upper left",
                cellLoc="left"
            )
            table.auto_set_font_size(False)
            table.set_fontsize(8)
            table.scale(1, 1.2)

            fig.text(0.12, 0.47, f"Top {args.topn} speakers (highest scores)", ha="left", va="top", fontsize=11)

            pdf.savefig(fig)
            plt.close(fig)

        # Last page: How to interpret
        fig = a4_fig()
        page_title(fig, "How to use v0 (next)")

        tips = [
            "1) Pick outliers (p99 or top-N) per dataset.",
            "2) For each outlier, inspect top_contrib_json (features with largest |z|).",
            "3) Then go to analysis/v1/gold=v13/examples and sample representative turns.",
            "4) (Phase3-2) LLM labeling: add functional labels (repair/question/backchannel/topic-shift etc.)",
        ]
        fig.text(0.08, 0.90, "\n".join(tips), ha="left", va="top", fontsize=12)

        pdf.savefig(fig)
        plt.close(fig)

    # optional upload
    if args.also_upload_s3:
        kms = os.environ.get("S3_KMS_KEY_ARN")
        aws_s3_cp(str(out_pdf), args.also_upload_s3, kms)

    print(json.dumps({"out_pdf": str(out_pdf), "uploaded": bool(args.also_upload_s3)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

