# scripts/phase3/make_atypicality_report_pdf.py
from __future__ import annotations

import argparse
import json
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


def fmt_stats(stats: dict) -> str:
    # 読みやすい固定順
    keys = ["n", "mean", "std", "p50", "p90", "p95", "p99", "max"]
    lines = ["{"]
    for k in keys:
        v = stats.get(k)
        if isinstance(v, float):
            lines.append(f'  "{k}": {v:.6g},')
        else:
            lines.append(f'  "{k}": {v},')
    if len(lines) > 1:
        lines[-1] = lines[-1].rstrip(",")
    lines.append("}")
    return "\n".join(lines)


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

    # 文字化け/埋め込み安定化（環境差が出にくい）
    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["ps.fonttype"] = 42

    with PdfPages(out_pdf) as pdf:
        # -------------------------
        # Page 1: Overview
        # -------------------------
        fig = a4_fig()
        page_title(fig, "Atypicality score v0 (speaker×dataset)")

        datasets = [str(x) for x in df["dataset"].unique().tolist()]
        txt = [
            f"- rows: {len(df):,}",
            f"- datasets: {', '.join(datasets)}",
            "- score: RMS(z) within dataset",
            "- scaler: robust_z (median/MAD) if generated as default",
            "",
            "Output columns:",
            "  dataset, speaker_id, role, n_rows, atypicality_v0, top_contrib_json, is_outlier_p99",
        ]
        fig.text(0.08, 0.90, "\n".join(txt), ha="left", va="top", fontsize=11)
        fig.text(
            0.08, 0.10,
            "Note: v0 is a deviation score for pragmatic feature distribution, not a diagnosis.",
            ha="left", va="bottom", fontsize=9
        )
        pdf.savefig(fig)
        plt.close(fig)

        # -------------------------
        # Per-dataset pages
        #   Page A: Distribution + stats
        #   Page B: Top-N table (full page)
        # -------------------------
        for dataset, g in df.groupby("dataset", dropna=False):
            x = g["atypicality_v0"].to_numpy(dtype=float)
            x = x[np.isfinite(x)]

            # Page A
            fig = a4_fig()
            page_title(fig, f"Distribution: {dataset}")

            ax = fig.add_axes([0.12, 0.55, 0.78, 0.30])
            ax.hist(x, bins=50)
            ax.set_xlabel("atypicality_v0")
            ax.set_ylabel("count")

            stats = {
                "n": int(len(g)),
                "mean": float(np.nanmean(x)) if len(x) else float("nan"),
                "std": float(np.nanstd(x)) if len(x) else float("nan"),
                "p50": float(np.nanpercentile(x, 50)) if len(x) else float("nan"),
                "p90": float(np.nanpercentile(x, 90)) if len(x) else float("nan"),
                "p95": float(np.nanpercentile(x, 95)) if len(x) else float("nan"),
                "p99": float(np.nanpercentile(x, 99)) if len(x) else float("nan"),
                "max": float(np.nanmax(x)) if len(x) else float("nan"),
            }

            fig.text(
                0.12, 0.48,
                fmt_stats(stats),
                ha="left", va="top", fontsize=10, family="monospace"
            )
            fig.text(
                0.12, 0.18,
                "Next: see the next page for Top-N speakers table.",
                ha="left", va="top", fontsize=10
            )

            pdf.savefig(fig)
            plt.close(fig)

            # Page B: table only (崩れ対策の本丸)
            fig = a4_fig()
            page_title(fig, f"Top {args.topn} speakers: {dataset}")

            top = g.sort_values("atypicality_v0", ascending=False).head(args.topn).copy()

            # 表に出す列（存在するものだけ）
            cols = ["speaker_id", "role", "n_rows", "atypicality_v0", "is_outlier_p99"]
            cols = [c for c in cols if c in top.columns]

            # 表示用の整形（桁・Noneなど）
            if "speaker_id" in top.columns:
                top["speaker_id"] = top["speaker_id"].astype(str)
            if "role" in top.columns:
                top["role"] = top["role"].fillna("").astype(str)
            if "n_rows" in top.columns:
                top["n_rows"] = top["n_rows"].fillna(0).astype(int)
            if "atypicality_v0" in top.columns:
                top["atypicality_v0"] = top["atypicality_v0"].astype(float).map(lambda v: f"{v:.6g}")
            if "is_outlier_p99" in top.columns:
                top["is_outlier_p99"] = top["is_outlier_p99"].astype(bool).map(lambda b: "True" if b else "False")

            ax2 = fig.add_axes([0.06, 0.06, 0.88, 0.86])
            ax2.axis("off")

            table = ax2.table(
                cellText=top[cols].values.tolist(),
                colLabels=cols,
                loc="upper left",
                cellLoc="left",
                bbox=[0.0, 0.0, 1.0, 1.0],  # ★軸内に強制フィット（はみ出し防止）
            )
            table.auto_set_font_size(False)
            table.set_fontsize(8)
            # 少しだけ縦を詰める（行が多い時の崩れ防止）
            table.scale(1.0, 1.05)

            pdf.savefig(fig)
            plt.close(fig)

        # -------------------------
        # Last page: How to interpret
        # -------------------------
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

    if args.also_upload_s3:
        import os
        kms = os.environ.get("S3_KMS_KEY_ARN")
        aws_s3_cp(str(out_pdf), args.also_upload_s3, kms)

    print(json.dumps({"out_pdf": str(out_pdf), "uploaded": bool(args.also_upload_s3)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

