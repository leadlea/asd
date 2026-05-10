# 参考文献（Bibliography）整合性チェック

作成日：2026-05-08（金）
作成者：福原玄
目的：paper1_ja.tex の `\bibitem` 17件 + #867 レビューで追加候補の5件 = **計22件**について、書誌情報の実在性・正確性を第三者データベース（PubMed/arXiv/ResearchGate/Springer/Wiley 等）で検証し、英語化投稿前のクリーンアップ対象を洗い出す。

---

## サマリー

| 状態 | 件数 | 概要 |
|:---:|---:|:---|
| ✅ 実在・正確 | 12 | 書誌情報に問題なし |
| ⚠️ 軽微な修正が必要 | 5 | article number / subtitle / ページ番号等の誤記 |
| 🚨 **幻覚の疑いあり** | 1 | 検索で一切ヒットせず、要精査（**Altozano 2026**） |
| 🆕 追加候補（#867対応） | 5 | 性差・年齢関連で追加予定 |
| 📝 存在未確認 | 1 | nakamura 2025（国内紀要、日本語）|
| **合計** | **22** | |

---

## 1. 既存17件の詳細チェック

### 🚨 重大な問題: 幻覚引用の疑い

#### #2 altozano2026 ← **検索で一切ヒットしない**

現行記述:
> Altozano, A., et al. (2026). Enhancing psychological assessments with open-ended questionnaires and large language models: An ASD case study. *IEEE Journal of Biomedical and Health Informatics*, 30(2), 1082-1093.

検証結果:
- IEEE Xplore, Google Scholar, Semantic Scholar いずれでも該当論文が検出されない
- タイトル + 著者名での検索でも関連論文が見つからない
- IEEE JBHI 2026 Vol.30 Issue 2 のページ範囲・著者とも一致する情報なし

**考えられる原因**:
1. LLM（本プロジェクトで利用）が生成した幻覚引用である可能性
2. 論文が in press で未索引化の可能性（低い。2026 は既に発行中）
3. 著者名または掲載誌の誤記の可能性

**推奨アクション**:
- 本引用の出所（どの段階で bibliography に追加されたか）を git log で遡及確認
- 本当に参照した論文が別にあれば正しい書誌情報に差し替え
- 該当論文が見つからない場合は**引用ごと削除**（投稿前に必須。幻覚引用は査読で即 reject 要因）
- 論文本文（paper1_ja.tex L78, L1471）での参照箇所: Hu 2025 / Mun 2024 とセットで「LLM を用いた ASD 分類の先行研究」として引用されているため、**1つ削除しても主張は維持できる**

### ⚠️ 軽微な誤記

#### #1 hu2025 — article number が誤り

現行: `*npj Digital Medicine*, 8, Article 302.`
正しい: `*npj Digital Medicine*, 8:763. doi: 10.1038/s41746-025-02133-9`（2025年12月16日掲載）

出典: https://pmc.ncbi.nlm.nih.gov/articles/PMC12708842/

**推奨**: "Article 302" → "Article 763" に訂正、DOI 追加

#### #3 mun2024 — 書誌情報の更新候補

現行は arXiv preprint として引用。arXiv 2409.00158 で実在確認。
2025年の Interspeech に類似タイトルの続編が採択されている模様（ISCA archive 2025 mun25b_interspeech）。

**推奨**: arXiv 引用のままでも OK だが、peer-reviewed 版が出ている場合は切り替え検討。要フォローアップ。

#### #15 kita2007 — サブタイトルが誤っている可能性

現行: `Kita, S. & Ide, S. (2007). Nodding, aizuchi, and final particles in Japanese conversation: How important is non-verbal signaling in a heavily verbal culture? *Pragmatics*, 17(2), 279-311.`

検証で見つかった正しいサブタイトル（ResearchGate/Pragmatics誌）:
`Nodding, aizuchi, and final particles in Japanese conversation: How conversation reflects the ideology of communication and social relationships`

出典: https://www.researchgate.net/publication/223678243

**推奨**: サブタイトルを `"How conversation reflects the ideology of communication and social relationships"` に修正

#### #4 nakamura2025 — 書誌情報の完備化

現行: `ADOS-2会話テキストからのASD分類: BERT由来特徴量とLightGBMによる検討. SICE東北支部研究会資料, 353-9.`

**推奨**:
- 国内紀要のため web 検索での実在確認が困難
- 著者初期、巻号、ページ範囲をフルに補完することが望ましい
- CiNii 等で最終確認を投稿前に実施

#### #14 meylan2014 — 年度の注意

現行: `Meylan, S. C. & Gahl, S. (2014).`
**正しくは 2014 で確認できたが**、Cognitive Science Society Proceedings は各年度で巻号が変わるので、Volume 36 の記載は正確。

**推奨**: 現状維持で OK。念のため論文タイトルと該当年度を再確認。

### ✅ 実在・書誌情報が正確な12件

| # | Key | 確認結果 |
|:-:|:---|:---|
| 5 | sacks1974 | Language, 50(4), 696-735 — 古典的文献、書誌情報 OK |
| 6 | schegloff1977 | Language, 53(2), 361-382 — 古典的文献、書誌情報 OK |
| 7 | levitan2012 | NAACL-HLT 2012, 11-19 — OK |
| 8 | deruiter2006 | Language, 82(3), 515-535 — OK |
| 9 | campione2002 | Speech Prosody 2002, 199-202 — OK |
| 10 | clark1996 | Using Language (Cambridge UP) — 古典書籍、OK |
| 11 | watanabe2003 | ICPhS-15, 2473-2476 — OK |
| 12 | kendrick2015 | Open Linguistics 1(1), 164-190 — OK |
| 13 | albert2018 | Topics in Cognitive Science 10(2), 279-313 — OK |
| 16 | holm1979 | Scandinavian Journal of Statistics 6(2), 65-70 — OK |
| 17 | dindar2022 | Language and Cognition 14(4), 556-580 — OK |

---

## 2. #867 追加候補5件の書誌情報確定

### 新規追加（推奨）

#### (A) Bortfeld, H., Leon, S. D., Bloom, J. E., Schober, M. F., & Brennan, S. E. (2001)

- タイトル: **Disfluency rates in conversation: Effects of age, relationship, topic, role, and gender**
- 掲載誌: *Language and Speech*, 44(2), 123-147
- DOI: 10.1177/00238309010440020101
- 出典: https://journals.sagepub.com/doi/10.1177/00238309010440020101 / https://pubmed.ncbi.nlm.nih.gov/11575901/
- 引用用途: A3（年齢×フィラー増加）の直接根拠

#### (B) Horton, W. S., Spieler, D. H., & Shriberg, E. (2010)

- タイトル: **A corpus analysis of patterns of age-related change in conversational speech**
- 掲載誌: *Psychology and Aging*, 25(3), 708-713
- PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC2943985/
- 引用用途: A1/A2（年齢と話速・沈黙）— 本研究の結果と逆方向である可能性を議論する根拠

#### (C) Laserna, C. M., Seih, Y.-T., & Pennebaker, J. W. (2014)

- タイトル: **Um... Who Like Says You Know: Filler Word Use as a Function of Age, Gender, and Personality**
- 掲載誌: *Journal of Language and Social Psychology*, 34(3), 328-338
- DOI: 10.1177/0261927X14526993
- 出典: https://www.researchgate.net/publication/275005568
- 引用用途: S3（フィラーの性差、計画フィラー vs discourse marker の区別）

> **注意**: 発行年は 2014 だが、掲載巻は Vol.34 (2015)。**APA 7 形式では発行年を 2014 で統一**（online first の年）。論文本文引用時に year の整合性を注意。

#### (D) Leaper, C., & Ayres, M. M. (2007)

- タイトル: **A meta-analytic review of moderators of gender differences in adults' talkativeness, affiliative, and assertive speech** (※論文では略称で "A meta-analytic review of gender variations..." と記載されることもあるが、正式タイトルは上記)
- 掲載誌: *Personality and Social Psychology Review*, 11(4), 328-363
- DOI: 10.1177/1088868307302221
- 出典: https://leaper.sites.ucsc.edu/publications/
- 引用用途: S1（発話率の性差、英語圏メタ分析）

#### (E) Tanaka, L. (2004)

- タイトル: ***Gender, Language and Culture: A Study of Japanese Television Interview Discourse***（書籍）
- 出版社: John Benjamins（Studies in Language Companion Series）
- 出典: https://catalog.princeton.edu/catalog/99125346413406421 / https://muse.jhu.edu/article/207185/summary
- 引用用途: 日本語テレビインタビュー談話における性・年齢・地位の非対称性

---

## 3. 投稿前 クリーンアップ項目（優先順）

### 🚨 最優先（必須）

1. **altozano2026 の実在確認 or 削除**
   - 論文ドラフト（paper1_ja.tex L78, L1471）で2箇所参照されている
   - 該当論文が見つからなければ、Hu 2025 / Mun 2024 / Nakamura 2025 のセットに留めて削除
   - 削除後は論文本文の参照箇所も整理

### ⚠️ 高優先

2. **hu2025 の article number 修正**（302 → 763）＋ DOI 追加
3. **kita2007 のサブタイトル修正**（"How important is non-verbal signaling..." → "How conversation reflects the ideology of communication and social relationships"）

### 📝 中優先（英訳時に対応）

4. **nakamura2025 の書誌情報完備化**（CiNii 等で著者初期、巻号、ページ範囲を確認）
5. **mun2024 の peer-reviewed 版への切り替え検討**（Interspeech 2025 採択版があるか確認）

### 🆕 新規追加（山下先生レビュー後の本文修正と同時）

6. **#867 対応の5件を bibliography に追加**（上記A〜E）

---

## 4. BRM 投稿時の追加作業（英語化フェーズ）

- **APA 7 th edition スタイルへの統一**
  - 現状: `\bibitem{key} Author, A., & Author, B. (Year). Title. Journal, vol(issue), pages.`
  - APA 7 表記: 基本ほぼ同じだが、`et al.` の使用ルール、イタリックの範囲、DOI 必須などの点で細部注意
- **`.bib` ファイル化**
  - `paper1_en.bib` を新規作成し、22件（+追加）を `@article{}` / `@book{}` / `@inproceedings{}` で構造化
  - LaTeX テンプレ切り替え時に `\bibliography{paper1_en}` で読み込む
- **引用形式の統一**
  - 本文中の `\cite{hu2025}` → `\citet{hu2025}` / `\citep{hu2025}` に natbib 形式で書き分け
- **Reference 数の拡充検討**
  - 現状22件 → BRM 平均30〜60件
  - 追加候補: Big Five 性格推定、IPIP-NEO の原典（Goldberg 1992 / Johnson 2014）、Ridge 回帰、機械学習ベースライン

---

## 5. 検証ログ（再現可能性担保）

本メモで参照した検証ソース:
- PubMed / PMC: Hu 2025, Bortfeld 2001, Horton 2010
- arXiv: Mun 2024 (2409.00158)
- ResearchGate: Kita & Ide 2007, Laserna et al. 2014
- SAGE Journals: Leaper & Ayres 2007, Bortfeld 2001
- Project MUSE / Princeton catalog: Tanaka 2004
- IEEE Xplore: altozano2026 で検索 → **ヒットなし**
- Google / Semantic Scholar: altozano2026 → ヒットなし

> 本調査は Web 検索結果に基づくため、IEEE 購読誌のみのアクセス制限、in-press 掲載等で一部情報が取得できない可能性がある。altozano2026 については図書館経由（UTokyo OPAC 等）の追加確認が望ましい。

---

## 6. 記録

| 日付 | 状態 | 担当 |
|:---:|:---|:---:|
| 2026-05-08 | 既存17件 + 追加候補5件の書誌情報を一括検証 | 福原 |
| 2026-05-08 | altozano2026 の幻覚引用疑いを発見、要フォローアップ | 福原 |
| 未定 | 山下先生レビュー後、クリーンアップ項目を論文本文に反映 | 福原 |
| 未定 | 英訳時に `.bib` ファイル化 + Reference 数拡充 | 福原 |
