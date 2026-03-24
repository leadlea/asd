# 要件定義書: 論文化（paper-authoring）

## はじめに

本要件定義書は、日本語会話コーパス（CEJC）から抽出した相互行為特徴量を用いた研究の論文化に必要な成果物を定義する。

NCNPレビュー（山下先生・宗田さん）のフィードバックに基づき、メインメッセージを「**日本語会話における相互行為特徴量の定量化指標の提案**」に据え直した。従来の「Cの頑健性」中心の構成から、特徴量そのものの記述・分析を先に置き、Big5との関連は妥当性検証の一部として後段に配置する構成に改訂した。

対象学会は発達支援学会（2026年11月）であり、メソッド＋リザルトを軸とした論文を完成させることが目標である。

既存の `paper1_ja.tex` はv1（N=500、IX群なし、PCA/クラスタ中心）であり、現在の研究（N=120 home2 HQ1、18特徴量、Ridge回帰）とは大きく異なるため、全面書き直しが必要である。

### Results構成の方針（NCNPレビュー反映）

```
Results
├── 1. 提案特徴量の抽出
│   ├── 1-1. 記述統計（分布・ばらつき）→ 指標としての有用性を丁寧に報告
│   └── 1-2. 特徴量カテゴリ内/間の相関分析 → 同一カテゴリ内の高相関等の性質
└── 2. 外部指標を用いた特徴量の妥当性検証
    ├── 2-1. コーパス基本情報との関連性（性別・年齢・出身・学歴）
    └── 2-2. 性格特性との関連性（Big5）→ メインの妥当性検証
```

## 用語集

- **論文生成システム（Paper_System）**: 論文LaTeXファイル、図表生成スクリプト、スライド資料、レビュー資料を含む論文化成果物の総体
- **特徴量抽出器（Feature_Extractor）**: `extract_interaction_features_min.py` による18特徴量の計算モジュール
- **回帰パイプライン（Regression_Pipeline）**: Ridge回帰 + 5-fold CV + permutation test + bootstrap安定性評価の一連の分析フロー
- **仮想教師（Virtual_Teacher）**: LLM（Sonnet4, Qwen3-235B, DeepSeek-V3, GPT-OSS-120B）がIPIP-NEO-120に基づき推定したBig Fiveスコア
- **Teacher間一致度（Teacher_Agreement）**: 同一会話×話者に対する複数LLM教師のスコア間Pearson相関の平均
- **Bootstrap安定性（Bootstrap_Stability）**: 500回リサンプリングにおけるTop-K inclusion rate（topk_rate）と符号一致率（sign_agree_rate）
- **CEJC**: 日本語日常会話コーパス（Corpus of Everyday Japanese Conversation）
- **EARS**: Easy Approach to Requirements Syntax（要件記述パターン）
- **Permutation_Test**: 目的変数を5000回シャッフルし、観測相関以上が偶然出る確率を算出する置換検定
- **NCNP**: 国立精神・神経医療研究センター
- **特徴量カテゴリ**: PG（タイミング）、FILL（フィラー）、IX（相互行為）、RESP（応答型）の4カテゴリ
- **コーパス基本情報（Corpus_Metadata）**: CEJCに付随する話者属性情報（性別、年齢、出身地域、学歴等）
- **紙芝居スライド（Kamishibai_Slides）**: 結果セクションを1枚1図で構成したプレゼンテーション資料。「このスライドでは、この図を使って、この結論を言う」を視覚的に整理する

## 要件

### 要件1: 論文LaTeX骨子の生成

**ユーザーストーリー:** 研究者として、NCNPレビューで合意した新構成（特徴量の提案→妥当性検証）を正確に反映したLaTeX論文骨子を生成したい。これにより、メインメッセージ「相互行為特徴量の定量化指標の提案」に沿った論文執筆を開始できる。

#### 受入基準

1. WHEN 論文骨子の生成が要求された場合、THE Paper_System SHALL Introduction、Method、Results、Discussion、Conclusion、Appendixの6セクションを含むLaTeXファイルを `paper1_ja.tex` として出力する
2. THE Paper_System SHALL Introductionセクションにおいて、日本語会話における相互行為特徴量の定量化指標の提案を研究目的として記述する
3. THE Paper_System SHALL Introductionセクションにおいて、談話×LLM×性格推定の先行研究ギャップ（`docs/homework/asd_paper.md` に基づく）を記述する
4. THE Paper_System SHALL Methodセクションにおいて、18特徴量を2段階（概要テーブル＋アルゴリズム詳細）で説明する構成を含む
5. THE Paper_System SHALL Methodセクションにおいて、データ（CEJC home2 HQ1、N=120）、仮想教師プロトコル（IPIP-NEO-120、4モデル）、回帰モデル（Ridge + 5-fold CV）、信頼性検証（permutation test、bootstrap）の各サブセクションを含む
6. THE Paper_System SHALL Resultsセクションにおいて、以下の順序で結果を配置する: (1) 提案特徴量の記述統計と分布、(2) 特徴量カテゴリ内/間の相関分析、(3) コーパス基本情報との関連性、(4) 性格特性（Big5）との関連性
7. THE Paper_System SHALL Appendixにおいて、A/E/N/Oの探索的結果と感度分析の配置枠を含む
8. THE Paper_System SHALL uplatex + dvipdfmx でコンパイル可能なLaTeX文書を出力する
9. IF LaTeXファイルのコンパイルに必要な画像ファイルが存在しない場合、THEN THE Paper_System SHALL プレースホルダーコメントを挿入し、コンパイルエラーを回避する

### 要件2: 論文用図表の生成

**ユーザーストーリー:** 研究者として、新しいResults構成（特徴量の記述→相関→外部指標との関連）に対応した論文用図表を生成したい。これにより、査読者やNCNP共同研究者が結果を直感的に理解できる。

#### 受入基準

1. WHEN 図表生成スクリプトが実行された場合、THE Paper_System SHALL 18特徴量の分布（ヒストグラムまたはバイオリンプロット）をPNG形式で出力する
2. WHEN 図表生成スクリプトが実行された場合、THE Paper_System SHALL 18特徴量の記述統計テーブル（N、mean、SD、min、p25、p50、p75、p90、max）をLaTeX tabular形式で出力する
3. WHEN 図表生成スクリプトが実行された場合、THE Paper_System SHALL 特徴量カテゴリ内およびカテゴリ間の相関行列ヒートマップをPNG形式で出力する
4. WHEN 図表生成スクリプトが実行された場合、THE Paper_System SHALL コーパス基本情報（性別・年齢等）と特徴量の関連を示す図表をPNG形式で出力する
5. WHEN 図表生成スクリプトが実行された場合、THE Paper_System SHALL Permutation test結果の可視化（Cの4教師比較バーチャート）をPNG形式で出力する
6. WHEN 図表生成スクリプトが実行された場合、THE Paper_System SHALL Bootstrap radar chart（Cの上位特徴量のtopk_rateとsign_agree_rate）をPNG形式で出力する
7. WHEN 図表生成スクリプトが実行された場合、THE Paper_System SHALL Teacher間一致度ヒートマップ（5 trait × 4 teacher）をPNG形式で出力する
8. THE Paper_System SHALL 生成された全図表を `reports/paper_figs_v2/` ディレクトリに保存する
9. THE Paper_System SHALL 図表生成に使用するデータを `artifacts/analysis/` 配下の既存parquetファイルから読み込む
10. IF 入力parquetファイルが存在しない場合、THEN THE Paper_System SHALL エラーメッセージにファイルパスと期待されるスキーマを含めて出力する

### 要件3: 特徴量の記述統計と分布の報告

**ユーザーストーリー:** 研究者として、提案する18特徴量の分布特性を丁寧に報告したい。これにより、各特徴量が個人差を捉える指標として有用であること（適度なばらつきがある等）を示せる。

#### 受入基準

1. THE Paper_System SHALL Resultsセクションの冒頭（Results 1-1）において、18特徴量の記述統計（N、mean、SD、min、p25、p50、p75、p90、max）をテーブルで報告する
2. THE Paper_System SHALL 各特徴量の分布形状（正規性、歪度、外れ値の有無）について記述する
3. THE Paper_System SHALL 分布に適度なばらつきがある特徴量について、個人差を捉える指標としての有用性を論じる
4. WHEN 特徴量の分布が極端に偏っている場合（例: 大半がゼロ）、THE Paper_System SHALL その特徴量の解釈上の注意点を記述する
5. THE Paper_System SHALL 記述統計の報告において、controls（除外変数: EXCL3）と説明変数の区別を明記する

### 要件4: 特徴量カテゴリ内/間の相関分析

**ユーザーストーリー:** 研究者として、18特徴量のカテゴリ内およびカテゴリ間の相関構造を分析・報告したい。これにより、同一カテゴリ内の特徴量が高い相関を示す等の構造的性質を明らかにし、特徴量セットの妥当性を示せる。

#### 受入基準

1. THE Paper_System SHALL Resultsセクション（Results 1-2）において、18特徴量間のPearson相関行列を報告する
2. THE Paper_System SHALL 相関行列をカテゴリ（PG、FILL、IX、RESP）ごとにブロック構造で可視化する
3. THE Paper_System SHALL 同一カテゴリ内の相関（例: PG系同士の相関）とカテゴリ間の相関を区別して報告する
4. WHEN 同一カテゴリ内の特徴量間に高い相関（|r| > 0.7）が観察された場合、THE Paper_System SHALL その相関の解釈（例: 同一構成概念の異なる側面を捉えている）を記述する
5. WHEN カテゴリ間で予想外の高い相関が観察された場合、THE Paper_System SHALL その相関の解釈と多重共線性への影響を記述する
6. THE Paper_System SHALL 相関分析の結果に基づき、特徴量セットの冗長性と独立性について考察する

### 要件5: コーパス基本情報との関連分析

**ユーザーストーリー:** 研究者として、提案特徴量とコーパスの基本情報（性別・年齢・出身地域・学歴等）との関連を分析したい。これにより、特徴量の妥当性を外部指標で検証し、納得感の強い結果から報告できる。

#### 受入基準

1. THE Paper_System SHALL Resultsセクション（Results 2-1）において、18特徴量とコーパス基本情報（性別、年齢）の関連を報告する
2. WHEN 性別と特徴量の関連を分析する場合、THE Paper_System SHALL 群間比較（t検定またはMann-Whitney U検定）の結果を報告する
3. WHEN 年齢と特徴量の関連を分析する場合、THE Paper_System SHALL 相関係数（PearsonまたはSpearman）の結果を報告する
4. THE Paper_System SHALL コーパス基本情報との関連分析において、納得感の強い結果（例: 年齢と応答遅れの関連）から順に報告する
5. WHEN コーパス基本情報が利用可能な場合、THE Paper_System SHALL 出身地域・学歴との関連も探索的に報告する
6. IF コーパス基本情報の一部が利用不可能な場合、THEN THE Paper_System SHALL 利用可能な属性のみで分析を実施し、利用不可能な属性についてはその旨を明記する
7. THE Paper_System SHALL コーパス基本情報との関連分析の結果を、特徴量の妥当性検証の文脈で解釈する

### 要件6: 性格特性（Big5）との関連分析（妥当性検証）

**ユーザーストーリー:** 研究者として、提案特徴量とBig5性格特性との関連を妥当性検証の最終段として報告したい。これにより、特徴量が心理学的構成概念と関連することを示し、指標としての有用性を裏付けられる。

#### 受入基準

1. THE Paper_System SHALL Resultsセクション（Results 2-2）において、Cの頑健性（4教師のpermutation結果）を主結果として報告する
2. THE Paper_System SHALL Cの頑健性をTeacher間一致度（C mean r=0.699）と関連づけて記述する
3. THE Paper_System SHALL Bootstrap Top Driversの結果（topk_rate、sign_agree_rate）を報告し、どの特徴量がCと関連するかを解釈する
4. THE Paper_System SHALL Big5との関連分析を「特徴量の妥当性検証」として位置づけ、「性格推定」ではないことを明確にする
5. WHILE Big5との関連分析が妥当性検証の位置づけである場合、THE Paper_System SHALL 「本分析は特徴量の構成概念妥当性の検証であり、性格推定モデルの構築を目的としない」旨の注記を含む

### 要件7: 分析結果の再現性検証

**ユーザーストーリー:** 研究者として、論文に記載する数値が既存スクリプトの出力と一致することを検証したい。これにより、論文の数値の正確性を担保できる。

#### 受入基準

1. WHEN 再現性検証が実行された場合、THE Regression_Pipeline SHALL `permutation_test_ridge_fixedalpha.py` の出力（r_obs、p値）が論文記載値（Sonnet4: r=0.434 p=0.0008、Qwen3: r=0.390 p=0.001、GPT-OSS: r=0.447 p=0.0008、DeepSeek: r=0.205 p=0.113）と一致することを検証する
2. WHEN 再現性検証が実行された場合、THE Regression_Pipeline SHALL `teacher_agreement_big5.py` の出力（C mean r=0.699、A mean r=0.435）が論文記載値と一致することを検証する
3. WHEN 再現性検証が実行された場合、THE Regression_Pipeline SHALL `bootstrap_coef_stability.py` の出力（Top3: FILL_has_any、IX_oirmarker_after_question_rate、PG_speech_ratio）が論文記載値と一致することを検証する
4. THE Regression_Pipeline SHALL 検証結果をTSV形式のサマリーファイルとして `artifacts/analysis/results/reproducibility_check.tsv` に出力する
5. IF 再現結果と論文記載値に乖離がある場合、THEN THE Regression_Pipeline SHALL 乖離の内容（期待値、実測値、差分）をサマリーファイルに記録する

### 要件8: NCNP共同研究者向けレビュー資料の生成

**ユーザーストーリー:** 研究者として、山下先生・宗田さんに共有できるレビュー資料を生成したい。これにより、NCNPミーティングで新しいResults構成と方法を効率的に議論できる。

#### 受入基準

1. WHEN レビュー資料の生成が要求された場合、THE Paper_System SHALL 新しいResults構成（特徴量の記述→相関→外部指標→Big5）を反映したMarkdown資料を出力する
2. THE Paper_System SHALL レビュー資料において、18特徴量を「概要（1行説明）」と「アルゴリズム（計算手順）」の2段階で説明する
3. THE Paper_System SHALL レビュー資料において、特徴量の記述統計・分布、カテゴリ内/間相関、コーパス基本情報との関連、Big5との関連の4つの結果を図表付きで提示する
4. THE Paper_System SHALL レビュー資料において、差別化ポイント（「性格推定」ではなく「相互行為特徴量の定量化指標の提案」としての立て付け）を明記する
5. THE Paper_System SHALL レビュー資料を `docs/homework/ncnp_review_v2.md` として出力する
6. WHILE レビュー資料が共同研究者に共有される状態にある場合、THE Paper_System SHALL 図表への相対パス参照が正しく解決されることを保証する

### 要件9: 紙芝居スライド資料の生成

**ユーザーストーリー:** 研究者として、結果セクションを1枚1図のプレゼンスライドに落とし込んだ紙芝居資料を生成したい。これにより、「このスライドでは、この図を使って、この結論を言う」という構成を視覚的に整理でき、研究発表の準備にもなる。

#### 受入基準

1. WHEN 紙芝居スライド資料の生成が要求された場合、THE Paper_System SHALL Results構成に対応した1枚1図のスライド資料をHTML形式で出力する
2. THE Paper_System SHALL 各スライドにおいて、(a) スライドタイトル、(b) 図表（1枚）、(c) この図で言いたい結論（1〜2文）の3要素を含む
3. THE Paper_System SHALL スライド構成を以下の順序で配置する: (1) 記述統計・分布、(2) カテゴリ内/間相関、(3) コーパス基本情報との関連、(4) Big5との関連（Permutation）、(5) Teacher間一致度、(6) Bootstrap Top Drivers
4. THE Paper_System SHALL スライド資料を `reports/paper_figs_v2/kamishibai_slides.html` として出力する
5. THE Paper_System SHALL スライド資料において、`reports/paper_figs_v2/` 配下のPNG画像を参照する
6. IF 参照する画像ファイルが存在しない場合、THEN THE Paper_System SHALL プレースホルダーテキストを表示し、エラーを回避する

### 要件10: 論文の差別化と位置づけの明確化

**ユーザーストーリー:** 研究者として、本研究の新規性と差別化ポイントを論文内で明確に表現したい。これにより、査読者に対して研究の貢献を説得的に示せる。

#### 受入基準

1. THE Paper_System SHALL Introductionにおいて、「性格推定」ではなく「日本語会話における相互行為特徴量の定量化指標の提案」として研究を位置づける記述を含む
2. THE Paper_System SHALL Methodにおいて、再現可能な評価設計（subject-wise split、permutation test 5000回、bootstrap 500回）を明示する
3. THE Paper_System SHALL Resultsにおいて、特徴量の記述・相関分析を先に配置し、外部指標との関連を妥当性検証として後段に配置する構成を採用する
4. THE Paper_System SHALL Discussionにおいて、日本語会話コーパスでの初の体系的検証であることを先行研究（`docs/homework/asd_paper.md`）との対比で記述する
5. THE Paper_System SHALL Discussionにおいて、限界（小標本N=120、外部検証未了、LLM教師の妥当性未検証）を明示する

### 要件11: 特徴量定義の文書化

**ユーザーストーリー:** 研究者として、18特徴量の定義と計算手順を論文品質で文書化したい。これにより、第三者が特徴量を再現できる。

#### 受入基準

1. THE Paper_System SHALL 18特徴量の各々について、名称、カテゴリ（PG/FILL/IX/RESP）、1行の概要説明、計算アルゴリズムの4項目を含む定義を提供する
2. THE Paper_System SHALL 特徴量定義において、`src/features/` 配下の実装コードとの対応関係を明示する
3. THE Paper_System SHALL 特徴量定義において、controls（除外変数: EXCL3）と説明変数の区別を明記する
4. WHEN 特徴量の計算に前提条件（分母がゼロの場合の扱い等）がある場合、THE Paper_System SHALL その前提条件と欠損値の処理方法を記述する
5. THE Paper_System SHALL 特徴量定義をLaTeX論文のMethodセクション内テーブルとして組版可能な形式で出力する

### 要件12: 探索的結果（A/E/N/O）のAppendix構成

**ユーザーストーリー:** 研究者として、C以外のtrait（A/E/N/O）の結果を探索的知見としてAppendixに整理したい。これにより、論文の透明性を高め、将来の研究への示唆を提供できる。

#### 受入基準

1. THE Paper_System SHALL Appendixにおいて、A/E/N/Oの各traitについてPermutation test結果（4教師×r_obs×p値）のテーブルを含む
2. THE Paper_System SHALL Appendixにおいて、A/E/N/Oの結果がteacher依存性を示すことを、Teacher間一致度との関連で記述する
3. THE Paper_System SHALL Appendixにおいて、Bootstrap Top10特徴量のCとの重なり（overlap）分析結果を含む
4. WHILE A/E/N/Oの結果が探索的位置づけである場合、THE Paper_System SHALL 「探索的結果であり確認的解釈は避けるべき」旨の注記を付す
5. IF 特定のteacher×trait組み合わせで有意な結果が得られた場合、THEN THE Paper_System SHALL その結果を報告しつつ、一般因子混入の可能性について注記する
