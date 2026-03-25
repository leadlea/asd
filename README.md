# 日本語会話における相互行為特徴量の定量化指標

日本語日常会話コーパス（CEJC）から抽出した **18の相互行為特徴量** を体系化し、
LLM仮想教師によるBig Five性格スコアとの関連を通じて指標の妥当性を検証する研究リポジトリ。

- 研究者: 福原玄（Lead lea）、山下祐一（NCNP）、宗田卓史（NCNP）
- 対象学会: 発達支援学会（2026年11月）
- 論文の軸: 相互行為特徴量の提案 + 2段階妥当性検証

---

## 研究概要

1. CEJC home2サブセット（N=120）から **4カテゴリ18特徴量** を再現可能に計測
   - PG（タイミング7変数）/ FILL（フィラー2変数）/ IX（相互行為6変数）/ RESP（応答型3変数）
2. 4つのLLM（Sonnet4, Qwen3-235B, DeepSeek-V3, GPT-OSS-120B）で Big Five を仮想教師として採点
3. Ridge回帰 + permutation test + bootstrap で **Conscientiousness（C）が3/4教師で頑健** であることを確認
4. 年齢との関連分析（表面的妥当性）→ Big5との関連分析（構成概念妥当性）の **2段階検証設計**

---

## 主要ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [NCNPレビュー資料 v2](docs/homework/ncnp_review_v2.md) | 最新の研究構成・結果・議論ポイント（共同研究者向け） |
| [論文ドラフト（LaTeX）](paper1_ja.tex) | 論文本体（uplatex + dvipdfmx） |
| [論文PDF](paper1_ja.pdf) | コンパイル済みPDF |
| [先行研究サーベイ](docs/homework/asd_paper.md) | Hu 2025, Altozano 2026, Mun 2024 等の整理 |
| [Big5再現実験の全手順](docs/homework/paper.md) | データ→特徴量→回帰→検定の全パイプライン |
| [C vs 他trait比較](docs/homework/cejc_AENO_vs_C_compare.md) | なぜCだけが頑健なのかの分析 |
| [特徴量辞書](docs/homework/homework_20260201.md) | 18特徴量の定義・計算方法（人間向け） |
| [紙芝居スライド](reports/paper_figs_v2/kamishibai_slides.html) | 6枚構成のプレゼン用HTML |

---

## 論文用図表（`reports/paper_figs_v2/`）

| ファイル | 内容 |
|---------|------|
| `fig_feature_distribution.png` | 18特徴量のカテゴリ別分布 |
| `fig_corr_heatmap_block.png` | 相関ヒートマップ（ブロック構造） |
| `fig_metadata_gender.png` | 性別 × 特徴量の箱ひげ図（Mann-Whitney U検定） |
| `fig_metadata_age.png` | 年齢 × 特徴量の散布図（Pearson/Spearman相関） |
| `fig_permutation_C_bar.png` | C の4教師 permutation test 結果 |
| `fig_teacher_heatmap.png` | Teacher間一致度ヒートマップ |
| `fig_bootstrap_C_radar.png` | Bootstrap Top10 レーダーチャート |

---

## ディレクトリ構成

```
.
├── paper1_ja.tex              # 論文本体（LaTeX）
├── paper1_ja.pdf              # コンパイル済みPDF
├── scripts/
│   ├── analysis/              # 統計分析（Ridge回帰・permutation・bootstrap）
│   ├── paper_figs/            # 論文用図表生成スクリプト
│   ├── big5/                  # LLMによるBig5採点（Bedrock経由）
│   ├── cejc/                  # CEJCコーパス前処理（話者メタデータビルド含む）
│   └── csj/                   # CSJコーパス前処理
├── artifacts/
│   ├── analysis/datasets/     # 分析用データセット（parquet）
│   ├── analysis/features_min/ # 抽出済み特徴量
│   └── analysis/results/      # 回帰・検定結果
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
| `verify_reproducibility.py` | 再現性検証（11項目チェック） |

### 図表生成（`scripts/paper_figs/`）

| スクリプト | 用途 |
|-----------|------|
| `gen_paper_figs_v2.py` | 論文用図表一括生成 |
| `feature_definitions.py` | 特徴量定義の共通モジュール |
| `gen_kamishibai_slides.py` | 紙芝居スライド生成 |

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

# Permutation test
python scripts/analysis/permutation_test_ridge_fixedalpha.py

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

# 再現性検証
python scripts/analysis/verify_reproducibility.py

# LaTeX コンパイル
uplatex paper1_ja.tex && dvipdfmx paper1_ja.dvi
```

> **注**: コーパス本文（CEJC発話テキスト）はライセンスの関係でリポジトリに含まれていません。
> データファイル（parquet）は `artifacts/` 以下にローカル配置し、sha256で同一性を担保しています。

---

## 旧コンテンツ

本リポジトリは元々 Nanami Pragmatics Dashboard（母子対話コーパスの語用論指標可視化）として開始しました。
旧ダッシュボードは引き続き GitHub Pages で閲覧可能です。

- [Nanami Pragmatics Dashboard](https://leadlea.github.io/asd/)
- [ダッシュボードガイド](https://leadlea.github.io/asd/nanami_pragmatics_dashboard_guide.html)
- [関連論文調査レポート](https://leadlea.github.io/asd/corpas_paper.html)
