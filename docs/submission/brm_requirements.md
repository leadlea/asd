# Behavior Research Methods（BRM）投稿要件の事前チェック

作成日：2026-05-10（日）
作成者：福原玄
目的：論文英語化前に BRM の投稿要件を把握し、現状の paper1_ja.tex が要件内に収まっているか、英訳後に調整が必要な箇所を事前に洗い出す。

---

## ジャーナル基本情報

- **タイトル**: Behavior Research Methods (BRM)
- **出版社**: Springer Nature（Psychonomic Society の公式ジャーナル）
- **Publishing Model**: Hybrid（Subscription + Open Access オプション、OA は APC あり）
- **Impact Factor**: ~2.8（2024-2025）
- **スコープ**: experimental psychology における方法・技法・計測機器。特に computer technology を用いた psychological research、刺激開発、実用的なデータ分析を重視。**「読者が自身の研究に応用できるように書く」ことを奨励**（本研究の「相互行為特徴量の定量化指標の提案」と非常に相性が良い）
- **Submission URL**: https://link.springer.com/journal/13428/submission-guidelines
- **How to publish**: https://link.springer.com/journal/13428/how-to-publish-with-us

---

## 投稿前チェックリスト（現状との対比）

| 項目 | BRM 要件（推定）| 現状（paper1_ja.tex） | 評価 | 英訳後の追加作業 |
|---|---|---|:-:|---|
| Article type | Original Article が主、Tutorial / Correspondence 等あり | Original Article 相当 | ✅ | 投稿時に選択 |
| Abstract 語数 | 250語以内（Springer 標準） | 日本語 ~500字程度 | ⚠️ | 英訳時に 200-250 語に圧縮 |
| 本文語数 | 厳密な上限明記なし、通常 6000〜10000語程度 | 日本語 ~47ページ、英訳後推定 6000-8000語 | ✅ | 要件内に収まる想定 |
| Reference 数 | 明記なし、通常 30〜60件 | 19件（+ #867で5件追加候補 = 24件） | ⚠️ | 英訳時にもう少し厚み（+5〜10件）を検討 |
| Reference style | **APA 7th edition**（Psychonomic Society 標準） | 現在 `\begin{thebibliography}` の形式、APA 寄り | 🟡 | `natbib` / `apacite` / `biblatex-apa` への切り替えを英語化時に実施 |
| Manuscript 形式 | 投稿時は **double-spaced**（APA 標準） | 現在シングル | 🟡 | 投稿用ドラフトで double-spaced に設定 |
| LaTeX テンプレ | Springer Nature LaTeX authoring template あり（推奨） | uplatex + dvipdfmx（日本語用） | 🟡 | 英語化時に Springer template へ移行 |
| Figures / Tables | 明示的な上限なし、本文必要分 + Supplementary を推奨 | Figures 7 + Tables 7 + Supplementary 2 程度 | ✅ | 問題なし |
| Figure 解像度 | 通常 300 dpi 以上 | 現在 `dpi=300` で生成済み | ✅ | なし |
| Data / Code Availability | 推奨（trusted repository）| [GitHub](https://github.com/leadlea/asd) で公開済み | ✅ | submission cover letter と Data Availability Statement に明記 |
| Ethical Responsibilities | 必須（Compliance with Ethical Standards）| 現在明記なし | ⚠️ | 英訳時に追加（CEJC 利用規約遵守、倫理審査の有無を記述）|
| Funding / Competing Interests | 必須 | 現在明記なし | ⚠️ | 英訳時に追加 |
| Supplementary Material | 許容（重要分析の補足として推奨）| 既に Appendix 2節（感度分析・交絡変数）構造あり | ✅ | そのまま Supplementary Material として分離 |
| 著者情報 | 所属・連絡先 | 現在日本語で記載 | ⚠️ | 英訳時に所属正式名（合同会社 Lead lea / NCNP）を英語で統一 |
| 匿名化（peer review）| 近年は **anonymization required**（著者情報をタイトルページから分離）| 未対応 | ⚠️ | 投稿時にタイトルページを分離 |

凡例: ✅ 問題なし / 🟡 形式調整のみ / ⚠️ 英訳時に内容追加が必要

---

## カテゴリ別の対応方針

### 1. 英訳の前に検討しておくべき点（構造判断）

1. **Article type の決定**
   - 本論文は「相互行為特徴量の定量化指標の提案」＋「妥当性検証」なので、**Original Article** が最適。
   - Tutorial 投稿（2026年3月 priority 締切）は本研究の性質と合わない。

2. **タイトル候補の絞り込み**
   - 現行: 「日本語日常会話における相互行為特徴量の定量化指標の提案——コーパス基本情報および Big5 性格特性による妥当性検証」
   - 英語候補 3案:
     - *Quantifying Interactional Features of Japanese Everyday Conversation: Validation via Corpus Metadata and LLM-estimated Big5 Personality*
     - *Interactional Feature Extraction from Japanese Conversation: A Validation Framework Using LLM-based Personality Scoring*
     - *Proposing and Validating Interactional Features in Japanese Everyday Conversation with LLM-based Big5 Personality Scoring*
   - BRM は method 提案寄りなので、**"Quantifying"** で始めるタイトルが審査員の目を引きやすい。

3. **Abstract 圧縮（200〜250語）**
   - 日本語 abstract → 英語 abstract は「構造化（Background / Method / Results / Conclusion）」が推奨。
   - 重要な数値（N=120, 19 features, 4 LLM teachers, Cの r≒0.43 など）を必ず含める。

### 2. 英訳時に発生する形式調整

1. **Reference style を APA 7 に変換**
   - 現行: `\begin{thebibliography}{99} \bibitem{...} ...`
   - 移行先: `natbib` + `apacite` または `biblatex-apa` で `.bib` ファイルに集約
   - 全24件を `.bib` に転記、APA スタイルで書誌情報を整える

2. **LaTeX テンプレート切り替え**
   - `uplatex` + `dvipdfmx` → Springer Nature LaTeX template（`pdflatex` 系）
   - 日本語版は paper1_ja.tex として保持、英語版を paper1_en.tex として新規作成し、両立
   - Springer Nature LaTeX template: https://www.springernature.com/gp/authors/campaigns/latex-author-support

3. **double-spaced ドラフトの用意**
   - `\usepackage{setspace}` + `\doublespacing` で対応

### 3. 投稿直前に追加する情報

1. **Data Availability Statement**
   - 例: "The code and intermediate artifacts supporting this study are openly available at https://github.com/leadlea/asd. The CEJC corpus is publicly available from the National Institute for Japanese Language and Linguistics under their data use agreement; raw transcripts are not redistributed in this repository due to licensing constraints."

2. **Ethical Compliance**
   - CEJC は公開コーパスで倫理審査不要（二次利用）であることを明記
   - LLM 利用について、Bedrock API のプライベートネットワーク運用とモデル仕様を明記

3. **Competing Interests**
   - 該当なし（None declared）

4. **Author Contributions (CRediT)**
   - 福原玄: Conceptualization, Methodology, Software, Formal analysis, Data curation, Writing (original draft)
   - 山下祐一: Conceptualization, Supervision, Writing (review & editing)
   - 宗田卓史: Methodology, Writing (review & editing)

5. **Funding**
   - 該当あれば明記（NCNP 共同研究等）

---

## リスク / 懸念点

### リスク1: Reference 数が少なめ
現状19件、英訳時に追加しても24件程度。BRM 平均は30〜60件。**足りない可能性**。
- **対策**: 英訳時に以下のカテゴリで引用を追加検討
  - LLM-based assessment 系（既に Hu 2025, Altozano 2026, Mun 2024 等はあり、1〜2件追加）
  - Big5 性格推定の既存手法（IPIP-NEO 原典、Big5 prediction のベンチマーク論文）
  - Ridge 回帰・Permutation test・Bootstrap の古典
  - 日本語会話特徴量の既存研究（Maynard 1989, 泉 2004 等）

### リスク2: CEJC データ制約
本文テキストをリポジトリに含められない、という制約は査読者に説明が必要。
- **対策**: Data Availability Statement と Method セクションで明確に記述。コード・中間成果物・特徴量ハッシュは GitHub に公開済み。

### リスク3: LLM 仮想教師の妥当性
BRM は "practical data analysis" を扱うので、仮想教師の妥当性検証（ベースライン検証・Dose-Response）が既に組み込まれている点は査読耐性が高い。
- **対策**: 現状維持で問題なし。ただし、LLM のモデルバージョンとデータ取得日付を明記することが Method の再現性に重要。

### リスク4: 新規性の位置づけ
BRM は method 提案ジャーナルなので、「19の特徴量を提案」がメイン貢献であることを Introduction/Discussion で明確にすべき。
- **対策**: 既存の論文構造は「特徴量提案 + 2段階妥当性検証」で整合しているので問題なし。英訳時に **Contributions** として箇条書きを Introduction 末尾に追加することを検討。

---

## 英訳ロードマップ（案）

Phase 0（準備） — レビュー対応後に着手
1. paper1_ja.tex の最終版を確定（山下先生レビュー反映後）
2. 引用候補を洗い出し（24 → 30〜40件を目標）
3. .bib ファイルを作成（既存 `\bibitem` を APA 形式に変換）

Phase 1（素案）— 1週間程度
4. タイトル・Abstract・Introduction・Method のドラフト英訳
5. Results は数値・図表キャプションから先に英訳
6. Discussion・Limitations・Conclusion は論旨を維持しつつ簡潔に

Phase 2（Springer テンプレ化）— 2〜3日
7. Springer Nature LaTeX template に移植
8. APA reference style の設定
9. figure 再配置（英語キャプション）

Phase 3（共著者レビュー）— 1〜2週間
10. 山下先生・宗田さんに英訳ドラフトを共有
11. 言い回しとロジックの最終調整

Phase 4（投稿準備）— 数日
12. Cover Letter 作成
13. Data Availability Statement / Ethical Compliance / Funding / CRediT の追記
14. 著者情報を分離したタイトルページ作成
15. 最終コンパイル確認

Phase 5（投稿）
16. https://link.springer.com/journal/13428/submission-guidelines から投稿
17. PsyArXiv preprint も同時公開

---

## 付録：確認済みの情報源

- BRM submission guidelines: https://link.springer.com/journal/13428/submission-guidelines（Cookie 壁で全文未取得、要フォローアップ）
- BRM how to publish: https://link.springer.com/journal/13428/how-to-publish-with-us
- Psychonomic Society BRM page: https://www.psychonomic.org/page/brm
- Springer Nature LaTeX template: https://www.springernature.com/gp/authors/campaigns/latex-author-support/see-where-our-services-will-take-you/18782940
- APA 7 citation example: Springer - Vancouver style は別、BRM は APA 7 が実態

> **Content was rephrased for compliance with licensing restrictions.** 本メモは公開情報と Springer 系列誌の共通要件から推定した内容を含む。投稿直前には公式 submission guidelines の原文を一度全件確認すること（Cookie 同意後にアクセス可能）。

---

## 記録

| 日付 | 状態 | 担当 |
|:---:|:---|:---:|
| 2026-05-08 | 投稿要件の棚卸し・現状との差分評価 | 福原 |
| 未定 | 山下先生レビュー反映後、英訳 Phase 0 開始 | 福原 |
| 未定 | 公式 submission guidelines 原文の再確認 | 福原 |
