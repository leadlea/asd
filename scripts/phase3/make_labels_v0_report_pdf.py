# scripts/phase3/make_labels_v0_report_pdf.py
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib import font_manager as fm


# -------------------------
# Font setup (JP)
# -------------------------
def setup_japanese_font(prefer: Optional[List[str]] = None) -> str:
    """
    Choose an available Japanese-capable font and set matplotlib rcParams.
    Returns chosen font name (or empty string if not found).
    """
    if prefer is None:
        prefer = [
            # macOS
            "Hiragino Sans",
            "Hiragino Kaku Gothic ProN",
            "Hiragino Kaku Gothic Pro",
            "Yu Gothic",
            "YuGothic",
            "Meiryo",
            # Noto/IPA (if installed)
            "Noto Sans CJK JP",
            "Noto Sans JP",
            "IPAexGothic",
            "IPAGothic",
            "TakaoGothic",
        ]

    available = {f.name for f in fm.fontManager.ttflist}
    chosen = ""
    for name in prefer:
        if name in available:
            chosen = name
            break

    if chosen:
        plt.rcParams["font.family"] = chosen
        # ついで：マイナス記号が文字化けする環境向け
        plt.rcParams["axes.unicode_minus"] = False

    return chosen


def a4_fig():
    return plt.figure(figsize=(8.27, 11.69))


def page_title(fig, text: str, y=0.97):
    # fontweight="bold" をやめる（フォント埋め込み警告回避）
    fig.text(0.5, y, text, ha="center", va="top", fontsize=16)


def _safe_json(s: Any) -> Dict[str, Any]:
    if not isinstance(s, str) or not s.strip():
        return {}
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels_parquet", required=True)
    ap.add_argument("--out_pdf", required=True)
    ap.add_argument("--topn", type=int, default=30)
    args = ap.parse_args()

    # ✅ Set JP font early (before creating figures)
    chosen_font = setup_japanese_font()

    df = pd.read_parquet(args.labels_parquet)
    out_pdf = Path(args.out_pdf)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["ps.fonttype"] = 42

    with PdfPages(out_pdf) as pdf:
        # Overview
        fig = a4_fig()
        page_title(fig, "LLM labeling v0 (Bedrock Claude Opus 4.5)")
        txt = [
            f"- rows: {len(df):,}",
            f"- datasets: {', '.join(sorted(df['dataset'].astype(str).unique().tolist()))}",
            f"- matplotlib font: {chosen_font or '(not found -> may miss JP glyphs)'}",
            "",
            "Columns:",
            "  dataset, speaker_id, atypicality_v0, labels_json, top_features_json, examples_json",
            "",
            "Note: v0 labels are hypothesis-level (feature/example grounded), not clinical diagnosis.",
        ]
        fig.text(0.08, 0.90, "\n".join(txt), ha="left", va="top", fontsize=11)
        pdf.savefig(fig)
        plt.close(fig)

        # Per dataset
        for ds, g in df.groupby("dataset"):
            g2 = g.sort_values("atypicality_v0", ascending=False).head(args.topn).copy()

            fig = a4_fig()
            page_title(fig, f"{ds}: Top {len(g2)} labeled outliers")
            ax = fig.add_axes([0.06, 0.06, 0.88, 0.86])
            ax.axis("off")

            rows: List[List[str]] = []
            for _, r in g2.iterrows():
                lj = _safe_json(r.get("labels_json"))
                labels = lj.get("labels") or []
                label_str = "; ".join([f"{x.get('label','')}({x.get('confidence',0):.2f})" for x in labels[:3]])
                summary = str(lj.get("summary") or "")
                rows.append(
                    [
                        str(r.get("speaker_id")),
                        f"{float(r.get('atypicality_v0')):.3f}" if r.get("atypicality_v0") is not None else "-",
                        label_str,
                        summary[:140].replace("\n", " "),
                    ]
                )

            col_labels = ["speaker_id", "score", "labels", "summary"]
            tbl = ax.table(
                cellText=rows,
                colLabels=col_labels,
                loc="upper left",
                cellLoc="left",
                bbox=[0, 0, 1, 1],
            )
            tbl.auto_set_font_size(False)
            tbl.set_fontsize(7)
            tbl.scale(1.0, 1.1)

            pdf.savefig(fig)
            plt.close(fig)

    print(json.dumps({"out_pdf": str(out_pdf), "font": chosen_font}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

