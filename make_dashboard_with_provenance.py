#!/usr/bin/env python3
import argparse, runpy, sys, os, hashlib, pandas as pd
from datetime import datetime

def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for ch in iter(lambda: f.read(8192), b''):
            h.update(ch)
    return h.hexdigest()[:10]

def summary_table(dyads_path):
    df = pd.read_csv(dyads_path)
    cols = [c for c in ["input_word_tokens","input_mlu","T2_child_word_types"] if c in df.columns]
    if "diagnostic_group" in df.columns and cols:
        g = df.groupby("diagnostic_group")[cols].mean().round(2)
        return g.to_markdown()
    return ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dyads", required=True)
    ap.add_argument("--desc",  required=True)
    ap.add_argument("--ttest", required=True)
    ap.add_argument("--out",   required=True)
    ap.add_argument("--orig",  required=True)  # ./make_dashboard.py
    args = ap.parse_args()

    # 元スクリプトを“そのままの引数”で実行
    sys.argv = [args.orig,
                "--dyads", args.dyads,
                "--desc",  args.desc,
                "--ttest", args.ttest,
                "--out",   args.out]
    runpy.run_path(args.orig, run_name="__main__")

    # Provenance 追記
    if not os.path.exists(args.out):
        raise SystemExit(f"ERROR: output not found: {args.out}")

    dyads_md5 = md5(args.dyads)
    desc_md5  = md5(args.desc)
    ttest_md5 = md5(args.ttest)
    built_at  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    prov = f"""
<!-- provenance block auto-inserted -->
<hr/>
<div style="font-family: ui-sans-serif, system-ui; font-size: 12px; color: #555;">
  <b>Built:</b> {built_at}<br/>
  <b>Dyads:</b> {os.path.basename(args.dyads)} (md5:{dyads_md5})<br/>
  <b>Desc:</b> {os.path.basename(args.desc)} (md5:{desc_md5})<br/>
  <b>T-test:</b> {os.path.basename(args.ttest)} (md5:{ttest_md5})<br/>
  <details style="margin-top:6px;"><summary>Group means snapshot (from dyads)</summary>
  <pre style="white-space:pre-wrap;">{summary_table(args.dyads)}</pre>
  </details>
</div>
"""
    # </body> の直前に挿入（無ければ末尾に追記）
    with open(args.out, "r+", encoding="utf-8", errors="ignore") as f:
        html = f.read()
        if "</body>" in html:
            html = html.replace("</body>", prov + "\n</body>")
        else:
            html = html + prov
        f.seek(0); f.write(html); f.truncate()

    print(f"Wrote: {args.out}")

if __name__ == "__main__":
    main()
