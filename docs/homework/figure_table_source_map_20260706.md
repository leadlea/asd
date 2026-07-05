# 図表 ↔ 解析ファイル 対応表（paper1_ja_st_rev_20260705）

原稿 `paper1_ja_st_rev_20260705.tex` に掲載の全図表と、それを出力した生成スクリプト・集計元データ・上流解析スクリプトの対応表。宗田さんの方法記載チェック用。

- 作成: 2026-07-06 / 福原
- 原稿: `paper1_ja_st_rev_20260705.tex`（44ページ）
- 図表の実体: `reports/paper_figs_v2/`（`tab_*.tex` / `fig_*.png`）
- 用語:
  - **生成スクリプト** = 原稿掲載の tex/png を直接出力するコード
  - **集計元データ** = 生成スクリプトが読み込むファイル（統計値の一次ソース）
  - **上流解析スクリプト** = 集計元データ（TSV等）を計算・出力したコード

## 本文（§3 結果）

| 番号(label) | 種別 | 原稿位置・内容 | 生成スクリプト::関数 | 集計元データ | 上流解析スクリプト |
|---|---|---|---|---|---|
| tab:feature\_def | 表 | §2.2 特徴量定義（19変数） | `gen_paper_figs_v2.py::gen_tab_feature_definitions` | `scripts/paper_figs/feature_definitions.py::get_explanatory_features()`（静的定義） | ― |
| fig:feature\_dist | 図 | §3.1 特徴量分布 | `gen_paper_figs_v2.py::gen_feature_distribution` | `artifacts/analysis/features_min/features_cejc_home2_hq1.parquet` | `scripts/analysis/extract_interaction_features_min.py` |
| tab:desc\_stats\_full | 表 | §3.1 記述統計量 | `gen_paper_figs_v2.py::gen_descriptive_stats_full_table` | 同上 features parquet | 同上 |
| fig:corr\_heatmap | 図 | §3.2 相関ヒートマップ | `gen_paper_figs_v2.py::gen_corr_heatmap_block` | 同上 features parquet | 同上 |
| tab:corr\_matrix | 表 | §3.2 相関行列 | `gen_paper_figs_v2.py::_gen_tab_corr_matrix`（gen\_corr\_heatmap\_block 内） | 同上 features parquet | 同上 |
| tab:metadata\_tests | 表 | §3.3 属性関連（性別U/年齢ρ） | `gen_paper_figs_v2.py::gen_tab_metadata_tests` | features parquet + `artifacts/analysis/.../cejc_speaker_metadata.tsv` | 検定は生成関数内（Mann-Whitney U / Spearman ρ, pairwise deletion） |
| tab:three\_stage | 表 | §3.4 3段階Ridge（R²/RMSE） | `scripts/paper_figs/gen_tab_three_stage_r2.py --teacher ensemble`（※先祖返り防止で batch 除外。旧 `gen_paper_figs_v2.py::gen_tab_three_stage` は不使用） | `artifacts/analysis/results/three_stage_metrics_ensemble.tsv` + `three_stage_paired_test_ensemble.tsv` | `scripts/analysis/three_stage_ridge.py`, `three_stage_paired_test.py` |
| fig:three\_stage | 図 | §3.4 3段階Ridge（R²棒） | `scripts/paper_figs/gen_fig_three_stage_r2.py --teacher ensemble`（※同上。旧 `gen_fig_three_stage_comparison` は不使用） | 同上 three\_stage\_*.tsv | 同上 |
| tab:ensemble\_perm | 表 | §3.4 置換検定（全5次元） | `gen_paper_figs_v2.py::gen_tab_ensemble_permutation` | `artifacts/analysis/results/ensemble_perm_v4/ensemble_summary.tsv` | `scripts/analysis/ensemble_permutation.py` |
| fig:predicted\_vs\_observed | 図 | §3.4 予測vs観測散布図 | `gen_paper_figs_v2.py::gen_fig_predicted_vs_observed` | `ensemble_perm_v4/ensemble_summary.tsv` + `datasets/cejc_home2_hq1_XY_{trait}only_ensemble.parquet` | `scripts/analysis/ensemble_permutation.py` |
| tab:permutation\_coef | 表 | §3.4 回帰係数置換検定（C） | `gen_paper_figs_v2.py::gen_tab_permutation_coef` | `artifacts/analysis/results/cejc_home2_hq1_Conly_*_controls_excluded/` | `scripts/analysis/permutation_coef_test.py` |
| tab:bootstrap\_variance | 表 | §3.4 Bootstrap安定性（C） | `gen_paper_figs_v2.py::gen_tab_bootstrap_variance` | `bootstrap_variance_{trait}_{teacher}.tsv` | `scripts/analysis/bootstrap_variance.py` |
| fig:bootstrap\_variance | 図 | §3.4 Bootstrap CIフォレスト | `gen_paper_figs_v2.py::gen_fig_bootstrap_variance` | 同上 bootstrap\_variance\_*.tsv | 同上 |

## 付録

| 番号(label) | 種別 | 原稿位置・内容 | 生成スクリプト::関数 | 集計元データ | 上流解析スクリプト |
|---|---|---|---|---|---|
| fig:metadata\_gender | 図 | 付録 属性(性別) | `gen_paper_figs_v2.py::gen_metadata_gender` | features parquet + cejc\_speaker\_metadata.tsv | 生成関数内で検定 |
| fig:metadata\_age | 図 | 付録 属性(年齢) | `gen_paper_figs_v2.py::gen_metadata_age` | 同上 | 同上 |
| tab:score\_stats | 表(インライン) | 付録 仮想Big5基本統計量 | 原稿に直書き（tex内 tabular） | `artifacts/big5/llm_scores/`（4モデルitem-level）+ Cronbach α | `scripts/big5/score_big5_bedrock.py`, `scripts/analysis/teacher_agreement_big5.py` |
| tab:three\_stage\_r | 表 | 付録 3段階Ridge（相関r版） | `scripts/paper_figs/gen_tab_three_stage_r2.py` | `three_stage_{trait}_{teacher}.tsv`（r列） | `scripts/analysis/three_stage_ridge.py` |
| tab:sensitivity\_alpha | 表 | 付録 α感度 | `gen_paper_figs_v2.py::gen_tab_sensitivity_alpha` | `artifacts/analysis/results/sensitivity/sensitivity_results.tsv`（analysis\_type=alpha） | `scripts/analysis/sensitivity_analysis.py --analysis_type alpha` |
| （交絡統制 本文値） | 数値 | 付録 交絡統制(Model A/B) | 原稿に直書き | `artifacts/analysis/results/confound_groupkfold_all.tsv` | `scripts/analysis/confound_analysis_groupkfold.py` |
| fig:teacher\_corr\_matrix\_appendix | 図 | 付録 モデル間相関行列 | `gen_paper_figs_v2.py::gen_fig_teacher_corr_matrix` | `docs/homework/assets/teacher_corr_{trait}.tsv` | `scripts/analysis/teacher_agreement_big5.py` |
| fig:teacher\_heatmap | 図 | 付録 モデル間一致度(平均) | `gen_paper_figs_v2.py::gen_fig_teacher_heatmap` | 同上 teacher\_corr\_*.tsv | 同上 |
| tab:perm\_all | 表 | 付録 個別モデル置換検定 | `gen_paper_figs_v2.py::gen_tab_permutation_all` | `artifacts/analysis/results/cejc_home2_hq1_*only_*_controls_excluded/` | `scripts/analysis/ensemble_permutation.py`（モデル別） |
| tab:baseline\_comparison | 表(インライン) | 付録 ベースライン検証3条件 | 原稿に直書き（tex内 tabular） | `artifacts/analysis/results/baseline_validation/comparison_summary.tsv`（条件1=`ensemble_perm_v4/ensemble_summary.tsv`） | `scripts/baseline/compare_conditions.py`（採点=`score_big5_bedrock.py`／分析=`ensemble_permutation.py`） |
| （Dose-Response 結果） | 数値 | 付録 Dose-Response実験 | 原稿に直書き | `artifacts/dose_response/`（YESNO/FILL/OIR × x0/x1/x3 monologues）＋採点結果 | Dose-Response前処理＋`score_big5_bedrock.py` |

## 再現メモ

- 図表の一括再生成: `.venv/bin/python scripts/paper_figs/gen_paper_figs_v2.py`（出力先 `reports/paper_figs_v2/`）
- 3段階Ridge図表（R²/RMSE主指標版・batch除外）: `.venv/bin/python scripts/paper_figs/gen_fig_three_stage_r2.py --teacher ensemble` および `gen_tab_three_stage_r2.py --teacher ensemble`（後者は付録の相関r版 `tab_three_stage_r.tex` も生成）
- データ同一性は各 parquet/tsv の sha256 で固定（`artifacts/` 配下、gitignore対象）
- 主結果の一次ソースは `artifacts/analysis/results/ensemble_perm_v4/ensemble_summary.tsv`（O=0.410 / C=0.432 / E=0.234 / A=0.449 / N=0.317）

## 補足（インライン表の注意）

`tab:score_stats`・`tab:baseline_comparison`・交絡統制の本文値・Dose-Response結果は、生成スクリプトが tex を直接出力せず**原稿に手入力**している。数値変更時は上記「集計元データ」を正として手動更新が必要（2026-07-06 のベースライン表 条件1 修正はこの経路の齟齬を解消したもの）。
