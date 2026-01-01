#!/usr/bin/env python3
import argparse, pandas as pd, math
from datetime import datetime

def fmt(x):
    if x is None or (isinstance(x,float) and math.isnan(x)):
        return "-"
    try:
        v = float(x)
        if v.is_integer():
            return str(int(v))
        return f"{v:.3f}"
    except Exception:
        return str(x)

def shorten(s, n=120):
    s = "" if s is None else str(s)
    s = s.replace("\n"," ").strip()
    return s if len(s) <= n else s[:n-1] + "…"

def pick_row(df, dataset_name):
    if dataset_name in df.index:
        return df.loc[dataset_name]
    return None

def get_metric(row, name):
    if row is None:
        return None
    # 互換マッピング
    alias = {
        "rate_question": ["rate_question","question_rate"],
        "rate_NE_valid": ["rate_NE_valid","sfp_ratio_NE"],   # 近い意味（完全一致ではないが説明用途として）
        "rate_YO_valid": ["rate_YO_valid","sfp_ratio_YO"],
        "RESP_NE_AIZUCHI_RATE": ["RESP_NE_AIZUCHI_RATE"],
        "RESP_NE_ENTROPY": ["RESP_NE_ENTROPY"],
        "RESP_YO_ENTROPY": ["RESP_YO_ENTROPY"],
        "aizuchi_rate_in_pairs": ["aizuchi_rate_in_pairs"],
        "n_conversations": ["n_conversations"],
        "segments_rows": ["segments_rows"],
        "pairs_rows": ["pairs_rows"],
    }
    keys = alias.get(name, [name])
    for k in keys:
        if k in row.index:
            return row[k]
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary-csv", required=True)
    ap.add_argument("--cejc-top-csv", required=True)
    ap.add_argument("--cejc-bottom-csv", required=True)
    ap.add_argument("--csj-top-csv", default=None)
    ap.add_argument("--csj-bottom-csv", default=None)
    ap.add_argument("--out-html", required=True)
    ap.add_argument("--gold-version", default="13")
    args = ap.parse_args()

    s = pd.read_csv(args.summary_csv)
    ds_col = "dataset" if "dataset" in s.columns else s.columns[0]
    s = s.set_index(ds_col)

    A = "cejc_dyad"
    B = "csj_dialog"
    ra = pick_row(s, A)
    rb = pick_row(s, B)

    metrics = [
        "n_conversations","segments_rows","pairs_rows",
        "rate_question","aizuchi_rate_in_pairs",
        "RESP_NE_AIZUCHI_RATE","RESP_NE_ENTROPY","RESP_YO_ENTROPY",
        "rate_NE_valid","rate_YO_valid",
    ]

    rows = []
    for m in metrics:
        va = get_metric(ra, m)
        vb = get_metric(rb, m)
        try:
            da = float(va) if va is not None and str(va)!="" else None
            db = float(vb) if vb is not None and str(vb)!="" else None
            diff = (da - db) if (da is not None and db is not None) else None
        except Exception:
            diff = None
        rows.append((m, va, vb, diff))

    cejc_top = pd.read_csv(args.cejc_top_csv).head(12)
    cejc_bot = pd.read_csv(args.cejc_bottom_csv).head(12)
    csj_top = pd.read_csv(args.csj_top_csv).head(12) if args.csj_top_csv else None
    csj_bot = pd.read_csv(args.csj_bottom_csv).head(12) if args.csj_bottom_csv else None

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    def ex_table(df, title):
        if df is None:
            return f"<div class='note'>（{title} は未生成）</div>"
        html = [f"<h3>{title}</h3>", "<div class='grid'>"]
        for _, r in df.iterrows():
            conv = r.get("conversation_id","")
            spk  = r.get("speaker_id","")
            rate = r.get("RESP_NE_AIZUCHI_RATE","")
            nne  = r.get("n_pairs_after_NE","")
            prev = shorten(r.get("prev_text",""), 140)
            resp = shorten(r.get("resp_text",""), 90)
            sfp  = r.get("prev_sfp_group","")
            iaz  = r.get("resp_is_aizuchi","")
            html.append(f"""
              <div class="card">
                <div class="meta">
                  <span class="tag">{conv}</span>
                  <span class="tag">spk={spk}</span>
                  <span class="tag">NEpairs={nne}</span>
                  <span class="tag">rate={fmt(rate)}</span>
                </div>
                <div class="line"><span class="lab">前:</span> <span class="txt">{prev}</span></div>
                <div class="line"><span class="lab">SFP:</span> <span class="txt">{sfp}</span></div>
                <div class="line"><span class="lab">応答:</span> <span class="txt">{resp}</span></div>
                <div class="meta2">aizuchi={iaz}</div>
              </div>
            """)
        html.append("</div>")
        return "\n".join(html)

    html = f"""<!doctype html>
<html lang="ja"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>ASD v13 CEJC dyad vs CSJ dialog</title>
<style>
  @page {{ size: A4; margin: 12mm; }}
  body {{ font-family: -apple-system,BlinkMacSystemFont,"Hiragino Kaku Gothic ProN","Noto Sans JP","Yu Gothic",sans-serif; color:#111; background:#fff; }}
  h1 {{ font-size: 20px; margin: 0 0 6px; }}
  h2 {{ font-size: 16px; margin: 16px 0 8px; }}
  h3 {{ font-size: 14px; margin: 14px 0 6px; }}
  .muted {{ color:#666; font-size: 11px; }}
  .page {{ page-break-after: always; }}
  .page:last-child {{ page-break-after: auto; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 11px; }}
  th, td {{ border: 1px solid #ddd; padding: 6px 8px; vertical-align: top; }}
  th {{ background:#f6f6f6; text-align: left; }}
  .k {{ width: 34%; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
  .card {{ border:1px solid #ddd; border-radius: 10px; padding: 8px; }}
  .meta {{ display:flex; flex-wrap: wrap; gap:6px; margin-bottom: 6px; }}
  .tag {{ background:#f1f1f1; padding:2px 6px; border-radius: 999px; font-size: 10px; }}
  .line {{ font-size: 11px; margin: 4px 0; }}
  .lab {{ color:#666; display:inline-block; min-width: 34px; }}
  .meta2 {{ color:#666; font-size: 10px; margin-top: 6px; }}
  .note {{ border:1px dashed #bbb; border-radius:10px; padding:10px; color:#666; font-size: 11px; }}
</style>
</head><body>

<section class="page">
  <h1>gold v{args.gold_version} — CEJC dyad vs CSJ dialog（A4）</h1>
  <div class="muted">生成: {now} / 入力: summary_datasets + examples（NE→応答）</div>

  <h2>1) 指標比較（summary）</h2>
  <table>
    <tr><th class="k">metric</th><th>{A}</th><th>{B}</th><th>diff（{A}-{B}）</th></tr>
    {''.join([f"<tr><td>{m}</td><td>{fmt(va)}</td><td>{fmt(vb)}</td><td>{fmt(d)}</td></tr>" for (m,va,vb,d) in rows])}
  </table>

  <div class="muted" style="margin-top:6px;">
    ※rate_NE_valid / rate_YO_valid が空の場合、sfp_ratio_NE / sfp_ratio_YO を近似表示します。
  </div>
</section>

<section class="page">
  <h2>2) 代表例（CEJC dyad / top & bottom）</h2>
  {ex_table(cejc_top, "CEJC dyad — top（aizuchi寄り）")}
  {ex_table(cejc_bot, "CEJC dyad — bottom（non-aizuchi寄り）")}
</section>

<section class="page">
  <h2>3) 代表例（CSJ dialog / top & bottom）</h2>
  {ex_table(csj_top, "CSJ dialog — top（aizuchi寄り）")}
  {ex_table(csj_bot, "CSJ dialog — bottom（non-aizuchi寄り）")}
</section>

</body></html>
"""
    with open(args.out_html, "w", encoding="utf-8") as f:
        f.write(html)
    print("[OK] wrote:", args.out_html)

if __name__ == "__main__":
    main()
