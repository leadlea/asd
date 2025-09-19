# scripts/loco_eval.py  （group-norm 対応 完全版）
from __future__ import annotations
import argparse, pathlib, re
from typing import Iterable, Tuple, Optional
import numpy as np, pandas as pd
import matplotlib.pyplot as plt

from sklearn.calibration import CalibratedClassifierCV
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, f1_score, balanced_accuracy_score, matthews_corrcoef
from sklearn.model_selection import LeaveOneGroupOut, StratifiedGroupKFold, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from runlog_util import append_changelog, write_run_json

# ---------- helpers ----------
def guess_corpus_from_file_id(fid: str) -> str:
    s = str(fid)
    if "/" in s:  # e.g., "Brown/ASD_xxx"
        return s.split("/")[0]
    m = re.match(r"^(ASD|TD)_([A-Za-z0-9]+)_", s)
    return m.group(2) if m else "Unknown"

def derive_groups(df: pd.DataFrame) -> pd.Series:
    if "corpus" in df.columns and df["corpus"].nunique(dropna=True) >= 2:
        return df["corpus"]
    return df["file_id"].map(guess_corpus_from_file_id)

def has_both_classes(y_subset: np.ndarray) -> bool:
    return len(np.unique(y_subset)) == 2

def select_numeric_features(df: pd.DataFrame) -> list[str]:
    meta = {"label","file_id","age","task_type","corpus"}
    return [c for c in df.columns if c not in meta and pd.api.types.is_numeric_dtype(df[c])]

def base_pipeline() -> Pipeline:
    return Pipeline([
        ("imp", SimpleImputer(strategy="median")),
        ("sc",  StandardScaler()),
        ("lr",  LogisticRegression(max_iter=2000, class_weight="balanced")),
    ])

def with_calibration(pipe: Pipeline, mode: str):
    if mode == "platt":
        return CalibratedClassifierCV(pipe, method="sigmoid", cv=3)
    if mode == "isotonic":
        return CalibratedClassifierCV(pipe, method="isotonic", cv=3)
    return pipe

# --- group-wise scaler (fit on train groups, apply to test groups) ---
class GroupStandardizer:
    def __init__(self, feats: list[str]):
        self.feats = feats
        self.stats: dict[str, tuple[pd.Series,pd.Series]] = {}
        self.global_mean: Optional[pd.Series] = None
        self.global_std: Optional[pd.Series]  = None

    def fit(self, X_df: pd.DataFrame, groups: pd.Series):
        tmp = X_df[self.feats].copy()
        tmp["_g"] = groups.values
        for g, sub in tmp.groupby("_g"):
            m = sub[self.feats].mean()
            s = sub[self.feats].std(ddof=0).replace(0, 1.0)
            self.stats[g] = (m, s)
        # fallback for unseen groups
        means = pd.concat([v[0] for v in self.stats.values()], axis=1)
        stds  = pd.concat([v[1] for v in self.stats.values()], axis=1)
        self.global_mean = means.mean(axis=1)
        self.global_std  = stds.mean(axis=1).replace(0,1.0)
        return self

    def transform(self, X_df: pd.DataFrame, groups: pd.Series) -> np.ndarray:
        # X_df のインデックスに合わせて groups をアライン
        X = X_df[self.feats]
        gser = pd.Series(groups.values, index=X_df.index)

        out = []
        for idx, row in X.iterrows():
            grp = gser.loc[idx]  # ラベルで参照（ilocではなくloc）
            if grp in self.stats:
                m, s = self.stats[grp]
            else:
                m, s = self.global_mean, self.global_std
            out.append(((row - m) / s).to_list())
        return np.asarray(out)

# ---------- main ----------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--feat_csv", required=True)
    ap.add_argument("--out_json", default="reports/loco_report.json")
    ap.add_argument("--out_png", default="reports/figures/loco_auc.png")
    ap.add_argument("--out_png_ba", default="reports/figures/loco_ba.png")
    ap.add_argument("--out_csv", default="reports/loco_folds.csv")
    ap.add_argument("--mode", choices=["loco","sgkf"], default="loco",
                    help="loco=Leave-One-Corpus-Out, sgkf=StratifiedGroupKFold")
    ap.add_argument("--splits", type=int, default=5, help="sgkf/フォールバック用のfold数")
    ap.add_argument("--threshold", type=float, default=0.5,
                    help="確率>=threshold を ASD と判定（例: 0.55）")
    ap.add_argument("--calibrate", choices=["none","platt","isotonic"], default="none",
                    help="確率校正: platt(sigmoid) / isotonic / none")
    ap.add_argument("--group-norm", choices=["none","corpus"], default="none",
                    help="グループ標準化の有無。'corpus' でコーパスごとにz-score。")
    args = ap.parse_args()

    df = pd.read_csv(args.feat_csv)
    if "label" not in df.columns or "file_id" not in df.columns:
        raise SystemExit("CSV must include 'label' and 'file_id'.")

    y = df["label"].map({"ASD":1,"TD":0}).values
    groups = derive_groups(df)
    feats = select_numeric_features(df)

    # splitter
    n_groups = int(pd.Series(groups).nunique())
    if args.mode == "loco" and n_groups >= 2:
        splitter: Iterable[Tuple[np.ndarray,np.ndarray]] = LeaveOneGroupOut().split(df[feats].values, y, groups)
        mode_used = "LoCO"
    elif args.mode == "sgkf" and n_groups >= 2:
        n_splits = max(2, min(args.splits, n_groups))
        splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=42)\
                    .split(df[feats].values, y, groups)
        mode_used = f"StratifiedGroupKFold({n_splits})"
    else:
        if len(np.unique(y)) == 2:
            minority = int(min(np.bincount(y)))
            n_splits = max(2, min(args.splits, max(2, minority)))
        else:
            n_splits = 2
        splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)\
                    .split(df[feats].values, y)
        mode_used = f"StratifiedKFold({n_splits}) [auto-fallback]"
        n_groups = 1

    aucs, f1s, bas, mccs, fold_rows = [], [], [], [], []
    single_class_folds = 0

    for fold_idx, split in enumerate(splitter):
        tr, te = split if isinstance(split, tuple) else split
        model = with_calibration(base_pipeline(), args.calibrate)

        # ---- group-wise normalization (fit on train, apply to test) ----
        if args.group_norm == "corpus":
            gnorm = GroupStandardizer(feats).fit(df.iloc[tr], groups.iloc[tr])
            Xtr = gnorm.transform(df.iloc[tr], groups.iloc[tr])
            Xte = gnorm.transform(df.iloc[te], groups.iloc[te])
        else:
            Xtr = df.iloc[tr][feats].values
            Xte = df.iloc[te][feats].values

        model.fit(Xtr, y[tr])
        prob = model.predict_proba(Xte)[:,1]
        pred = (prob >= args.threshold).astype(int)
        y_te = y[te]

        if has_both_classes(y_te):
            auc = roc_auc_score(y_te, prob)
            f1  = f1_score(y_te, pred, zero_division=0)
            ba  = balanced_accuracy_score(y_te, pred)
            mcc = matthews_corrcoef(y_te, pred)
        else:
            auc, f1, ba, mcc = (np.nan, 0.0, 0.5, 0.0)
            single_class_folds += 1

        aucs.append(auc); f1s.append(f1); bas.append(ba); mccs.append(mcc)
        fold_rows.append({
            "fold": fold_idx, "n_test": int(len(te)),
            "auc": None if (isinstance(auc,float) and np.isnan(auc)) else float(auc),
            "f1": float(f1), "ba": float(ba), "mcc": float(mcc),
            "single_class": int(not has_both_classes(y_te)),
        })

    auc_mean = float(np.nanmean(aucs)) if np.any(~np.isnan(aucs)) else None
    f1_mean  = float(np.mean(f1s)) if f1s else None
    ba_mean  = float(np.mean(bas)) if bas else None
    mcc_mean = float(np.mean(mccs)) if mccs else None

    report = {
        "mode": mode_used, "n_samples": int(len(y)), "n_groups": n_groups,
        "features_used": feats, "threshold": float(args.threshold),
        "calibrate": args.calibrate, "group_norm": args.group_norm,
        "auc_mean": auc_mean, "f1_mean": f1_mean, "ba_mean": ba_mean, "mcc_mean": mcc_mean,
        "aucs_by_fold": [None if (isinstance(a,float) and np.isnan(a)) else float(a) for a in aucs],
        "f1s_by_fold": [float(v) for v in f1s],
        "ba_by_fold":  [float(v) for v in bas],
        "mcc_by_fold": [float(v) for v in mccs],
        "single_class_folds": int(single_class_folds),
    }
    write_run_json(report, args.out_json)

    # save CSV
    pathlib.Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(fold_rows).to_csv(args.out_csv, index=False, encoding="utf-8")

    # plots
    plot_auc = [0.0 if (v is None or (isinstance(v,float) and np.isnan(v))) else v for v in report["aucs_by_fold"]]
    pathlib.Path(args.out_png).parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(6,4))
    plt.bar(range(len(plot_auc)), plot_auc)
    plt.title(f"{mode_used} — AUC by fold (undefined shown as 0)")
    plt.xlabel("Fold"); plt.ylabel("AUC")
    plt.tight_layout(); plt.savefig(args.out_png, dpi=180); plt.close()

    plt.figure(figsize=(6,4))
    plt.bar(range(len(bas)), bas)
    plt.title(f"{mode_used} — Balanced Accuracy by fold")
    plt.xlabel("Fold"); plt.ylabel("Balanced Accuracy")
    plt.tight_layout(); plt.savefig(args.out_png_ba, dpi=180); plt.close()

    append_changelog({
        "title": f"{mode_used} eval (thr={args.threshold}, calib={args.calibrate}, gnorm={args.group_norm})",
        "notes": f"Groups={n_groups} | single-class folds={single_class_folds} | Features={len(feats)}",
        "metrics": {"AUC": auc_mean if auc_mean is not None else "NA", "F1": f1_mean, "BA": ba_mean, "MCC": mcc_mean},
        "params": {"feat_csv": args.feat_csv, "mode": args.mode, "splits": args.splits,
                   "threshold": args.threshold, "calibrate": args.calibrate, "group_norm": args.group_norm}
    })
if __name__ == "__main__":
    main()
