from __future__ import annotations
import argparse, pathlib, re, json, numpy as np, pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import roc_auc_score, balanced_accuracy_score, f1_score, matthews_corrcoef
from sklearn.calibration import CalibratedClassifierCV
from runlog_util import append_changelog, write_run_json

def corpus(fid:str)->str:
    m=re.match(r"^(ASD|TD)_([A-Za-z0-9]+)_", str(fid)); return m.group(2) if m else "Unknown"

def build_pipe(C=1.0, calibrate="platt"):
    base=Pipeline([("imp",SimpleImputer(strategy="median")),
                   ("sc", StandardScaler()),
                   ("lr", LogisticRegression(max_iter=2000,class_weight="balanced", C=C))])
    if calibrate=="platt":   return CalibratedClassifierCV(base, method="sigmoid", cv=3)
    if calibrate=="isotonic":return CalibratedClassifierCV(base, method="isotonic", cv=3)
    return base

ap=argparse.ArgumentParser()
ap.add_argument("--feat_csv", required=True)
ap.add_argument("--features", nargs="+", required=True, help="使用する特徴名をスペース区切りで")
ap.add_argument("--threshold", type=float, default=0.55)
ap.add_argument("--splits", type=int, default=2)
ap.add_argument("--calibrate", choices=["platt","isotonic","none"], default="platt")
ap.add_argument("--C", type=float, default=1.0)
ap.add_argument("--out_json", default="reports/feature_subset_report.json")
ap.add_argument("--tag", default="")
args=ap.parse_args()

df=pd.read_csv(args.feat_csv)
if "corpus" not in df.columns: df["corpus"]=df["file_id"].map(corpus)
y=df["label"].map({"ASD":1,"TD":0}).values
X=df[args.features].values
groups=df["corpus"].values

sgkf=StratifiedGroupKFold(n_splits=max(2,args.splits), shuffle=True, random_state=42)
model=build_pipe(C=args.C, calibrate=args.calibrate)

aucs, bas, f1s, mccs=[],[],[],[]
for tr,te in sgkf.split(X,y,groups):
    model.fit(X[tr], y[tr])
    prob=model.predict_proba(X[te])[:,1]
    pred=(prob>=args.threshold).astype(int)
    aucs.append(roc_auc_score(y[te], prob))
    bas.append(balanced_accuracy_score(y[te], pred))
    f1s.append(f1_score(y[te], pred, zero_division=0))
    from sklearn.metrics import matthews_corrcoef
    mccs.append(matthews_corrcoef(y[te], pred))

rep={"mode":"feature_subset_sgkf",
     "features":args.features,
     "threshold":args.threshold,
     "calibrate":args.calibrate,
     "C":args.C,
     "AUC_mean":float(np.mean(aucs)),
     "BA_mean":float(np.mean(bas)),
     "F1_mean":float(np.mean(f1s)),
     "MCC_mean":float(np.mean(mccs)),
     "folds":{"AUC":list(map(float,aucs)),"BA":list(map(float,bas)),"F1":list(map(float,f1s))}}
write_run_json(rep, args.out_json)
append_changelog({
  "title":"Feature subset eval",
  "notes": f"{args.tag or 'subset'} | k={args.splits}, thr={args.threshold}, calib={args.calibrate}, C={args.C}",
  "metrics":{"AUC":rep["AUC_mean"],"BA":rep["BA_mean"],"F1":rep["F1_mean"],"MCC":rep["MCC_mean"]},
  "params":{"features":args.features}
})
print(json.dumps(rep, indent=2))
