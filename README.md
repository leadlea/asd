# 日本語会話における相互行為特徴量の定量化指標

日本語日常会話コーパス（CEJC）から抽出した **18の相互行為特徴量** を体系化し、
LLM仮想教師によるBig Five性格スコアとの関連を通じて指標の妥当性を検証する研究リポジトリ。

- 研究者: 福原玄（Lead lea）、山下祐一（NCNP）、宗田卓史（NCNP）
- 対象学会: 成人発達支援学会（2026年9月@高知）
- 論文の軸: 相互行為特徴量の提案 + 2段階妥当性検証

---

## 研究概要

1. CEJC home2サブセット（N=120）から **4カテゴリ18特徴量** を再現可能に計測
   - **Classical（既存研究ベース 9個）**: PG（タイミング7変数）+ FILL（フィラー2変数）
   - **Novel（新規提案 9個）**: IX（相互行為6変数）+ RESP（応答型3変数）
2. 4つのLLM（Sonnet4, Qwen3-235B, DeepSeek-V3, GPT-OSS-120B）で Big Five を仮想教師として採点
3. **アンサンブルBig5**（4教師item-level平均）を主結果として報告 → **5次元中4次元（O, C, A, N）で有意**
4. Ridge回帰 + permutation test（5000回）+ bootstrap（500回）で頑健性を検証
5. ベースライン（Classical 9個）vs 拡張モデル（全18個）比較で **Novel特徴量の付加価値** を定量化
6. 交絡統制（性別・年齢）後も **Cの有意性が維持**（3/4教師、平均Δr=+0.026）

---

## 主要結果

### アンサンブルBig5 Permutation Test

| Trait | r_obs | p値 | 有意? |
|-------|-------|-----|-------|
| O（開放性） | 0.360 | 0.0048 | ✅ |
| **C（誠実性）** | **0.447** | **0.0004** | ✅ |
| E（外向性） | 0.217 | 0.0902 | ❌ |
| A（協調性） | 0.465 | 0.0004 | ✅ |
| N（神経症傾向） | 0.309 | 0.0152 | ✅ |

### 個別教師結果（C: 誠実性）
- Sonnet4: r=0.434, p=0.0008 ✅
- Qwen3-235B: r=0.390, p=0.0010 ✅
- GPT-OSS-120B: r=0.447, p=0.0008 ✅
- DeepSeek-V3: r=0.205, p=0.1130 ❌

### 交絡統制（C, 性別・年齢追加後）
- 3/4教師で有意性維持、平均Δr=+0.026（精度向上）
- 特徴量とCの関連は性別・年齢の交絡ではないことを確認

### Bootstrap Top Drivers（C, Sonnet4基準）
- FILL_has_any（フィラー出現率, +）
- IX_oirmarker_after_question_rate（質問直後OIR率, +）
- PG_speech_ratio（発話率, +）

### 教師間一致度
- C: mean r=0.699（最高）→ 仮想教師として最も安定
- A: mean r=0.435（最低）→ 教師依存性が大きい

---

## 主要ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [論文PDF](paper1_ja.pdf) | コンパイル済みPDF（27ページ） |
| [論文ドラフト（LaTeX）](paper1_ja.tex) | 論文本体（uplatex + dvipdfmx） |
| [紙芝居スライド](reports/paper_figs_v2/kamishibai_slides.html) | 8枚構成のプレゼン用HTML（Methods 2枚 + Results 6枚） |
| [NCNPレビュー資料 v2](docs/homework/ncnp_review_v2.md) | 研究構成・結果・議論ポイント（共同研究者向け） |
| [先行研究サーベイ](docs/homework/asd_paper.md) | Hu 2025, Altozano 2026, Mun 2024 等の整理 |
| [Big5再現実験の全手順](docs/homework/paper.md) | データ→特徴量→回帰→検定の全パイプライン |
| [特徴量辞書](docs/homework/homework_20260201.md) | 18特徴量の定義・計算方法（人間向け） |

---

## 論文用図表（`reports/paper_figs_v2/`）

| ファイル | 内容 |
|---------|------|
| `fig_ensemble_permutation.png` | アンサンブルBig5 全5次元 permutation test 結果 |
| `fig_baseline_vs_extended.png` | ベースライン vs 拡張モデル比較（Δr） |
| `fig_feature_distribution.png` | 18特徴量のカテゴリ別分布 |
| `fig_corr_heatmap_block.png` | 相関ヒートマップ（ブロック構造） |
| `fig_metadata_gender.png` | 性別 × 特徴量の箱ひげ図（Mann-Whitney U検定） |
| `fig_metadata_age.png` | 年齢 × 特徴量の散布図（Pearson/Spearman相関） |
| `fig_permutation_C_bar.png` | C の4教師 permutation test 結果 |
| `fig_teacher_heatmap.png` | Teacher間一致度ヒートマップ |
| `fig_bootstrap_C_radar.png` | Bootstrap Top10 レーダーチャート |
| `tab_ensemble_permutation.tex` | アンサンブル結果LaTeXテーブル |
| `tab_baseline_vs_extended.tex` | ベースラインvs拡張比較LaTeXテーブル |
| `tab_feature_definitions.tex` | 特徴量定義テーブル（Classical/Novel分類付き） |

---

## ディレクトリ構成

```
.
├── paper1_ja.tex              # 論文本体（LaTeX）
├── paper1_ja.pdf              # コンパイル済みPDF
├── scripts/
│   ├── analysis/              # 統計分析（Ridge回帰・permutation・bootstrap・交絡統制）
│   ├── paper_figs/            # 論文用図表生成スクリプト
│   ├── big5/                  # LLMによるBig5採点（Bedrock経由）
│   ├── cejc/                  # CEJCコーパス前処理（話者メタデータビルド含む）
│   └── csj/                   # CSJコーパス前処理
├── artifacts/
│   ├── analysis/datasets/     # 分析用データセット（parquet）
│   ├── analysis/features_min/ # 抽出済み特徴量
│   └── analysis/results/      # 回帰・検定・アンサンブル・ベースライン比較・交絡統制結果
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
| `extract_interaction_features_min.py` | 18特徴量の抽出 |
| `train_cejc_big5_from_features.py` | 特徴量 → Big5 Ridge回帰 |
| `permutation_test_ridge_fixedalpha.py` | 置換検定（5000回） |
| `bootstrap_coef_stability.py` | Bootstrap係数安定性（500回） |
| `teacher_agreement_big5.py` | LLM教師間一致度 |
| `ensemble_permutation.py` | アンサンブルBig5（4教師平均）permutation test |
| `baseline_vs_extended.py` | ベースライン（Classical 9個）vs 拡張（全18個）比較 |
| `confound_analysis.py` | 交絡変数（性別・年齢）統制分析 |
| `verify_reproducibility.py` | 再現性検証（11項目チェック） |

### 図表生成（`scripts/paper_figs/`）

| スクリプト | 用途 |
|-----------|------|
| `gen_paper_figs_v2.py` | 論文用図表一括生成（16種類） |
| `feature_definitions.py` | 特徴量定義の共通モジュール（Classical/Novel分類付き） |
| `gen_kamishibai_slides.py` | 紙芝居スライド生成（Methods 2枚 + Results 6枚） |

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
  --exclude_cols "n_pairs_total,n_pairs_after_NE,n_pairs_after_YO,IX_n_pairs,IX_n_pairs_after_question,PG_total_time,PG_overlap_rate,PG_resp_overlap_rate,FILL_text_len,FILL_cnt_total,FILL_cnt_eto,FILL_cnt_e,FILL_cnt_ano" \
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
uplatex paper1_ja.tex && dvipdfmx paper1_ja.dvi
```

> **注**: コーパス本文（CEJC発話テキスト）はライセンスの関係でリポジトリに含まれていません。
> データファイル（parquet）は `artifacts/` 以下にローカル配置し、sha256で同一性を担保しています。

---

## 山下先生フィードバック対応ログ

→ [docs/homework/yamashita_feedback_v3_log.md](docs/homework/yamashita_feedback_v3_log.md)

11項目すべて対応完了。対応内容・Before→Afterの一覧、想定外の結果（アンサンブルでO/A/Nも有意）、交絡統制結果の詳細を記載。

---

## 旧コンテンツ

本リポジトリは元々 Nanami Pragmatics Dashboard（母子対話コーパスの語用論指標可視化）として開始しました。
旧ダッシュボードは引き続き GitHub Pages で閲覧可能です。

- [Nanami Pragmatics Dashboard](https://leadlea.github.io/asd/)
- [ダッシュボードガイド](https://leadlea.github.io/asd/nanami_pragmatics_dashboard_guide.html)
- [関連論文調査レポート](https://leadlea.github.io/asd/corpas_paper.html)
