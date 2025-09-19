#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Baseline classifier for ASD vs TD with pragmatic/prosodic features.

機能:
- 数値列のみ抽出し、全欠損/高欠損(>50%)/定数列を自動除外
- SimpleImputer(median) + StandardScaler + LogisticRegression で学習
- データ件数・クラス比に応じて n_splits を自動調整（最低2分割）
- データ不足時は係数ではなく特徴量の平均“規模感”で暫定可視化
- --exclude_cols で age / len_tokens などを一時的に除外可能
- JSON レポートと寄与図(png)を保存

使い方:
python -m src.models.baseline \
  --feat_csv data/processed/features_merged.csv \
  --report_json reports/baseline_report.json \
  --exclude_cols "age,len_tokens"
"""

import argparse
import json
import os
from typing import List, Dict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--feat_csv", required=True, help="Merged feature CSV")
    ap.add_argument("--report_json", required=True, help="Path to write report JSON")
    ap.add_argument(
        "--exclude_cols",
        default="",
        help="Comma-separated column names to drop before training (e.g., 'age,len_tokens')",
    )
    ap.add_argument(
        "--fig_path",
        default="reports/figures/top_features.png",
        help="Path to save top-features bar plot",
    )
    ap.add_argument(
        "--high_nan_threshold",
        type=float,
        default=0.5,
        help="Drop numeric columns with NaN ratio > threshold (default 0.5).",
    )
    ap.add_argument(
        "--topk",
        type=int,
        default=12,
        help="Number of top features to visualize (default 12).",
    )
    return ap.parse_args()


def auto_n_splits(y: np.ndarray) -> int:
    n = len(y)
    pos = int(y.sum())
    neg = n - pos
    if n < 2:
        return 0
    max_by_class = min(pos if pos > 0 else n, neg if neg > 0 else n)
    return max(0, min(5, n, max_by_class))


def drop_bad_columns(num_df: pd.DataFrame, high_nan_threshold: float) -> Dict[str, List[str]]:
    info = {"all_nan": [], "high_nan": [], "constant": []}

    # 全欠損
    all_nan_cols = num_df.columns[num_df.isna().all()].tolist()
    if all_nan_cols:
        info["all_nan"] = all_nan_cols
        num_df.drop(columns=all_nan_cols, inplace=True, errors="ignore")

    # 高欠損
    nan_rate = num_df.isna().mean()
    high_nan_cols = nan_rate[nan_rate > high_nan_threshold].index.tolist()
    if high_nan_cols:
        info["high_nan"] = high_nan_cols
        num_df.drop(columns=high_nan_cols, inplace=True, errors="ignore")

    # 定数列
    nunique = num_df.nunique(dropna=True)
    const_cols = nunique[nunique <= 1].index.tolist()
    if const_cols:
        info["constant"] = const_cols
        num_df.drop(columns=const_cols, inplace=True, errors="ignore")

    return info


def main():
    args = parse_args()

    # 1) 入力取得
    df = pd.read_csv(args.feat_csv)
    if "label" not in df.columns:
        raise SystemExit("ERROR: 'label' 列が見つかりません。meta結合を確認してください。")

    # 2) ラベル作成
    y = (df["label"].astype(str).str.upper() == "ASD").astype(int).values

    # 3) 数値列のみ抽出 + 任意の列を除外
    num = df.select_dtypes(include=[np.number]).copy()

    user_excl = [c.strip() for c in args.exclude_cols.split(",") if c.strip()]
    drop_user = [c for c in user_excl if c in num.columns]
    if drop_user:
        num.drop(columns=drop_user, inplace=True, errors="ignore")

    # 欠損・定数列の自動除外
    removed_info = drop_bad_columns(num, args.high_nan_threshold)

    cols = num.columns.tolist()
    X = num.values

    report = {
        "n_samples": int(len(df)),
        "class_counts": {"ASD": int(y.sum()), "TD": int((y == 0).sum())},
        "removed_columns": removed_info,
        "excluded_columns": drop_user,
        "used_feature_count": int(len(cols)),
        "used_features": cols,
    }

    # 4) CV設定
    splits = auto_n_splits(y)
    report["n_splits"] = int(splits)

    # 5) 学習 or フォールバック
    if splits >= 2 and X.shape[1] > 0:
        skf = StratifiedKFold(n_splits=splits, shuffle=True, random_state=42)
        aucs, f1s, coefs = [], [], []

        for tr, te in skf.split(X, y):
            pipe = make_pipeline(
                SimpleImputer(strategy="median"),
                StandardScaler(),
                LogisticRegression(max_iter=200),
            )
            pipe.fit(X[tr], y[tr])
            p = pipe.predict_proba(X[te])[:, 1]
            aucs.append(roc_auc_score(y[te], p))
            f1s.append(f1_score(y[te], (p > 0.5).astype(int)))

            # 係数を元スケールへ（標準化のスケールで割る）
            clf = pipe.named_steps["logisticregression"]
            sc = pipe.named_steps["standardscaler"]
            coef = clf.coef_[0] / (sc.scale_ + 1e-9)
            coefs.append(coef)

        coef_mean = np.mean(coefs, axis=0)
        top_idx = np.argsort(-np.abs(coef_mean))[: args.topk]
        top_feats = [cols[i] for i in top_idx]
        top_vals = coef_mean[top_idx].tolist()

        report.update(
            {
                "cv_auc_mean": float(np.mean(aucs)),
                "cv_f1_mean": float(np.mean(f1s)),
                "mode": "cv_coefficients",
                "top_features": [{"name": n, "coef": float(v)} for n, v in zip(top_feats, top_vals)],
            }
        )

    else:
        # データ不足 or 特徴ゼロ → 暫定可視化（欠損は0埋め、平均の規模感で並べる）
        Xi = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        vals = Xi.mean(axis=0) if (len(Xi) > 0 and Xi.size > 0) else np.zeros(len(cols))

        top_idx = np.argsort(-np.abs(vals))[: args.topk]
        top_feats = [cols[i] for i in top_idx]
        top_vals = [float(vals[i]) for i in top_idx]

        report.update(
            {
                "cv_auc_mean": None,
                "cv_f1_mean": None,
                "mode": "magnitude_fallback",
                "note": "Insufficient samples/classes for CV or no usable features; showing magnitude fallback.",
                "top_features": [{"name": n, "coef_like": v} for n, v in zip(top_feats, top_vals)],
            }
        )

    # 6) 図を保存
    os.makedirs(os.path.dirname(args.fig_path), exist_ok=True)
    plt.figure()
    plt.barh(top_feats[::-1], top_vals[::-1])
    title = "Top feature contributions (logistic coeff.)" if report["mode"] == "cv_coefficients" else "Top features (magnitude fallback)"
    plt.title(title)
    plt.tight_layout()
    plt.savefig(args.fig_path, dpi=160)

    # 7) レポート保存
    os.makedirs(os.path.dirname(args.report_json), exist_ok=True)
    with open(args.report_json, "w") as f:
        json.dump(report, f, indent=2)

    print(f"saved report -> {args.report_json}")
    print(f"saved fig    -> {args.fig_path}")


if __name__ == "__main__":
    main()
