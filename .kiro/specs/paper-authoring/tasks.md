# 実装計画: 論文化（paper-authoring）

## 概要

既存の分析結果（artifacts/analysis/）を入力として、論文用図表生成スクリプト、LaTeX論文本体、再現性検証スクリプト、NCNPレビュー資料の4成果物を段階的に実装する。各ステップは前のステップの出力に依存し、最終的にすべてが統合される。

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

- [x] 9. 最終チェックポイント - 全成果物の統合確認
  - Ensure all tests pass, ask the user if questions arise.
  - 全4成果物（gen_paper_figs_v2.py、paper1_ja.tex、verify_reproducibility.py、ncnp_review_v2.md）の存在と整合性を確認
  - LaTeX論文が図表生成スクリプトの出力を正しく参照していることを確認

## Notes

- `*` 付きタスクはオプションであり、MVP達成のためにスキップ可能
- 各タスクは具体的な要件番号を参照しトレーサビリティを確保
- チェックポイントで段階的に動作確認を行う
- プロパティテストはhypothesisライブラリで実装し、普遍的な正当性を検証
- ユニットテストは具体的なエッジケースとエラー条件を検証
