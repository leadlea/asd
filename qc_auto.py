#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto-QC for CHAT sessions using IQR/percentile thresholds.
Run from your repo root, e.g.:
  python qc_auto.py \
    --utterances data/processed/utterances_clean.csv \
    --out_csv data/processed/utterances_qc.csv \
    --out_metrics reports/session_metrics.csv \
    --out_speaker reports/speaker_metrics.csv \
    --save_thresholds reports/qc_auto_thresholds.json
"""
import argparse, json, re
from pathlib import Path
import pandas as pd
import numpy as np
from collections import Counter, defaultdict

def iqr_bounds(series, clip_low=None, clip_high=None):
    s = pd.to_numeric(series, errors="coerce").dropna().astype(float)
    q1, q3 = np.percentile(s, [25, 75])
    iqr = q3 - q1
    lo = q1 - 1.5 * iqr
    hi = q3 + 1.5 * iqr
    if clip_low is not None:
        lo = max(lo, clip_low)
    if clip_high is not None:
        hi = min(hi, clip_high)
    return lo, hi

def tokenize(s: str):
    return re.findall(r"[A-Za-z']+", (s or "").lower())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--utterances", required=True, help="data/processed/utterances_clean.csv")
    ap.add_argument("--out_csv", required=True, help="data/processed/utterances_qc.csv")
    ap.add_argument("--out_metrics", required=True, help="reports/session_metrics.csv")
    ap.add_argument("--out_speaker", required=True, help="reports/speaker_metrics.csv")
    ap.add_argument("--save_thresholds", required=True, help="reports/qc_auto_thresholds.json")
    ap.add_argument("--adult_speakers", default="INV,MOT,FAT", help="comma-separated adult speaker codes")
    ap.add_argument("--child_speakers", default="CHI", help="comma-separated child speaker codes")
    args = ap.parse_args()

    utter = pd.read_csv(args.utterances)
    adult_set = set(x.strip() for x in args.adult_speakers.split(",") if x.strip())
    child_set = set(x.strip() for x in args.child_speakers.split(",") if x.strip())

    # --- per-session counts (recompute from utterances) ---
    grp = utter.groupby("file_id")["speaker"].value_counts().unstack(fill_value=0)
    grp["n_total"] = grp.sum(axis=1)
    grp["n_ADULT"] = grp[list(adult_set & set(grp.columns))].sum(axis=1) if adult_set else 0
    grp["n_CHILD"] = grp[list(child_set & set(grp.columns))].sum(axis=1) if child_set else 0
    denom = (grp["n_ADULT"] + grp["n_CHILD"]).replace(0, np.nan)
    grp["chi_ratio"] = (grp["n_CHILD"] / denom).fillna(0.0)

    # --- robust thresholds ---
    n_total_lo, n_total_hi = iqr_bounds(grp["n_total"])
    chi_ratio_lo, chi_ratio_hi = iqr_bounds(grp["chi_ratio"], clip_low=0.0, clip_high=1.0)
    # percentiles
    n_total_p10, n_total_p90 = np.percentile(grp["n_total"], [10, 90])
    chi_p10, chi_p90 = np.percentile(grp["chi_ratio"], [10, 90])
    # harmonize
    n_total_lo_h = max(n_total_lo, n_total_p10)
    n_total_hi_h = min(n_total_hi, n_total_p90)
    chi_ratio_lo_h = max(chi_ratio_lo, chi_p10, 0.0)
    chi_ratio_hi_h = min(chi_ratio_hi, chi_p90, 1.0)
    # min counts (p10 floors with floor>=20)
    n_child_p10 = np.percentile(grp["n_CHILD"], 10) if "n_CHILD" in grp.columns else 0
    n_adult_p10 = np.percentile(grp["n_ADULT"], 10) if "n_ADULT" in grp.columns else 0

    thresholds = {
        "n_total": {"lo": int(round(n_total_lo_h)), "hi": int(round(n_total_hi_h))},
        "chi_ratio": {"lo": float(round(chi_ratio_lo_h, 3)), "hi": float(round(chi_ratio_hi_h, 3))},
        "n_CHILD_min": int(max(20, round(n_child_p10))),
        "n_ADULT_min": int(max(20, round(n_adult_p10))),
        "adult_speakers": sorted(list(adult_set)),
        "child_speakers": sorted(list(child_set)),
    }
    Path(args.save_thresholds).parent.mkdir(parents=True, exist_ok=True)
    with open(args.save_thresholds, "w") as f:
        json.dump(thresholds, f, indent=2)

    # --- keep sessions ---
    keep_idx = grp.index[
        (grp["n_total"] >= thresholds["n_total"]["lo"]) &
        (grp["n_total"] <= thresholds["n_total"]["hi"]) &
        (grp["chi_ratio"] >= thresholds["chi_ratio"]["lo"]) &
        (grp["chi_ratio"] <= thresholds["chi_ratio"]["hi"]) &
        (grp["n_CHILD"] >= thresholds["n_CHILD_min"]) &
        (grp["n_ADULT"] >= thresholds["n_ADULT_min"])
    ]
    keep = set(keep_idx.tolist())

    # --- export utterances_qc.csv with role ---
    def to_role(sp):
        if sp in adult_set: return "ADULT"
        if sp in child_set: return "CHILD"
        return None

    out_rows = utter[utter["file_id"].isin(keep)].copy()
    out_rows["role"] = out_rows["speaker"].map(to_role)
    out_rows = out_rows[out_rows["role"].notna()]
    Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
    out_rows.to_csv(args.out_csv, index=False)

    # --- recompute session metrics on the kept set ---
    def per_session_metrics(df: pd.DataFrame):
        def toks(s): return tokenize(s)
        metrics = []
        for fid, g in df.groupby("file_id"):
            child = g[g["role"]=="CHILD"]["utt_clean"].tolist()
            adult = g[g["role"]=="ADULT"]["utt_clean"].tolist()
            c_toks = sum([toks(u) for u in child], [])
            a_toks = sum([toks(u) for u in adult], [])
            n_c, n_a = len(child), len(adult)
            chi_ratio = n_c/max(1, n_c+n_a)
            mlu_c = (len(c_toks)/max(1,n_c)) if n_c else 0
            mlu_a = (len(a_toks)/max(1,n_a)) if n_a else 0
            ttr_c = (len(set(c_toks))/max(1,len(c_toks))) if c_toks else 0
            ttr_a = (len(set(a_toks))/max(1,len(a_toks))) if a_toks else 0
            avgc_c = (sum(len(u) for u in child)/max(1,n_c)) if n_c else 0
            avgc_a = (sum(len(u) for u in adult)/max(1,n_a)) if n_a else 0
            metrics.append([fid,n_c,n_a,round(chi_ratio,3),
                            round(mlu_c,3),round(mlu_a,3),
                            round(ttr_c,3),round(ttr_a,3),
                            round(avgc_c,1),round(avgc_a,1)])
        cols = ["file_id","n_child","n_adult","chi_ratio",
                "mlu_child","mlu_adult","ttr_child","ttr_adult",
                "avg_chars_child","avg_chars_adult"]
        return pd.DataFrame(metrics, columns=cols)

    met_df = per_session_metrics(out_rows)
    Path(args.out_metrics).parent.mkdir(parents=True, exist_ok=True)
    met_df.to_csv(args.out_metrics, index=False)

    # --- global speaker metrics ---
    def speaker_agg(df: pd.DataFrame, role: str):
        g = df[df["role"]==role]["utt_clean"].tolist()
        tok = sum([tokenize(u) for u in g], [])
        n_utt = len(g)
        mlu = (len(tok)/max(1,n_utt)) if n_utt else 0
        ttr = (len(set(tok))/max(1,len(tok))) if tok else 0
        avg_chars = (sum(len(u) for u in g)/max(1,n_utt)) if n_utt else 0
        return {"role":role,"n_utt":n_utt,"mlu":round(mlu,3),"ttr":round(ttr,3),"avg_chars":round(avg_chars,1)}

    spk_df = pd.DataFrame([speaker_agg(out_rows,"CHILD"), speaker_agg(out_rows,"ADULT")])
    spk_df.to_csv(args.out_speaker, index=False)

    print("[qc_auto] thresholds ->", args.save_thresholds)
    print("[qc_auto] kept sessions:", len(keep))
    print("[qc_auto] wrote ->", args.out_csv)
    print("[qc_auto] metrics ->", args.out_metrics, " | speaker ->", args.out_speaker)

if __name__ == "__main__":
    main()
