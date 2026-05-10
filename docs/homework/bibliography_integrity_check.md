# 参考文献（Bibliography）整合性チェック

作成日：2026-05-10（日）
作成者：福原玄
目的：paper1_ja.tex の `\bibitem` 17件 + #867 レビューで追加候補の5件 = **計22件**について、書誌情報の実在性・正確性を第三者データベース（PubMed/arXiv/ResearchGate/Springer/Wiley 等）で検証し、英語化投稿前のクリーンアップ対象を洗い出す。

---

## サマリー

| 状態 | 件数 | 概要 |
|:---:|---:|:---|
| ✅ 実在・正確 | 13 | 書誌情報に問題なし（nakamura2025 は原典PDFで実在確認済み。書誌細部は最終確認推奨） |
| ⚠️ 軽微な修正が必要 | 4 | article number / subtitle / ページ番号等の誤記 |
| 🔄 **差し替えが必要** | 1 | **altozano2026 は書誌情報の転記ミスだったと判明。山下先生からご紹介いただいた原典は Wright et al. 2026 (Nature Human Behaviour) であり、これが本研究の方法論的土台に該当する。** |
| 🆕 追加候補（#867対応） | 5 | 性差・年齢関連で追加予定 |
| **合計** | **22** | （既存17件 + 追加候補5件）|

---

## 1. 既存17件の詳細チェック

### 🔄 差し替えが必要: altozano2026 → Wright et al. 2026

#### #2 altozano2026 ← 山下先生からのメール原典と一致せず

現行記述:
> Altozano, A., et al. (2026). Enhancing psychological assessments with open-ended questionnaires and large language models: An ASD case study. *IEEE Journal of Biomedical and Health Informatics*, 30(2), 1082-1093.

検証結果:
- IEEE Xplore, Google Scholar, Semantic Scholar いずれでも該当論文が検出されない
- タイトル + 著者名での検索でも関連論文が見つからない
- IEEE JBHI 2026 Vol.30 Issue 2 のページ範囲・著者とも一致する情報なし

**メール原典の確認結果**:
- 山下先生のメールで紹介された論文は、実際には **Wright, A. G. C., Ringwald, W. R., Vize, C. E. et al. (2026). Assessing personality using zero-shot generative AI scoring of brief open-ended text. *Nature Human Behaviour*. https://doi.org/10.1038/s41562-025-02389-x** であった
- 現行の altozano2026 書誌情報は、参照元論文と一致していない（著者名・掲載誌・タイトル・巻号すべて異なる）
- したがって altozano2026 は **書誌情報の転記ミス**と判断してよい（原典 Wright et al. 2026 の書誌情報を bibitem として転記する際に、別の書誌情報が紛れ込んだもの）

**さらに重要な点**: Wright et al. 2026 は本研究の**方法論的土台**に該当する論文である。
- 複数LLMに性格尺度アイテムを Likert で答えさせる
- 複数LLM平均（アンサンブル）が自己報告と最も一致
- 自己報告との収束的妥当性 r ≈ .3〜.6
- 外的妥当性（日常感情・対人行動・精神病理予測）を確認

本研究の仮想教師プロトコル（4 LLM × IPIP-NEO-120 × アンサンブル平均）は、Wright et al. 2026 の方法論を日本語会話コーパスに適用・拡張したものとして位置づけるのが最も正確。

**推奨アクション**:
1. `\bibitem{altozano2026}` を削除し、`\bibitem{wright2026}` を新規追加
2. citation key `altozano2026` → `wright2026` に変更
3. 論文本文 L78（Introduction）L1471（Discussion）での引用文脈を書き直す
   - 現状は「ASD/TD 分類の先行研究」として誤った文脈で引用されている
   - Wright et al. 2026 は「ゼロショット LLM Big5 推定の方法論的土台」なので、Introduction の (b) 段落または新規段落で**本研究の方法論的基盤**として紹介するのが正確
4. Method 2.3（仮想教師プロトコル）でも Wright et al. 2026 を参照する1行を追加
   - 「本研究の仮想教師プロトコルは Wright et al. (2026) の複数LLMアンサンブルアプローチを日本語会話コーパスに適用したものである」
5. Discussion 4.6 で Wright et al. 2026 との比較を議論（r ≈ .3〜.6 vs 本研究の C: r ≈ .43 等）

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

#### #14 meylan2014 — 年度の注意

現行: `Meylan, S. C. & Gahl, S. (2014).`
**正しくは 2014 で確認できたが**、Cognitive Science Society Proceedings は各年度で巻号が変わるので、Volume 36 の記載は正確。

**推奨**: 現状維持で OK。念のため論文タイトルと該当年度を再確認。

### ✅ 実在・書誌情報が正確な13件

| # | Key | 確認結果 |
|:-:|:---|:---|
| 4 | nakamura2025 | SICE東北支部研究会資料 353-9（2025年）— 原典PDF（https://www.topic.ad.jp/sice/htdocs/papers/353/353-9.pdf）で実在確認。書誌細部（著者フルネーム・ページ範囲・DOI等）は投稿前に原典で最終確認推奨 |
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

### 🔄 最優先（レビュー戻り待ち・Wordでの修正確認が必要）

1. **altozano2026 → Wright et al. 2026 への差し替え（山下先生が Word で修正中の可能性が高い）**
   - 山下先生は `paper1_ja_st.docx` を Word で直接編集中のため、**bibliography と引用文脈はすでに差し替え済みの可能性がある**
   - 週末レビュー戻りの Word を受領した時点で、以下を確認・LaTeX に同期する:
     - `\bibitem{altozano2026}` が Wright et al. 2026 に差し替わっているか（Nature Hum Behav, 2026, DOI: 10.1038/s41562-025-02389-x）
     - 本文 L78（Introduction）/ L1471（Discussion）の引用文脈が ASD/TD 分類から「ゼロショット LLM Big5 推定の方法論的土台」に書き換わっているか
   - **Word 側に未反映の箇所があれば**、Method 2.3（仮想教師プロトコル）および Discussion 4.6 に本研究の方法論的基盤として Wright et al. 2026 を位置づける追記を改訂案として提示する
   - **こちら側で先行修正は行わず**、レビュー戻り内容との差分のみを LaTeX に同期するのが安全

2. **Hu 2025 の詳細言及の拡充（提案ベース）**
   - 山下先生のメール2通目で、Hu 2025 が ASD 関連の言語特徴を10個抽出している点（エコラリア、代名詞誤用、非典型的語用論パターン等）を紹介いただいた
   - 本研究の「相互行為特徴量を定量化する」アプローチとの対比として、Introduction または Discussion で引用内容を充実させる提案を残しておく
   - レビュー戻り時に、Word 側で既に拡充済みでなければ改訂案として提示する

### ⚠️ 高優先

2. **hu2025 の article number 修正**（302 → 763）＋ DOI 追加
3. **kita2007 のサブタイトル修正**（"How important is non-verbal signaling..." → "How conversation reflects the ideology of communication and social relationships"）

### 📝 中優先（英訳時に対応）

4. **nakamura2025 の書誌細部の最終確認**（原典PDF https://www.topic.ad.jp/sice/htdocs/papers/353/353-9.pdf で実在確認済み。著者フルネーム・ページ範囲・DOI 等の細部のみ投稿前に原典で確認）
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
- IEEE Xplore: altozano2026 で検索 → ヒットなし（主要DBで未index化の可能性）
- Google / Semantic Scholar: altozano2026 → ヒットなし

> 本調査は Web 検索結果に基づくため、IEEE 購読誌のみのアクセス制限、in-press 掲載等で一部情報が取得できない可能性がある。altozano2026 については山下先生のメールからの原典情報再取得を予定。

---

## 6. 記録

| 日付 | 状態 | 担当 |
|:---:|:---|:---:|
| 2026-05-08 | 既存17件 + 追加候補5件の書誌情報を一括検証 | 福原 |
| 2026-05-08 | altozano2026 は書誌情報の転記ミス（福原の記載ミス）と判明。山下先生からご紹介いただいた原典は Wright et al. 2026 (Nature Hum Behav) であり、本研究の方法論的土台に該当することが確認された | 福原 |
| 2026-05-08 | 山下先生が `paper1_ja_st.docx` で Wright et al. 2026 への差し替えを Word 直接編集で対応中の可能性あり。こちら側は先行修正せず、週末レビュー戻りとの差分を LaTeX に同期する方針とする | 福原 |
| 2026-05-10 | nakamura2025 の実在を原典PDF（https://www.topic.ad.jp/sice/htdocs/papers/353/353-9.pdf）で確認。サマリー表・§1・§3 を更新し「存在未確認」扱いを解消 | 福原 |
| 未定 | 週末レビュー戻りを受領後、Word 側の修正内容を確認し LaTeX に同期 | 福原 |
| 未定 | 英訳時に `.bib` ファイル化 + Reference 数拡充 | 福原 |
