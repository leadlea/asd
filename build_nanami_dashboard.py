#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Nanami / TYP ダッシュボード生成スクリプト（*_gpu フォルダのみ対象 / 白背景UI）
GitHub Pages公開向けに、レポートへのリンクを file:// または 相対パス(./<sess>/report.html) で出力できます。
"""

import sys, argparse, glob, urllib.parse
from pathlib import Path
import pandas as pd

def read_csv_safe(path: Path):
    if path.exists():
        try:
            return pd.read_csv(path)
        except Exception as e:
            print(f"[warn] CSV 読み込み失敗: {path}: {e}", file=sys.stderr)
    return pd.DataFrame()

def to_file_uri(p: Path) -> str:
    try:
        ap = p.resolve().as_posix()
        return "file://" + urllib.parse.quote(ap)
    except Exception:
        return ""

def build_dashboard(root: Path, out_html: Path, title: str, link_mode: str) -> None:
    root = root.resolve()
    sess_dirs = sorted([Path(p) for p in glob.glob(str(root / "*_gpu")) if Path(p).is_dir()])

    rows = []
    for d in sess_dirs:
        turns = read_csv_safe(d / "turns.csv")
        pros  = read_csv_safe(d / "prosody.csv")
        prag  = read_csv_safe(d / "pragmatics.csv")
        echoes = read_csv_safe(d / "echoes.csv")
        dups   = read_csv_safe(d / "duplicates.csv")
        report = d / "report.html"

        if turns.empty and pros.empty and prag.empty:
            continue

        tmap = {r["role"]: r for _, r in turns.iterrows()} if not turns.empty else {}
        pmap = {r["role"]: r for _, r in pros.iterrows()} if not pros.empty else {}
        gmap = {r["role"]: r for _, r in prag.iterrows()} if not prag.empty else {}

        def g(m, r, k, default=None):
            try:
                return float(m.get(r, {}).get(k, default))
            except Exception:
                return default

        if link_mode == "pages":
            report_href = f"./{d.name}/report.html" if report.exists() else ""
        else:
            report_href = to_file_uri(report) if report.exists() else ""

        data = {
            "session": d.name.replace("_gpu",""),  # 表示用
            "sess_dir": d.name,
            "chi_utts":  tmap.get("CHI", {}).get("n_utts", 0),
            "mot_utts":  tmap.get("MOT", {}).get("n_utts", 0),
            "chi_tokens":tmap.get("CHI", {}).get("n_tokens", 0),
            "mot_tokens":tmap.get("MOT", {}).get("n_tokens", 0),
            "chi_mlu":   tmap.get("CHI", {}).get("mlu", 0.0),
            "mot_mlu":   tmap.get("MOT", {}).get("mlu", 0.0),
            "chi_f0":    pmap.get("CHI", {}).get("f0_mean", 0.0),
            "mot_f0":    pmap.get("MOT", {}).get("f0_mean", 0.0),
            "chi_q":     g(gmap, "CHI", "question_rate", 0.0),
            "mot_q":     g(gmap, "MOT", "question_rate", 0.0),
            "echoes":    0 if echoes is None else len(echoes.index),
            "near_dups": 0 if dups is None else len(dups.index),
            "report_uri": report_href,
        }
        rows.append(data)

    if not rows:
        raise SystemExit(f"[error] *_gpu の対象フォルダが見つかりませんでした: {root}")

    df = pd.DataFrame(rows).sort_values("session")
    df["token_ratio_chi_mot"] = df["chi_tokens"] / df["mot_tokens"].replace(0, 1)

    summary_csv = root / "Nanami_summary.csv"
    df_out = df[["session","chi_utts","mot_utts","chi_tokens","mot_tokens","chi_mlu","mot_mlu","chi_f0","mot_f0","chi_q","mot_q","echoes","near_dups","token_ratio_chi_mot","report_uri"]]
    df_out.to_csv(summary_csv, index=False, float_format="%.6f")
    print(f"[ok] wrote summary CSV: {summary_csv}")

    k_sessions = len(df)
    k_tokens_chi = int(df["chi_tokens"].sum())
    k_tokens_mot = int(df["mot_tokens"].sum())
    k_mlu_chi = float(df["chi_mlu"].mean())
    k_mlu_mot = float(df["mot_mlu"].mean())

    def h(x, digits=2, integer=False):
        try:
            if integer:
                return f"{int(round(float(x))):,}"
            return f"{float(x):,.{digits}f}"
        except Exception:
            return "—"

    tr_html = []
    for _, r in df.iterrows():
        width_pct = min(200.0, max(0.0, float(r["token_ratio_chi_mot"]) * 100.0))
        link_html = (f'<a class="btn btn-outline small" href="{r["report_uri"]}" target="_blank">開く</a>'
                     if r["report_uri"] else '<span class="muted small">—</span>')
        tr_html.append(f"""
        <tr>
          <td class="label"><b>{r['session']}</b></td>
          <td><span class="pill pill-chi">CHI</span> {h(r['chi_utts'],0,True)} / {h(r['chi_tokens'],0,True)} / {h(r['chi_mlu'])}</td>
          <td><span class="pill pill-mot">MOT</span> {h(r['mot_utts'],0,True)} / {h(r['mot_tokens'],0,True)} / {h(r['mot_mlu'])}</td>
          <td><div class="bar" title="{h(r['token_ratio_chi_mot'])}"><span style="width:{width_pct}%"></span></div></td>
          <td>{h(r['chi_f0'])} / {h(r['mot_f0'])}</td>
          <td>{h(float(r['chi_q'])*100)} / {h(float(r['mot_q'])*100)}</td>
          <td>{int(r['echoes'])} / {int(r['near_dups'])}</td>
          <td>{link_html}</td>
        </tr>
        """)

    bars_html = []
    for _, r in df.iterrows():
        width_pct = min(200.0, max(0.0, float(r["token_ratio_chi_mot"]) * 100.0))
        bars_html.append(f"""
        <div style="display:grid;grid-template-columns:110px 1fr 60px;gap:10px;align-items:center;margin:8px 0;">
          <div class="muted small">{r['session']}</div>
          <div class="bar"><span style="width:{width_pct}%"></span></div>
          <div class="right small">{h(r['token_ratio_chi_mot'])}</div>
        </div>
        """)

    html = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title}</title>
<style>
  :root {{
    --bg:#ffffff; --card:#ffffff; --muted:#6b7280; --text:#111827; --accent:#2563eb;
    --chi:#16a34a; --mot:#f59e0b; --warn:#dc2626; --border:#e5e7eb;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; padding:24px; font:14px/1.6 system-ui, -apple-system, Segoe UI, Roboto, 'Hiragino Sans', 'Noto Sans JP', Arial, sans-serif; background:var(--bg); color:var(--text); }}
  h1 {{ font-size:28px; margin:0 0 8px 0; }}
  h2 {{ font-size:18px; margin:24px 0 8px 0; color:#1f2937; }}
  p.lead {{ color:#374151; margin:6px 0 18px 0; }}
  .wrap {{ max-width:1200px; margin:0 auto; }}
  .row {{ display:grid; grid-template-columns: 1fr 1fr; gap:16px; }}
  .card {{ background:var(--card); border:1px solid var(--border); border-radius:14px; padding:16px; box-shadow:0 1px 2px rgba(0,0,0,.04); }}
  .muted {{ color:var(--muted); }}
  .btn {{ background:var(--accent); color:#fff; padding:8px 12px; border-radius:10px; border:1px solid var(--accent); font-weight:600; cursor:pointer; }}
  .btn-outline {{ background:#fff; color:var(--accent); border:1px solid var(--accent); }}
  table {{ width:100%; border-collapse:collapse; margin-top:8px; }}
  th, td {{ padding:8px 10px; border-bottom:1px solid var(--border); text-align:right; white-space:nowrap;}}
  th {{ color:#111827; font-weight:700; text-align:left; }}
  td.label {{ text-align:left; }}
  .pill {{ display:inline-block; padding:2px 8px; border-radius:999px; font-weight:700; font-size:12px; border:1px solid transparent; }}
  .pill-chi {{ background:#ecfdf5; color:var(--chi); border-color:#bbf7d0; }}
  .pill-mot {{ background:#fff7ed; color:var(--mot); border-color:#fed7aa; }}
  .bar {{ position:relative; height:14px; background:#f3f4f6; border-radius:7px; overflow:hidden; border:1px solid var(--border); }}
  .bar > span {{ position:absolute; top:0; left:0; height:100%; background:linear-gradient(90deg, var(--accent), #60a5fa); }}
  .kvs {{ display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; margin-top:8px; }}
  .kv {{ background:#ffffff; border:1px solid var(--border); padding:12px; border-radius:10px; box-shadow:0 1px 1px rgba(0,0,0,.03); }}
  .kv .t {{ font-size:12px; color:#6b7280; }}
  .kv .v {{ font:600 22px/1.2 ui-sans-serif, system-ui; margin-top:2px; }}
  .footnote {{ font-size:12px; color:#6b7280; }}
  .right {{ text-align:right; }}
  .small {{ font-size:12px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>{title}</h1>
  <p class="lead">MiiPro/Nanami（TYP）の *_gpu セッションを統合し、CHI/MOT 指標を横断表示しています。各行の「開く」から詳細レポート（report.html）に遷移できます。</p>

  <div class="card">
    <h2>1. 概況（山下先生向け説明）</h2>
    <div class="row">
      <div>
        <div class="kvs">
          <div class="kv"><div class="t">セッション数</div><div class="v">{k_sessions}</div></div>
          <div class="kv"><div class="t">総トークン数（CHI / MOT）</div><div class="v">{k_tokens_chi:,} / {k_tokens_mot:,}</div></div>
          <div class="kv"><div class="t">平均MLU（CHI / MOT）</div><div class="v">{h(k_mlu_chi)} / {h(k_mlu_mot)}</div></div>
        </div>
      </div>
      <div class="card">
        <div class="small">
          本ダッシュボードは、日本語TYPコーパス（MiiPro/Nanami）の母子対話音声から、
          <b>Whisper-small(GPU)</b> による自動文字起こしと、<b>F0クラスタ（高F0=CHI）</b>による話者割当を行い、
          発話/語用論/韻律の主要指標を自動集計したものです。近接する短文の復唱や重複は自動で折り畳み、
          公平性のため中央9分窓にクリップして可視化しています（MVP仕様）。
          臨床評価用途では、追加の手動検証・精緻化を推奨します。
        </div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>2. セッション別サマリー</h2>
    <table>
      <thead>
        <tr>
          <th>Session</th>
          <th class="right">CHI 発話/Token/MLU</th>
          <th class="right">MOT 発話/Token/MLU</th>
          <th class="right">Token比 CHI/MOT</th>
          <th class="right">F0 平均 (CHI/MOT)</th>
          <th class="right">質問率 % (CHI/MOT)</th>
          <th class="right">Echoes / NearDups</th>
          <th class="right">レポート</th>
        </tr>
      </thead>
      <tbody>
        {''.join(tr_html)}
      </tbody>
    </table>
  </div>

  <div class="card">
    <h2>3. CHI vs MOT の可視化（Token 比）</h2>
    {''.join(bars_html)}
    <div class="footnote">バーは CHI/MOT の Token 比（&gt;1 で CHI が多い）を示します。</div>
  </div>

  <div class="card">
    <h2>方法と前提（要約）</h2>
    <ul class="small">
      <li>対象: <code>*_gpu</code> のみ（GPU実行で得たセッション）</li>
      <li>データ: CHILDES <b>MiiPro/Nanami</b>（TYP）各 mp3</li>
      <li>ASR: OpenAI Whisper <code>small</code>（GPU）、日本語固定、温度=0、Beam=5</li>
      <li>話者: F0 と RMS による2クラスタ → 高F0側を CHI、低F0側を MOT</li>
      <li>重複処理: 隣接の短文復唱（echo）・近傍重複（near dup）を類似度しきいで折り畳み</li>
      <li>集計: 発話数、Token数、MLU、F0、発話間隔、質問率、談話標識/心的語彙（100語当たり）など</li>
      <li>ウィンドウ: 全体から中央 9分相当を抽出（比較の公平性）</li>
      <li>注意: 本MVPは自動処理を前提。研究報告・臨床応用には人手確認を併用</li>
    </ul>
  </div>

</div>
</body>
</html>
"""
    out_html.write_text(html, encoding="utf-8")
    print(f"[ok] wrote dashboard HTML: {out_html}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="*_gpu セッションフォルダが並ぶディレクトリ（例: /Users/you/cpsy/out/audio/Nanami）")
    ap.add_argument("--out", default=None, help="出力HTMLパス（省略時は <root>/Nanami_dashboard.html）")
    ap.add_argument("--title", default="ASD 音声MVP ダッシュボード（Nanami / TYP）")
    ap.add_argument("--link_mode", choices=["file","pages"], default="file", help="report.htmlへのリンク方式: file=ローカル, pages=相対リンク")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.exists():
        raise SystemExit(f"[error] root が見つかりません: {root}")

    out_html = Path(args.out) if args.out else (root / "Nanami_dashboard.html")
    out_html.parent.mkdir(parents=True, exist_ok=True)

    build_dashboard(root, out_html, args.title, args.link_mode)

if __name__ == "__main__":
    main()
