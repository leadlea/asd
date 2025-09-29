#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nadig (.cha) 直読み → CHI の語用論指標 → ASD/TYP 群平均 + メタ解析用CSV

- 対象: data/raw/asd/Nadig の英語(100番台)のみ、偶数=ASD / 奇数=TYP
- 解析窓は .cha そのまま（BN2015準拠データで T2の9分窓になっている想定）
- Subject内に複数 .cha があれば Subject内平均 → 群平均（= 各被験者を等重み）

オプション:
--restrict_to_dyads で BN2015 の dyads CSV（例: dyads.bn2015.full.csv）を渡すと、
そこの t2_files_used 等から subject(3桁) を抽出し、その 11/11 のみを集計。

出力:
  --out_csv           : group(ASD/TYP) × 指標（群平均） + n_dyads
  --byfile_out_csv    : ファイル明細（デバッグ用）
  --meta_out          : メタ解析用（各指標ごとの mean/sd/n と Hedges g, 95%CI）

使い方（BN2015の11/11に揃える推奨）:
  python src/features/pragmatics_from_cha.py \
    --nadig_dir data/raw/asd/Nadig \
    --restrict_to_dyads dyads.bn2015.full.csv \
    --out_csv data/processed/pragmatics_child_group.csv \
    --byfile_out_csv data/processed/pragmatics_child_byfile.csv \
    --meta_out data/processed/pragmatics_meta.csv
"""
from __future__ import annotations
import argparse, os, glob, re, math
import pandas as pd
import numpy as np

# ===== パターン類 =====
WH_RE    = re.compile(r'^\s*(who|what|why|how|when|where|which|whose)\b', re.I)
QMARK_RE = re.compile(r'\?\s*$')
TOKEN_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

# Discourse Markers 辞書（Contrast 拡張版）
DM_LEX = {
    "fill":     [r"you know", r"i mean", r"well", r"like"],
    "contrast": [
        r"but", r"however", r"though", r"although",
        r"yet", r"whereas", r"instead",
        r"but then", r"even so", r"on the other hand",
        r"in contrast", r"nevertheless", r"nonetheless", r"still"
    ],
    "causal":   [r"because", r"so\b", r"therefore", r"thus", r"since\b"],
    "shift":    [r"anyway", r"by the way", r"now,", r"ok,", r"okay,"],
}
DM_PAT = {k: re.compile(r"\b(?:%s)\b" % "|".join(v), re.I) for k, v in DM_LEX.items()}

def per100(x: float, base: float, eps: float = 1e-9) -> float:
    return 100.0 * x / (base + eps)

def count_tokens(s: str) -> int:
    return len(TOKEN_RE.findall(s or ""))

def ms_total(text: str) -> int:
    MS_VERBS = {"think","know","believe","guess","remember","forget","feel","want","hope",
                "pretend","notice","decide","understand","suppose","realize","wish","doubt"}
    MS_ADJS  = {"sure","afraid","glad","sorry","certain","uncertain","anxious","confident"}
    MS_NOUNS = {"idea","plan","belief","memory","thought","feeling","desire","hope"}
    toks=[t.lower() for t in TOKEN_RE.findall(text or "")]
    return sum(t in MS_VERBS for t in toks) + sum(t in MS_ADJS for t in toks) + sum(t in MS_NOUNS for t in toks)

def subject_from_filename(path: str) -> int | None:
    """'asd_Nadig_101.cha' → 101 を返す（3桁優先）。"""
    m=re.search(r"(\d{3})(?!\d)", os.path.basename(path))
    return int(m.group(1)) if m else None

def group_from_subject(subj: int) -> str | None:
    """100番台=英語のみ、偶数=ASD/奇数=TYP。"""
    if subj is None or not (100 <= subj < 200):
        return None
    return "ASD" if (subj % 2 == 0) else "TYP"

def parse_cha_chi_metrics(path: str) -> dict:
    """1つの .cha から CHI 指標を返す。"""
    chi_utts=[]
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            if raw.startswith("*CHI:"):
                chi_utts.append(raw.split(":",1)[1])
    n_utt=len(chi_utts)
    tok_n=sum(count_tokens(u) for u in chi_utts)
    is_whq=[bool(WH_RE.match(u)) for u in chi_utts]
    is_qmark=[bool(QMARK_RE.search(u)) for u in chi_utts]
    is_ynq=[qm and not wh for qm,wh in zip(is_qmark,is_whq)]
    is_q_any=[a or b for a,b in zip(is_whq,is_ynq)]
    dm_sum={k:sum(len(DM_PAT[k].findall(u)) for u in chi_utts) for k in DM_PAT}
    ms_sum=sum(ms_total(u) for u in chi_utts)
    return {
        "q_all_rate": (sum(is_q_any)/n_utt) if n_utt>0 else 0.0,
        "q_wh_rate":  (sum(is_whq)/n_utt)   if n_utt>0 else 0.0,
        "q_yn_rate":  (sum(is_ynq)/n_utt)   if n_utt>0 else 0.0,
        "dm_fill_per100utt":     per100(dm_sum["fill"], n_utt),
        "dm_contrast_per100utt": per100(dm_sum["contrast"], n_utt),
        "dm_causal_per100utt":   per100(dm_sum["causal"], n_utt),
        "dm_shift_per100utt":    per100(dm_sum["shift"], n_utt),
        "ms_total_per100w":      per100(ms_sum, tok_n if tok_n>0 else 1e-9),
        "n_utt": n_utt, "tok_n": tok_n,
    }

def extract_subjects_from_dyads(dyads_csv: str) -> set[int]:
    """dyads CSV から 3桁 subject を総当たり抽出（t2_files_used 等を横断）。"""
    try:
        dy = pd.read_csv(dyads_csv)
    except Exception:
        return set()
    subs=set()
    for col in dy.columns:
        if dy[col].dtype == object:
            for val in dy[col].astype(str).fillna(""):
                for t in re.findall(r"(\d{3})(?!\d)", val):
                    n=int(t)
                    if 100 <= n < 200:
                        subs.add(n)
    return subs

def hedges_g_from_groups(n1, m1, s1, n2, m2, s2):
    """Hedges g とSE, 95%CI。n1=ASD, n2=TYP。"""
    if (n1 is None) or (n2 is None) or (n1+n2 - 2) <= 0:
        return np.nan, np.nan, np.nan, np.nan
    sp = math.sqrt(((n1-1)*(s1**2) + (n2-1)*(s2**2)) / max(n1+n2-2, 1))
    if sp == 0:
        return np.nan, np.nan, np.nan, np.nan
    d  = (m1 - m2) / sp
    J  = 1 - 3/(4*(n1+n2)-9) if (n1+n2)>2 else 1.0
    g  = J * d
    se = math.sqrt((n1+n2)/(n1*n2) + (g*g)/(2*(n1+n2-2))) if (n1+n2-2)>0 else np.nan
    lo, hi = (g - 1.96*se, g + 1.96*se) if not np.isnan(se) else (np.nan, np.nan)
    return g, se, lo, hi

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--nadig_dir", required=True, help="例: data/raw/asd/Nadig")
    ap.add_argument("--out_csv", required=True)
    ap.add_argument("--byfile_out_csv", default="")
    ap.add_argument("--meta_out", default="")
    ap.add_argument("--restrict_to_dyads", default="", help="例: dyads.bn2015.full.csv（指定すると 11/11 subject に限定）")
    args=ap.parse_args()

    # 11/11 subject 抽出（任意）
    restrict_subjects=set()
    if args.restrict_to_dyads:
        restrict_subjects = extract_subjects_from_dyads(args.restrict_to_dyads)
        if restrict_subjects:
            print(f"[INFO] Restricting to subjects from dyads ({len(restrict_subjects)}):",
                  sorted(restrict_subjects))
        else:
            print(f"[WARN] Could not extract subjects from {args.restrict_to_dyads}. Proceeding without restriction.")

    # .cha 収集
    cha_files=sorted(glob.glob(os.path.join(args.nadig_dir, "*.cha")))
    if not cha_files:
        raise SystemExit(f"No .cha found in {args.nadig_dir}")

    # 解析
    rows=[]
    for fp in cha_files:
        subj=subject_from_filename(fp)
        grp =group_from_subject(subj)  # None → 非英語/不正番号は除外
        if grp is None:
            continue
        if restrict_subjects and (subj not in restrict_subjects):
            continue
        met=parse_cha_chi_metrics(fp)
        met.update({"file": os.path.basename(fp), "subject": subj, "group": grp})
        rows.append(met)

    if not rows:
        raise SystemExit("No English Nadig files matched the criteria. Check paths / dyads restriction.")

    byfile=pd.DataFrame(rows)

    # Subject内平均 → 群平均
    metrics=["q_all_rate","q_wh_rate","q_yn_rate",
             "dm_fill_per100utt","dm_contrast_per100utt","dm_causal_per100utt","dm_shift_per100utt",
             "ms_total_per100w"]
    per_subject=(byfile.groupby(["group","subject"])[metrics].mean().reset_index())

    # 群平均テーブル
    grp = (per_subject.groupby("group")[metrics].mean().round(6))
    grp["n_dyads"]=per_subject.groupby("group")["subject"].nunique().astype(int)
    grp = grp[["n_dyads"]+metrics].sort_index()

    # 保存
    os.makedirs(os.path.dirname(args.out_csv) or ".", exist_ok=True)
    grp.reset_index().to_csv(args.out_csv, index=False)
    print(f"Wrote {args.out_csv}  shape={grp.shape}")
    print(grp.reset_index().to_string(index=False))

    if args.byfile_out_csv:
        os.makedirs(os.path.dirname(args.byfile_out_csv) or ".", exist_ok=True)
        byfile.to_csv(args.byfile_out_csv, index=False)
        print(f"Wrote {args.byfile_out_csv}  shape={byfile.shape}")

    # メタ解析CSV（mean/sd/n と Hedges g）
    if args.meta_out:
        stats = per_subject.groupby("group")[metrics].agg(['mean','std','count'])
        def mk_row(m):
            n1 = int(stats.loc['ASD', (m,'count')]); m1 = float(stats.loc['ASD',(m,'mean')]); s1 = float(stats.loc['ASD',(m,'std')])
            n2 = int(stats.loc['TYP', (m,'count')]); m2 = float(stats.loc['TYP',(m,'mean')]); s2 = float(stats.loc['TYP',(m,'std')])
            g, se, lo, hi = hedges_g_from_groups(n1,m1,s1,n2,m2,s2)
            return dict(metric=m,
                        mean_ASD=m1, sd_ASD=s1, n_ASD=n1,
                        mean_TYP=m2, sd_TYP=s2, n_TYP=n2,
                        hedges_g=g, se=se, ci95_lo=lo, ci95_hi=hi)
        meta = pd.DataFrame([mk_row(m) for m in metrics])
        os.makedirs(os.path.dirname(args.meta_out) or ".", exist_ok=True)
        meta.to_csv(args.meta_out, index=False)
        print(f"Wrote {args.meta_out}  shape={meta.shape}")

if __name__=="__main__":
    main()
