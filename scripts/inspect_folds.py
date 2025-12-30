from __future__ import annotations
import argparse, re, pathlib, pandas as pd, numpy as np
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, roc_auc_score, f1_score, balanced_accuracy_score, matthews_corrcoef

def corpus_from_fid(s: str) -> str:
    m = re.match(r"^(ASD|TD)_([A-Za-z0-9]+)_", str(s))
    return m.group(2) if m else "Unknown"

def build_pipe():
    return Pipeline([("imp", SimpleImputer(strategy="median")),
                     ("sc", StandardScaler()),
                     ("lr", LogisticRegression(max_iter=2000, class_weight="balanced"))])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feat_csv", required=True)
    ap.add_argument("--splits", type=int, default=2)
    ap.add_argument("--threshold", type=float, default=0.55)
    ap.add_argument("--out_membership", default="reports/fold_membership.csv")
    ap.add_argument("--out_confusion", default="reports/confusion_by_fold.csv")
    args = ap.parse_args()

    df = pd.read_csv(args.feat_csv)
    if "corpus" not in df.columns:
        df["corpus"] = df["file_id"].map(corpus_from_fid)
    y = df["label"].map({"ASD":1,"TD":0}).values
    groups = df["corpus"].values
    meta = {"label","file_id","age","task_type","corpus"}
    feats = [c for c in df.columns if c not in meta and pd.api.types.is_numeric_dtype(df[c])]
    X = df[feats].values

    sgkf = StratifiedGroupKFold(n_splits=max(2,args.splits), shuffle=True, random_state=42)
    pipe = build_pipe()

    rows_membership, rows_conf = [], []
    for fold, (tr, te) in enumerate(sgkf.split(X, y, groups)):
        # membership table
        sub = df.iloc[te][["file_id","label","corpus"]].copy()
        sub["fold"] = fold
        rows_membership.append(sub)

        # metrics + confusion
        pipe.fit(X[tr], y[tr])
        prob = pipe.predict_proba(X[te])[:,1]
        pred = (prob >= args.threshold).astype(int)
        yt = y[te]
        tn, fp, fn, tp = confusion_matrix(yt, pred, labels=[0,1]).ravel()
        auc = roc_auc_score(yt, prob)
        f1  = f1_score(yt, pred, zero_division=0)
        ba  = balanced_accuracy_score(yt, pred)
        mcc = matthews_corrcoef(yt, pred)
        rows_conf.append({"fold":fold,"n_test":len(te),"auc":auc,"f1":f1,"ba":ba,"mcc":mcc,
                          "tn":tn,"fp":fp,"fn":fn,"tp":tp})

    pathlib.Path(args.out_membership).parent.mkdir(parents=True, exist_ok=True)
    pd.concat(rows_membership, ignore_index=True).to_csv(args.out_membership, index=False, encoding="utf-8")
    pd.DataFrame(rows_conf).to_csv(args.out_confusion, index=False, encoding="utf-8")
    print("saved:", args.out_membership, "and", args.out_confusion)

if __name__ == "__main__":
    main()
