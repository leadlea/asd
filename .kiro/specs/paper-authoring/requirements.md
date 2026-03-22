# 要件定義書: 論文化（paper-authoring）

## はじめに

本要件定義書は、日本語会話コーパス（CEJC）から抽出した相互行為特徴量を用いて、LLMが推定したBig Five性格スコアを古典的NLP/語用論特徴量で予測・解釈する研究の論文化に必要な成果物を定義する。対象学会は発達支援学会（2026年11月）であり、メソッド＋リザルトを軸とした論文を完成させることが目標である。

既存の `paper1_ja.tex` はv1（N=500、IX群なし、PCA/クラスタ中心）であり、現在の研究（N=120 home2 HQ1、18特徴量、Ridge回帰、Cの頑健性中心）とは大きく異なるため、全面書き直しが必要である。

## 用語集

- **論文生成システム（Paper_System）**: 論文LaTeXファイル、図表生成スクリプト、レビュー資料を含む論文化成果物の総体
- **特徴量抽出器（Feature_Extractor）**: `extract_interaction_features_min.py` による18特徴量の計算モジュール
- **回帰パイプライン（Regression_Pipeline）**: Ridge回帰 + 5-fold CV + permutation test + bootstrap安定性評価の一連の分析フロー
- **仮想教師（Virtual_Teacher）**: LLM（Sonnet4, Qwen3-235B, DeepSeek-V3, GPT-OSS-120B）がIPIP-NEO-120に基づき推定したBig Fiveスコア
- **Teacher間一致度（Teacher_Agreement）**: 同一会話×話者に対する複数LLM教師のスコア間Pearson相関の平均
- **Bootstrap安定性（Bootstrap_Stability）**: 500回リサンプリングにおけるTop-K inclusion rate（topk_rate）と符号一致率（sign_agree_rate）
- **CEJC**: 日本語日常会話コーパス（Corpus of Everyday Japanese Conversation）
- **EARS**: Easy Approach to Requirements Syntax（要件記述パターン）
- **Permutation_Test**: 目的変数を5000回シャッフルし、観測相関以上が偶然出る確率を算出する置換検定
- **NCNP**: 国立精神・神経医療研究センター

## 要件

### 要件1: 論文LaTeX骨子の生成

**ユーザーストーリー:** 研究者として、現在の研究内容（N=120、18特徴量、Ridge回帰、Cの頑健性）を正確に反映したLaTeX論文骨子を生成したい。これにより、NCNPミーティングで合意済みの構成に沿った論文執筆を開始できる。

#### 受入基準

1. WHEN 論文骨子の生成が要求された場合、THE Paper_System SHALL Introduction、Method、Results、Discussion、Conclusion、Appendixの6セクションを含むLaTeXファイルを `paper1_ja.tex` として出力する
2. THE Paper_System SHALL Introductionセクションにおいて、談話×LLM×性格推定の先行研究ギャップ（`docs/homework/asd_paper.md` に基づく）を記述する
3. THE Paper_System SHALL Methodセクションにおいて、18特徴量を2段階（概要テーブル＋アルゴリズム詳細）で説明する構成を含む
4. THE Paper_System SHALL Methodセクションにおいて、データ（CEJC home2 HQ1、N=120）、仮想教師プロトコル（IPIP-NEO-120、4モデル）、回帰モデル（Ridge + 5-fold CV）、信頼性検証（permutation test、bootstrap）の各サブセクションを含む
5. THE Paper_System SHALL Resultsセクションにおいて、Cの頑健性（4教師のpermutation結果）を主結果として配置し、Teacher間一致度とBootstrap Top Driversを補助結果として配置する
6. THE Paper_System SHALL Appendixにおいて、A/E/N/Oの探索的結果と感度分析の配置枠を含む
7. THE Paper_System SHALL uplatex + dvipdfmx でコンパイル可能なLaTeX文書を出力する
8. IF LaTeXファイルのコンパイルに必要な画像ファイルが存在しない場合、THEN THE Paper_System SHALL プレースホルダーコメントを挿入し、コンパイルエラーを回避する

### 要件2: 論文用図表の生成

**ユーザーストーリー:** 研究者として、主要結果を視覚的に伝える論文用図表を生成したい。これにより、査読者やNCNP共同研究者が結果を直感的に理解できる。

#### 受入基準

1. WHEN 図表生成スクリプトが実行された場合、THE Paper_System SHALL Permutation test結果の可視化（Cの4教師比較バーチャート）をPNG形式で出力する
2. WHEN 図表生成スクリプトが実行された場合、THE Paper_System SHALL Bootstrap radar chart（Cの上位特徴量のtopk_rateとsign_agree_rate）をPNG形式で出力する
3. WHEN 図表生成スクリプトが実行された場合、THE Paper_System SHALL Teacher間一致度ヒートマップ（5 trait × 4 teacher）をPNG形式で出力する
4. WHEN 図表生成スクリプトが実行された場合、THE Paper_System SHALL 18特徴量の記述統計テーブル（N、mean、SD、p50、p90）をLaTeX tabular形式で出力する
5. THE Paper_System SHALL 生成された全図表を `reports/paper_figs_v2/` ディレクトリに保存する
6. THE Paper_System SHALL 図表生成に使用するデータを `artifacts/analysis/` 配下の既存parquetファイルから読み込む
7. IF 入力parquetファイルが存在しない場合、THEN THE Paper_System SHALL エラーメッセージにファイルパスと期待されるスキーマを含めて出力する

### 要件3: 分析結果の再現性検証

**ユーザーストーリー:** 研究者として、論文に記載する数値が既存スクリプトの出力と一致することを検証したい。これにより、論文の数値の正確性を担保できる。

#### 受入基準

1. WHEN 再現性検証が実行された場合、THE Regression_Pipeline SHALL `permutation_test_ridge_fixedalpha.py` の出力（r_obs、p値）が論文記載値（Sonnet4: r=0.434 p=0.0008、Qwen3: r=0.390 p=0.001、GPT-OSS: r=0.447 p=0.0008、DeepSeek: r=0.205 p=0.113）と一致することを検証する
2. WHEN 再現性検証が実行された場合、THE Regression_Pipeline SHALL `teacher_agreement_big5.py` の出力（C mean r=0.699、A mean r=0.435）が論文記載値と一致することを検証する
3. WHEN 再現性検証が実行された場合、THE Regression_Pipeline SHALL `bootstrap_coef_stability.py` の出力（Top3: FILL_has_any、IX_oirmarker_after_question_rate、PG_speech_ratio）が論文記載値と一致することを検証する
4. THE Regression_Pipeline SHALL 検証結果をTSV形式のサマリーファイルとして `artifacts/analysis/results/reproducibility_check.tsv` に出力する
5. IF 再現結果と論文記載値に乖離がある場合、THEN THE Regression_Pipeline SHALL 乖離の内容（期待値、実測値、差分）をサマリーファイルに記録する

### 要件4: NCNP共同研究者向けレビュー資料の生成

**ユーザーストーリー:** 研究者として、山下先生・宗田さんに共有できるレビュー資料を生成したい。これにより、NCNPミーティングで方法と結果を効率的に議論できる。

#### 受入基準

1. WHEN レビュー資料の生成が要求された場合、THE Paper_System SHALL 方法セクション（特徴量の2段階説明）と結果セクション（Cの頑健性中心）を含むMarkdown資料を出力する
2. THE Paper_System SHALL レビュー資料において、18特徴量を「概要（1行説明）」と「アルゴリズム（計算手順）」の2段階で説明する
3. THE Paper_System SHALL レビュー資料において、Permutation test結果、Teacher間一致度、Bootstrap Top Driversの3つの主要結果を図表付きで提示する
4. THE Paper_System SHALL レビュー資料において、差別化ポイント（「性格推定」ではなく「会話の相互行為の計測」としての立て付け）を明記する
5. THE Paper_System SHALL レビュー資料を `docs/homework/ncnp_review_v2.md` として出力する
6. WHILE レビュー資料が共同研究者に共有される状態にある場合、THE Paper_System SHALL 図表への相対パス参照が正しく解決されることを保証する

### 要件5: 論文の差別化と位置づけの明確化

**ユーザーストーリー:** 研究者として、本研究の新規性と差別化ポイントを論文内で明確に表現したい。これにより、査読者に対して研究の貢献を説得的に示せる。

#### 受入基準

1. THE Paper_System SHALL Introductionにおいて、「性格推定」ではなく「会話の相互行為の再現可能な計測」として研究を位置づける記述を含む
2. THE Paper_System SHALL Methodにおいて、再現可能な評価設計（subject-wise split、permutation test 5000回、bootstrap 500回）を明示する
3. THE Paper_System SHALL Resultsにおいて、複数LLM教師の頑健性検証（4教師中3教師でCが有意）をTeacher間一致度（C mean r=0.699）と関連づけて記述する
4. THE Paper_System SHALL Discussionにおいて、日本語会話コーパスでの初の体系的検証であることを先行研究（`docs/homework/asd_paper.md`）との対比で記述する
5. THE Paper_System SHALL Discussionにおいて、限界（小標本N=120、外部検証未了、LLM教師の妥当性未検証）を明示する

### 要件6: 特徴量定義の文書化

**ユーザーストーリー:** 研究者として、18特徴量の定義と計算手順を論文品質で文書化したい。これにより、第三者が特徴量を再現できる。

#### 受入基準

1. THE Paper_System SHALL 18特徴量の各々について、名称、カテゴリ（PG/FILL/IX/RESP）、1行の概要説明、計算アルゴリズムの4項目を含む定義を提供する
2. THE Paper_System SHALL 特徴量定義において、`src/features/` 配下の実装コードとの対応関係を明示する
3. THE Paper_System SHALL 特徴量定義において、controls（除外変数: EXCL3）と説明変数の区別を明記する
4. WHEN 特徴量の計算に前提条件（分母がゼロの場合の扱い等）がある場合、THE Paper_System SHALL その前提条件と欠損値の処理方法を記述する
5. THE Paper_System SHALL 特徴量定義をLaTeX論文のMethodセクション内テーブルとして組版可能な形式で出力する

### 要件7: 探索的結果（A/E/N/O）のAppendix構成

**ユーザーストーリー:** 研究者として、C以外のtrait（A/E/N/O）の結果を探索的知見としてAppendixに整理したい。これにより、論文の透明性を高め、将来の研究への示唆を提供できる。

#### 受入基準

1. THE Paper_System SHALL Appendixにおいて、A/E/N/Oの各traitについてPermutation test結果（4教師×r_obs×p値）のテーブルを含む
2. THE Paper_System SHALL Appendixにおいて、A/E/N/Oの結果がteacher依存性を示すことを、Teacher間一致度との関連で記述する
3. THE Paper_System SHALL Appendixにおいて、Bootstrap Top10特徴量のCとの重なり（overlap）分析結果を含む
4. WHILE A/E/N/Oの結果が探索的位置づけである場合、THE Paper_System SHALL 「探索的結果であり確認的解釈は避けるべき」旨の注記を付す
5. IF 特定のteacher×trait組み合わせで有意な結果が得られた場合、THEN THE Paper_System SHALL その結果を報告しつつ、一般因子混入の可能性について注記する
