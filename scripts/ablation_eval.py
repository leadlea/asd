# scripts/ablation_eval.py
from __future__ import annotations

import argparse
import pathlib
from typing import List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from runlog_util import append_changelog, write_run_json


def cv_scores(X, y, pipe, threshold: float, n_splits=5, seed=42):
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    aucs, f1s = [], []
    for tr, te in skf.split(X, y):
        pipe.fit(X[tr], y[tr])
        prob = pipe.predict_proba(X[te])[:, 1]
        pred = (prob >= threshold).astype(int)
        # AUC は常に計算（単一クラスにはならない前提の通常CV）
        aucs.append(roc_auc_score(y[te], prob))
        f1s.append(f1_score(y[te], pred, zero_division=0))
    return float(np.mean(aucs)), float(np.mean(f1s))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--feat_csv", required=True)
    ap.add_argument("--out_json", default="reports/ablation_report.json")
    ap.add_argument("--out_png", default="reports/figures/ablation_delta.png")
    ap.add_argument("--threshold", type=float, default=0.5,
                    help="決定しきい値（例: 0.55）。未指定なら0.5。")
    ap.add_argument("--splits", type=int, default=5)
    args = ap.parse_args()

    df = pd.read_csv(args.feat_csv)
    if "label" not in df.columns:
        raise SystemExit("CSV must include 'label'.")

    y = df["label"].map({"ASD": 1, "TD": 0}).values
    meta = {"label", "file_id", "age", "task_type", "corpus"}
    num_cols: List[str] = [
        c for c in df.columns if c not in meta and pd.api.types.is_numeric_dtype(df[c])
    ]
    # --- Robustness: drop all-NaN columns and constants (avoid imputer warnings) ---
    num_cols = [c for c in num_cols if df[c].notna().any()]
    num_cols = [c for c in num_cols if df[c].nunique(dropna=True) > 1]
    # （念のため）意図せず混入した 'cohort' を強制除外
    if "cohort" in num_cols:
        num_cols.remove("cohort")

    pipe = Pipeline(
        [
            ("imp", SimpleImputer(strategy="median")),
            ("sc", StandardScaler()),
            ("lr", LogisticRegression(max_iter=2000, class_weight="balanced")),
        ]
    )

    # Full model
    X_full = df[num_cols].values
    base_auc, base_f1 = cv_scores(
        X_full, y, pipe, threshold=args.threshold, n_splits=args.splits
    )

    rows = []
    for feat in num_cols:
        drop_cols = [c for c in num_cols if c != feat]
        X = df[drop_cols].values
        auc, f1 = cv_scores(
            X, y, pipe, threshold=args.threshold, n_splits=args.splits
        )
        rows.append(
            {
                "feature": feat,
                "auc_drop": base_auc - auc,
                "f1_drop": base_f1 - f1,
                "auc": auc,
                "f1": f1,
            }
        )
    rows.sort(key=lambda r: (r["auc_drop"], r["f1_drop"]), reverse=True)

    report = {
        "mode": "ablation_leave1out",
        "n_features": len(num_cols),
        "base_auc": base_auc,
        "base_f1": base_f1,
        "threshold": args.threshold,
        "rows": rows[:50],
    }
    write_run_json(report, args.out_json)

    # Plot
    top = rows[:15]
    labels = [r["feature"] for r in top]
    deltas = [r["auc_drop"] for r in top]
    pathlib.Path(args.out_png).parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 6))
    y_pos = range(len(labels))
    plt.barh(y_pos, deltas)
    plt.yticks(y_pos, labels)
    plt.gca().invert_yaxis()
    plt.title("Ablation ΔAUC (higher = more important)")
    plt.xlabel("ΔAUC (base - ablated)")
    plt.tight_layout()
    plt.savefig(args.out_png, dpi=180)
    plt.close()

    append_changelog(
        {
            "title": "Feature ablation (leave-1-out)",
            "notes": f"Base AUC={base_auc:.3f}, F1={base_f1:.3f}, thr={args.threshold} | Features={len(num_cols)} | splits={args.splits}",
            "metrics": {"AUC": base_auc, "F1": base_f1},
            "params": {
                "feat_csv": args.feat_csv,
                "out_json": args.out_json,
                "threshold": args.threshold,
                "splits": args.splits,
            },
        }
    )


if __name__ == "__main__":
    main()
