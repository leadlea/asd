#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ensemble Big5 Permutation Test.

Compute ensemble Big5 scores by averaging trait_score across 4 LLM teachers,
then run Ridge + Permutation test for all 5 traits (O, C, E, A, N).

Usage:
    python scripts/analysis/ensemble_permutation.py \
        --items_dir artifacts/big5/llm_scores \
        --features_parquet artifacts/analysis/features_min/features_cejc_home2_hq1.parquet \
        --out_dir artifacts/analysis/results/ensemble_perm
"""
from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler

# ── Constants ────────────────────────────────────────────────────────
TRAITS = ["O", "C", "E", "A", "N"]
TEACHERS = ["sonnet4", "qwen3-235b", "deepseek-v3", "gpt-oss-120b"]


# ── Core functions (same logic as permutation_test_ridge_fixedalpha.py) ──
def pearsonr(a, b) -> float:
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    a = a - a.mean()
    b = b - b.mean()
    den = np.sqrt((a * a).sum()) * np.sqrt((b * b).sum())
    return float((a * b).sum() / den) if den != 0 else float("nan")


def cv_ridge_r(X, y, folds, seed, alpha):
    kf = KFold(n_splits=folds, shuffle=True, random_state=seed)
    rs = []
    for tr, te in kf.split(X):
        Xtr, Xte = X[tr], X[te]
        ytr, yte = y[tr], y[te]

        imp = SimpleImputer(strategy="median")
        Xtr = imp.fit_transform(Xtr)
        Xte = imp.transform(Xte)

        sc = StandardScaler()
        Xtr = sc.fit_transform(Xtr)
        Xte = sc.transform(Xte)

        m = Ridge(alpha=alpha, random_state=seed)
        m.fit(Xtr, ytr)
        yh = m.predict(Xte)
        rs.append(pearsonr(yte, yh))
    return float(np.mean(rs))


# ── Data loading ─────────────────────────────────────────────────────
def load_trait_scores(items_dir: str, trait: str, teachers: list[str]) -> pd.DataFrame:
    """Load trait scores from all available teachers and average across them.

    Returns a DataFrame with columns: conversation_id, speaker_id, trait_score
    (averaged across teachers).
    """
    dfs = []
    for teacher in teachers:
        dir_name = f"dataset=cejc_home2_hq1_v1__items={trait}24__teacher={teacher}"
        merged_dir = Path(items_dir) / dir_name / "teacher_merged"
        parquet_path = merged_dir / f"trait_scores_{trait}_merged.parquet"

        if not parquet_path.exists():
            warnings.warn(
                f"Missing parquet for teacher={teacher}, trait={trait}: {parquet_path}"
            )
            continue

        df = pd.read_parquet(parquet_path)
        # Expect columns: conversation_id, speaker_id, trait, model_id, trait_score
        df = df[["conversation_id", "speaker_id", "trait_score"]].copy()
        df = df.rename(columns={"trait_score": f"score_{teacher}"})
        dfs.append(df)

    if not dfs:
        raise FileNotFoundError(
            f"No teacher parquets found for trait={trait} in {items_dir}"
        )

    n_teachers = len(dfs)
    if n_teachers < len(teachers):
        warnings.warn(
            f"trait={trait}: only {n_teachers}/{len(teachers)} teachers available"
        )

    # Merge all teachers on (conversation_id, speaker_id)
    merged = dfs[0]
    for df in dfs[1:]:
        merged = merged.merge(df, on=["conversation_id", "speaker_id"], how="inner")

    # Average trait_score across teachers
    score_cols = [c for c in merged.columns if c.startswith("score_")]
    merged["trait_score"] = merged[score_cols].mean(axis=1)

    return merged[["conversation_id", "speaker_id", "trait_score"]].copy()


# ── Main ─────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(
        description="Ensemble Big5 Permutation Test (4-teacher average)"
    )
    ap.add_argument(
        "--items_dir",
        default="artifacts/big5/llm_scores",
        help="Root dir containing dataset=...items=...teacher=... folders",
    )
    ap.add_argument(
        "--features_parquet",
        default="artifacts/analysis/features_min/features_cejc_home2_hq1.parquet",
        help="Path to features parquet",
    )
    ap.add_argument("--exclude_cols", default="", help="Extra columns to exclude (comma-separated)")
    ap.add_argument("--alpha", type=float, default=100.0, help="Ridge alpha")
    ap.add_argument("--cv_folds", type=int, default=5, help="CV folds")
    ap.add_argument("--n_perm", type=int, default=5000, help="Permutation rounds")
    ap.add_argument("--seed", type=int, default=42, help="Random seed")
    ap.add_argument("--out_dir", required=True, help="Output directory")
    args = ap.parse_args()

    # Load features
    feat_df = pd.read_parquet(args.features_parquet)
    feat_df = feat_df.replace([np.inf, -np.inf], np.nan)

    # Columns to exclude from features
    excl = set(c.strip() for c in args.exclude_cols.split(",") if c.strip())
    excl |= {"conversation_id", "speaker_id"}

    summary_rows = []

    for trait in TRAITS:
        print(f"\n{'='*60}")
        print(f"  Trait: {trait}")
        print(f"{'='*60}")

        # 1. Load and average trait scores across teachers
        scores_df = load_trait_scores(args.items_dir, trait, TEACHERS)
        print(f"  Ensemble scores: {len(scores_df)} rows")

        # 2. Merge with features
        merged = scores_df.merge(feat_df, on=["conversation_id", "speaker_id"], how="inner")
        if len(merged) < len(scores_df):
            warnings.warn(
                f"trait={trait}: join reduced rows from {len(scores_df)} to {len(merged)}"
            )
        print(f"  After join with features: {len(merged)} rows")

        # 3. Prepare X, y
        y_col = "trait_score"
        y = merged[y_col].astype(float).to_numpy()

        feat_cols = [
            c for c in merged.columns if c not in excl and c != y_col
        ]
        # Validate feature columns exist
        missing = [c for c in feat_cols if c not in merged.columns]
        if missing:
            raise KeyError(f"Missing feature columns: {missing}")

        X = merged[feat_cols].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)

        # Drop rows with NaN in y
        ok = ~np.isnan(y)
        X = X[ok]
        y = y[ok]
        print(f"  Features: {X.shape[1]} cols, {X.shape[0]} samples")

        # 4. Observed r
        r_obs = cv_ridge_r(X, y, args.cv_folds, args.seed, args.alpha)
        print(f"  r_obs = {r_obs:.3f}")

        # 5. Permutation test
        rng = np.random.default_rng(args.seed)
        r_perm = np.empty(args.n_perm, float)
        for i in range(args.n_perm):
            yp = rng.permutation(y)
            r_perm[i] = cv_ridge_r(X, yp, args.cv_folds, args.seed, args.alpha)
            if (i + 1) % 500 == 0:
                print(f"    perm {i+1}/{args.n_perm} done")

        p_val = (np.sum(np.abs(r_perm) >= abs(r_obs)) + 1.0) / (args.n_perm + 1.0)
        print(f"  p(|r|) = {p_val:.4f}  (n_perm={args.n_perm})")

        # 6. Write permutation.log
        trait_dir = Path(args.out_dir) / f"ensemble_{trait}"
        trait_dir.mkdir(parents=True, exist_ok=True)
        log_path = trait_dir / "permutation.log"
        with open(log_path, "w") as f:
            f.write(f"alpha={args.alpha}\n")
            f.write(f"r_obs={r_obs:.3f}\n")
            f.write(f"p(|r|)={p_val:.4f}  (n_perm={args.n_perm})\n")
        print(f"  Wrote {log_path}")

        summary_rows.append({"trait": trait, "r_obs": round(r_obs, 3), "p_value": round(p_val, 4)})

    # 7. Write ensemble_summary.tsv
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_df = pd.DataFrame(summary_rows)
    summary_path = out_dir / "ensemble_summary.tsv"
    summary_df.to_csv(summary_path, sep="\t", index=False)
    print(f"\nWrote {summary_path}")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
