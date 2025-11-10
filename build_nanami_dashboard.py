#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Nanami / TYP ダッシュボード生成スクリプト（*_gpu フォルダのみ対象 / 白背景UI）
GitHub Pages 公開向けに、report.html へのリンクを
 - pages: 出力HTMLからの相対パス
 - file : file:// スキーム
で出力できます。

【変更点】
- 空CSV（duplicates.csv / echoes.csv など）は警告なくスキップ（0件扱い）
- ルート直下に Nanami_summary.csv を出力
"""

import sys
import argparse
import glob
import urllib.parse
from pathlib import Path
from datetime import datetime

import pandas as pd
from pandas.errors import EmptyDataError


# --------- utils ---------
def read_csv_quiet(path: Path) -> pd.DataFrame:
    """
    空/欠損/壊れたCSVは DataFrame() を返し、警告は出さない。
    """
    try:
        if not path.exists() or path.stat().st_size == 0:
            return pd.DataFrame()
        return pd.read_csv(path)
    except (EmptyDataError, OSError, UnicodeDecodeError, ValueError):
        return pd.DataFrame()
    except Exception:
        # 予期しないエラーでもダッシュボード生成は継続
        return pd.DataFrame()


def to_file_uri(p: Path) -> str:
    try:
        ap = p.resolve().as_posix()
        return "file://" + urllib.parse.quote(ap)
    except Exception:
        return ""


def fmt_num(x, digits=2, integer=False) -> str:
    try:
        if integer:
            return f"{int(round(float(x))):,}"
        return f"{float(x):,.{digits}f}"
    except Exception:
        return "—"


# --------- core ---------
def build_dashboard(root: Path, out_html: Path, title: str, link_mode: str) -> None:
    root = root.resolve()
    sess_dirs = sorted([Path(p) for p in glob.glob(str(root / "*_gpu")) if Path(p).is_dir()])

    rows = []
    for d in sess_dirs:
        turns = read_csv_quiet(d / "turns.csv")
        pros  = read_csv_quiet(d / "prosody.csv")
        prag  = read_csv_quiet(d / "pragmatics.csv")
        echoes = read_csv_quiet(d / "echoes.csv")
        dups   = read_csv_quiet(d / "duplicates.csv")
        report = d / "report.html"

        # 主要CSVがすべて空ならスキップ
        if turns.empty and pros.empty and prag.empty:
            continue

        tmap = {r["role"]: r for _, r in turns.iterrows()} if not turns.empty else {}
        pmap = {r["role"]: r for _, r in pros.iterrows()} if not pros.empty else {}
        gmap = {r["role"]: r for _, r in prag.iterrows()} if not prag.empty else {}

        def get_num(m, role, key, default=0.0):
            try:
                v = m.get(role, {}).get(key, default)
                return float(v)
            except Exception:
                return default

        if link_mode == "pages":
            report_href = f"./{d.name}/report.html" if report.exists() else ""
        else:
            report_href = to_file_uri(report) if report.exists() else ""

        # echoes / near_dups は空CSVなら 0
        echoes_n = 0 if echoes is None or echoes.empty else len(echoes.index)
        dups_n   = 0 if dups is None or dups.empty else len(dups.index)

        data = {
            "session": d.name.replace("_gpu", ""),  # 表示用
            "sess_dir": d.name,
            "chi_utts":  tmap.get("CHI", {}).get("n_utts", 0),
            "mot_utts":  tmap.get("MOT", {}).get("n_utts", 0),
            "chi_tokens": tmap.get("CHI", {}).get("n_tokens", 0),
            "mot_tokens": tmap.get("MOT", {}).get("n_tokens", 0),
            "chi_mlu":    tmap.get("CHI", {}).get("mlu", 0.0),
            "mot_mlu":    tmap.get("MOT", {}).get("mlu", 0.0),
            "chi_f0":     pmap.get("CHI", {}).get("f0_mean", 0.0),
            "mot_f0":     pmap.get("MOT", {}).get("f0_mean", 0.0),
            "chi_q":      get_num(gmap, "CHI", "question_rate", 0.0),
            "mot_q":      get_num(gmap, "MOT", "question_rate", 0.0),
            "echoes":     echoes_n,
            "near_dups":  dups_n,
            "report_uri": report_href,
        }
        rows.append(data)

    if not rows:
        raise SystemExit(f"[error] *_gpu の対象フォルダが見つかりませんでした: {root}")

    df = pd.DataFrame(rows).sort_values("session")
    # 0除算ガード
    denom = df["mot_tokens"].replace(0, 1)
    df["token_ratio_chi_mot"] = pd.to_numeric(df["chi_tokens"], errors="coerce").fillna(0) / pd.to_numeric(denom, errors="coerce").fillna(1)

    # Summary CSV
    summary_csv = root / "Nanami_summary.csv"
    df_out = df[
        ["session", "chi_utts", "mot_utts", "chi_tokens", "mot_tokens",
         "chi_mlu", "mot_mlu", "chi_f0", "mot_f0", "chi_q", "mot_q",
         "echoes", "near_dups", "token_ratio_chi_mot", "report_uri"]
    ]
    df_out.to_csv(summary_csv, index=False, float_format="%.6f")
    print(f"[ok] wrote summary CSV: {summary_csv}")

    # 概況値
    k_sessions = int(len(df))
    k_tokens_chi = int(pd.to_numeric(df["chi_tokens"], errors="coerce").fillna(0).sum())
    k_tokens_mot = int(pd.to_numeric(df["mot_tokens"], errors="coerce").fillna(0).sum())
    k_mlu_chi = float(pd.to_numeric(df["chi_mlu"], errors="coerce").fillna(0).mean())
    k_mlu_mot = float(pd.to_numeric(df["mot_mlu"], errors="coerce").fillna(0).mean())

    # テーブル行
    tr_html = []
    for _, r in df.iterrows():
        ratio = float(r["token_ratio_chi_mot"]) if pd.notna(r["token_ratio_chi_mot"]) else 0.0
        width_pct = max(0.0, min(200.0, ratio * 100.0))
        link_html = (f'<a class="btn btn-outline small" href="{r["report_uri"]}" target="_blank">開く</a>'
                     if r["report_uri"] else '<span class="muted small">—</span>')
        tr_html.append(f"""
        <tr>
          <td class="label"><b>{r['session']}</b></td>
          <td><span class="pill pill-chi">CHI</span> {fmt_num(r['chi_utts'],0,True)} / {fmt_num(r['chi_tokens'],0,True)} / {fmt_num(r['chi_mlu'])}</td>
          <td><span class="pill pill-mot">MOT</span> {fmt_num(r['mot_utts'],0,True)} / {fmt_num(r['mot_tokens'],0,True)} / {fmt_num(r['mot_mlu'])}</td>
          <td><div class="bar" title="{fmt_num(ratio)}"><span style="width:{width_pct}%"></span></div></td>
          <td>{fmt_num(r['chi_f0'])} / {fmt_num(r['mot_f0'])}</td>
          <td>{fmt_num(float(r['chi_q'])*100)} / {fmt_num(float(r['mot_q'])*100)}</td>
          <td>{int(r['echoes'])} / {int(r['near_dups'])}</td>
          <td>{link_html}</td>
        </tr>
        """)

    # 比率バー群
    bars_html = []
    for _, r in df.iterrows():
        ratio = float(r["token_ratio_chi_mot"]) if pd.notna(r["token_ratio_chi_mot"]) else 0.0
        width_pct = max(0.0, min(200.0, ratio * 100.0))
        bars_html.append(f"""
        <div style="display:grid;grid-template-columns:110px 1fr 60px;gap:10px;align-items:center;margin:8px 0;">
          <div class="muted small">{r['session']}</div>
          <div class="bar"><span style="width:{width_pct}%"></span></div>
          <div class="right small">{fmt_num(ratio)}</div>
        </div>
        """)

    # HTML
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
  body {{ margin:0; padding:24px; font:14px/1.6 system-ui,-apple-system,Segoe UI,Roboto,'Hiragino Sans','Noto Sans JP',Arial,sans-serif; background:var(--bg); color:var(--text); }}
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
  .meta {{ color:#6b7280; font-size:12px; margin-top:6px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>{title}</h1>
  <p class="lead">MiiPro/Nanami（TYP）の *_gpu セッションを統合し、CHI/MOT 指標を横断表示しています。各行の「開く」から詳細レポート（report.html）に遷移できます。</p>

  <div class="meta">Generated at: {generated_at}</div>

  <div class="card">
    <h2>1. 概況（山下先生向け説明）</h2>
    <div class="row">
      <div>
        <div class="kvs">
          <div class="kv"><div class="t">セッション数</div><div class="v">{k_sessions}</div></div>
          <div class="kv"><div class="t">総トークン数（CHI / MOT）</div><div class="v">{k_tokens_chi:,} / {k_tokens_mot:,}</div></div>
          <div class="kv"><div class="t">平均MLU（CHI / MOT）</div><div class="v">{fmt_num(k_mlu_chi)} / {fmt_num(k_mlu_mot)}</div></div>
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
    ap.add_argument("--link_mode", choices=["file", "pages"], default="file", help="report.html へのリンク方式: file=ローカル, pages=相対リンク")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.exists():
        raise SystemExit(f"[error] root が見つかりません: {root}")

    out_html = Path(args.out) if args.out else (root / "Nanami_dashboard.html")
    out_html.parent.mkdir(parents=True, exist_ok=True)

    build_dashboard(root, out_html, args.title, args.link_mode)


if __name__ == "__main__":
    main()
