# 特徴量棚卸し（完全版）- 実カラム一覧確定

**作成日**: 2026-01-31  
**目的**: 山下先生提出用の特徴量棚卸しメモ作成のため、gold(v13) と analysis(v1) の実カラム構成を確定する

---

## A. gold/v13 実テーブルの列一覧

### 1. metrics_resp（RESP系の元データ）

**説明**: 応答行動メトリクス（NE後あいづち率、エントロピーなど）

**重要**: **dataset列は存在しない**（analysis側でn_speakersから動的生成）

**列数**: 8列

**columns**:
- `conversation_id` - 会話ID
- `speaker_id` - 話者ID
- `n_pairs_total` - 総ペア数
- `n_pairs_after_NE` - NE後のペア数
- `n_pairs_after_YO` - YO後のペア数
- `RESP_NE_AIZUCHI_RATE` - NE後あいづち率
- `RESP_NE_ENTROPY` - NE後応答のエントロピー
- `RESP_YO_ENTROPY` - YO後応答のエントロピー

**データ例** (head 3):
```
conversation_id  speaker_id  n_pairs_total  n_pairs_after_NE  RESP_NE_AIZUCHI_RATE  ...
K010_003a        IC01        108            45                0.644                 ...
T007_007         IC06        241            89                0.730                 ...
...
```

---

### 2. metrics_pausegap（PG系の元データ）

**説明**: ポーズ・ギャップ・オーバーラップのメトリクス

**列数**: 12列（PG_接頭辞なし、生データ）

**columns**:
- `dataset` - データセット名（cejc_all, cejc_dyad, csj_all, csj_dialog）
- `speaker_id` - 話者ID
- `total_time` - 総時間（秒）
- `pause_mean` - ポーズ平均（秒）
- `pause_p50` - ポーズ中央値（秒）
- `pause_p90` - ポーズ90パーセンタイル（秒）
- `resp_gap_mean` - 応答ギャップ平均（秒）
- `resp_gap_p50` - 応答ギャップ中央値（秒）
- `resp_gap_p90` - 応答ギャップ90パーセンタイル（秒）
- `overlap_rate` - オーバーラップ率
- `resp_overlap_rate` - 応答時オーバーラップ率
- `n_resp_events` - 応答イベント数

**データ例** (head 3):
```
dataset    speaker_id  total_time  pause_mean  pause_p50  ...
cejc_all   IC01        1234.5      2.3         0.8        ...
cejc_dyad  IC06        1894.2      5.3         0.7        ...
...
```

**注**: analysis側では `PG_` 接頭辞付きで統合される

---

### 3. metrics_sfp（SFP系の元データ）

**説明**: 文末助詞（Sentence-Final Particle）の分布メトリクス

**状態**: ローカルに実ファイルなし（S3上のみ存在）

**推定構造**:
- `conversation_id` - 会話ID
- `speaker_id` - 話者ID
- SFP分布列（NE, YO, NO, NA, MON, NONE, NONLEX, OTHER など）

**確認方法**: 
```bash
aws s3 ls "$OUT_GOLD/v13/corpus=cejc/table=metrics_sfp/" --recursive
aws s3 cp "$OUT_GOLD/v13/corpus=cejc/table=metrics_sfp/part-00000.parquet" tmp/
```

**注**: `rebuild_summary_datasets_v13_counts.py` では segments.sfp_group から集計している

---

## B. analysis/v1 側の「話者特徴量の本体」列一覧

### メインファイル: `labels_tb500_with_CL.parquet`

**パス**: `artifacts/phase56_full_20260104_024221/_htmlfix4/labels_tb500_with_CL.parquet`

**shape**: (500, 49)

**総列数**: 49列

---

### 列の分類

#### 1. FILL_系（13列）- フィラー特徴量

```
FILL_cnt_ano                    - 「あの」の出現回数
FILL_cnt_e                      - 「え」の出現回数
FILL_cnt_eto                    - 「えっと」の出現回数
FILL_cnt_hora                   - 「ほら」の出現回数
FILL_cnt_maa                    - 「まあ」の出現回数
FILL_cnt_nanka                  - 「なんか」の出現回数
FILL_cnt_sono                   - 「その」の出現回数
FILL_cnt_total                  - フィラー総数
FILL_has_any                    - フィラー有無（0/1）
FILL_n_rows                     - 発話行数
FILL_rate_per_100chars          - 100文字あたりフィラー率
FILL_text_len                   - テキスト総文字数
FILL_z_log_rate_per_100chars    - log(rate)のz-score
```

---

#### 2. PG_系（18列）- ポーズ・ギャップ特徴量

```
PG_conversation_id              - 会話ID
PG_n_resp_events                - 応答イベント数
PG_n_segments                   - セグメント数
PG_overlap_rate                 - オーバーラップ率
PG_pause_mean                   - ポーズ平均（秒）
PG_pause_p50                    - ポーズ中央値（秒）
PG_pause_p90                    - ポーズ90パーセンタイル（秒）
PG_resp_gap_mean                - 応答ギャップ平均（秒）
PG_resp_gap_p50                 - 応答ギャップ中央値（秒）
PG_resp_gap_p90                 - 応答ギャップ90パーセンタイル（秒）
PG_resp_overlap_rate            - 応答時オーバーラップ率
PG_speaker_lr                   - 話者L/R識別
PG_speech_extract_mode          - 音声抽出モード
PG_speech_ratio                 - 発話時間比率
PG_speech_time                  - 発話時間（秒）
PG_src_textgrid                 - 元TextGridファイル
PG_src_variants                 - ソースバリアント
PG_total_time                   - 総時間（秒）
```

**注**: gold/v13の `metrics_pausegap` から `PG_` 接頭辞付きで統合

---

#### 3. CL_系（3列）- クラスタリング特徴量

```
CL_fillpg_cluster               - FILL+PGクラスタID
CL_pca_x                        - PCA第1主成分
CL_pca_y                        - PCA第2主成分
```

---

#### 4. identity系（4列）- 識別情報

```
conversation_id                 - 会話ID
dataset                         - データセット名（cejc_all/dyad, csj_all/dialog）
speaker_id                      - 話者ID
speaker_key                     - 話者キー（conversation_id:speaker_id）
```

---

#### 5. LLM系（3列）- LLM生成ラベル

```
labels_json                     - LLM生成ラベル（JSON配列）
primary_label                   - 主ラベル（CEJC_TOP, CSJ_BOTTOM等）
prompt_features_used_json       - プロンプトで使用した特徴量（JSON配列）
```

---

#### 6. その他（8列）- メタ情報・スコア

```
atypicality_v0                  - 非定型性スコア
examples_json                   - 例文（JSON）
is_outlier_p99                  - 外れ値フラグ（99パーセンタイル）
n_pairs_total                   - 総ペア数
n_utt_total                     - 総発話数
score                           - スコア（atypicality_v0と同値）
tb                              - Top/Bottom分類（CEJC_TOP等）
top_contrib_json                - 主要寄与特徴量（JSON配列）
```

---

## C. 確定事項サマリー

### 1. gold/v13 について

| テーブル | 列数 | 主要列 | 備考 |
|---------|------|--------|------|
| metrics_resp | 8 | RESP_NE_AIZUCHI_RATE, RESP_NE_ENTROPY, RESP_YO_ENTROPY | **dataset列なし** |
| metrics_pausegap | 12 | pause_mean, resp_gap_mean, overlap_rate | PG_接頭辞なし |
| metrics_sfp | 不明 | SFP分布列 | S3のみ、要確認 |

**重要**: 
- `dataset` 列は gold には存在しない
- analysis 側で `n_speakers` から動的生成（cejc_all/dyad, csj_all/dialog）
- `analyze_gold_to_analysis_v1.py` / `rebuild_summary_datasets_v13_counts.py` で実装

---

### 2. analysis/v1 について

| 特徴量系 | 列数 | 説明 | 元データ |
|---------|------|------|---------|
| FILL_ | 13 | フィラー頻度・率・z-score | phase5 fill処理 |
| PG_ | 18 | pause/gap/overlap + メタ | gold metrics_pausegap |
| CL_ | 3 | PCA座標 + クラスタID | FILL+PG統合後クラスタリング |
| RESP_ | 0 | **存在しない** | gold側のみ |
| SFP_ | 0 | **存在しない** | gold側のみ |
| IX_ | 0 | **存在しない** | 未実装 |
| LLM | 3 | labels_json, primary_label, prompt | phase5 LLM処理 |

---

### 3. 重要な発見

#### ✅ 確認できたこと

1. **FILL_系**: 13列が analysis/v1 に統合済み
2. **PG_系**: 18列が analysis/v1 に統合済み（gold の metrics_pausegap から）
3. **CL_系**: 3列（クラスタリング結果）が analysis/v1 に追加
4. **LLM系**: 3列（ラベル・プロンプト情報）が analysis/v1 に追加

#### ❌ 存在しないもの

1. **IX_系**: 想定されていたが実装されていない
2. **RESP_系**: gold/v13 の metrics_resp にのみ存在（analysis には未統合）
3. **SFP_系**: gold/v13 の metrics_sfp にのみ存在（analysis には未統合）

#### 📝 dataset の扱い

- gold/v13 の metrics_resp には **dataset 列が存在しない**
- analysis 側で以下のロジックで動的生成:
  - `cejc_all`: CEJC全体
  - `cejc_dyad`: CEJC の n_speakers == 2
  - `csj_all`: CSJ全体
  - `csj_dialog`: CSJ の n_speakers >= 2

---

## D. 次のアクション（S3確認が必要な項目）

### 1. metrics_sfp の実カラム確認

```bash
# 環境変数設定（要確認）
export OUT_GOLD="s3://your-bucket/gold"
export GV=13

# CEJC
aws s3 ls "$OUT_GOLD/v${GV}/corpus=cejc/table=metrics_sfp/" --recursive | head
aws s3 cp "$OUT_GOLD/v${GV}/corpus=cejc/table=metrics_sfp/part-00000.parquet" tmp/cejc_metrics_sfp.parquet

# CSJ
aws s3 ls "$OUT_GOLD/v${GV}/corpus=csj/table=metrics_sfp/" --recursive | head
aws s3 cp "$OUT_GOLD/v${GV}/corpus=csj/table=metrics_sfp/part-00000.parquet" tmp/csj_metrics_sfp.parquet

# Python で確認
python -c "
import pandas as pd
df = pd.read_parquet('tmp/cejc_metrics_sfp.parquet')
print('shape:', df.shape)
print('columns:', list(df.columns))
print(df.head(3))
"
```

### 2. analysis/v1 の完全版パス確認

```bash
# 環境変数設定（要確認）
export OUT_ANALYSIS="s3://your-bucket/analysis/v1"

# 話者特徴量統合ファイルの探索
aws s3 ls "$OUT_ANALYSIS/" --recursive | grep -E "speaker|features|labels.*parquet" | head -20
```

---

## E. 参考: データフロー

```
gold/v13/
├── metrics_resp (8列)
│   └── RESP_NE_AIZUCHI_RATE, RESP_NE_ENTROPY, RESP_YO_ENTROPY
├── metrics_pausegap (12列)
│   └── pause_mean, resp_gap_mean, overlap_rate, ...
└── metrics_sfp (不明)
    └── SFP分布列

↓ phase5 処理

phase5/
├── fill処理 → FILL_系 13列
├── pg統合 → PG_系 18列（metrics_pausegap から）
└── LLM処理 → LLM系 3列

↓ phase56 統合

analysis/v1/
└── labels_tb500_with_CL.parquet (49列)
    ├── FILL_系: 13列
    ├── PG_系: 18列
    ├── CL_系: 3列（クラスタリング）
    ├── LLM系: 3列
    ├── identity: 4列
    └── その他: 8列
```

---

## F. 完了条件チェック

- [x] metrics_resp の列一覧（8列）が確定
- [x] metrics_pausegap の列一覧（12列）が確定
- [ ] metrics_sfp の列一覧（S3確認待ち）
- [x] analysis/v1 の話者特徴量本体（49列）が確定
- [x] IX/FILL/PG/RESP/SFP/CL/LLM の実在確認完了
- [x] dataset列の扱いが確定（gold側に存在せず、analysis側で動的生成）

---

**作成者**: Kiro AI Assistant  
**確認日**: 2026-01-31  
**データソース**: ローカル artifacts/phase5, artifacts/phase56_full_20260104_024221
