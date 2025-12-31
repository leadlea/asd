# scripts/phase3/compute_atypicality_v0.py
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List

import numpy as np
import pandas as pd


def is_s3(path: str) -> bool:
    return path.startswith("s3://")


def aws_s3_cp(local_path: str, s3_path: str, kms_key_arn: Optional[str]) -> None:
    cmd = ["aws", "s3", "cp", local_path, s3_path]
    if kms_key_arn:
        cmd += ["--sse", "aws:kms", "--sse-kms-key-id", kms_key_arn]
    subprocess.run(cmd, check=True)


def read_any(path: str) -> pd.DataFrame:
    if is_s3(path):
        # aws s3 cp で一旦落とす（依存を減らす）
        with tempfile.TemporaryDirectory() as td:
            local = str(Path(td) / "in.parquet")
            subprocess.run(["aws", "s3", "cp", path, local], check=True)
            return pd.read_parquet(local)
    return pd.read_parquet(path)


def robust_mean_std(x: np.ndarray) -> tuple[float, float]:
    """
    median/MAD ベースの robust z
    std ≈ 1.4826 * MAD
    """
    med = np.nanmedian(x)
    mad = np.nanmedian(np.abs(x - med))
    std = 1.4826 * mad
    # 0割回避
    if not np.isfinite(std) or std == 0.0:
        std = np.nanstd(x)
    if not np.isfinite(std) or std == 0.0:
        std = 1.0
    return float(med), float(std)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True, help="speaker_features.parquet (s3:// or local)")
    ap.add_argument("--out", required=True, help="output parquet (s3:// or local)")
    ap.add_argument("--topk", type=int, default=10)
    ap.add_argument("--scaler", choices=["zscore", "robust_z"], default="robust_z")
    args = ap.parse_args()

    df = read_any(args.features)

    id_cols = [c for c in ["dataset", "speaker_id", "role", "n_rows"] if c in df.columns]

    # v0は mean 系だけでスコアを作る（std列は説明用に残っててもOK）
    feat_cols = [c for c in df.columns if c.endswith("__mean") and c not in id_cols]

    if len(feat_cols) == 0:
        raise RuntimeError("No feature columns found (expected *__mean).")

    out_rows = []
    for dataset, g in df.groupby("dataset", dropna=False):
        g = g.copy()
        X = g[feat_cols].to_numpy(dtype=float)

        centers = np.zeros(X.shape[1], dtype=float)
        scales = np.ones(X.shape[1], dtype=float)

        for j in range(X.shape[1]):
            col = X[:, j]
            if args.scaler == "robust_z":
                mu, sd = robust_mean_std(col)
            else:
                mu = float(np.nanmean(col))
                sd = float(np.nanstd(col))
                if not np.isfinite(sd) or sd == 0.0:
                    sd = 1.0
            centers[j] = mu
            scales[j] = sd

        Z = (X - centers) / scales
        # RMS(z)
        score = np.sqrt(np.nanmean(Z ** 2, axis=1))

        for i in range(len(g)):
            zrow = Z[i, :]
            absz = np.abs(zrow)
            top_idx = np.argsort(-absz)[: args.topk]
            contrib = [
                {
                    "feature": feat_cols[j],
                    "z": float(zrow[j]),
                    "abs_z": float(absz[j]),
                    "value": float(X[i, j]),
                }
                for j in top_idx
                if np.isfinite(absz[j])
            ]

            rec = {
                "dataset": dataset,
                "speaker_id": g.iloc[i]["speaker_id"] if "speaker_id" in g.columns else None,
                "role": g.iloc[i]["role"] if "role" in g.columns else None,
                "n_rows": int(g.iloc[i]["n_rows"]) if "n_rows" in g.columns else None,
                "atypicality_v0": float(score[i]),
                "top_contrib_json": json.dumps(contrib, ensure_ascii=False),
            }
            out_rows.append(rec)

    out = pd.DataFrame(out_rows)

    # しきい値などの “使いやすい列” も追加（v0）
    out["is_outlier_p99"] = False
    for dataset, g in out.groupby("dataset", dropna=False):
        thr = float(np.nanpercentile(g["atypicality_v0"].to_numpy(), 99))
        out.loc[g.index, "is_outlier_p99"] = g["atypicality_v0"] >= thr

    kms = os.environ.get("S3_KMS_KEY_ARN")
    if is_s3(args.out):
        with tempfile.TemporaryDirectory() as td:
            local_out = str(Path(td) / "atypicality_v0.parquet")
            out.to_parquet(local_out, index=False)
            aws_s3_cp(local_out, args.out, kms)
    else:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(args.out, index=False)

    print(json.dumps({
        "rows": int(len(out)),
        "out": args.out,
        "datasets": sorted([str(x) for x in out["dataset"].unique().tolist()]),
        "scaler": args.scaler,
        "topk": args.topk,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

