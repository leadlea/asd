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
        with tempfile.TemporaryDirectory() as td:
            local = str(Path(td) / "in.parquet")
            subprocess.run(["aws", "s3", "cp", path, local], check=True)
            return pd.read_parquet(local)
    return pd.read_parquet(path)


def robust_center_scale(col: np.ndarray) -> tuple[float, float]:
    """median/MAD -> robust std. all-NaN 安全."""
    v = col[np.isfinite(col)]
    if v.size == 0:
        return 0.0, 1.0
    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med)))
    sd = 1.4826 * mad
    if not np.isfinite(sd) or sd == 0.0:
        sd = float(np.std(v))
    if not np.isfinite(sd) or sd == 0.0:
        sd = 1.0
    return med, sd


def z_center_scale(col: np.ndarray) -> tuple[float, float]:
    v = col[np.isfinite(col)]
    if v.size == 0:
        return 0.0, 1.0
    mu = float(np.mean(v))
    sd = float(np.std(v))
    if not np.isfinite(sd) or sd == 0.0:
        sd = 1.0
    return mu, sd


def pick_feature_cols(df: pd.DataFrame) -> List[str]:
    """
    優先順:
      1) __wmean（table別→join版の本命）
      2) __mean（旧版）
      3) __avg（保険）
    """
    # 数値列だけ
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    # suffix 優先で選ぶ
    for suf in ["__wmean", "__mean", "__avg"]:
        cols = [c for c in num_cols if c.endswith(suf)]
        if cols:
            return cols

    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True, help="speaker_features.parquet (s3:// or local)")
    ap.add_argument("--out", required=True, help="output parquet (s3:// or local)")
    ap.add_argument("--topk", type=int, default=10)
    ap.add_argument("--scaler", choices=["zscore", "robust_z"], default="robust_z")
    args = ap.parse_args()

    df = read_any(args.features)

    # 必須列
    if "dataset" not in df.columns:
        raise RuntimeError(f"features must include 'dataset' column. got cols={list(df.columns)[:50]}")
    if "speaker_id" not in df.columns:
        raise RuntimeError(f"features must include 'speaker_id' column. got cols={list(df.columns)[:50]}")

    feat_cols = pick_feature_cols(df)
    if len(feat_cols) == 0:
        raise RuntimeError(
            "No feature columns found. Expected numeric columns ending with "
            "__wmean (preferred) or __mean or __avg."
        )

    out_rows = []
    for dataset, g in df.groupby("dataset", dropna=False):
        g = g.copy()

        X = g[feat_cols].to_numpy(dtype=float)

        centers = np.zeros(X.shape[1], dtype=float)
        scales = np.ones(X.shape[1], dtype=float)

        for j in range(X.shape[1]):
            col = X[:, j]
            if args.scaler == "robust_z":
                mu, sd = robust_center_scale(col)
            else:
                mu, sd = z_center_scale(col)
            centers[j] = mu
            scales[j] = sd

        Z = (X - centers) / scales
        # RMS(z)
        score = np.sqrt(np.nanmean(Z ** 2, axis=1))

        for i in range(len(g)):
            zrow = Z[i, :]
            absz = np.abs(zrow)

            top_idx = np.argsort(-np.nan_to_num(absz, nan=-1.0))[: args.topk]

            contrib = []
            for j in top_idx:
                if not np.isfinite(absz[j]):
                    continue
                val = X[i, j]
                contrib.append(
                    {
                        "feature": feat_cols[j],
                        "z": float(zrow[j]) if np.isfinite(zrow[j]) else None,
                        "abs_z": float(absz[j]),
                        "value": float(val) if np.isfinite(val) else None,
                    }
                )

            rec = {
                "dataset": dataset,
                "speaker_id": g.iloc[i]["speaker_id"],
                "n_utt_total": int(g.iloc[i]["n_utt_total"]) if "n_utt_total" in g.columns and pd.notna(g.iloc[i]["n_utt_total"]) else None,
                "n_pairs_total": int(g.iloc[i]["n_pairs_total"]) if "n_pairs_total" in g.columns and pd.notna(g.iloc[i]["n_pairs_total"]) else None,
                "atypicality_v0": float(score[i]) if np.isfinite(score[i]) else None,
                "top_contrib_json": json.dumps(contrib, ensure_ascii=False),
            }
            out_rows.append(rec)

    out = pd.DataFrame(out_rows)

    # datasetごとのp99
    out["is_outlier_p99"] = False
    for dataset, g in out.groupby("dataset", dropna=False):
        x = g["atypicality_v0"].to_numpy(dtype=float)
        x = x[np.isfinite(x)]
        if x.size == 0:
            continue
        thr = float(np.nanpercentile(x, 99))
        out.loc[g.index, "is_outlier_p99"] = out.loc[g.index, "atypicality_v0"] >= thr

    kms = os.environ.get("S3_KMS_KEY_ARN")
    if is_s3(args.out):
        with tempfile.TemporaryDirectory() as td:
            local_out = str(Path(td) / "atypicality_v0.parquet")
            out.to_parquet(local_out, index=False)
            aws_s3_cp(local_out, args.out, kms)
    else:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(args.out, index=False)

    print(json.dumps(
        {
            "rows": int(len(out)),
            "out": args.out,
            "datasets": sorted([str(x) for x in out["dataset"].unique().tolist()]),
            "scaler": args.scaler,
            "topk": args.topk,
            "n_features": len(feat_cols),
            "feature_suffix_used": ("__wmean" if any(c.endswith("__wmean") for c in feat_cols)
                                   else "__mean" if any(c.endswith("__mean") for c in feat_cols)
                                   else "__avg"),
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()

