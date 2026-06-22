# ADR-0010: 「NaN」表記の廃止 — 本文は「欠損値」、英語表・スクリプトは「missing」

- 状態: Accepted
- 日付: 2026-06-22
- 決定者: 福原玄（NCNP共同研究・筆頭）
- 関連: `paper1_ja.tex`（2.2.3 ほか）, `reports/paper_figs_v2/tab_feature_definitions.tex`, `scripts/paper_figs/feature_definitions.py`, ADR-0009

## コンテキスト

2.2.3（欠損値処理）等で計算機用語「NaN」をそのまま使用していた。一般読者・査読者には説明なしの「NaN」は伝わりにくく、「NaNとは？」と問われやすい。論文全体での統一が必要。

## 決定

1. 日本語本文の「NaN」を「欠損値」に置換（`〜はNaNとした`→`〜は欠損値とした`、`欠損（NaN）`→`欠損`）。
2. 読者に見える英語の特徴量定義表（`tab_feature_definitions.tex`）の `NaN if 〜` を `missing if 〜` に置換。
3. 再現性のため、生成元 `scripts/paper_figs/feature_definitions.py` の同一文字列も `missing if` に置換（次回再生成時も一致）。

## 反映箇所

| ファイル | 置換 | 件数 |
|------|------|------|
| paper1_ja.tex | `NaNとした`→`欠損値とした`, `欠損（NaN）`→`欠損` | 4 |
| tab_feature_definitions.tex（生成物） | `NaN if`→`missing if` | 15 |
| feature_definitions.py（生成元） | `NaN if`→`missing if` | 15 |

## 検証

- `NaN` 残存: 0（本文・生成表・生成元）。
- uplatex 2パス＋dvipdfmx: 正常、47ページ、未解決の参照・引用なし。
- 生成物と生成元の両方を更新したため、テーブル再生成時も整合。

## 次の1手

最新PDFで2.2.3の欠損値記述と特徴量定義表（missing表記）を確認。次の項目を待つ。
