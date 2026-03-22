---
inclusion: always
---

# ASD会話特徴量 論文化プロジェクト指示書

## プロジェクト概要

本プロジェクトは、日本語会話コーパス（CEJC・CSJ）から抽出した**相互行為特徴量**を用いて、
LLMが推定したBig Five性格スコアを古典的NLP/語用論特徴量で予測・解釈する研究の**論文化**を目的とする。

- リポジトリ: https://github.com/leadlea/asd
- 研究者: 福原玄（筆頭）、山下祐一（NCNP）、宗田卓史（NCNP）
- 対象学会: 発達支援学会（2026年11月）等、NLPガチ勢と直接競合しない場を想定
- 論文の軸: **メソッド＋リザルト**（方法論の再現性と結果の頑健性）

## 研究の核心（3行で）

1. 日本語会話テキストから**相互行為特徴量**（タイミング・フィラー・応答型・修復・話題連結）を再現可能に計測する
2. LLM（4モデル）が推定したBig Fiveスコアを**仮想教師**として、特徴量→性格推定の回帰モデルを構築する
3. **Conscientiousness（C: 誠実性）が複数LLM教師で頑健に推定可能**であることを示し、どの特徴量が効くかを解釈する

## 共同研究者の役割

- **山下祐一先生（NCNP）**: 臨床的妥当性の監修、参考論文の選定、研究方針の助言
- **宗田卓史さん（NCNP）**: LLM+少数リアルデータの観点、古典NLPとLLMの補完関係の議論
- **福原玄**: 実装・分析・論文執筆の主担当、ASD当事者としての仮説生成

## ディレクトリ構成（論文化に関連する主要部分）

```
.
├── src/features/          # 特徴量抽出コア（discourse_minimal.py, pragmatics.py等）
├── scripts/
│   ├── analysis/          # 統計分析（Ridge回帰、permutation test、bootstrap）
│   │   ├── train_cejc_big5_from_features.py      # 特徴量→Big5回帰
│   │   ├── permutation_test_ridge_fixedalpha.py   # 置換検定
│   │   ├── bootstrap_coef_stability.py            # bootstrap安定性
│   │   ├── teacher_agreement_big5.py              # LLM教師間一致度
│   │   └── extract_interaction_features_min.py    # 特徴量抽出（最小版）
│   ├── big5/              # LLMによるBig5採点（Bedrock経由）
│   │   └── score_big5_bedrock.py
│   ├── paper_figs/        # 論文用図表生成
│   ├── cejc/              # CEJCコーパス前処理
│   └── csj/               # CSJコーパス前処理
├── artifacts/
│   ├── analysis/          # 分析結果（特徴量、データセット、結果）
│   │   ├── datasets/      # 分析用データセット（parquet）
│   │   ├── features_min/  # 抽出済み特徴量
│   │   └── results/       # 回帰・検定結果
│   ├── big5/              # Big5採点結果（LLMスコア、Cronbach's α等）
│   ├── cejc/              # CEJCモノローグ（v1固定、sha256付き）
│   └── csj/               # CSJモノローグ
├── docs/
│   ├── homework/          # 分析メモ・宿題（先生への報告資料）
│   │   ├── paper.md                    # Big5再現実験の全手順・結果
│   │   ├── cejc_AENO_vs_C_compare.md   # C vs 他trait比較（本論の核心）
│   │   ├── homework_20260201.md         # 特徴量辞書（人間向け）
│   │   └── asd_paper.md                # 先行研究サーベイ
│   └── minutes/           # 議事メモ
├── reports/               # 生成済みレポート・図表
├── tools/                 # 論文レポート生成ツール
├── reproduce/             # 先行研究再現スクリプト
└── paper1_ja.tex          # 論文LaTeXドラフト（初期版）
```

## データセット

### CEJC（主データ: N=120）
- **CEJC home2 HQ1**: 自宅・少人数会話、品質フィルタ済み（N=120 conversation×speaker）
- 特徴量: PG（タイミング）/ FILL（フィラー）/ IX（相互行為）/ RESP（応答型）= 18変数
- Big5教師: 4 LLM（Sonnet4, Qwen3-235B, DeepSeek-V3, GPT-OSS-120B）

### CSJ（追試データ: N=36）
- CSJ対話D、side擬似モノローグ
- Big5のCronbach's α検証（ensemble効果の追試）

### Big5採点プロトコル
- IPIP-NEO-120（日本語120項目）
- 4モデル×120問、item-level平均でensemble構築
- sha256によるデータ固定・再現性担保

## 主要結果（論文の核）

### 1. Cの頑健性（Permutation test）
- Sonnet4: r=0.434, p=0.0008 (**sig**)
- Qwen3: r=0.390, p=0.001 (**sig**)
- GPT-OSS: r=0.447, p=0.0008 (**sig**)
- DeepSeek: r=0.205, p=0.113 (n.s.)
→ **4教師中3教師で有意**、Cは頑健に立つ

### 2. Teacher間一致度
- C: mean r=0.699（最高）→ 疑似教師として安定
- A: mean r=0.435（最低）→ teacher依存性が大きい

### 3. Bootstrap Top Drivers（C, Sonnet4基準）
- FILL_has_any (+), IX_oirmarker_after_question_rate (+), PG_speech_ratio (+)
- PG_resp_gap_mean (−), IX_lex_overlap_mean (−)

### 4. Ensemble Cronbach's α
- CEJC: 全trait α≥0.78（ensemble効果で安定化）
- CSJ: C/E/N/O高α、Aのみ弱い（発話量依存）

## 18特徴量一覧（説明変数）

| カテゴリ | 特徴量 | 概要 |
|---------|--------|------|
| PG | PG_speech_ratio | 発話率 |
| PG | PG_pause_mean/p50/p90 | 沈黙の長さ |
| PG | PG_resp_gap_mean/p50/p90 | 応答遅れ |
| FILL | FILL_has_any | フィラー出現発話数 |
| FILL | FILL_rate_per_100chars | 100文字あたりフィラー率 |
| IX | IX_oirmarker_rate | 修復開始（OIR）率 |
| IX | IX_oirmarker_after_question_rate | 質問直後OIR率 |
| IX | IX_yesno_rate | YES/NO応答率 |
| IX | IX_yesno_after_question_rate | 質問直後YES/NO率 |
| IX | IX_lex_overlap_mean | 語彙つながり |
| IX | IX_topic_drift_mean | 話題逸脱度 |
| RESP | RESP_NE_AIZUCHI_RATE | 「ね」直後相槌率 |
| RESP | RESP_NE_ENTROPY | 「ね」直後応答多様性 |
| RESP | RESP_YO_ENTROPY | 「よ」直後応答多様性 |

## 論文化の方針

### 構成案（メソッド＋リザルト中心）
1. Introduction: 談話×LLM×性格推定のギャップ（先行研究サーベイ `asd_paper.md` 参照）
2. Method: 特徴量の2段階説明（概要＋アルゴリズム）、データ、モデル
3. Results: C中心の頑健性 + teacher依存性分析
4. Discussion: 相互行為特徴量の解釈、限界、将来展望
5. Appendix: A/E/N/O（探索的結果）、感度分析

### 差別化ポイント
- **「性格推定」ではなく「会話の相互行為の計測」**として立て付ける
- 再現可能な評価設計（subject-wise split、permutation test、bootstrap）
- 複数LLM教師の頑健性検証（teacher間一致度）
- 日本語会話コーパスでの初の体系的検証

## 論文化に向けたタスク（優先順）

1. **現在地の整理**: これまでの分析結果・スクリプトの棚卸し
2. **再現性検証**: 主要スクリプトの実行確認、結果の一致確認
3. **論文骨子生成**: Introduction〜Conclusionの構成案
4. **図表生成**: 論文用の図表（permutation結果、bootstrap radar、teacher一致ヒートマップ等）
5. **NCNPレビュー資料**: 山下先生・宗田さんに共有できる状態の資料作成

## 技術スタック

- Python 3.12 / venv
- pandas, scikit-learn (Ridge, KMeans, PCA), scipy
- AWS Bedrock（LLM推論: ap-northeast-1）
- parquet形式でデータ管理（sha256でバージョン固定）
- LaTeX（uplatex + dvipdfmx）で論文組版

## コーディング規約

- データファイルはgit管理対象外（.gitignore）、再現コマンド・スクリプト・QCログをgitに残す
- sha256でデータの同一性を担保
- スクリプトは `scripts/` 以下に機能別に配置
- 分析結果は `artifacts/analysis/results/` に保存
- 論文用図表は `reports/paper_figs_paper1*/` に保存

## 外部データ・今後のアクセス先

- 国語研（コーパス紐づき性格・特性データ）→ 鈴木あすみさん（4月〜国語研着任）に相談
- 当事者研究（綾屋さん・東大）→ CREST領域会議で熊谷先生に相談
- Japanese Intimacy Dialog Corpus (JID): https://aclanthology.org/2024.paclic-1.10/
- 応用脳科学コンソーシアムのデータ
- その他オープンDB

## 参考論文（主要）

- Hu et al. 2025 (npj Digital Medicine): ADOS-2対話×ゼロショットLLM
- Altozano et al. 2026 (IEEE JBHI): 自由回答×LLM×ASD/TD分類
- Mun et al. 2024: ASR→PLM→重症度回帰（韓国語）
- Nakamura et al. 2025 (SICE): ADOS-2会話×BERT特徴+LightGBM（日本語）
- Big5×LLM原著論文（daily diaries, IPIP-NEO-120）

## 注意事項

- コーパス本文（発話テキスト）や大きなparquetはライセンス・容量の観点でgit管理対象外
- LLMへのコーパス投入は閉じたプライベートネットワーク（Bedrock）で運用
- 「診断」ではなく「特性（traits）推定」として立て付ける（臨床的・倫理的配慮）
- 論文の主張は控えめに（小標本・外部検証未了の限界を明示）
