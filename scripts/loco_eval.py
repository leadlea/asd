import pandas as pd, numpy as np, re
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, f1_score

def corpus_of(fid):
    m=re.search(r"_(\w+)_\d+", str(fid)); return m.group(1) if m else "UNK"

def load_features(asd_csv, td_csv):
    a=pd.read_csv(asd_csv); t=pd.read_csv(td_csv)
    a["label"]=1; t["label"]=0
    df=pd.concat([a,t], ignore_index=True)
    df["corpus"]=df["file_id"].apply(corpus_of)
    return df

def metrics(y, p, thr=0.5):
    y=y.astype(int)
    auc = roc_auc_score(y, p) if len(set(y))>1 else np.nan
    f1  = f1_score(y, (p>=thr).astype(int)) if len(set(y))>1 else np.nan
    return auc, f1

def main():
    base=Path("reports")
    df=load_features(base/"features_child_asd.csv", base/"features_child_td.csv")
    feats=[c for c in df.columns if c.endswith("_per_1k") or c.endswith("_per_utt")]
    out=[]
    for corp in sorted(df["corpus"].unique()):
        tr=df[df["corpus"]!=corp]; te=df[df["corpus"]==corp]
        Xtr,ytr = tr[feats].fillna(0), tr["label"].values
        Xte,yte = te[feats].fillna(0), te["label"].values
        if len(set(ytr))<2 or len(set(yte))<2:
            out.append({"fold":corp,"AUC":np.nan,"F1":np.nan,"note":"class-imbalance"}); continue
        clf=LogisticRegression(max_iter=500)
        clf.fit(Xtr,ytr)
        p = clf.predict_proba(Xte)[:,1]
        auc,f1 = metrics(yte,p)
        w = pd.Series(clf.coef_[0], index=feats).sort_values(key=lambda s:s.abs(), ascending=False)[:10]
        out.append({"fold":corp,"AUC":round(auc,3),"F1":round(f1,3),
                    "top_weights":"; ".join(f"{k}={v:.2f}" for k,v in w.items())})
    pd.DataFrame(out).to_csv(base/"loco_results.csv", index=False)
    print("wrote ->", base/"loco_results.csv")

if __name__=="__main__": main()
