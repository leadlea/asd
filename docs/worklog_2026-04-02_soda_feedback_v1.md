# Worklog: 宗田さんフィードバック対応 v1（soda-feedback-v1）

日付: 2026-04-02
担当: 福原玄（実装）、Kiro（支援）
Spec: `.kiro/specs/soda-feedback-v1/`

## 背景

NCNP共同研究者・宗田卓史さんから受けた論文ドラフト（paper1_ja.tex）に対する詳細フィードバックへの対応。4本柱＋細かいコメント多数。

## 4本柱の対応

### 1. 話者重複の調査と報告

- `scripts/analysis/speaker_overlap_analysis.py` を新規作成
- 実データ結果: ユニーク話者74名、重複話者25名（71件、59.2%）、女性38名・男性36名
- paper1_ja.tex 2.1節に4つのsubsubsectionを新設（パイプライン概説、HQ1フィルタ詳細、メタ情報紐付け、話者重複・性別内訳）
- Limitationに話者重複バイアスの可能性とICC分析の将来課題を明記
- subject-wise splitの説明を2.1節と2.4節に記載

### 2. 本文とAppendixの切り分け

- 3.4.2節（個別LLM教師比較）の詳細をAppendixに移動
- 本文には「Cは4教師中3教師で有意」の要約＋Appendix参照を残す
- Appendixに新設: プロンプトテンプレート（付録E）、LLM推定スコア基本統計量（付録F、実データ埋め済み）、教師間一致度詳細（付録G）

### 3. 3段階Ridge回帰

- `scripts/analysis/three_stage_ridge.py` を新規作成
- アンサンブルBig5で全5次元×5000回Permutation test実行（seed=42）
- 主要結果（表7）:
  - C: Stage1 r=0.408 → Stage2 r=0.395 → Stage3 r=0.445（Δr₂→₃=+0.050）
  - A: Stage1 r=0.494（人口統計のみで最高）
  - O: Δr₁→₂=+0.155（Classical追加で大幅向上）
  - N: 全ステージ非有意
- 図表: fig_three_stage_comparison.png, tab_three_stage.tex

### 4. 説明可能性の再整理（Permutation係数検定＋Bootstrap分散分析）

- `scripts/analysis/permutation_coef_test.py` を新規作成（5000回、seed=42）
- `scripts/analysis/bootstrap_variance.py` を新規作成（500回復元抽出、seed=42）
- アンサンブルBig5のCに対する結果:
  - Permutation有意（表8）: 7特徴量（PG_speech_ratio, PG_pause_mean/p50/p90, IX_yesno_rate, IX_yesno_after_question_rate, RESP_NE_ENTROPY）
  - Bootstrap CI非跨ぎ（表9）: 9特徴量（上記7個＋FILL_rate_per_100chars, RESP_NE_AIZUCHI_RATE）
  - 共通特徴量（両方で有意＋安定）: 7個
- 旧Top-K/符号一致率をSD/CIベースに全面変更
- 図表: fig_bootstrap_variance.png, tab_bootstrap_variance.tex, tab_permutation_coef.tex

## 細かいコメントへの対応

| 項目 | 対応 |
|------|------|
| 前処理パイプライン追記 | 2.1節に新設 |
| 特徴量名の直感化 | 表・本文に日本語名併記 |
| OIRマーカー完全リスト | 11個を本文に記載 |
| シャノンエントロピー計算詳細 | ユニグラム、自然対数、計算式を明記 |
| CV記述の厳密化 | 「各foldのrの5-fold平均」と明記 |
| alpha=100の選定根拠 | α∈{10,50,100,200,500}の感度分析を報告 |
| 多重共線性の方法移動 | 3.2節→2.4節 |
| Permutation testの統合 | 2.5節→2.4節 |
| アンサンブル計算方法 | 方法セクションに記載 |
| 教師間一致度の説明強化 | 3.4.6節に定義パラグラフ新設、4×4相関行列図追加 |
| p90列の削除 | 記述統計テーブルから削除 |
| 年齢の生データ化 | 「age列の実数値」に変更 |
| 棒グラフの改善 | 散布図＋テーブル形式に変更 |
| プロットタイプの統一 | バイオリンプロットに統一 |

## 数値同期（最終整合）

- 3.4.1: A(r=0.465)が最高精度、C(r=0.447)が教師横断で最も頑健、と明確に分離
- 3.4.3: 表7の値に完全同期
- 3.4.4: 表8ベースで有意7特徴量に更新
- 3.4.5: 表9ベースでCI非跨ぎ9特徴量に更新、7共通特徴量を明示
- 要旨・考察・結論: 旧3特徴量セット（FILL_has_any, IX_oirmarker_after_question_rate, PG_speech_ratio）→新7共通特徴量に全面更新
- 「Cが最高精度」→「Cが教師横断で最も頑健」に修正

## 成果物

### 新規スクリプト（4本）
- `scripts/analysis/speaker_overlap_analysis.py`
- `scripts/analysis/three_stage_ridge.py`
- `scripts/analysis/permutation_coef_test.py`
- `scripts/analysis/bootstrap_variance.py`

### 新規テスト（6プロパティ＋ユニット）
- `tests/test_speaker_overlap_property.py` — Property 1
- `tests/test_three_stage_ridge_property.py` — Property 2
- `tests/test_permutation_coef_property.py` — Property 3
- `tests/test_bootstrap_variance_property.py` — Property 4
- `tests/test_p90_exclusion_property.py` — Property 5
- `tests/test_plot_type_unification_property.py` — Property 6
- `tests/test_gen_tab_permutation_coef.py` — ユニットテスト

### 分析結果（アンサンブル、全5次元）
- `artifacts/analysis/results/three_stage_ensemble/` — 3段階Ridge
- `artifacts/analysis/results/permutation_coef_ensemble/` — Permutation係数検定
- `artifacts/analysis/results/bootstrap_variance_ensemble/` — Bootstrap分散分析
- `artifacts/analysis/results/speaker_overlap_report.tsv` — 話者重複レポート

### 図表（実データ生成）
- `reports/paper_figs_v2/fig_three_stage_comparison.png`
- `reports/paper_figs_v2/fig_bootstrap_variance.png`
- `reports/paper_figs_v2/fig_teacher_corr_matrix.png`
- `reports/paper_figs_v2/tab_three_stage.tex`
- `reports/paper_figs_v2/tab_permutation_coef.tex`
- `reports/paper_figs_v2/tab_bootstrap_variance.tex`

### 論文
- `paper1_ja.tex` — 38ページ、プレースホルダーゼロ、TODO残りゼロ
- `paper1_ja.pdf` — 5.1MB

### 紙芝居
- `reports/paper_figs_v2/kamishibai_slides.html` — スライド7,8を更新

## テスト結果

全18テスト パス（4.5秒）。LaTeX 2パスコンパイル正常。

## 注意事項

- 分析はアンサンブルBig5（4教師item-level平均）で実行済み。sonnet単体の結果も `artifacts/analysis/results/` に残存
- seed=42, Ridge α=100, 5-fold subject-wise CV, 5000 permutations, 500 bootstrap の制約を遵守
- 付録FのLLM推定スコア基本統計量はXYデータのY列から算出（項目平均スケール1〜5）。次元スコア（24〜120）ではない点に注意
