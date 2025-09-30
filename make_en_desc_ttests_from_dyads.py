#!/usr/bin/env python3
import argparse, pandas as pd, numpy as np, math
try:
    from scipy import stats as st
except Exception:
    st = None

MEASURES = [
    ("Tokens",      "input_word_tokens"),
    ("Types",       "input_word_types"),
    ("MLU",         "input_mlu"),
    ("Utterances",  "input_num_utterances"),
    ("VOCD_D",      "input_D"),                 # 無ければスキップ
    ("ChildTypes",  "T2_child_word_types"),
]

def welch_t(a, b):
    a = a.dropna().astype(float); b = b.dropna().astype(float)
    n1, n2 = len(a), len(b)
    if n1<2 or n2<2: return (np.nan, np.nan)
    m1, m2 = a.mean(), b.mean()
    v1, v2 = a.var(ddof=1), b.var(ddof=1)
    se2 = v1/n1 + v2/n2
    if se2<=0: return (np.nan, np.nan)
    t = (m1 - m2) / math.sqrt(se2)
    df = (se2**2) / ((v1**2)/(n1**2*(n1-1)) + (v2**2)/(n2**2*(n2-1)))
    return (t, df)

def pooled_sd(a, b):
    a = a.dropna().astype(float); b = b.dropna().astype(float)
    n1, n2 = len(a), len(b)
    if n1<2 or n2<2: return np.nan
    v1, v2 = a.var(ddof=1), b.var(ddof=1)
    return math.sqrt(((n1-1)*v1 + (n2-1)*v2) / (n1+n2-2))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dyads", required=True)
    ap.add_argument("--outdir", default="out/bn2015")
    ap.add_argument("--lang", default="EN")
    a = ap.parse_args()

    df = pd.read_csv(a.dyads)
    if "language" in df.columns:
        df = df[df["language"].astype(str).str.upper()==a.lang]
    if "diagnostic_group" not in df.columns:
        raise SystemExit("diagnostic_group 列が必要です")

    # ==== table3: 記述統計 ====
    rows=[]
    cols = ["T2_age_months","T2_child_word_types","input_D",
            "input_mlu","input_num_utterances","input_word_tokens","input_word_types"]
    for col in cols:
        if col not in df.columns: continue
        for grp, sub in df.groupby("diagnostic_group"):
            s = pd.to_numeric(sub[col], errors="coerce").dropna()
            if len(s)==0: 
                rows.append({"group":grp,"column":col,"n":0,"mean":"","sd":"","range":"—"})
                continue
            rows.append({
                "group": grp,
                "column": col,
                "n": int(len(s)),
                "mean": float(s.mean()),
                "sd": float(s.std(ddof=1)) if len(s)>1 else 0.0,
                "range": f"({s.min():.2f}, {s.max():.2f})"
            })
    desc = pd.DataFrame(rows, columns=["group","column","n","mean","sd","range"])
    desc_path = f"{a.outdir}/table3_descriptives_en.csv"
    desc.to_csv(desc_path, index=False)

    # ==== table2: Welch t-tests ====
    rows=[]
    for label, col in MEASURES:
        if col not in df.columns: 
            continue
        asd = pd.to_numeric(df[df["diagnostic_group"]=="ASD"][col], errors="coerce")
        typ = pd.to_numeric(df[df["diagnostic_group"]=="TYP"][col], errors="coerce")
        mA, sA, nA = float(asd.mean()), float(asd.std(ddof=1)), int(asd.notna().sum())
        mT, sT, nT = float(typ.mean()), float(typ.std(ddof=1)), int(typ.notna().sum())
        t, dfree = welch_t(asd, typ)
        if st is not None and not (np.isnan(t) or np.isnan(dfree)):
            p = 2*(1 - st.t.cdf(abs(t), dfree))
        else:
            p = ""
        sp = pooled_sd(asd, typ)
        d = (mA - mT)/sp if (sp is not None and sp>0 and not math.isnan(sp)) else ""
        rows.append({
            "measure": label, "column": col,
            "n_ASD": nA, "mean_ASD": mA, "sd_ASD": sA,
            "n_TYP": nT, "mean_TYP": mT, "sd_TYP": sT,
            "t_Welch": t if not np.isnan(t) else "",
            "p_value": p, "cohen_d": d
        })
    ttest = pd.DataFrame(rows, columns=["measure","column","n_ASD","mean_ASD","sd_ASD",
                                        "n_TYP","mean_TYP","sd_TYP","t_Welch","p_value","cohen_d"])
    ttest_path = f"{a.outdir}/table2_en_ttests.csv"
    ttest.to_csv(ttest_path, index=False)

    print("Wrote:", desc_path)
    print("Wrote:", ttest_path)

if __name__ == "__main__":
    main()
