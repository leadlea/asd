# 日本語会話における相互行為特徴量の定量化指標

日本語日常会話コーパス（CEJC）から抽出した **19の相互行為特徴量** を体系化し、
LLM仮想教師によるBig Five性格スコアとの関連を通じて指標の妥当性を検証する研究リポジトリ。

- 研究者: 福原玄（Lead lea）、山下祐一（NCNP）、宗田卓史（NCNP）
- 対象学会: 成人発達支援学会（2026年9月@高知）
- 論文の軸: 相互行為特徴量の提案 + 2段階妥当性検証（3段階Ridge + Permutation係数検定 + Bootstrap分散分析）

---

## 対応状況（2026-07 更新）

| 項目 | 状態 | 備考 |
|------|------|------|
| IX\_topic\_drift\_mean除外 | ✅ 完了 | 統制変数に移動、完全共線性（r=-1.00）の理由をMethod節に明記 |
| 多重比較補正（Holm-Bonferroni） | ✅ 完了 | 補正後もO/C/A/Nの4次元が有意維持 |
| Novel特徴量の先行研究整理 | ✅ 完了 | Kendrick 2015, Meylan & Gahl 2014, Kita & Ide 2007, Dindar et al. 2022等追加 |
| 新規特徴量追加 | ✅ 完了 | PG\_overlap\_rate復帰（Levitan et al. 2012）、PG\_pause\_variability追加 → 計19特徴量 |
| 感度分析 | ✅ 完了 | gap\_tol 6条件、YES/NOリスト 2条件、NE/YOマッチング 3条件 |
| LLMベースライン検証 | ✅ 完了 | 3条件比較（テキスト/要約のみ/ランダム）全工程完了、論文に実測値反映済み |
| 論文LaTeX（日本語） | ✅ 完了 | 46ページ、全セクション実測値反映済み（PDF再コンパイル済み） |
| 紙芝居スライド | ✅ 完了 | 9枚構成（Methods 2枚 + Results 7枚、ベースライン検証スライド含む） |
| **論文最終仕上げ** | ✅ 完了 | 下記「paper-finalization 変更履歴」参照 |
| **Feature Dose-Response実験** | 🔄 進行中 | フィラー率の段階的操作（×0/×1/×3）→ Cスコア変化検証。LLM採点実行中 |
| **次ステップ: 英語化** | ⏳ 未着手 | BRM投稿に向けた英語版作成 |

### paper-finalization 変更履歴（2026-04-15 MTG合意事項）

BRM投稿に向けた最終仕上げとして、以下の作業を実施した。

| # | 作業内容 | 概要 |
|---|---------|------|
| 1 | 表6・表7の数値整合性確認 | `verify_numerical_consistency.py` で3段階Ridge / Permutation係数検定のr\_obs値を照合・統一 |
| 2 | 表5の列削減 | アンサンブルPermutation結果テーブルを4列（Trait, r\_obs, p\_corrected, Sig.）に簡素化 |
| 3 | 図5をPredicted vs Observed散布図に変更 | `fig_predicted_vs_observed.png` 新規追加。Out-of-fold予測値による5次元散布図 |
| 4 | 図6（3段階Ridge比較）の品質向上 | フォントサイズ・カラーパレット・Δr注釈を改善 |
| 5 | 図3・図4のSupplementary移動 + 図番号再割り当て | 性別・年齢図を図S1・S2に移動、本文の図番号を再整理 |
| 6 | Checkpoint - 図表修正の動作確認 | 全図表再生成 + LaTeXコンパイル確認 |
| 7 | CONSORTフローチャート作成 | `fig_consort_flowchart.png` 新規追加。Method 2.1節に配置 |
| 8 | LLM循環的相互行為検証 | `llm_circular_interaction.py` 新規作成 + Discussion 4.5節に結果追記 |
| 9 | Google Docs形式エクスポート | Makefile `docx` ターゲット追加（pandoc変換） |
| 10 | 全体整合性の最終確認 | 全図表再生成、LaTeX 2パスコンパイル成功、参照整合性確認、README更新 |

### 2026-04-16 追加修正（MTGフィードバック反映）

| # | 作業内容 | 概要 |
|---|---------|------|
| A | CONSORTフローチャート数値確定 | [要確認]→実数値（577→140→378→120）。横長レイアウトに変更 |
| B | HQ1フィルタ閾値の明記 | ペア数≥80, 文字数≥2000, 質問直後ペア≥10 の3条件をMethod 2.1.2節に追記 |
| C | Supplementaryプロンプト掲載 | 条件1/2/3のプロンプト全文、IPIP-NEO-120項目構成を付録に追加 |
| D | Feature Dose-Response実験パイプライン | `scripts/dose_response/` に5スクリプト新規作成。Makefileターゲット追加 |
| E | Discussion 4.5節の更新 | 実データ操作のDose-Response設計に書き換え。結果はプレースホルダー（LLM採点実行中） |

---

## 研究概要

1. CEJC home2サブセット（N=120）から **4カテゴリ19特徴量** を再現可能に計測
   - **Classical（既存研究ベース 10個）**: PG（タイミング8変数）+ FILL（フィラー2変数）
   - **Novel（新規提案 9個）**: IX（相互行為5変数）+ RESP（応答型3変数）+ PG\_pause\_variability
2. 4つのLLM（Sonnet4, Qwen3-235B, DeepSeek-V3, GPT-OSS-120B）で Big Five を仮想教師として採点
3. **アンサンブルBig5**（4教師item-level平均）を主結果として報告 → **Holm補正後も5次元中4次元（O, C, A, N）で有意**
4. Ridge回帰 + permutation test（5000回）+ bootstrap（500回）で頑健性を検証
5. **3段階Ridge回帰比較**（人口統計のみ → +Classical → +Novel）で段階的な追加効果を定量化
6. **Permutation回帰係数検定** + **Bootstrap分散分析**（SD/CIベース）の2本立てで寄与特徴量を同定
7. 交絡統制（性別・年齢）後も **Cの有意性が維持**（3/4教師、平均Δr=+0.026）
8. **話者重複の定量報告**: 74名ユニーク話者/25名重複（59.2%）、subject-wise splitで対処
9. **感度分析**: gap\_tol / YES/NOリスト / NE/YOマッチングの3軸でCの頑健性を確認
10. **LLMベースライン検証**: 3条件比較（テキストあり / 要約のみ / ランダムテキスト）でLLMの内容依存性を検証済み。条件3（ランダム）で全次元非有意、条件2のα崩壊を確認

---

## 主要結果

### アンサンブルBig5 Permutation Test（19特徴量、Holm補正後）

| Trait | r_obs | p値 | p値(補正後) | 有意? |
|-------|-------|-----|------------|-------|
| O（開放性） | 0.410 | 0.0014 | 0.0042 | ✅ |
| **C（誠実性）** | **0.432** | **0.0006** | **0.0024** | ✅ |
| E（外向性） | 0.234 | 0.0658 | 0.0658 | ❌ |
| A（協調性） | 0.449 | 0.0004 | 0.0020 | ✅ |
| N（神経症傾向） | 0.317 | 0.0122 | 0.0244 | ✅ |

> v3→v4でOが0.360→0.410に改善。PG\_overlap\_rate復帰の効果が大きい。

### 感度分析（Cの頑健性）

| パラメータ | 条件数 | Cのr\_obs範囲 | 結果 |
|-----------|--------|-------------|------|
| gap\_tol | 6条件 (0.01〜1.0) | 0.426〜0.432 | 全条件 p≤0.001、閾値選択に対して頑健 |
| YES/NOリスト | 2条件 (narrow/broad) | 0.424〜0.432 | 差はわずか |
| NE/YOマッチング | 3条件 | 0.432〜0.434 | ほぼ同一 |

### LLMベースライン検証（3条件比較）✅ 完了

LLMが会話テキストの**内容**に基づいて性格推定しているか、**表層的統計量**のみに依存しているかを検証。

| 条件 | O | C | E | A | N |
|------|-----|------|------|-----|------|
| 条件1（テキスト） | 0.410* | 0.432* | 0.234 | 0.449* | 0.317* |
| 条件2（要約のみ） | 0.528* | 0.640* | 0.302* | 0.374* | 0.711* |
| 条件3（ランダム） | 0.161 | -0.080 | -0.072 | 0.071 | -0.280 |

> 条件3（ランダム）で全次元非有意 → LLMはテキスト内容を利用している。条件2のα崩壊（平均0.04〜0.30）→ 統計量だけでは一貫した性格像を構成できない。

### 個別教師結果（C: 誠実性）
- Sonnet4: r=0.434, p=0.0008 ✅
- Qwen3-235B: r=0.390, p=0.0010 ✅
- GPT-OSS-120B: r=0.447, p=0.0008 ✅
- DeepSeek-V3: r=0.205, p=0.1130 ❌

### 交絡統制（C, 性別・年齢追加後）
- 3/4教師で有意性維持、平均Δr=+0.026（精度向上）
- 特徴量とCの関連は性別・年齢の交絡ではないことを確認

### Cの主要寄与特徴量（Permutation有意 ∩ Bootstrap CI非跨ぎ: 7共通特徴量）
- PG\_speech\_ratio（発話率, +）
- PG\_pause\_mean（平均沈黙長, −）
- PG\_pause\_p50（沈黙長中央値, −）
- PG\_pause\_p90（沈黙長90パーセンタイル, −）
- IX\_yesno\_rate（YES/NO応答率, +）
- IX\_yesno\_after\_question\_rate（質問直後YES/NO率, +）
- RESP\_NE\_ENTROPY（「ね」直後応答多様性, −）

### 3段階Ridge回帰比較（アンサンブルBig5）

| Trait | Stage1 (人口統計) | Stage2 (+Classical) | Stage3 (+Novel) | Δr₂→₃ |
|-------|------------------|--------------------|-----------------|---------| 
| O | r=0.309* | r=0.464** | r=0.442** | -0.023 |
| **C** | **r=0.408**\*\* | **r=0.395**\*\* | **r=0.445**\*\* | **+0.050** |
| E | r=0.100 | r=0.268* | r=0.208 | -0.060 |
| A | r=0.494** | r=0.457** | r=0.464** | +0.007 |
| N | r=0.173 | r=0.162 | r=0.223 | +0.061 |

### 教師間一致度
- C: mean r=0.699（最高）→ 仮想教師として最も安定
- A: mean r=0.435（最低）→ 教師依存性が大きい

---

## 主要ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [論文PDF](paper1_ja.pdf) | コンパイル済みPDF（46ページ） |
| [論文ドラフト（LaTeX）](paper1_ja.tex) | 論文本体（uplatex + dvipdfmx） |
| [紙芝居スライド](https://leadlea.github.io/asd/reports/paper_figs_v2/kamishibai_slides.html) | 9枚構成のプレゼン用HTML（Methods 2枚 + Results 7枚） |
| [MTGアジェンダ（2026-04-15）](docs/agenda_20260415_mtg.md) | v4フィードバック対応チェックリスト + 議論ポイント |
| [作業報告（宗田FB対応）](docs/worklog_2026-04-02_soda_feedback_v1.md) | 4本柱＋細かいコメント対応の全記録 |
| [NCNPレビュー資料 v2](docs/homework/ncnp_review_v2.md) | 研究構成・結果・議論ポイント（共同研究者向け） |
| [先行研究サーベイ](docs/homework/asd_paper.md) | Hu 2025, Altozano 2026, Mun 2024 等の整理 |
| [Big5再現実験の全手順](docs/homework/paper.md) | データ→特徴量→回帰→検定の全パイプライン |
| [特徴量辞書](docs/homework/homework_20260201.md) | 19特徴量の定義・計算方法（人間向け） |

---

## 論文用図表（`reports/paper_figs_v2/`）

| ファイル | 内容 |
|---------|------|
| `fig_consort_flowchart.png` | 🆕 CONSORT形式の前処理パイプラインフローチャート |
| `fig_predicted_vs_observed.png` | 🆕 Predicted vs Observed散布図（5次元、out-of-fold予測） |
| `fig_ensemble_permutation.png` | アンサンブルBig5 全5次元 permutation test 結果 |
| `fig_baseline_vs_extended.png` | ベースライン vs 拡張モデル比較（Δr） |
| `fig_feature_distribution.png` | 19特徴量のカテゴリ別分布 |
| `fig_corr_heatmap_block.png` | 相関ヒートマップ（ブロック構造） |
| `fig_metadata_gender.png` | 性別 × 特徴量の箱ひげ図（Supplementary図S1） |
| `fig_metadata_age.png` | 年齢 × 特徴量の散布図（Supplementary図S2） |
| `fig_permutation_C_bar.png` | C の4教師 permutation test 結果 |
| `fig_teacher_heatmap.png` | Teacher間一致度ヒートマップ |
| `fig_bootstrap_C_radar.png` | Bootstrap Top10 レーダーチャート |
| `fig_three_stage_comparison.png` | 3段階Ridge回帰比較（5次元）🔄 品質向上済み |
| `fig_bootstrap_variance.png` | Bootstrap分散分析フォレストプロット |
| `fig_teacher_corr_matrix.png` | 4×4教師間Pearson相関行列（5次元） |
| `tab_ensemble_permutation.tex` | アンサンブル結果LaTeXテーブル（🔄 4列に簡素化） |
| `tab_baseline_vs_extended.tex` | ベースラインvs拡張比較LaTeXテーブル |
| `tab_three_stage.tex` | 3段階Ridge比較LaTeXテーブル |
| `tab_permutation_coef.tex` | Permutation回帰係数検定LaTeXテーブル |
| `tab_bootstrap_variance.tex` | Bootstrap分散分析LaTeXテーブル |
| `tab_feature_definitions.tex` | 特徴量定義テーブル（Classical/Novel分類付き） |

---

## ディレクトリ構成

```
.
├── paper1_ja.tex              # 論文本体（LaTeX）
├── paper1_ja.pdf              # コンパイル済みPDF
├── scripts/
│   ├── analysis/              # 統計分析（Ridge回帰・permutation・bootstrap・交絡統制・感度分析）
│   ├── baseline/              # LLMベースライン検証（3条件比較パイプライン）
│   ├── paper_figs/            # 論文用図表生成スクリプト
│   ├── big5/                  # LLMによるBig5採点（Bedrock経由）
│   ├── cejc/                  # CEJCコーパス前処理（話者メタデータビルド含む）
│   └── csj/                   # CSJコーパス前処理
├── artifacts/
│   ├── analysis/datasets/     # 分析用データセット（parquet）
│   ├── analysis/features_min/ # 抽出済み特徴量
│   ├── analysis/results/      # 回帰・検定・アンサンブル・ベースライン比較・交絡統制結果
│   └── baseline/              # ベースライン検証中間成果物（monologues_summary/random, shuffle_mapping）
├── docs/
│   ├── homework/              # 分析メモ・レビュー資料
│   └── minutes/               # 議事メモ
├── reports/
│   └── paper_figs_v2/         # 論文用図表（最新）
└── .kiro/
    ├── specs/                 # Spec駆動開発の仕様書
    └── steering/              # Kiroステアリングファイル
```

---

## 主要スクリプト

### 分析パイプライン（`scripts/analysis/`）

| スクリプト | 用途 |
|-----------|------|
| `extract_interaction_features_min.py` | 19特徴量の抽出 |
| `train_cejc_big5_from_features.py` | 特徴量 → Big5 Ridge回帰 |
| `permutation_test_ridge_fixedalpha.py` | 置換検定（5000回） |
| `bootstrap_coef_stability.py` | Bootstrap係数安定性（500回） |
| `teacher_agreement_big5.py` | LLM教師間一致度 |
| `ensemble_permutation.py` | アンサンブルBig5（4教師平均）permutation test |
| `baseline_vs_extended.py` | ベースライン（Classical 10個）vs 拡張（全19個）比較 |
| `confound_analysis.py` | 交絡変数（性別・年齢）統制分析 |
| `speaker_overlap_analysis.py` | 話者重複調査（ユニーク話者数・重複件数・性別内訳） |
| `three_stage_ridge.py` | 3段階Ridge回帰比較（人口統計→+Classical→+Novel） |
| `permutation_coef_test.py` | Permutation回帰係数検定（個別特徴量の有意性） |
| `bootstrap_variance.py` | Bootstrap分散分析（SD/CIベースの係数安定性） |
| `sensitivity_analysis.py` | 感度分析（gap\_tol / YES/NOリスト / NE/YOマッチング） |
| `verify_reproducibility.py` | 再現性検証（11項目チェック） |
| `verify_numerical_consistency.py` | 🆕 表6・表7の数値整合性検証（3段階Ridge vs Permutation係数検定） |
| `llm_circular_interaction.py` | 🆕 LLM循環的相互行為検証（特徴量操作→性格推定の循環的検証） |

### ベースライン検証（`scripts/baseline/`）

| スクリプト | 用途 |
|-----------|------|
| `gen_summary_monologues.py` | 条件2: 統計情報テキストのみのmonologues生成 |
| `gen_random_monologues.py` | 条件3: テキストシャッフル（derangement）によるmonologues生成 |
| `compare_conditions.py` | 3条件のr\_obs比較テーブル生成 |
| `prepare_ensemble_dirs.py` | 条件別LLMスコアをensemble\_permutation.py互換ディレクトリに配置 |
| `run_scoring_summary.sh` | 条件2のLLM採点実行スクリプト（4教師×5trait） |
| `run_scoring_random.sh` | 条件3のLLM採点実行スクリプト（4教師×5trait） |
| `run_ensemble_conditions.sh` | 条件2・3のensemble + permutation test実行 |

### 図表生成（`scripts/paper_figs/`）

| スクリプト | 用途 |
|-----------|------|
| `gen_paper_figs_v2.py` | 論文用図表一括生成（24種類: 14図 + 10テーブル） |
| `feature_definitions.py` | 特徴量定義の共通モジュール（Classical/Novel分類付き） |
| `gen_kamishibai_slides.py` | 紙芝居スライド生成（Methods 2枚 + Results 7枚） |

### コーパス前処理（`scripts/cejc/`）

| スクリプト | 用途 |
|-----------|------|
| `build_cejc_speaker_meta.py` | CEJC話者メタデータビルド（S3上の話者.csv + 話者・会話対応表.csv → metadata TSV） |

---

## 技術スタック

- Python 3.12 / venv
- pandas, numpy, scikit-learn (Ridge), scipy
- matplotlib（可視化）
- AWS Bedrock（LLM推論: ap-northeast-1）
- LaTeX（uplatex + dvipdfmx）
- parquet形式 + sha256 によるデータ固定

---

## 再現手順

```bash
# 環境構築
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 特徴量抽出（要: artifacts/内のparquetデータ）
python scripts/analysis/extract_interaction_features_min.py

# Ridge回帰 + CV
python scripts/analysis/train_cejc_big5_from_features.py

# Permutation test（個別教師）
python scripts/analysis/permutation_test_ridge_fixedalpha.py

# アンサンブルBig5 Permutation test
python scripts/analysis/ensemble_permutation.py \
  --items_dir artifacts/big5/llm_scores \
  --features_parquet artifacts/analysis/features_min/features_cejc_home2_hq1.parquet \
  --exclude_cols "n_pairs_total,n_pairs_after_NE,n_pairs_after_YO,IX_n_pairs,IX_n_pairs_after_question,PG_total_time,PG_resp_overlap_rate,FILL_text_len,FILL_cnt_total,FILL_cnt_eto,FILL_cnt_e,FILL_cnt_ano,IX_topic_drift_mean" \
  --out_dir artifacts/analysis/results

# ベースライン vs 拡張モデル比較（例: C/sonnet）
python scripts/analysis/baseline_vs_extended.py \
  --xy_parquet artifacts/analysis/datasets/cejc_home2_hq1_XY_Conly_sonnet.parquet \
  --y_col Y_C --out_dir artifacts/analysis/results

# 交絡統制分析（例: C/sonnet）
python scripts/analysis/confound_analysis.py \
  --xy_parquet artifacts/analysis/datasets/cejc_home2_hq1_XY_Conly_sonnet.parquet \
  --y_col Y_C --metadata_tsv artifacts/analysis/cejc_speaker_metadata.tsv \
  --out_dir artifacts/analysis/results

# Bootstrap
python scripts/analysis/bootstrap_coef_stability.py

# CEJC話者メタデータビルド（S3からCSVをダウンロード後）
python scripts/cejc/build_cejc_speaker_meta.py \
  --features_parquet artifacts/analysis/features_min/features_cejc_home2_hq1.parquet \
  --speaker_csv /tmp/cejc_speaker.csv \
  --mapping_csv /tmp/cejc_speaker_conversation.csv \
  --out artifacts/analysis/cejc_speaker_metadata.tsv

# 論文用図表生成（メタデータTSV付き）
python scripts/paper_figs/gen_paper_figs_v2.py \
  --metadata_tsv artifacts/analysis/cejc_speaker_metadata.tsv

# 紙芝居スライド生成
python scripts/paper_figs/gen_kamishibai_slides.py

# 再現性検証
python scripts/analysis/verify_reproducibility.py

# LaTeX コンパイル
uplatex paper1_ja.tex && uplatex paper1_ja.tex && dvipdfmx paper1_ja.dvi

# Google Docs形式エクスポート（pandoc）
make docx                 # → reports/paper1_ja.docx

# ベースライン検証（データ準備のみ、LLM採点は手動）
make baseline-prep        # 条件2・3のmonologues生成
# → 手動: bash scripts/baseline/run_scoring_summary.sh  (条件2 LLM採点)
# → 手動: bash scripts/baseline/run_scoring_random.sh   (条件3 LLM採点)
# → 手動: bash scripts/baseline/run_ensemble_conditions.sh (ensemble + permutation)
make baseline-compare     # 3条件比較テーブル生成
```

> **注**: コーパス本文（CEJC発話テキスト）はライセンスの関係でリポジトリに含まれていません。
> データファイル（parquet）は `artifacts/` 以下にローカル配置し、sha256で同一性を担保しています。

---

## フィードバック対応ログ

### 論文最終仕上げ（paper-finalization, 2026-04-15 MTG後）

2026-04-15 MTGで合意されたBRM投稿に向けた最終仕上げ。図表の修正・移動（図3/4のSupplementary移動、図5のPredicted vs Observed散布図化、図6の品質向上、表5の列削減）、CONSORTフローチャート新規作成、LLM循環的相互行為検証スクリプト作成、Google Docs形式エクスポート（Makefile docxターゲット）、数値整合性検証を実施。全図表再生成・LaTeXコンパイル・参照整合性を確認済み。

### 山下先生 v4フィードバック対応（2026-04-06〜07）

| 指摘事項 | 対応 |
|---------|------|
| IX\_topic\_drift\_mean削除 | 統制変数に移動、完全共線性の理由をMethod節に明記 |
| 多重比較補正 | Holm-Bonferroni法実装、補正後もO/C/A/Nの4次元が有意維持 |
| Novel特徴量の先行研究整理 | Kendrick 2015, Meylan & Gahl 2014, Kita & Ide 2007, Dindar et al. 2022等追加。「測定手法の新規性」vs「応用の新規性」を区別 |
| 新規特徴量追加 | PG\_overlap\_rate復帰（Levitan et al. 2012）、PG\_pause\_variability追加 → 計19特徴量 |
| パラメータ感度分析 | gap\_tol 6条件、YES/NOリスト 2条件、NE/YOマッチング 3条件で実施。Cは全条件で頑健 |
| LLMテキストなしベースライン | 3条件比較パイプライン実装・LLM採点完了・比較テーブル生成済み。論文に実測値反映 |

### 宗田さんフィードバック対応（2026-04-02）
→ [docs/worklog_2026-04-02_soda_feedback_v1.md](docs/worklog_2026-04-02_soda_feedback_v1.md)

4本柱（話者重複・Appendix切り分け・3段階Ridge・説明可能性再整理）＋細かいコメント全対応。新規スクリプト4本、プロパティテスト6本、アンサンブルBig5で全分析実行。

### 山下先生フィードバック対応
→ [docs/homework/yamashita_feedback_v3_log.md](docs/homework/yamashita_feedback_v3_log.md)

11項目すべて対応完了。対応内容・Before→Afterの一覧、想定外の結果（アンサンブルでO/A/Nも有意）、交絡統制結果の詳細を記載。

---

## 旧コンテンツ

本リポジトリは元々 Nanami Pragmatics Dashboard（母子対話コーパスの語用論指標可視化）として開始しました。
旧ダッシュボードは引き続き GitHub Pages で閲覧可能です。

- [Nanami Pragmatics Dashboard](https://leadlea.github.io/asd/)
- [ダッシュボードガイド](https://leadlea.github.io/asd/nanami_pragmatics_dashboard_guide.html)
- [関連論文調査レポート](https://leadlea.github.io/asd/corpas_paper.html)
