#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

TRAITS = ["C","A","E","N","O"]
TEACHERS = ["qwen3-235b", "deepseek-v3", "gpt-oss-120b"]  # sonnet以外

BOOT_DIR_TMPL = "artifacts/analysis/results/bootstrap/cejc_home2_hq1_{T}only_{teacher}_controls_excluded"
OUT_FIG_DIR = Path("docs/homework/assets/figs")
OUT_MD = Path("docs/homework/cejc_bootstrap_cards_nonsonnet.md")

def load_bootstrap_summary(t: str, teacher: str) -> pd.DataFrame:
    p = Path(BOOT_DIR_TMPL.format(T=t, teacher=teacher)) / "bootstrap_summary.tsv"
    if not p.exists():
        raise FileNotFoundError(f"missing: {p}")
    df = pd.read_csv(p, sep="\t")

    # 列名ゆれ吸収
    # 必須: feature, topk_rate, sign_agree_rate, coef_mean
    if "feature" not in df.columns:
        # featureっぽい列を探す
        feat_col = next((c for c in df.columns if "feat" in c.lower()), None)
        if not feat_col:
            raise ValueError(f"feature column not found in {p}")
        df = df.rename(columns={feat_col: "feature"})
    if "topk_rate" not in df.columns:
        rate_col = next((c for c in df.columns if "top" in c.lower() and "rate" in c.lower()), None)
        if not rate_col:
            raise ValueError(f"topk_rate column not found in {p}")
        df = df.rename(columns={rate_col: "topk_rate"})
    if "sign_agree_rate" not in df.columns:
        # sign_agree など
        s_col = next((c for c in df.columns if "sign" in c.lower() and "agree" in c.lower()), None)
        if not s_col:
            raise ValueError(f"sign_agree_rate column not found in {p}")
        df = df.rename(columns={s_col: "sign_agree_rate"})
    if "coef_mean" not in df.columns:
        c_col = next((c for c in df.columns if "coef" in c.lower() and "mean" in c.lower()), None)
        if not c_col:
            raise ValueError(f"coef_mean column not found in {p}")
        df = df.rename(columns={c_col: "coef_mean"})

    # 数値化
    for c in ["topk_rate","sign_agree_rate","coef_mean"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def radar_plot(labels: list[str], values: list[float], title: str, out_png: Path):
    # radar: 0..1
    vals = np.asarray(values, dtype=float)
    vals = np.clip(vals, 0.0, 1.0)

    N = len(labels)
    angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
    # close loop
    angles += angles[:1]
    vals = np.r_[vals, vals[:1]]

    fig = plt.figure(figsize=(5.2, 5.2))
    ax = plt.subplot(111, polar=True)

    ax.plot(angles, vals, linewidth=2)
    ax.fill(angles, vals, alpha=0.12)

    ax.set_ylim(0, 1.0)
    ax.set_yticks([0.2,0.4,0.6,0.8,1.0])
    ax.set_yticklabels(["0.2","0.4","0.6","0.8","1.0"], fontsize=8)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_title(title, pad=14)

    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200)
    plt.close(fig)

def card_block(t: str, teacher: str, top10: pd.DataFrame, img_topk: str, img_sign: str) -> str:
    # Markdown table (left)
    lines = []
    lines.append('<table>\n<tr>\n')
    lines.append('<td valign="top" width="62%">\n\n')
    lines.append(f'### {t} Top10（{teacher}）\n')
    lines.append('| Feature | Dir | topk_rate | sign_agree |\n')
    lines.append('|---|:---:|---:|---:|\n')
    for _, r in top10.iterrows():
        d = "+" if float(r["coef_mean"]) > 0 else "−"
        lines.append(f'| {r["feature"]} | {d} | {float(r["topk_rate"]):.3f} | {float(r["sign_agree_rate"]):.3f} |\n')
    lines.append('\n</td>\n')

    # Images (right)
    lines.append('<td valign="top" width="38%" align="center">\n\n')
    lines.append(f'<a href="{img_topk}"><img src="{img_topk}" width="280"></a><br>\n')
    lines.append('<sub><b>topk_rate</b>（クリックで拡大）</sub>\n<br><br>\n')
    lines.append(f'<a href="{img_sign}"><img src="{img_sign}" width="280"></a><br>\n')
    lines.append('<sub><b>sign_agree_rate</b>（クリックで拡大）</sub>\n\n')
    lines.append('</td>\n</tr>\n</table>\n')
    return "".join(lines)

def main():
    OUT_FIG_DIR.mkdir(parents=True, exist_ok=True)

    md = []
    md.append("# Bootstrap stability cards (non-sonnet teachers)\n\n")
    md.append("- topk_rate = Top10 inclusion frequency (Bootstrap 500)\n")
    md.append("- sign_agree_rate = sign agreement frequency (Bootstrap 500)\n\n")

    for teacher in TEACHERS:
        md.append(f"## Teacher: {teacher}\n\n")

        for t in TRAITS:
            df = load_bootstrap_summary(t, teacher)
            top10 = df.sort_values("topk_rate", ascending=False).head(10).copy()

            labels = top10["feature"].tolist()
            topk_vals = top10["topk_rate"].tolist()
            sign_vals = top10["sign_agree_rate"].tolist()

            # output png paths
            img_topk = f"assets/figs/radar_{teacher}_{t}_topk_rate.png"
            img_sign = f"assets/figs/radar_{teacher}_{t}_sign_agree.png"

            radar_plot(labels, topk_vals, f"CEJC home2 HQ1 — {teacher} — {t}: topk_rate", OUT_FIG_DIR / f"radar_{teacher}_{t}_topk_rate.png")
            radar_plot(labels, sign_vals, f"CEJC home2 HQ1 — {teacher} — {t}: sign_agree_rate", OUT_FIG_DIR / f"radar_{teacher}_{t}_sign_agree.png")

            md.append(card_block(t, teacher, top10, img_topk, img_sign))
            md.append("\n")

    OUT_MD.write_text("".join(md), encoding="utf-8")
    print("OK:", OUT_MD)

if __name__ == "__main__":
    main()
