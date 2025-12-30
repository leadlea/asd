from __future__ import annotations
import argparse, json, pathlib, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import f1_score, balanced_accuracy_score, roc_auc_score
from runlog_util import append_changelog, write_run_json

def build_pipe():
    return Pipeline([
        ("imp", SimpleImputer(strategy="median")),
        ("sc",  StandardScaler()),
        ("lr",  LogisticRegression(max_iter=2000, class_weight="balanced")),
    ])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feat_csv", required=True)
    ap.add_argument("--splits", type=int, default=3)
    ap.add_argument("--out_json", default="reports/threshold_report.json")
    ap.add_argument("--out_png",  default="reports/figures/threshold_curve.png")
    args = ap.parse_args()

    df = pd.read_csv(args.feat_csv)
    y = df["label"].map({"ASD":1,"TD":0}).values
    # グループはfile_idから推定（コーパス混成foldを作るためSGKFを使用）
    import re
    groups = df["file_id"].map(lambda s: re.match(r"^(ASD|TD)_([A-Za-z0-9]+)_", str(s)).group(2) if re.match(r"^(ASD|TD)_([A-Za-z0-9]+)_", str(s)) else "Unknown")
    meta = {"label","file_id","age","task_type","corpus"}
    feats = [c for c in df.columns if c not in meta and pd.api.types.is_numeric_dtype(df[c])]
    X = df[feats].values

    sgkf = StratifiedGroupKFold(n_splits=max(2, args.splits), shuffle=True, random_state=42)
    pipe = build_pipe()

    # CVで確率を集める
    probs, y_true = [], []
    for tr, te in sgkf.split(X, y, groups):
        pipe.fit(X[tr], y[tr])
        p = pipe.predict_proba(X[te])[:,1]
        probs.extend(p.tolist()); y_true.extend(y[te].tolist())
    probs = np.array(probs); y_true = np.array(y_true)

    # しきい値スイープ
    ths = np.linspace(0.1, 0.9, 17)
    rows = []
    for th in ths:
        pred = (probs >= th).astype(int)
        f1 = f1_score(y_true, pred, zero_division=0)
        ba = balanced_accuracy_score(y_true, pred)
        rows.append({"threshold": float(th), "f1": float(f1), "ba": float(ba)})
    df_curve = pd.DataFrame(rows)

    # ベスト選択（F1優先→BA）
    best_f1 = df_curve.iloc[df_curve["f1"].idxmax()]
    best_ba = df_curve.iloc[df_curve["ba"].idxmax()]
    best = best_f1 if best_f1["f1"] >= best_ba["f1"] else best_ba

    # 図
    pathlib.Path(args.out_png).parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7,4))
    plt.plot(df_curve["threshold"], df_curve["f1"], label="F1")
    plt.plot(df_curve["threshold"], df_curve["ba"], label="Balanced Acc.")
    plt.axvline(best["threshold"], linestyle="--")
    plt.title("Threshold sweep (CV probs)")
    plt.xlabel("Threshold"); plt.ylabel("Score")
    plt.legend(); plt.tight_layout(); plt.savefig(args.out_png, dpi=180); plt.close()

    # 保存 & CHANGELOG
    report = {
        "mode": "threshold_sweep_cv",
        "n_samples": int(len(y_true)),
        "features_used": feats,
        "best": {"threshold": float(best["threshold"]), "f1": float(best["f1"]), "ba": float(best["ba"])},
        "curve": rows
    }
    write_run_json(report, args.out_json)
    append_changelog({
        "title": "Threshold sweep (CV probs)",
        "notes": f"splits={args.splits}",
        "metrics": {"F1*": float(best['f1']), "BA*": float(best['ba'])},
        "params": {"best_threshold": float(best["threshold"]), "feat_csv": args.feat_csv}
    })

if __name__ == "__main__":
    main()
