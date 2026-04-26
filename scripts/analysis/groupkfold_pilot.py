#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pilot: GroupKFold (subject-wise) vs KFold (observation-wise) comparison.

Compare permutation test results between:
  - KFold (observation-wise): current implementation
  - GroupKFold (subject-wise): same speaker never in both train and test

Usage:
    python scripts/analysis/groupkfold_pilot.py \
        --xy_parquet artifacts/analysis/datasets/cejc_home2_hq1_XY_Conly_sonnet.parquet \
        --y_col Y_C \
        --metadata_tsv artifacts/analysis/cejc_speaker_metadata.tsv
"""
from __future__ import annotations

import argparse
import time

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold, KFold
from sklearn.preprocessing import StandardScaler

# 19 explanatory features (same as confound_analysis.py)
ALL_FEATURES = [
    "PG_speech_ratio", "PG_pause_mean", "PG_pause_p50", "PG_pause_p90",
    "PG_resp_gap_mean", "PG_resp_gap_p50", "PG_resp_gap_p90", "PG_overlap_rate",
    "FILL_has_any", "FILL_rate_per_100chars",
    "IX_oirmarker_rate", "IX_oirmarker_after_question_rate",
    "IX_yesno_rate", "IX_yesno_after_question_rate", "IX_lex_overlap_mean",
    "RESP_NE_AIZUCHI_RATE", "RESP_NE_ENTROPY", "RESP_YO_ENTROPY",
    "PG_pause_variability",
]


def pearsonr(a, b) -> float:
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    a = a - a.mean()
    b = b - b.mean()
    den = np.sqrt((a * a).sum()) * np.sqrt((b * b).sum())
    return float((a * b).sum() / den) if den != 0 else float("nan")


def cv_ridge_r(X, y, splits, seed, alpha, groups=None):
    """CV Ridge regression with optional GroupKFold."""
    if groups is not None:
        kf = GroupKFold(n_splits=splits)
        split_iter = kf.split(X, y, groups)
    else:
        kf = KFold(n_splits=splits, shuffle=True, random_state=seed)
        split_iter = kf.split(X)

    rs = []
    for tr, te in split_iter:
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


def run_permutation(X, y, splits, seed, alpha, n_perm, groups=None):
    r_obs = cv_ridge_r(X, y, splits, seed, alpha, groups)

    rng = np.random.default_rng(seed)
    r_perm = np.empty(n_perm, float)
    for i in range(n_perm):
        yp = rng.permutation(y)
        r_perm[i] = cv_ridge_r(X, yp, splits, seed, alpha, groups)

    p = (np.sum(np.abs(r_perm) >= abs(r_obs)) + 1.0) / (n_perm + 1.0)
    return r_obs, p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xy_parquet", required=True)
    ap.add_argument("--y_col", default="Y_C")
    ap.add_argument("--metadata_tsv", default="artifacts/analysis/cejc_speaker_metadata.tsv")
    ap.add_argument("--alpha", type=float, default=100.0)
    ap.add_argument("--cv_folds", type=int, default=5)
    ap.add_argument("--n_perm", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    # Load data
    df = pd.read_parquet(args.xy_parquet).replace([np.inf, -np.inf], np.nan)
    meta = pd.read_csv(args.metadata_tsv, sep="\t")
    merged = df.merge(
        meta[["conversation_id", "speaker_id", "cejc_person_id"]],
        on=["conversation_id", "speaker_id"],
        how="left",
    )

    y = merged[args.y_col].astype(float).to_numpy()
    X = merged[ALL_FEATURES].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    groups = merged["cejc_person_id"].to_numpy()

    print(f"N={len(y)}, unique_speakers={len(set(groups))}, features={X.shape[1]}")
    print(f"alpha={args.alpha}, folds={args.cv_folds}, n_perm={args.n_perm}")
    print()

    # --- KFold (observation-wise) ---
    print("=" * 50)
    print("  KFold (observation-wise) — current implementation")
    print("=" * 50)
    t0 = time.time()
    r_kf, p_kf = run_permutation(X, y, args.cv_folds, args.seed, args.alpha, args.n_perm, groups=None)
    t_kf = time.time() - t0
    print(f"  r = {r_kf:.4f}, p = {p_kf:.4f}  ({t_kf:.1f}s)")

    # --- GroupKFold (subject-wise) ---
    print()
    print("=" * 50)
    print("  GroupKFold (subject-wise) — proposed fix")
    print("=" * 50)
    t0 = time.time()
    r_gkf, p_gkf = run_permutation(X, y, args.cv_folds, args.seed, args.alpha, args.n_perm, groups=groups)
    t_gkf = time.time() - t0
    print(f"  r = {r_gkf:.4f}, p = {p_gkf:.4f}  ({t_gkf:.1f}s)")

    # --- Summary ---
    print()
    print("=" * 50)
    print("  COMPARISON")
    print("=" * 50)
    print(f"  KFold:      r={r_kf:.4f}, p={p_kf:.4f}")
    print(f"  GroupKFold: r={r_gkf:.4f}, p={p_gkf:.4f}")
    print(f"  Δr = {r_gkf - r_kf:+.4f}")
    sig_kf = "**" if p_kf < 0.05 else "n.s."
    sig_gkf = "**" if p_gkf < 0.05 else "n.s."
    print(f"  KFold: {sig_kf}, GroupKFold: {sig_gkf}")


if __name__ == "__main__":
    main()
