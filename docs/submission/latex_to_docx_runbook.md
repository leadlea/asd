# Runbook: LaTeX → docx 変換（pandoc / Word 運用）

> 目的: `paper1_ja.tex`（数値・再現のソース）から、山下先生(Word派)・宗田さん・BRM(Word中心)向けの docx を再現可能に生成する。既存 `paper1_ja_st.docx` のレイアウトを reference-doc として再利用する（宗田さん助言）。
> 関連: `.kiro/steering/brm-journal-compliance.md`（F群）、`docs/submission/brm_compliance_checklist.md`、`docs/homework/docx_comments_inventory.md`。
> 作成: 2026-06-21 / 動作確認: pandoc 3.8.2 (macOS)

## 1. 前提
- pandoc 3.x（未導入なら `brew install pandoc`）
- リポジトリルートから実行する（`\input{reports/paper_figs_v2/...}` の相対パス解決のため）
- 図表は `reports/paper_figs_v2/` に生成済みであること（fig_*.png / tab_*.tex）

## 2. 実行
```bash
# 既定: paper1_ja.tex -> build/paper1_ja_pandoc.docx（reference-doc=paper1_ja_st.docx）
bash scripts/build/latex_to_docx.sh

# 引数指定: INPUT OUTPUT REFDOC
bash scripts/build/latex_to_docx.sh paper1_ja.tex build/paper1_ja_pandoc.docx paper1_ja_st.docx
```

## 3. スクリプトの要点（再現性・安全策）
- `--resource-path=.:reports/paper_figs_v2`: pandoc は `\graphicspath` を無視するため画像解決に必須。
- `--reference-doc=paper1_ja_st.docx`: **スタイルのみ**流用（本文内容はコピーされない）。チームの Word レイアウトを継承。
- `--mathml`: 数式を OMML 化（Word で編集可能）。
- 参考文献は `thebibliography`（ファイル内）。`.bib`/citeproc は不要。
- **上書きガード**: 出力が `paper1_ja_st.docx`（校閲正本）を指す場合は中断。生成物は `build/` 配下（git管理外）。

## 4. 変換結果の検証（2026-06-21 実施・合格）
| 項目 | 結果 |
|------|------|
| 画像埋め込み | 22 media ✅ |
| 表（w:tbl） | 10 ✅ |
| 見出しスタイル | reference-doc のスタイルID（1〜4）適用 ✅ |
| テンプレ継承 | Abstract / Author / ImageCaption / CaptionedFigure / TableCaption ✅ |
| 参考文献本文化 | Sacks / Schegloff / Kendrick / Levitan 等を確認 ✅ |
| LaTeXコメント漏れ（MTG6/22） | 0 ✅ |
| 数式 | MathML(OMML) ✅ |

検証コマンド例:
```bash
cd build && mkdir -p _inspect && cd _inspect && unzip -oq ../paper1_ja_pandoc.docx
ls word/media | wc -l                                   # 画像数
grep -oE '<w:pStyle w:val="[^"]*"' word/document.xml | sort | uniq -c | sort -rn
grep -c "MTG6/22" word/document.xml                     # 0 を確認
cd ../.. && rm -rf build/_inspect
```

## 5. 既知の制約 / 投稿前TODO
- **\cite はラベル描画**（番号/キー）。BRM=APA 7 の著者-年整形は英語版で `.bib` + citeproc 化が必要（`brm_compliance_checklist.md` C7/E2）。
- **見出しは reference-doc の数値スタイルID依存**。テンプレ docx を差し替えると ID が変わりうる。差し替え時は §4 の pStyle 確認を再実行。
- **校閲記録(track changes)は引き継がれない**。宗田さん/山下先生の Word とマージする際は、本変換 docx を「LaTeX 最新版の参照」として使い、正本は先生方の Word を維持する（先行確定しない）。
- longtable/booktabs の複雑な表は Word 上で軽微な手直しが要る場合がある。

## 6. 運用フロー（チーム）
1. LaTeX 側で数値・図表を確定（ソース・オブ・トゥルース）。
2. 本 runbook で docx 生成 → 内容確認。
3. 先生・宗田さんの Word 戻り（校閲記録つき）を**正本**として受領。
4. 戻り差分（#2011/#39 等）を照合し、LaTeX を後追い同期。
5. 投稿フェーズで APA `.bib` 化・英訳・reference-doc を投稿規程に合わせて更新。

## 次の1手
英語投稿に備え、`paper1_en.bib`（APA 7）を起こし、変換コマンドに `--citeproc --bibliography=paper1_en.bib --csl=apa.csl` を足した英語版ターゲットを本スクリプトに追加する。
