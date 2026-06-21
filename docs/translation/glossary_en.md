# Japanese→English Glossary for paper1_ja.tex

作成日: 2026-05-10（日）
作成者: 福原玄
目的: 論文の自動翻訳→英語版作成時に、用語ブレをゼロに抑えるための**統一翻訳辞書**。
  DeepL / Claude / GPT への入力時に、この辞書に沿って事前置換または後処理を行う。
  特徴量19個の英語表記は `scripts/paper_figs/feature_definitions.py` を一次ソースとする。

---

## 使い方

1. **翻訳前**: 日本語原稿 (`paper1_ja.tex`) を章単位で LLM に投入する直前に、
   本glossaryを「翻訳時に以下の用語統一を厳守」というシステム指示として先頭に付与する。
2. **翻訳後**: Python の一括置換スクリプト（将来的に `scripts/translation/apply_glossary.py`）で
   残った日本語用語や揺れをダブルチェック。
3. **新語が出たら**: 本ファイルに追記 → git commit で用語の履歴を残す。

翻訳原則:
- 本研究で確立した固有名（相互行為特徴量、仮想教師など）は定訳を守る。
- BRM / APA7 では **American English** を基本（behavior, analyze, utilize ではなく use, など）。
- 略語は初出時に fullname(ABBR) 形式で導入し、以降は ABBR のみ。

---

## 1. 研究の骨格用語（Framework）

| 日本語 | English（定訳） | 備考 |
|:--|:--|:--|
| 相互行為特徴量 | interactional features | 単数 interactional feature, 複数 interactional features。本研究のメインコンセプト。"interaction features" は避ける |
| 定量化指標の提案 | proposal of quantitative indicators | Abstract・§3.4・§4.7 で頻出 |
| 定量化 | quantification | 動詞 quantify |
| 仮想教師 | virtual teacher | "pseudo-teacher" とはしない（統一） |
| 仮想教師プロトコル | virtual teacher protocol | §2.3 |
| 教師モデル | teacher model | LLM 教師のこと。"teacher LLM" とも可だが teacher model で統一 |
| 教師横断 | teacher-wise robust / across teachers | 文脈で使い分け |
| 教師間一致度 | inter-teacher agreement | §3.4.6。"teacher agreement" 単独は避ける |
| 教師モデル依存性 | teacher-model dependence | §3.4.2, §3.4.6 |
| 教師依存性が大きい | strongly teacher-model-dependent | |
| 頑健性 | robustness | |
| 頑健な予測 | robust prediction | |
| 説明可能性 | explainability | §1(b)。"interpretability" とは使い分け（XAI 文脈では explainability） |
| 解釈可能 | interpretable | |
| 循環的枠組み | cyclic framework | §1(d), §4.5, §4.6 |
| 相互補完 | mutual complementarity | §1(d) |
| LLMで推定→古典特徴量で解釈→新たな特徴量を定義→LLMで検証 | estimate with LLMs → interpret with classical features → define new features → validate with LLMs | §1(d) のまま構造保持 |

---

## 2. コーパス・データセット（Corpus / Dataset）

| 日本語 | English | 備考 |
|:--|:--|:--|
| 日本語日常会話コーパス | Corpus of Everyday Japanese Conversation | 初出で Corpus of Everyday Japanese Conversation (CEJC) と導入。以降 CEJC |
| CEJC home2サブセット | CEJC home2 subset | 固定表記 |
| home2 HQ1 | home2 HQ1 subset | 品質フィルタ HQ1 |
| 品質フィルタ（HQ1） | quality filter (HQ1) | |
| 自宅・少人数会話 | at-home conversations with few participants | home2 の説明 |
| 発話ペア数 | utterance pair count / number of adjacent pairs | 閾値: ≥80 |
| テキスト文字数 | text character count | 閾値: ≥2,000 |
| 質問直後ペア数 | post-question pair count | 閾値: ≥10 |
| 会話ID | conversation ID (conversation\_id) | コード変数名と同じ表記 |
| 話者ID | speaker ID (cejc\_person\_id) | |
| 話者.csv | speaker.csv | 固定 |
| 話者会話対応表.csv | speaker–conversation mapping table (speaker\_conversation.csv) | |
| ユニーク話者 | unique speakers | 本研究 N=74 |
| 会話×話者ペア | conversation × speaker pair / record | レコード単位 N=120 |
| レコード | record | 本研究の分析単位 |
| 話者の重複 | speaker overlap | |
| 重複話者 | overlapping speakers | |

---

## 3. 特徴量カテゴリ（Feature Categories）

| 日本語 | English | 備考 |
|:--|:--|:--|
| 既存研究ベースの特徴量 | Classical Features | 10個。固定表記 |
| 新規提案の特徴量 | Novel Features | 9個。固定表記 |
| タイミング系（PG） | Prosodic/Gap (PG) features | |
| フィラー系（FILL） | Filler (FILL) features | |
| 相互行為構造系（IX） | Interaction-structure (IX) features | |
| 応答型系（RESP） | Response-typing (RESP) features | |

---

## 4. 19特徴量の英訳（一次ソース: feature_definitions.py）

本文中での英語名は `scripts/paper_figs/feature_definitions.py` の `name` と `summary` を一次ソースとする。
LaTeX 本文中で `\texttt{PG\_speech\_ratio}` のように表記している変数名はそのまま維持する。
日本語名（例: 「発話率」）が本文中で variable name と併記されている箇所は、英訳時に variable name のみとするか、
`speech ratio (PG\_speech\_ratio)` の形式に統一する。

### 4.1 Classical Features（10個）

| 変数名 | 日本語名（本文中） | English summary（APA7表記） |
|:--|:--|:--|
| PG\_speech\_ratio | 発話率 | speech ratio |
| PG\_pause\_mean | 平均沈黙長 | mean pause duration |
| PG\_pause\_p50 | 沈黙長中央値 | median pause duration |
| PG\_pause\_p90 | 沈黙長90パーセンタイル | 90th percentile pause duration |
| PG\_resp\_gap\_mean | 平均応答遅れ | mean response gap |
| PG\_resp\_gap\_p50 | 応答遅れ中央値 | median response gap |
| PG\_resp\_gap\_p90 | 応答遅れ90パーセンタイル | 90th percentile response gap |
| PG\_overlap\_rate | 重なり率 | overlap rate |
| FILL\_has\_any | フィラー出現発話率 | filler-containing utterance rate |
| FILL\_rate\_per\_100chars | 100文字あたりフィラー率 | filler rate per 100 characters |

### 4.2 Novel Features（9個）

| 変数名 | 日本語名（本文中） | English summary（APA7表記） |
|:--|:--|:--|
| IX\_oirmarker\_rate | 修復開始率 | OIR marker rate |
| IX\_oirmarker\_after\_question\_rate | 質問直後修復開始率 | post-question OIR rate |
| IX\_yesno\_rate | YES/NO応答率 | yes/no response rate |
| IX\_yesno\_after\_question\_rate | 質問直後YES/NO率 | post-question yes/no rate |
| IX\_lex\_overlap\_mean | 語彙重複度 / 語彙重なり | lexical overlap |
| RESP\_NE\_AIZUCHI\_RATE | 「ね」直後相槌率 | post-NE aizuchi rate |
| RESP\_NE\_ENTROPY | 「ね」直後応答多様性 | post-NE response entropy |
| RESP\_YO\_ENTROPY | 「よ」直後応答多様性 | post-YO response entropy |
| PG\_pause\_variability | 沈黙長の変動係数 | pause duration coefficient of variation (CV) |

### 4.3 統制変数（EXCL3, 13個）

| 変数名 | 日本語 | English |
|:--|:--|:--|
| IX\_topic\_drift\_mean | 話題逸脱度 | topic drift（IX\_lex\_overlap\_mean との完全共線性で説明変数から除外） |
| n\_pairs\_total | 隣接ペア総数 | total adjacent pair count |
| n\_pairs\_after\_NE | 「ね」直後ペア数 | pairs after NE particle |
| n\_pairs\_after\_YO | 「よ」直後ペア数 | pairs after YO particle |
| IX\_n\_pairs | IX用ペア数 | IX pair count |
| IX\_n\_pairs\_after\_question | 質問直後ペア数 | post-question pair count |
| PG\_total\_time | 会話全体時間 | total conversation time |
| PG\_resp\_overlap\_rate | 応答重なり率 | response overlap rate |
| FILL\_text\_len | テキスト文字数 | text character count |
| FILL\_cnt\_total | フィラー総数 | total filler count |
| FILL\_cnt\_eto | 「えっと」数 | "etto" filler count |
| FILL\_cnt\_e | 「えー」数 | "ee" filler count |
| FILL\_cnt\_ano | 「あの」数 | "ano" filler count |

---

## 5. Big5 性格特性（Personality Traits）

| 日本語 | English | 略号 | 備考 |
|:--|:--|:--:|:--|
| Big5 性格特性 | Big5 personality traits | — | 和文・英文とも「Big5」に統一（宗田さんレビュー反映）。英語投稿時は投稿先の慣例に応じ "Big Five" 表記の要否を最終確認 |
| 開放性 | Openness | O | to experience は付けない |
| 誠実性 | Conscientiousness | C | 本研究の主結果次元 |
| 外向性 | Extraversion | E | Extroversion ではない |
| 協調性 | Agreeableness | A | |
| 神経症傾向 | Neuroticism | N | |
| 性格特性 | personality traits | — | |
| 性格スコア | personality scores | — | |
| 性格次元 | personality dimension | — | |
| アンサンブルBig5 | ensemble Big5 | — | 4 LLM 教師の item-level 平均 |
| アンサンブル | ensemble | — | |
| item-level 平均 | item-level mean | — | |
| IPIP-NEO-120 | IPIP-NEO-120 | — | 固定。初出時に International Personality Item Pool NEO-120 と併記 |
| 120項目 | 120 items | — | |
| 5件法 | 5-point Likert scale | — | |
| 逆転項目 | reverse-scored items | — | |
| Cronbach's α | Cronbach's α | — | 記号は α で統一 |
| 内的一貫性 | internal consistency | — | |

---

## 6. LLM 教師モデル（Teacher Models）

| 日本語 | English | 備考 |
|:--|:--|:--|
| Sonnet4 | Sonnet4 (Anthropic Claude Sonnet 4) | 初出で fullname |
| Qwen3-235B | Qwen3-235B (Alibaba Qwen3, 235B parameters) | |
| DeepSeek-V3 | DeepSeek-V3 | |
| GPT-OSS-120B | GPT-OSS-120B | 記載通り |
| AWS Bedrock | AWS Bedrock | 固有名 |
| 大規模言語モデル | large language model (LLM) | 略号。LLMs（複数形） |
| ゼロショット | zero-shot | |

---

## 7. 統計手法（Statistical Methods）

| 日本語 | English | 備考 |
|:--|:--|:--|
| Ridge 回帰 | ridge regression | "Ridge regression" でも可（固有感は文頭で） |
| L2 正則化 | L2 regularization | |
| 正則化パラメータ α | regularization parameter α | |
| 最小二乗回帰 | ordinary least squares (OLS) regression | |
| 多重共線性 | multicollinearity | |
| 交差検証 | cross-validation (CV) | |
| 5-fold 交差検証 | 5-fold cross-validation | |
| subject-wise split | subject-wise split | 固定（本研究キーワード） |
| GroupKFold | GroupKFold | scikit-learn の固有名 |
| リーク防止 | leakage prevention | |
| 情報リーク | information leakage | |
| out-of-fold 予測値 | out-of-fold prediction | OOF prediction |
| Pearson 相関係数 | Pearson correlation coefficient | |
| Spearman 順位相関係数 | Spearman rank correlation coefficient | ρ |
| Mann-Whitney U 検定 | Mann-Whitney U test | 両側検定 = two-sided test |
| 置換検定 | permutation test | |
| Permutation 回帰係数検定 | permutation test for regression coefficients | §3.4.4 |
| Bootstrap | bootstrap | 小文字。"Bootstrap" は文頭のみ |
| Bootstrap 分散ベース安定性分析 | bootstrap variance-based stability analysis | §3.4.5 |
| 復元抽出 | sampling with replacement | |
| リサンプリング | resampling | |
| 標準偏差 (SD) | standard deviation (SD) | |
| 95% 信頼区間 (CI) | 95% confidence interval (CI) | |
| 多重比較補正 | multiple-comparison correction | |
| Holm-Bonferroni 法 | Holm-Bonferroni method | |
| Holm 法 | Holm method | |
| Bonferroni 法 | Bonferroni method | |
| FDR 制御法 | false discovery rate (FDR) control | BH 法 = Benjamini-Hochberg procedure |
| 補正前 p 値 | uncorrected p-value | |
| 補正後 p 値 | corrected p-value / adjusted p-value | |
| 観測相関係数 r\_obs | observed correlation coefficient (r\_obs) | |
| 回帰係数 β | regression coefficient (β) | |
| 有意水準 | significance level | α = 0.05 |
| 有意差 | significant difference | |
| 有意 | significant | |
| 非有意 | non-significant (n.s.) | |
| シャノンエントロピー | Shannon entropy | |
| 変動係数 (CV) | coefficient of variation (CV) | |
| 記述統計 | descriptive statistics | |
| 四分位点 | quartiles | |
| 90パーセンタイル | 90th percentile | |
| 中央値 | median | |
| ダミー変数 | dummy variable | |
| 乱数シード | random seed | |
| Fisher-Yates シャッフル | Fisher-Yates shuffle | |
| derangement（完全順列） | derangement | |

---

## 8. 会話分析・語用論（Conversation Analysis / Pragmatics）

| 日本語 | English | 備考 |
|:--|:--|:--|
| 会話分析 | Conversation Analysis (CA) | 分野名は固有名扱い |
| 談話分析 | discourse analysis | |
| 相互行為論 | interactional linguistics | |
| 語用論 | pragmatics | |
| ターンテイキング | turn-taking | ハイフン必須 |
| 話者交替 | speaker transition | |
| 修復連鎖 | repair sequence | |
| 修復開始 | repair initiation | |
| 他者開始修復 (OIR) | Other-Initiated Repair (OIR) | |
| 自己開始修復 | self-initiated repair | |
| OIR マーカー | OIR marker | |
| 隣接ペア | adjacency pair | |
| 第一部分 / 第二部分 | first pair part / second pair part | FPP / SPP |
| 選好構造 | preference organization | |
| 選好的応答 | preferred response | |
| フィラー | filler / filled pause | 初出で filler (filled pause) |
| 計画フィラー | planning filler | §2.2 |
| 談話標識 | discourse marker | §2.2 |
| 相槌 | backchannel / aizuchi | 本研究では backchannel (aizuchi) と併記が安全 |
| 相槌多様性 | backchannel diversity | §dindar2022 |
| 終助詞 | sentence-final particle | |
| 終助詞「ね」 | sentence-final particle NE | 斜体で NE |
| 終助詞「よ」 | sentence-final particle YO | 斜体で YO |
| 共感 | empathy / affiliation | 文脈で使い分け |
| 確認 | confirmation | |
| 語彙重なり | lexical overlap | |
| 語彙つながり | lexical continuity | 併用あり |
| 話題連結 | topical connection | |
| 話題の連続性 | topical continuity | |
| 話題逸脱度 | topic drift | |
| 文字バイグラム Jaccard 係数 | character-bigram Jaccard coefficient | |

---

## 9. 妥当性・信頼性（Validity / Reliability）

| 日本語 | English | 備考 |
|:--|:--|:--|
| 表面的妥当性 | face validity | |
| 構成概念妥当性 | construct validity | |
| 収束的妥当性 | convergent validity | |
| 外的妥当性 | external validity | |
| 再現性 | reproducibility / replicability | 文脈注意: 狭義の reproducibility（同じデータ・コード）と replicability（別データ）は使い分け |
| 信頼性 | reliability | |
| 信頼区間 | confidence interval | |
| 再現可能 | reproducible | |
| 査読耐性 | peer-review readiness | 本文ではこの表現は使わない（内部用語） |

---

## 10. 実験デザイン・ベースライン検証（Experimental Design）

| 日本語 | English | 備考 |
|:--|:--|:--|
| 3条件比較 | three-condition comparison | §2.6, §3.5 |
| 条件1（テキストあり） | Condition 1 (full text) | |
| 条件2（要約のみ） | Condition 2 (summary statistics only) | |
| 条件3（ランダムテキスト） | Condition 3 (random text / shuffled text) | |
| 陰性対照 | negative control | |
| 主条件 | primary condition | |
| ベースライン検証 | baseline validation | |
| テキスト内容依存 | content-dependent | 判定ラベル |
| 表層統計量依存 | surface-statistic-dependent | 判定ラベル |
| Feature Dose-Response 実験 | Feature Dose-Response experiment | §4.5 |
| 用量反応関係 | dose-response relationship | |
| 交絡 | confounding | |
| 交絡変数 | confounding variable | |
| 残余交絡 | residual confounding | |
| 統制変数 | control variable | |
| 統制前後 | before/after control | |
| 話者属性 | speaker attributes | |
| 人口統計変数 | demographic variables | sex, age |
| 3段階 Ridge 回帰比較 | three-stage ridge regression comparison | §3.4.3 |
| Stage 1 / 2 / 3 | Stage 1 / Stage 2 / Stage 3 | 大文字固定 |
| Δr\_{1→2} / Δr\_{2→3} | Δr\_{1→2} / Δr\_{2→3} | LaTeX そのまま |

---

## 11. 論文構成・章見出し（Paper Structure）

| 日本語 | English | 備考 |
|:--|:--|:--|
| はじめに | Introduction | §1 |
| 方法 | Methods | §2。BRM は Method 単数も可 |
| データ | Data | §2.1 |
| 特徴量 | Features | §2.2 |
| 仮想教師プロトコル | Virtual Teacher Protocol | §2.3 |
| 回帰モデル | Regression Model | §2.4 |
| 信頼性検証 | Reliability Validation | §2.5 |
| ベースライン検証 | Baseline Validation | §2.6 |
| 結果 | Results | §3 |
| 記述統計と分布 | Descriptive Statistics and Distributions | §3.1 |
| 相関分析 | Correlation Analysis | §3.2 |
| コーパス基本情報との関連性 | Associations with Corpus Metadata | §3.3 |
| 性格特性との関連性 | Associations with Personality Traits | §3.4 |
| アンサンブル Permutation test 結果 | Ensemble Permutation Test Results | §3.4.1 |
| 個別教師結果の要約と頑健性 | Individual Teacher Results and Robustness | §3.4.2 |
| 3段階 Ridge 回帰比較 | Three-Stage Ridge Regression Comparison | §3.4.3 |
| Permutation 回帰係数検定 | Permutation Test for Regression Coefficients | §3.4.4 |
| Bootstrap 分散ベース安定性分析 | Bootstrap Variance-Based Stability Analysis | §3.4.5 |
| 教師間一致度 | Inter-Teacher Agreement | §3.4.6 |
| ベースライン検証結果 | Baseline Validation Results | §3.5 |
| 考察 | Discussion | §4 |
| 限界 | Limitations | §4.8 |
| 結論 | Conclusion | §5 |
| 付録 | Appendix | |
| 感度分析 | Sensitivity Analysis | |
| Supplementary Material | Supplementary Material | そのまま |

---

## 12. 頻出フレーズ（Recurring Phrases）

| 日本語 | English |
|:--|:--|
| 性格推定モデルの構築ではなく | not to build a personality estimation model |
| 会話の相互行為の再現可能な計測 | reproducible measurement of conversational interaction |
| 日本語会話コーパスにおける初の体系的検証 | the first systematic validation on a Japanese conversation corpus |
| 特徴量の提案そのものにある | lies in the proposal of the features themselves |
| 提案指標の妥当性を検証するための手段 | a means to validate the proposed indicators |
| 本研究の主たる貢献は | the main contribution of this study is |
| 今後の課題 | future work / remains for future work |
| 先行研究と整合する | consistent with prior work |
| 社会言語学的に既知の知見 | established findings in sociolinguistics |
| 影響が強い特徴量 | features with strong influence |
| 安定的に寄与する | contribute stably |
| 係数の符号が一貫している | the sign of the coefficient is consistent |
| 95%CI がゼロを跨がない | 95% CI does not include zero / excludes zero |
| 教師横断で最も頑健 | most robust across teachers |
| 教師間一致度も最も高い | exhibits the highest inter-teacher agreement |
| 仮想教師として使用する | use as virtual teachers |
| 相互行為の定量化指標 | quantitative indicators of conversational interaction |

---

## 13. 固有記号・数値表記（Notation）

| 日本語 | English |
|:--|:--|
| $N = 120$ | N = 120 （本文中では italic N） |
| $r = 0.447$ | r = .447 （APA7 は先頭の 0 を省略。散文内では r = 0.447 でも可。誌の投稿規程に従う） |
| $p < 0.001$ | p < .001 （APA7）。本文中で一貫するなら p < 0.001 でも可 |
| $p = 0.0004$ | p = .0004 |
| 4 教師 | four teacher models |
| 5 次元 | five dimensions |
| 19 特徴量 | 19 features / the 19 proposed features |
| 21 特徴量（Stage3 で人口統計含む） | 21 variables |
| 120 レコード | 120 records |
| 74 名のユニーク話者 | 74 unique speakers |

---

## 14. 著者・所属（Front Matter）

| 日本語 | English |
|:--|:--|
| 福原 玄 | Gen Fukuhara |
| 合同会社 Lead lea（リーレア） | Lead lea LLC |
| 山下 祐一 | Yuichi Yamashita |
| 国立精神・神経医療研究センター（NCNP）神経研究所 疾病研究第七部 | Department of Pathophysiology of Mental Disorders, National Institute of Neuroscience, National Center of Neurology and Psychiatry (NCNP) |
| 宗田 卓史 | Takafumi Soda |
| 国立精神・神経医療研究センター（NCNP） | National Center of Neurology and Psychiatry (NCNP) |
| 連絡先 | Correspondence |

---

## 15. 参考文献（Reference 固定訳）

以下は bibitem key と著者表記の英語標準形の対応表。
`docs/homework/bibliography_integrity_check.md` の結果を反映。

| bibitem key | 英語標準形（APA7 in-text） |
|:--|:--|
| hu2025 | Hu et al. (2025) |
| altozano2026 → wright2026 | Wright et al. (2026)（山下先生 Word 側で差し替え想定） |
| mun2024 | Mun et al. (2024) |
| nakamura2025 | Nakamura et al. (2025) |
| sacks1974 | Sacks, Schegloff, and Jefferson (1974) / Sacks et al. (1974) |
| schegloff1977 | Schegloff, Jefferson, and Sacks (1977) |
| levitan2012 | Levitan et al. (2012) |
| deruiter2006 | De Ruiter, Mitterer, and Enfield (2006) / De Ruiter et al. (2006) |
| campione2002 | Campione and Véronis (2002) |
| clark1996 | Clark (1996) |
| watanabe2003 | Watanabe (2003) |
| kendrick2015 | Kendrick (2015) |
| albert2018 | Albert and De Ruiter (2018) |
| meylan2014 | Meylan and Gahl (2014) |
| kita2007 | Kita and Ide (2007) |
| holm1979 | Holm (1979) |
| dindar2022 | Dindar et al. (2022) |
| bortfeld2001（追加候補） | Bortfeld et al. (2001) |
| horton2010（追加候補） | Horton, Spieler, and Shriberg (2010) |
| laserna2014（追加候補） | Laserna, Seih, and Pennebaker (2014) |
| leaper2007（追加候補） | Leaper and Ayres (2007) |
| tanaka2004（追加候補） | Tanaka (2004) |

---

## 16. 注意すべき誤訳パターン

- **"interactional features" を "interaction features" と書かない**（定訳固定）
- **"Conscientiousness" を "consciousness" と誤訳しない**（自動翻訳で頻発。レビュー必須）
- **"Agreeableness" を "agreement" と誤訳しない**
- **"subject-wise split" を "subject-based split" や "speaker-based split" に書き換えない**（本研究キーワード）
- **"virtual teacher" を "pseudo teacher" / "proxy teacher" に揺らさない**
- **"aizuchi" を "nodding" / "response" に訳さない**（日本語会話分析の固有概念としてローマ字保持。初出で backchannel と併記）
- **"OIR" を "other-initiation-of-repair" と書かない**（Other-Initiated Repair で統一）
- **"N" と "Neuroticism" の N** は文脈で読み間違えられやすいので、サンプルサイズは *N* = 120 のように italic、性格次元は plain N で区別
- **"r" と "ρ"** の取り違えに注意（Pearson は r、Spearman は ρ）

---

## 17. 翻訳時の LLM プロンプト雛形

```
You are translating a Japanese academic paper (methodology / results section)
into American English for Behavior Research Methods (BRM) journal submission.

Strict requirements:
1. Use the glossary below for all specialized terms. Do NOT deviate.
2. Keep LaTeX commands, math, citations (\cite{...}), labels (\label{...}),
   and references (\ref{...}) unchanged.
3. Keep variable names (PG_speech_ratio, IX_yesno_rate, etc.) verbatim.
4. Use APA7 style conventions where applicable (e.g., italic N, r, p;
   leading zero optional for p-values; "five-point Likert scale").
5. Preserve paragraph structure and sentence-level citations.
6. Do NOT paraphrase beyond what is needed for natural English.
7. Translate 会話分析 CA terminology using established English equivalents
   (e.g., "turn-taking", "adjacency pair", "Other-Initiated Repair (OIR)",
   "backchannel (aizuchi)", "sentence-final particle").

Glossary:
[paste sections 1–15 of glossary_en.md here]

Now translate the following section:
[paste Japanese text]
```

---

## 18. 更新履歴

| 日付 | 内容 | 担当 |
|:---:|:--|:---:|
| 2026-05-10 | 初版作成。feature_definitions.py を一次ソースに 19特徴量英訳を確定。会話分析・統計・Big5 用語を網羅 | 福原 |
