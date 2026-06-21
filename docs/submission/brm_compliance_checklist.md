# BRM 投稿準備チェックリスト（Behavior Research Methods / Springer）

> 投稿先: Behavior Research Methods（Springer, Psychonomic Society）。最終投稿は英語。
> 運用: ステアリング `brm-journal-compliance.md` と対。状態は ✅完了 / 🔄進行中 / ⏳未着手 / ❓要確認 で更新。
> 一次ソース: https://link.springer.com/journal/13428/submission-guidelines
> 作成: 2026-06-21 / 最終更新: 2026-06-21

## A. ジャーナル規程の確定（❓は公式ページ動的描画で未抽出。投稿前に Editorial Manager で確定）

> 取得試行ログ（2026-06-21）: Springer submission-guidelines（link/www とも JS描画で本文抽出不可）、Psychonomic 公式ポリシー（HTTP 403）。数値規定は機械取得できず。確定手段=ブラウザで Editorial Manager のオンライン投稿規程を直接参照、または編集事務局へ照会。

| # | 項目 | 状態 | メモ |
|---|------|:---:|------|
| A1 | 参考文献スタイル = APA 7 | ✅ | 確定 |
| A2 | 投稿系統 = Springer Editorial Manager | ✅ | Hybrid 誌、Psychonomic Society 公式誌 |
| A3 | 本文 語数上限 | ❓ | BRM は抽出可能な範囲で厳密な総語数上限を明示せず。要 Editorial Manager 確認 |
| A4 | Abstract 語数上限 | ❓ | APA既定250語を暫定上限に執筆。BRM固有値は要確認（暫定値で本文を確定しない） |
| A5 | キーワード数 | ❓ | 5前後を暫定。要確認 |
| A6 | 受理原稿形式（LaTeX可否・テンプレ） | ❓ | LaTeX継続可か、Word指定か。Springer Nature LaTeX template の要否 |
| A7 | 引用パッケージ（apacite / biblatex-apa） | ❓ | LaTeX可の場合 |
| A8 | Article type 選択 | ❓ | Original/Research を想定（Tutorial 枠も別途あり） |
| A9 | 図表 点数・解像度・形式・カラー費 | ❓ | TIFF/EPS/PDF 等 |
| A10 | Highlights / Significance statement 要否 | ❓ | |
| A11 | stimuli・コードの公開推奨 | ✅ | BRM は読者が再利用しやすい形での公開を推奨（確定） |

## B. 開示・倫理ステートメント（Psychonomic Society 必須 / TOP Level 1）

> 確定根拠: Psychonomic Society Open Practices Statement（2018-07-11承認・2020-03更新）。Open Practices Statement は **(1) データ／マテリアルの公開可否と所在（公開時は永続識別子=DOI/URL必須）、(2) 事前登録の有無と対象** を必ず明記する。

| # | 項目 | 状態 | メモ |
|---|------|:---:|------|
| B1 | Open Practices Statement（データ可用性＋所在/DOI） | ⏳ | コーパス本文はライセンス上非公開。再現スクリプト・QCログ・sha256 を GitHub(leadlea/asd) で公開→**永続識別子(リリースタグ or Zenodo DOI)を付与**して所在明記 |
| B2 | Code / materials availability（同上 statement内） | ⏳ | コーパス非公開の理由（ライセンス・容量）も明記 |
| B3 | Preregistration の有無 | ⏳ | 未登録なら statement に「事前登録なし」と明記（必須記載） |
| B4 | Ethics approval / Consent | ⏳ | CEJC二次利用の倫理的位置づけ。山下先生と要相談 |
| B5 | Competing interests | ⏳ | |
| B6 | Funding statement | ⏳ | |
| B7 | Author contributions（CRediT） | ⏳ | 福原=実装/分析/執筆、山下=監修、宗田さん=助言 |
| B8 | 全著者 ORCID | ⏳ | |
| B9 | Open Practices badges 申請可否 | ⏳ | Open Data / Open Materials / Preregistered の3種 |
| B10 | **日本語要旨の併載**（Psychonomic は英語以外の要旨を許可） | ⏳ | 英語要旨の直下に日本語要旨を配置→受理時に併載（コピーエディット無し）。本研究の日本語ドラフト資産を活かせる |

## C. 参考文献クリーンアップ（bibliography_integrity_check.md と同期）

| # | 項目 | 状態 | メモ |
|---|------|:---:|------|
| C1 | altozano2026 → wright2026 (Nature Hum Behav) 差し替え | 🔄 | 山下先生Word戻り待ち→LaTeX同期。方法論的土台として位置づけ |
| C2 | hu2025 Article 763 + DOI 修正 | ⏳ | 英訳時 |
| C3 | kita2007 サブタイトル修正 | ⏳ | 英訳時 |
| C4 | nakamura2025 書誌細部の最終確認 | ⏳ | 原典PDFで確認済み、細部のみ |
| C5 | #867 追加5件（Bortfeld/Horton/Laserna/Leaper/Tanaka） | ⏳ | 性差・年齢の文脈特異性議論と同時 |
| C6 | Reference 数の拡充（現22件→BRM平均30〜60） | ⏳ | Big5×LLM原典、IPIP-NEO原典 等 |
| C7 | `paper1_en.bib` 化 + APA7統一 | ⏳ | 英訳フェーズ |

## D. 本文・図表の整合（日本語版で先行確定）

| # | 項目 | 状態 | メモ |
|---|------|:---:|------|
| D1 | 説明変数 = 19（Classical 10 / Novel 9）三者一致 | ✅ | abstract・本文・コード一致確認済(2026-06-21) |
| D2 | GroupKFold subject-wise split の用語統一（本文3箇所） | 🔄 | abstract済。1.3節/2.1節/2.4節に GroupKFold 明記（MTG6/22印あり） |
| D3 | Holm補正 補正前後p の併記 | ✅ | |
| D4 | p90 列削除（記述統計表） | ✅ | |
| D5 | IX_topic_drift_mean 除外（共線性） | ✅ | 統制変数化 |
| D6 | Results 構成（Soda案）反映 | ✅ | |
| D7 | 性差・年齢を「文脈特異性」で議論（#867） | 🔄 | 山下先生レビュー待ち |

## E. 英訳フェーズ

| # | 項目 | 状態 | メモ |
|---|------|:---:|------|
| E1 | `glossary_en.md` を唯一の用語辞書として確定 | 🔄 | 特徴量名・指標名・統計用語 |
| E2 | 本文中 `\cite` → `\citet`/`\citep` 書き分け | ⏳ | |
| E3 | APA構成へ並べ替え（Author note等） | ⏳ | |
| E4 | ネイティブ／専門校正 | ⏳ | |

## F. Word 運用（先生=Word派 / BRM=Word中心 / soda docx 正本）

> 役割: `paper1_ja.tex`=数値・再現ソース、`paper1_ja_st.docx`=協働・レビュー・投稿面。対応計画は `docs/homework/docx_comments_inventory.md`（宗田さん52コメント, Phase1〜5）を正本とする。

| # | 項目 | 状態 | メモ |
|---|------|:---:|------|
| F1 | pandoc reference-doc（テンプレートWord）方針確定 | ✅ | 既存 paper1_ja_st.docx をスタイル基準として流用（新規テンプレ作成は不要）。検証合格 2026-06-21 |
| F2 | LaTeX→docx 変換の runbook化＋スクリプト | ✅ | `scripts/build/latex_to_docx.sh` + `docs/submission/latex_to_docx_runbook.md`。出力 build/paper1_ja_pandoc.docx（git管理外）。画像22/表10/テンプレスタイル継承を確認 |
| F2b | 英語版変換ターゲット（APA .bib + citeproc） | ⏳ | paper1_en.bib 作成後に --citeproc/--csl=apa.csl を追加 |
| F3 | 宗田さんdocx編集の差分照合 #2011（個別教師記述の整理が削除過多でないか） | ⏳ | Word戻り受領時に最優先 |
| F4 | 宗田さんdocx編集の差分照合 #39（修正で主張が変わっていないか） | ⏳ | 同上 |
| F5 | 山下先生Word戻り → LaTeX後追い同期（先行確定しない） | 🔄 | altozano2026→wright2026差し替え等(C1)と連動 |
| F6 | 校閲記録(track changes)を保持したまま受け渡し | ⏳ | 削除記録の相互確認のため |

## 次の1手
本MTG（6/22）で日本語版の D2（GroupKFold用語統一）と D7（#867方針）を確定させ、確定後に A3〜A10 の [要確認] を Editorial Manager で一括確認するタスクを切る。
