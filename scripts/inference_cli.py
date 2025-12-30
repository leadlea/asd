# scripts/inference_cli.py
from __future__ import annotations
import argparse, json, pathlib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression

META_COLS = {"label", "file_id", "age", "task_type", "corpus"}

def load_preset(path="config/model_config.json") -> dict:
    p = pathlib.Path(path)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def build_pipe(C: float = 1.0) -> Pipeline:
    return Pipeline([
        ("imp", SimpleImputer(strategy="median")),
        ("sc",  StandardScaler()),
        ("lr",  LogisticRegression(max_iter=2000, class_weight="balanced", C=C)),
    ])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feat_csv", required=True)
    ap.add_argument("--out_csv", default="reports/predictions.csv")
    ap.add_argument("--threshold", type=float, default=None,
                    help="未指定なら config/model_config.json の decision_threshold を使用")
    ap.add_argument("--features", nargs="*", help="使う特徴名（未指定なら全数値列）")
    ap.add_argument("--C", type=float, default=None, help="LogReg の正則化（未指定なら preset の C か 1.0）")
    args = ap.parse_args()

    preset = load_preset()
    thr = args.threshold if args.threshold is not None else float(preset.get("decision_threshold", 0.5))
    C   = float(args.C if args.C is not None else preset.get("C", 1.0))

    df = pd.read_csv(args.feat_csv)

    # 特徴の決定
    if args.features:
        feats = args.features
    elif "features" in preset and isinstance(preset["features"], list) and preset["features"]:
        feats = list(preset["features"])
    else:
        feats = [c for c in df.columns if c not in META_COLS and pd.api.types.is_numeric_dtype(df[c])]

    if not set(feats).issubset(df.columns):
        missing = [f for f in feats if f not in df.columns]
        raise SystemExit(f"Features not found in CSV: {missing}")

    X = df[feats].values
    # ラベルが無いCSVでも動くように、無い場合はダミー0で学習（確率のみ欲しいとき）
    if "label" in df.columns:
        y = df["label"].map({"ASD":1, "TD":0}).fillna(0).astype(int).values
    else:
        y = np.zeros(len(df), dtype=int)

    pipe = build_pipe(C=C)
    pipe.fit(X, y)
    prob = pipe.predict_proba(X)[:, 1]
    pred = (prob >= thr).astype(int)

    out = pd.DataFrame({
        "file_id": df.get("file_id", pd.Series(range(len(df)))),
        "prob_asd": prob,
        "pred_asd": pred
    })

    pathlib.Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out_csv, index=False, encoding="utf-8")
    print(f"Saved {args.out_csv} with threshold={thr}, C={C}, features={len(feats)}")

if __name__ == "__main__":
    main()
