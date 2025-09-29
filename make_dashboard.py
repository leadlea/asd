#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BN2015（英語）ダッシュボード生成スクリプト（最終版）

機能:
- 既存の再現出力（dyads/desc/ttest）を表示
- Pragmatics（CHIのみ、ASD vs TYP）は --prag_child_grp の CSV を表示
- Pragmatics のメタ解析CSV（mean/sd/n + Hedges g, 95%CI）をそのまま全カラム表示（--prag_meta）
- T3 があれば Figure1 (Input MLU × T3 %spoken) を描画
- Paper Comparison（Table 1/2）を表示
- 出力先 --out がディレクトリなら {out}/bn2015_dashboard.html に保存

使い方例:
python make_dashboard.py \
  --dyads dyads.bn2015.full.csv \
  --desc  out/bn2015/table3_descriptives_en.csv \
  --ttest out/bn2015/table2_en_ttests.csv \
  --out   out/bn2015 \
  --prag_child_grp data/processed/pragmatics_child_group.csv \
  --prag_meta      data/processed/pragmatics_meta.csv
"""
import argparse
import os
import math
import re
import pandas as pd
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ===== 論文（英語列）の目標値（Paper Comparison 用） =====
PAPER_T1 = {  # Table 1 (child@T2)
    ("ASD","T2_child_word_types"): (48.46, 42.48),
    ("TYP","T2_child_word_types"): (59.00, 34.36),
    ("ASD","T2_age_months"):       (61.89, 10.99),
    ("TYP","T2_age_months"):       (32.30,  8.43),
}
PAPER_T2 = {  # Table 2 (maternal input@T2)
    ("ASD","input_word_tokens"):     (664.64, 328.94),
    ("TYP","input_word_tokens"):     (1126.36, 222.29),
    ("ASD","input_word_types"):      (142.64, 29.80),
    ("TYP","input_word_types"):      (146.46, 39.37),
    ("ASD","input_mlu"):             (4.75, 0.92),
    ("TYP","input_mlu"):             (5.40, 0.81),
    ("ASD","input_num_utterances"):  (112.36, 58.62),
    ("TYP","input_num_utterances"):  (112.36, 37.43),
}

HTML_CSS = """
<style>
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, "Hiragino Kaku Gothic ProN", Meiryo, sans-serif; margin:24px; }
h1 { font-size: 22px; margin: 0 0 12px; }
h2 { font-size: 18px; margin: 18px 0 8px; }
h3 { font-size: 16px; margin: 12px 0 6px; }
.muted { color: #777; }
.tbl { border-collapse: collapse; width: 100%; margin: 6px 0 16px; font-size: 13px; }
.tbl th, .tbl td { border: 1px solid #ddd; padding: 6px 8px; text-align: right; }
.tbl th { background: #f6f6f6; text-align: center; }
.tbl td:first-child, .tbl th:first-child { text-align: left; }
.small { font-size: 12px; }
.note { font-size: 12px; color:#555; margin: 6px 0 14px; }
.hr { height:1px; background:#eee; margin:18px 0; }
.kbd { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; background:#f3f3f3; border:1px solid #ddd; padding:0 4px; border-radius:3px; }
</style>
"""

# ---------- utils ----------
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dyads", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--desc", required=True)
    ap.add_argument("--ttest", required=True)
    ap.add_argument("--prag_child_grp", default="", help="ASD/TYP group means (CHI only), e.g., data/processed/pragmatics_child_group.csv")
    ap.add_argument("--prag_meta", default="", help="meta-analysis CSV (e.g., data/processed/pragmatics_meta.csv)")
    return ap.parse_args()

def to_html_table(df: pd.DataFrame, round_float=True) -> str:
    if df is None or len(df) == 0:
        return '<div class="muted">（データなし）</div>'
    df = df.copy()
    if round_float:
        for c in df.columns:
            if pd.api.types.is_float_dtype(df[c]):
                df[c] = df[c].apply(lambda v: "" if pd.isna(v) else (int(v) if float(v).is_integer() else round(float(v), 3)))
    cols = list(df.columns)
    html = ['<table class="tbl">']
    html.append("<thead><tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr></thead>")
    html.append("<tbody>")
    for _, row in df.iterrows():
        html.append("<tr>" + "".join(f"<td>{row[c]}</td>" for c in cols) + "</tr>")
    html.append("</tbody></table>")
    return "\n".join(html)

def smart_read_csv(path_or_empty: str, basename_hint: str = "") -> pd.DataFrame:
    """
    与えられたパスが無い場合に、よくある場所を探索して読む。
    """
    cands = []
    if path_or_empty:
        cands.append(path_or_empty)
        cands.append(os.path.basename(path_or_empty))
    if basename_hint:
        cands.append(basename_hint)
    base = os.path.basename(path_or_empty or basename_hint)
    for root in ["", "data/processed", "out/bn2015", "reports/reproduction/bang_nadig_2015", "."]:
        if base:
            cands.append(os.path.join(root, base))
    seen = set()
    for p in cands:
        if not p or p in seen:
            continue
        seen.add(p)
        if os.path.exists(p):
            try:
                print(f"[INFO] read_csv: {p}")
                return pd.read_csv(p)
            except Exception as e:
                print(f"[WARN] Failed to read {p}: {e}")
    if path_or_empty:
        print(f"[WARN] CSV not found: {path_or_empty}")
    return pd.DataFrame()

def clean_desc_ranges(df: pd.DataFrame) -> pd.DataFrame:
    """descのrange列を (xx.xx, yy.yy) へ整形し、NaNはダッシュに。"""
    if df is None or df.empty or "range" not in df.columns:
        return df
    def _fmt(x):
        s = str(x)
        if "nan" in s.lower():
            return "—"
        nums = re.findall(r"[-+]?\d*\.\d+|\d+", s)
        if len(nums) >= 2:
            a, b = float(nums[0]), float(nums[1])
            return f"({a:.2f}, {b:.2f})"
        return s
    out = df.copy()
    out["range"] = out["range"].apply(_fmt)
    return out

# ---------- paper comparison ----------
def paper_compare_block(desc_df: pd.DataFrame, which="T1"):
    """desc_df から group×column の mean/sd を拾い、PAPER_* と比較テーブルを生成"""
    if desc_df is None or desc_df.empty or not {"group","column","mean","sd"} <= set(desc_df.columns):
        return '<div class="muted">（記述統計CSVが見つからない/列不足のため比較を省略）</div>'
    paper = PAPER_T1 if which=="T1" else PAPER_T2
    rows = []
    for (grp, col), (p_mean, p_sd) in paper.items():
        sub = desc_df[(desc_df["group"]==grp) & (desc_df["column"]==col)]
        if len(sub)==0:
            rows.append({"measure": col, "group": grp, "mine_mean":"", "paper_mean":p_mean,
                         "Δmean": "", "Δmean%": "", "mine_sd":"", "paper_sd": p_sd, "Δsd":"", "Δsd%": ""})
            continue
        mine_mean = float(sub["mean"].values[0])
        mine_sd   = float(sub["sd"].values[0]) if not pd.isna(sub["sd"].values[0]) else np.nan
        dmean = mine_mean - p_mean
        dmean_pct = (dmean / p_mean * 100.0) if p_mean else np.nan
        dsd = (mine_sd - p_sd) if not np.isnan(mine_sd) else np.nan
        dsd_pct = (dsd / p_sd * 100.0) if p_sd else np.nan
        rows.append({
            "measure": col, "group": grp,
            "mine_mean": round(mine_mean, 3), "paper_mean": p_mean,
            "Δmean": round(dmean, 2), "Δmean%": round(dmean_pct, 2) if not np.isnan(dmean_pct) else "",
            "mine_sd": round(mine_sd, 3) if not np.isnan(mine_sd) else "",
            "paper_sd": p_sd,
            "Δsd": round(dsd, 2) if not np.isnan(dsd) else "",
            "Δsd%": round(dsd_pct, 2) if not np.isnan(dsd_pct) else "",
        })
    out = pd.DataFrame(rows, columns=["measure","group","mine_mean","paper_mean","Δmean","Δmean%","mine_sd","paper_sd","Δsd","Δsd%"])
    return to_html_table(out)

# ---------- main ----------
def main():
    args = parse_args()

    # 出力パス（ファイル or ディレクトリ）
    if args.out.lower().endswith(".html"):
        out_dir = os.path.dirname(args.out) or "."
        out_html = args.out
    else:
        out_dir = args.out
        out_html = os.path.join(out_dir, "bn2015_dashboard.html")
    os.makedirs(out_dir, exist_ok=True)

    # 入力読み込み
    dy = pd.read_csv(args.dyads)
    desc_raw = smart_read_csv(args.desc, basename_hint="table3_descriptives_en.csv")
    ttest = smart_read_csv(args.ttest, basename_hint="table2_en_ttests.csv")
    prag = smart_read_csv(args.prag_child_grp, basename_hint="pragmatics_child_group.csv")
    prag_meta = smart_read_csv(args.prag_meta, basename_hint="pragmatics_meta.csv")

    # Descriptives 整形（range・NaNの見た目）
    desc = clean_desc_ranges(desc_raw)

    # Figure 1（T3あれば）
    if "T3_mcdi_pct_spoken" in dy.columns and "input_mlu" in dy.columns:
        tmp = dy[["input_mlu","T3_mcdi_pct_spoken"]].copy()
        tmp["input_mlu"] = pd.to_numeric(tmp["input_mlu"], errors="coerce")
        tmp["T3_mcdi_pct_spoken"] = pd.to_numeric(tmp["T3_mcdi_pct_spoken"], errors="coerce")
        tmp = tmp.dropna()
        if len(tmp) > 0:
            fig_path = os.path.join(out_dir, "figure1_mlu_vs_mcdi_updated.png")
            plt.figure(figsize=(6,4))
            plt.scatter(tmp["input_mlu"], tmp["T3_mcdi_pct_spoken"])
            plt.xlabel("Maternal Input MLU (T2)")
            plt.ylabel("Child Vocabulary 6 Months Later (MCDI, %spoken)")
            plt.tight_layout(); plt.savefig(fig_path, dpi=150); plt.close()
            fig1_html = f'<img src="{os.path.basename(fig_path)}" style="max-width:100%;">'
        else:
            fig1_html = '<div class="muted">T3 は列はありますが、数値が欠損のためプロットできません。</div>'
    else:
        fig1_html = '<div class="muted">T3（MCDI %spoken）または input_mlu が未提供のため、Figure 1 を省略します。</div>'

    # 言語×群の件数
    if {"language","diagnostic_group","dyad_id"} <= set(dy.columns):
        counts = dy.groupby(["language","diagnostic_group"], as_index=False)["dyad_id"].count().rename(columns={"dyad_id":"n"})
    else:
        # セーフティ: 必要列が無い場合は全件数だけ出す
        tmp = pd.DataFrame({"n":[len(dy)]})
        counts = tmp

    # Pragmatics（ASD/TYP, CHIのみ）
    if not prag.empty:
        # group列 or index を正規化
        if "group" in prag.columns:
            prag = prag.set_index("group")
        if "n_dyads" in prag.columns:
            try:
                prag["n_dyads"] = prag["n_dyads"].astype("Int64")  # 小数見せ防止
            except Exception:
                pass
        rename = {
            "n_dyads":"n_dyads",
            "q_all_rate":"Questions (All) — per utter",
            "q_wh_rate":"WH Questions — per utter",
            "q_yn_rate":"Yes/No Questions — per utter",
            "dm_fill_per100utt":"DM: Fill — /100 utt",
            "dm_contrast_per100utt":"DM: Contrast — /100 utt",
            "dm_causal_per100utt":"DM: Causal — /100 utt",
            "dm_shift_per100utt":"DM: Shift — /100 utt",
            "ms_total_per100w":"Mental-state (Total) — /100 w",
        }
        cols = [c for c in ["n_dyads","q_all_rate","q_wh_rate","q_yn_rate",
                            "dm_fill_per100utt","dm_contrast_per100utt","dm_causal_per100utt","dm_shift_per100utt",
                            "ms_total_per100w"] if c in prag.columns]
        order_groups = [g for g in ["ASD","TYP"] if g in prag.index]
        tidy = prag.loc[order_groups, cols].T.reset_index().rename(columns={"index":"Metric"})
        tidy["Metric"] = tidy["Metric"].map(lambda k: rename.get(k, k))
        prag_html = to_html_table(tidy)
    else:
        prag_html = '<div class="muted">pragmatics_child_group.csv が見つからないため、このセクションは省略します。（--prag_child_grp のパスを確認）</div>'

    # Pragmatics meta 表
    if not prag_meta.empty:
        meta_cols = [c for c in [
            "metric","mean_ASD","sd_ASD","n_ASD",
            "mean_TYP","sd_TYP","n_TYP",
            "hedges_g","se","ci95_lo","ci95_hi"
        ] if c in prag_meta.columns]
        meta_html = to_html_table(prag_meta[meta_cols])
    else:
        meta_html = '<div class="muted">pragmatics_meta.csv が見つからないため、このセクションは省略します。（--prag_meta のパスを確認）</div>'

    # t-tests / desc HTML
    ttest_html = to_html_table(ttest)
    desc_html  = to_html_table(desc)
    counts_html= to_html_table(counts)

    # Paper Comparison
    pc_t1_html = paper_compare_block(desc_raw, which="T1")
    pc_t2_html = paper_compare_block(desc_raw, which="T2")

    # HTML 組み立て
    html = []
    html.append("<!doctype html><meta charset='utf-8'>")
    html.append(HTML_CSS)
    html.append("<h1>BN2015 再現ダッシュボード（英語）</h1>")
    html.append('<div class="note">このページは make_dashboard.py で再生成されます。</div>')

    html.append("<h2>Figure 1: Input MLU (T2) × MCDI % Spoken (T3)</h2>")
    html.append(fig1_html)

    html.append('<div class="hr"></div>')
    html.append("<h2>Summary</h2>")
    html.append("<h3>Counts by language × group</h3>")
    html.append(counts_html)

    html.append('<div class="hr"></div>')
    html.append("<h2>Group Comparison (EN, ASD vs TYP)</h2>")
    html.append("<h3>EN Welch t-tests (ASD vs TYP)</h3>")
    html.append(ttest_html)

    html.append('<div class="hr"></div>')
    html.append("<h2>Descriptives (EN)</h2>")
    html.append(desc_html)

    html.append('<div class="hr"></div>')
    html.append("<h2>Paper Comparison (EN)</h2>")
    html.append("<h3>Paper vs Ours — Table 1 metrics</h3>")
    html.append(pc_t1_html)
    html.append("<h3>Paper vs Ours — Table 2 metrics</h3>")
    html.append(pc_t2_html)

    html.append('<div class="hr"></div>')
    html.append("<h2>Pragmatics (CHI) — ASD vs TYP</h2>")
    html.append("<div class='note'>Nadig英語（100番台）、偶数=ASD/奇数=TYP。BN2015で使用した 11/11 subject のみを集計。指標の単位: per utter / per 100 utt / per 100 w。</div>")
    html.append("<div class='note'>Contrast は CHI では低頻度です。辞書（but/however/though/although/yet/whereas/instead/but then/even so/on the other hand/in contrast/nevertheless/nonetheless/still）で探索済み。0 は“未検出”=実測ゼロを意味します。</div>")
    html.append(prag_html)

    html.append('<div class="hr"></div>')
    html.append("<h2>Pragmatics — Meta metrics (ASD vs TYP)</h2>")
    html.append("<div class='note'>各指標の mean/sd/n と Hedges g（Hedges' g）, 95%CI を CSV そのまま掲載します。</div>")
    html.append(meta_html)

    # ソースファイル一覧（ベース名だけ表示）
    html.append('<div class="hr"></div>')
    src_tbl = pd.DataFrame({
        "file": ["table2_en_ttests.csv","table3_descriptives_en.csv","dyads.csv",
                 "pragmatics_child_group.csv","pragmatics_meta.csv"],
        "path": [os.path.basename(args.ttest), os.path.basename(args.desc), os.path.basename(args.dyads),
                 os.path.basename(args.prag_child_grp) if args.prag_child_grp else "",
                 os.path.basename(args.prag_meta) if args.prag_meta else ""],
    })
    html.append("<h3>Source CSVs</h3>")
    html.append(to_html_table(src_tbl, round_float=False))

    with open(out_html, "w", encoding="utf-8") as w:
        w.write("\n".join(html))
    print(f"Wrote: {out_html}")

if __name__ == "__main__":
    main()
