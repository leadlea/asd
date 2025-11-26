# build_nanami_compare_html.py
# compare_nanami.py が出力した 3つの CSV を読み込み、
# GitHub Pages 用の比較レポート HTML を生成するスクリプト。
#
# 使い方:
#   python compare_nanami.py        # CSVを生成
#   python build_nanami_compare_html.py
# → web/nanami_compare.html が生成される

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent

# compare_nanami.py が書き出した CSV のパス
csv_dir = ROOT / "out" / "audio"
token_share_path = csv_dir / "nanami_compare_token_share.csv"
detail_path      = csv_dir / "nanami_compare_detail.csv"
totals_path      = csv_dir / "nanami_compare_totals.csv"

# 出力先 (GitHub Pages 用に web 配下に出す想定)
web_dir = ROOT / "docs"
web_dir.mkdir(parents=True, exist_ok=True)
html_path = web_dir / "nanami_compare.html"

# ---------- CSV 読み込み ----------
token_df  = pd.read_csv(token_share_path)
detail_df = pd.read_csv(detail_path)
totals_df = pd.read_csv(totals_path)

# ---------- (1) CHIトークン比をパーセント表示用に整形 ----------
token_view = token_df.copy()

for col in ["DIAR", "F0", "DIAR_minus_F0"]:
    if col in token_view.columns:
        # 0.774 -> 77.4 のように%
        token_view[col] = (token_view[col] * 100).round(1)

token_view.rename(
    columns={
        "session": "Session",
        "DIAR": "DIAR CHI Token %",
        "F0": "F0 CHI Token %",
        "DIAR_minus_F0": "DIAR − F0 (pt)"
    },
    inplace=True,
)

# ---------- (2) totals_df から8セッション合計の要約 ----------
def chi_share(method: str):
    sub = totals_df[totals_df["method"] == method]
    chi_tok = int(sub.loc[sub["role"] == "CHI", "n_tokens"].iloc[0])
    mot_tok = int(sub.loc[sub["role"] == "MOT", "n_tokens"].iloc[0])
    share = chi_tok / (chi_tok + mot_tok)
    return share, chi_tok, mot_tok

diar_share, diar_chi, diar_mot = chi_share("DIAR")
f0_share,   f0_chi,   f0_mot   = chi_share("F0")

# ---------- (3) HTML テーブル生成 ----------
def df_to_html_table(df: pd.DataFrame, table_id: str = "", wide: bool = False) -> str:
    classes = "tbl"
    if wide:
        classes += " tbl-wide"
    return df.to_html(
        index=False,
        classes=classes,
        border=0,
        justify="center"
    )

token_table_html  = df_to_html_table(token_view, table_id="tbl-token", wide=False)
detail_table_html = df_to_html_table(detail_df, table_id="tbl-detail", wide=True)

# ---------- (4) HTML テンプレ ----------
html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>Nanami/TYP 話者分離 比較レポート（pyannote vs F0）</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, "YuGothic", "Yu Gothic", sans-serif;
      margin: 0;
      padding: 24px;
      background: #f6f7fb;
      color: #222;
      line-height: 1.6;
    }}
    h1, h2, h3 {{
      margin: 0 0 0.5em;
    }}
    h1 {{
      font-size: 1.6rem;
      margin-bottom: 1rem;
    }}
    h2 {{
      font-size: 1.3rem;
      margin-top: 2rem;
      border-left: 4px solid #3b82f6;
      padding-left: 0.5rem;
    }}
    p.lead {{
      margin-bottom: 1rem;
      color: #555;
    }}
    .badge {{
      display: inline-block;
      padding: 0.1em 0.6em;
      border-radius: 999px;
      font-size: 0.8rem;
      background: #e5e7eb;
      margin-right: 0.4em;
    }}
    .card {{
      background: #fff;
      border-radius: 12px;
      padding: 16px 20px;
      box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
      margin-bottom: 16px;
    }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-top: 8px;
    }}
    .summary-item h3 {{
      font-size: 0.95rem;
      margin-bottom: 0.2rem;
      color: #555;
    }}
    .summary-item .value {{
      font-size: 1.2rem;
      font-weight: 600;
    }}
    .summary-item .sub {{
      font-size: 0.8rem;
      color: #777;
    }}
    .tbl-wrapper {{
      margin-top: 8px;
      overflow-x: auto;
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
      padding: 8px 12px;
    }}
    table.tbl {{
      border-collapse: collapse;
      width: 100%;
      font-size: 0.8rem;
    }}
    table.tbl thead tr {{
      background: #eff2fb;
    }}
    table.tbl th,
    table.tbl td {{
      padding: 6px 8px;
      border-bottom: 1px solid #e5e7eb;
      text-align: center;
      white-space: nowrap;
    }}
    table.tbl th {{
      font-weight: 600;
      color: #374151;
    }}
    table.tbl tr:nth-child(even) td {{
      background: #fafbff;
    }}
    table.tbl tr:hover td {{
      background: #e0f2fe;
    }}
    .tbl-wide {{
      font-size: 0.75rem;
    }}
    .note {{
      font-size: 0.8rem;
      color: #6b7280;
      margin-top: 4px;
    }}
    footer {{
      margin-top: 32px;
      font-size: 0.75rem;
      color: #9ca3af;
      text-align: right;
    }}
  </style>
</head>
<body>

  <h1>Nanami/TYP 話者分離 比較レポート（pyannote vs F0）</h1>
  <p class="lead">
    MiPro/Nanami（TYP）8セッション（10129〜20319）について、従来の <strong>F0しきい値ベース話者推定</strong> と
    <strong>pyannote.audio を用いた話者分離</strong> を比較した結果をまとめたレポートです。<br>
    compare_nanami.py が出力した CSV（token シェア・詳細・合計値）をもとに自動生成しています。
  </p>

  <div class="card">
    <span class="badge">Summary</span>
    <div class="summary-grid">
      <div class="summary-item">
        <h3>DIAR: CHI Token シェア</h3>
        <div class="value">{diar_share * 100:.1f}%</div>
        <div class="sub">CHI: {diar_chi:,} / MOT: {diar_mot:,} tokens</div>
      </div>
      <div class="summary-item">
        <h3>F0: CHI Token シェア</h3>
        <div class="value">{f0_share * 100:.1f}%</div>
        <div class="sub">CHI: {f0_chi:,} / MOT: {f0_mot:,} tokens</div>
      </div>
      <div class="summary-item">
        <h3>差（DIAR − F0）</h3>
        <div class="value">{(diar_share - f0_share) * 100:.1f} pt</div>
        <div class="sub">F0は系統的にCHIを少なめに推定</div>
      </div>
    </div>
  </div>

  <h2>1. セッション別 CHI トークン比（pyannote vs F0）</h2>
  <div class="tbl-wrapper">
    {token_table_html}
  </div>
  <p class="note">
    ※ 各セッションの CHI トークン比を 0–100% で表示。<br>
    DIAR − F0 が正のとき、F0法が子ども発話を少なめに見積もっていたことを意味します。
  </p>

  <h2>2. セッション別 詳細指標（utterance数 / Token数 / MLU / Prosody / 語用論）</h2>
  <div class="tbl-wrapper">
    {detail_table_html}
  </div>


  <footer>
    Generated by build_nanami_compare_html.py
  </footer>
</body>
</html>
"""

# ---------- (5) 書き出し ----------
html_path.write_text(html, encoding="utf-8")
print(f"HTML written to: {html_path}")
