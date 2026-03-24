# 実装計画: 論文化（paper-authoring）

## 概要

既存の分析結果（artifacts/analysis/）を入力として、論文用図表生成スクリプト、LaTeX論文本体、再現性検証スクリプト、NCNPレビュー資料、紙芝居スライド資料の成果物を段階的に実装する。各ステップは前のステップの出力に依存し、最終的にすべてが統合される。

NCNPレビュー（山下先生・宗田さん）のフィードバックに基づき、メインメッセージを「相互行為特徴量の定量化指標の提案」に据え直し、Results構成を新4段構成（記述統計→相関→コーパス基本情報→Big5）に改訂した。タスク1〜9は完了済みであり、タスク10以降で新要件に対応する。

## Tasks

- [x] 1. 図表生成スクリプトの実装（`scripts/paper_figs/gen_paper_figs_v2.py`）
  - [x] 1.1 CLIインターフェースとデータ読み込み基盤の実装
    - argparseで `--results_dir`, `--bootstrap_dir`, `--features_parquet`, `--out_dir` の4引数を定義
    - permutation.logパーサー（正規表現で `r_obs`, `p(|r|)` を抽出）を実装
    - bootstrap_summary.tsv、features parquetの読み込みユーティリティを実装
    - 入力ファイル不在時のエラーハンドリング（FileNotFoundError捕捉、パス＋期待スキーマをstderrに出力）
    - _Requirements: 2.6, 2.7_

  - [ ]* 1.2 Property 3のプロパティテスト: 欠損入力時のエラーメッセージの情報性
    - **Property 3: 欠損入力時のエラーメッセージの情報性**
    - hypothesisでランダムなファイルパス文字列を生成し、エラーメッセージにそのパス文字列が含まれることを検証
    - `@settings(max_examples=100)`
    - **Validates: Requirements 2.7**

  - [x] 1.3 Permutation testバーチャート生成（`fig_permutation_C_bar.png`）の実装
    - Cの4教師（Sonnet4, Qwen3, GPT-OSS, DeepSeek）のr_obsとp値をバーチャートで可視化
    - 有意水準（p<0.05）のラインを描画、p値をバー上にアノテーション
    - matplotlib描画エラー時はValueErrorを捕捉しスキップして他の図表生成を継続
    - _Requirements: 2.1_

  - [x] 1.4 Bootstrap radarチャート生成（`fig_bootstrap_C_radar.png`）の実装
    - CのBootstrap Top10特徴量のtopk_rateとsign_agree_rateをレーダーチャートで可視化
    - bootstrap_summary.tsvからtopk_rate降順でTop10を選択
    - _Requirements: 2.2_

  - [x] 1.5 Teacher間一致度ヒートマップ生成（`fig_teacher_heatmap.png`）の実装
    - 5 trait × 4 teacherのPearson相関行列をヒートマップで可視化
    - 各traitのmean rを表示
    - _Requirements: 2.3_

  - [x] 1.6 記述統計テーブル生成（`tab_descriptive_stats.tex`）の実装
    - 18特徴量のN, mean, SD, p50, p90をLaTeX tabular形式で出力
    - features parquetから計算、NaN列の適切な処理
    - _Requirements: 2.4_

  - [ ]* 1.7 Property 2のプロパティテスト: 記述統計テーブルの完全性
    - **Property 2: 記述統計テーブルの完全性**
    - hypothesisでランダムな18カラムのDataFrameを生成し、出力LaTeXテーブルが18行×5統計量を含むことを検証
    - `@settings(max_examples=100)`
    - **Validates: Requirements 2.4**

  - [x] 1.8 Permutation全結果テーブル（`tab_permutation_all.tex`）と特徴量定義テーブル（`tab_feature_definitions.tex`）の実装
    - 全trait×全teacherのpermutation結果をLaTeX tabular形式で出力
    - 18特徴量の名称・カテゴリ・概要・計算式をLaTeX tabular形式で出力
    - _Requirements: 2.4, 6.1, 6.5_

  - [ ]* 1.9 Property 1のプロパティテスト: 図表生成の完全性
    - **Property 1: 図表生成の完全性**
    - hypothesisで有効な分析結果データ（permutation結果、bootstrap結果、特徴量データ）を生成し、全期待ファイル（3 PNG）が出力されることを検証
    - `@settings(max_examples=100)`
    - **Validates: Requirements 2.1, 2.2, 2.3**

- [x] 2. チェックポイント - 図表生成スクリプトの動作確認
  - Ensure all tests pass, ask the user if questions arise.
  - `python scripts/paper_figs/gen_paper_figs_v2.py` を実行し、`reports/paper_figs_v2/` に全ファイルが生成されることを確認

- [x] 3. 特徴量定義データ構造の実装と検証
  - [x] 3.1 18特徴量定義のPythonデータ構造を実装
    - 各特徴量に name, category (PG/FILL/IX/RESP), summary, algorithm の4項目を持つdict/dataclassを定義
    - `extract_interaction_features_min.py` のコードから計算アルゴリズムを導出
    - controls（EXCL3）と説明変数の区別を明記
    - 分母ゼロ時のNaN処理を記述
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [ ]* 3.2 Property 5のプロパティテスト: 特徴量定義の4項目完全性
    - **Property 5: 特徴量定義の4項目完全性**
    - 特徴量定義データ構造の各エントリに name, category, summary, algorithm の4項目が非空で含まれることを検証
    - `@settings(max_examples=100)`
    - **Validates: Requirements 6.1**

- [x] 4. 再現性検証スクリプトの実装（`scripts/analysis/verify_reproducibility.py`）
  - [x] 4.1 Permutation結果の検証ロジックの実装
    - 論文記載値（Sonnet4: r=0.434 p=0.0008、Qwen3: r=0.390 p=0.001、GPT-OSS: r=0.447 p=0.0008、DeepSeek: r=0.205 p=0.113）をハードコード
    - permutation.logから実測値を読み込み、一致判定
    - ファイル不在時は `actual="FILE_NOT_FOUND"` として記録し継続
    - _Requirements: 3.1, 3.4, 3.5_

  - [x] 4.2 Teacher間一致度・Bootstrap Top3の検証ロジックの実装
    - Teacher間一致度（C mean r=0.699、A mean r=0.435）の検証
    - Bootstrap Top3（FILL_has_any、IX_oirmarker_after_question_rate、PG_speech_ratio）の検証
    - 数値パース失敗時は `actual="PARSE_ERROR"` として記録
    - _Requirements: 3.2, 3.3, 3.5_

  - [x] 4.3 TSVサマリー出力の実装
    - 全検証結果を `artifacts/analysis/results/reproducibility_check.tsv` に出力
    - カラム: check_item, expected, actual, match, diff
    - 乖離がある場合は差分を記録（数値は絶対差、文字列は "MISMATCH"）
    - _Requirements: 3.4, 3.5_

  - [ ]* 4.4 再現性検証スクリプトのユニットテスト
    - 既知の結果ファイル群で全項目 `match=True` を検証
    - 意図的乖離ファイルで `match=False` と差分記録を検証
    - ファイル不在時の `FILE_NOT_FOUND` 記録を検証
    - _Requirements: 3.1, 3.2, 3.3, 3.5_

- [x] 5. チェックポイント - 再現性検証の実行確認
  - Ensure all tests pass, ask the user if questions arise.
  - `python scripts/analysis/verify_reproducibility.py` を実行し、reproducibility_check.tsv の内容を確認

- [x] 6. 論文LaTeX本体の実装（`paper1_ja.tex`）
  - [x] 6.1 LaTeX文書構造とプリアンブルの実装
    - uplatex + dvipdfmx対応のプリアンブル（documentclass, usepackage等）
    - `\graphicspath{{reports/paper_figs_v2/}}` の設定
    - 6セクション（Introduction〜Appendix）の骨格を定義
    - 画像・テーブルファイル不在時のプレースホルダーコメント挿入
    - _Requirements: 1.1, 1.7, 1.8_

  - [x] 6.2 Introductionセクションの執筆
    - 談話×LLM×性格推定の先行研究ギャップ（`docs/homework/asd_paper.md` ベース）
    - 「性格推定」ではなく「会話の相互行為の再現可能な計測」としての位置づけ
    - _Requirements: 1.2, 5.1_

  - [x] 6.3 Methodセクションの執筆
    - 2.1 データ（CEJC home2 HQ1, N=120）
    - 2.2 特徴量（18変数の2段階説明: `\input{tab_feature_definitions.tex}` + アルゴリズム詳細）
    - 2.3 仮想教師プロトコル（IPIP-NEO-120, 4モデル）
    - 2.4 回帰モデル（Ridge + 5-fold CV）
    - 2.5 信頼性検証（permutation test 5000回, bootstrap 500回）
    - controls（EXCL3）と説明変数の区別を明記
    - _Requirements: 1.3, 1.4, 5.2, 6.1, 6.3, 6.4, 6.5_

  - [x] 6.4 Resultsセクションの執筆
    - 3.1 Cの頑健性（主結果: 4教師permutation、`\input{tab_permutation_all.tex}`、`\includegraphics{fig_permutation_C_bar.png}`）
    - 3.2 Teacher間一致度（補助結果: `\includegraphics{fig_teacher_heatmap.png}`）
    - 3.3 Bootstrap Top Drivers（補助結果: `\includegraphics{fig_bootstrap_C_radar.png}`）
    - 複数LLM教師の頑健性をTeacher間一致度（C mean r=0.699）と関連づけて記述
    - _Requirements: 1.5, 5.3_

  - [x] 6.5 Discussion・Conclusion・Appendixセクションの執筆
    - Discussion: 相互行為特徴量の解釈、日本語会話コーパスでの初の体系的検証、限界（N=120、外部検証未了、LLM教師の妥当性未検証）
    - Conclusion: 主要知見のまとめ
    - Appendix: A/E/N/Oの探索的permutation結果テーブル、Bootstrap overlap分析、感度分析枠
    - 「探索的結果であり確認的解釈は避けるべき」旨の注記
    - 有意結果への一般因子混入の可能性に関する注記
    - _Requirements: 1.6, 5.4, 5.5, 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]* 6.6 LaTeX論文構造のユニットテスト
    - 6セクション（Introduction〜Appendix）の存在を検証
    - Methodセクション内の4サブセクションの存在を検証
    - Appendix内のA/E/N/O permutationテーブルの存在を検証
    - 「探索的結果」注記の存在を検証
    - 限界記述（N=120、外部検証未了）の存在を検証
    - _Requirements: 1.1, 1.4, 1.6, 7.1, 7.4, 5.5_

  - [ ]* 6.7 Property 6のプロパティテスト: 有意結果への一般因子混入注記
    - **Property 6: 有意結果への一般因子混入注記**
    - Appendix内のteacher×trait permutation結果でp<0.05の場合、近傍に一般因子混入の可能性に関する注記テキストが存在することを検証
    - `@settings(max_examples=100)`
    - **Validates: Requirements 7.5**

- [x] 7. チェックポイント - LaTeX論文のコンパイル確認
  - Ensure all tests pass, ask the user if questions arise.
  - `uplatex paper1_ja.tex && dvipdfmx paper1_ja.dvi` でコンパイルが通ることを確認

- [x] 8. NCNPレビュー資料の実装（`docs/homework/ncnp_review_v2.md`）
  - [x] 8.1 レビュー資料本体の執筆
    - 研究の位置づけ（差別化ポイント: 「性格推定」ではなく「会話の相互行為の計測」）
    - 方法: 18特徴量の2段階説明（概要＋アルゴリズム）
    - 結果: Permutation / Teacher一致度 / Bootstrap（`reports/paper_figs_v2/` 配下のPNG参照付き）
    - 議論ポイント（NCNPミーティング用）
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 8.2 Property 4のプロパティテスト: Markdown内画像参照の解決可能性
    - **Property 4: Markdown内画像参照の解決可能性**
    - 生成されたMarkdown内の全画像参照パスを抽出し、Markdownファイルの位置から相対解決した場合に対応ファイルが存在することを検証
    - `@settings(max_examples=100)`
    - **Validates: Requirements 4.6**

  - [ ]* 8.3 レビュー資料のユニットテスト
    - 「方法」「結果」セクションの存在を検証
    - 18特徴量の概要とアルゴリズムの両方が記載されていることを検証
    - _Requirements: 4.1, 4.2_

- [x] 9. 最終チェックポイント（v1） - 全成果物の統合確認
  - Ensure all tests pass, ask the user if questions arise.
  - 全4成果物（gen_paper_figs_v2.py、paper1_ja.tex、verify_reproducibility.py、ncnp_review_v2.md）の存在と整合性を確認
  - LaTeX論文が図表生成スクリプトの出力を正しく参照していることを確認


- [x] 10. 新規図表の追加実装（`scripts/paper_figs/gen_paper_figs_v2.py` への関数追加）
  - [x] 10.1 CLIに `--metadata_tsv` 引数を追加し、コーパス基本情報読み込みを実装
    - argparseに `--metadata_tsv` オプションを追加（コーパス基本情報TSV: 性別・年齢等）
    - メタデータTSV不在時は警告出力しメタデータ関連図の生成をスキップ（他の図表生成は継続）
    - メタデータに期待カラム（gender, age）が不足する場合は利用可能なカラムのみで処理
    - _Requirements: 2.4, 2.9, 2.10, 5.6_

  - [x] 10.2 特徴量分布図の生成（`fig_feature_distribution.png`）
    - 18特徴量のバイオリンプロットまたはヒストグラムをPNG形式で出力
    - features parquetから読み込み、カテゴリ（PG/FILL/IX/RESP）ごとにグループ化して描画
    - NaN値の適切な処理（dropna）
    - _Requirements: 2.1, 3.1, 3.2_

  - [x] 10.3 拡張記述統計テーブルの生成（`tab_descriptive_stats_full.tex`）
    - 18特徴量のN, mean, SD, min, p25, p50, p75, p90, maxをLaTeX tabular形式で出力
    - 既存の `tab_descriptive_stats.tex`（5統計量）を拡張した9統計量版
    - _Requirements: 2.2, 3.1_

  - [x] 10.4 相関行列ヒートマップの生成（`fig_corr_heatmap_block.png`）
    - 18特徴量間のPearson相関行列をカテゴリ（PG→FILL→IX→RESP）ブロック構造で可視化
    - カテゴリ境界線を描画し、同一カテゴリ内/カテゴリ間の相関構造を視覚的に区別
    - 相関行列テーブル（`tab_corr_matrix.tex`）もLaTeX tabular形式で同時出力
    - _Requirements: 2.3, 4.1, 4.2, 4.3_

  - [x] 10.5 コーパス基本情報関連図の生成（`fig_metadata_gender.png`, `fig_metadata_age.png`）
    - 性別×特徴量: 箱ひげ図 + Mann-Whitney U検定結果（検定統計量・p値をアノテーション）
    - 年齢×特徴量: 散布図 + Pearson/Spearman相関係数・p値をアノテーション
    - コーパス基本情報との関連分析結果テーブル（`tab_metadata_tests.tex`）をLaTeX tabular形式で出力
    - scipy.statsを使用（mannwhitneyu, pearsonr, spearmanr）
    - _Requirements: 2.4, 5.1, 5.2, 5.3, 5.7_

  - [ ]* 10.6 Property 7のプロパティテスト: コーパス基本情報分析の統計的正当性
    - **Property 7: コーパス基本情報分析の統計的正当性**
    - hypothesisでランダムな性別（M/F）・年齢データと特徴量データを生成し、群間比較の検定統計量・p値、相関係数・p値が正しい形式で出力されることを検証
    - `@settings(max_examples=100)`
    - **Validates: Requirements 5.2, 5.3**

  - [ ]* 10.7 Property 1（拡張版）のプロパティテスト: 図表生成の完全性（新規図表含む）
    - **Property 1: 図表生成の完全性（拡張版）**
    - hypothesisで有効な分析結果データ（permutation結果、bootstrap結果、特徴量データ、コーパス基本情報）を生成し、全期待ファイル（既存3 PNG + 新規3 PNG）が出力されることを検証
    - `@settings(max_examples=100)`
    - **Validates: Requirements 2.1, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8**

  - [ ]* 10.8 Property 2（拡張版）のプロパティテスト: 拡張記述統計テーブルの完全性
    - **Property 2: 記述統計テーブルの完全性（拡張版）**
    - hypothesisでランダムな18カラムのDataFrameを生成し、出力LaTeXテーブルが18行×9統計量（N, mean, SD, min, p25, p50, p75, p90, max）を含むことを検証
    - `@settings(max_examples=100)`
    - **Validates: Requirements 2.2, 3.1**

- [x] 11. 論文LaTeXのResults構成改訂（`paper1_ja.tex`）
  - [x] 11.1 Resultsセクションを新4段構成に書き直し
    - 3.1 提案特徴量の記述統計と分布（Results 1-1）: `\input{tab_descriptive_stats_full.tex}` + `\includegraphics{fig_feature_distribution.png}` + 分布形状の記述
    - 3.2 特徴量カテゴリ内/間の相関分析（Results 1-2）: `\input{tab_corr_matrix.tex}` + `\includegraphics{fig_corr_heatmap_block.png}` + 同一カテゴリ内高相関の解釈
    - 3.3 コーパス基本情報との関連性（Results 2-1）: `\input{tab_metadata_tests.tex}` + `\includegraphics{fig_metadata_gender.png}` + `\includegraphics{fig_metadata_age.png}` + 納得感の強い結果から順に報告
    - 3.4 性格特性（Big5）との関連性（Results 2-2）: 既存のPermutation/Teacher一致度/Bootstrap結果を「妥当性検証」として位置づけ直し
    - 既存のResults内容（6.4で実装済み）を新構成に再配置
    - _Requirements: 1.6, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 5.1, 5.2, 5.3, 5.4, 5.7, 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 11.2 Introductionのメインメッセージ更新
    - 「性格推定」→「日本語会話における相互行為特徴量の定量化指標の提案」にメインメッセージを変更
    - 研究目的の記述を改訂（特徴量の提案が主、Big5との関連は妥当性検証の位置づけ）
    - _Requirements: 1.2, 10.1_

  - [x] 11.3 Discussionの更新
    - 特徴量の記述・相関分析結果に基づく考察を追加
    - コーパス基本情報との関連に基づく考察を追加
    - 差別化ポイント（「定量化指標の提案」としての立て付け）を強化
    - _Requirements: 10.4, 10.5_

  - [ ]* 11.4 LaTeX論文構造のユニットテスト（新Results構成対応）
    - Results内の新4段構成（記述統計→相関→コーパス基本情報→Big5）の順序を検証
    - 「構成概念妥当性の検証であり、性格推定モデルの構築を目的としない」旨の注記の存在を検証
    - 新規図表（fig_feature_distribution, fig_corr_heatmap_block, fig_metadata_gender, fig_metadata_age）の参照を検証
    - _Requirements: 1.6, 6.4, 6.5_

- [x] 12. NCNPレビュー資料の改訂（`docs/homework/ncnp_review_v2.md`）
  - [x] 12.1 レビュー資料を新Results構成に改訂
    - 研究の位置づけを「相互行為特徴量の定量化指標の提案」に更新
    - 結果セクションを新4段構成（記述統計→相関→コーパス基本情報→Big5）に改訂
    - 新規図表（分布図、相関ヒートマップ、コーパス基本情報関連図）への参照を追加
    - 議論ポイントにNCNPレビューフィードバックの反映状況を追記
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [ ]* 12.2 Property 4のプロパティテスト（改訂版）: Markdown内画像参照の解決可能性
    - **Property 4: Markdown内画像参照の解決可能性（改訂版）**
    - 改訂後のMarkdown内の全画像参照パス（新規図表含む）を抽出し、Markdownファイルの位置から相対解決した場合に対応ファイルが存在することを検証
    - `@settings(max_examples=100)`
    - **Validates: Requirements 8.6**

- [x] 13. 紙芝居スライド資料の実装（`scripts/paper_figs/gen_kamishibai_slides.py`）
  - [x] 13.1 紙芝居スライド生成スクリプトの実装
    - Results構成に対応した6枚のスライドを1枚1図で構成するHTML生成スクリプト
    - スライド構成:
      - スライド1: 提案特徴量の分布（`fig_feature_distribution.png`）→ 18特徴量は適度なばらつきを持ち、個人差を捉える指標として有用
      - スライド2: カテゴリ内/間相関（`fig_corr_heatmap_block.png`）→ 同一カテゴリ内で高相関、カテゴリ間は独立性が高い
      - スライド3: コーパス基本情報との関連（`fig_metadata_gender.png` / `fig_metadata_age.png`）→ 性別・年齢と一部特徴量に有意な関連
      - スライド4: Big5との関連 Permutation（`fig_permutation_C_bar.png`）→ Cは4教師中3教師で有意、教師非依存の頑健性
      - スライド5: Teacher間一致度（`fig_teacher_heatmap.png`）→ C: mean r=0.699で最高、仮想教師として安定
      - スライド6: Bootstrap Top Drivers（`fig_bootstrap_C_radar.png`）→ FILL_has_any, IX_oirmarker_after_question_rate, PG_speech_ratioが上位
    - 各スライドに (a) タイトル、(b) 図表（imgタグ）、(c) 結論テキスト（1〜2文）の3要素を含む
    - 自己完結型HTML（CSS埋め込み、画像は相対パス参照）
    - 画像不在時はプレースホルダーテキスト「[図表未生成: {filename}]」を表示
    - 出力先: `reports/paper_figs_v2/kamishibai_slides.html`
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [ ]* 13.2 Property 8のプロパティテスト: 紙芝居スライドの3要素完全性
    - **Property 8: 紙芝居スライドの3要素完全性**
    - 生成されたHTML内の各スライドに (a) スライドタイトル、(b) 図表参照（imgタグまたはプレースホルダー）、(c) 結論テキストの3要素が含まれることを検証
    - `@settings(max_examples=100)`
    - **Validates: Requirements 9.2, 9.6**

  - [ ]* 13.3 紙芝居スライドのユニットテスト
    - スライド数が6枚であることを検証
    - スライド順序（記述統計→相関→コーパス基本情報→Permutation→Teacher一致度→Bootstrap）の検証
    - 画像不在時のプレースホルダーテキスト表示の検証
    - 出力ファイルが `reports/paper_figs_v2/kamishibai_slides.html` に生成されることを検証
    - _Requirements: 9.1, 9.3, 9.4, 9.6_

- [x] 14. 最終チェックポイント（v2） - NCNPレビュー反映後の全成果物統合確認
  - Ensure all tests pass, ask the user if questions arise.
  - 新規図表（fig_feature_distribution, fig_corr_heatmap_block, fig_metadata_gender, fig_metadata_age）が `reports/paper_figs_v2/` に生成されていることを確認
  - 論文LaTeX（`paper1_ja.tex`）が新Results構成で正しくコンパイルされることを確認（`uplatex paper1_ja.tex && dvipdfmx paper1_ja.dvi`）
  - NCNPレビュー資料（`docs/homework/ncnp_review_v2.md`）が新構成を反映していることを確認
  - 紙芝居スライド（`reports/paper_figs_v2/kamishibai_slides.html`）が6枚構成で生成されていることを確認
  - 再現性検証スクリプト（`verify_reproducibility.py`）が新規追加値にも対応していることを確認

## Notes

- `*` 付きタスクはオプションであり、MVP達成のためにスキップ可能
- 各タスクは具体的な要件番号を参照しトレーサビリティを確保
- チェックポイントで段階的に動作確認を行う
- プロパティテストはhypothesisライブラリで実装し、普遍的な正当性を検証
- ユニットテストは具体的なエッジケースとエラー条件を検証
- タスク1〜9は完了済み（v1成果物）。タスク10〜14はNCNPレビューフィードバックに基づく改訂・追加
- 新規図表（分布図、相関ヒートマップ、コーパス基本情報関連図）は既存スクリプトへの関数追加で対応し、既存成果物を壊さない
- 紙芝居スライドは独立した新規スクリプト（`gen_kamishibai_slides.py`）として実装
