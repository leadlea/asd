# 山下先生向け 1分要約（宿題：特徴量テーブル＋組み合わせ）

- **gold（v13）**は、S3格納庫のraw原本を直接触らず、curated（utterances）から**再現可能に生成**する中間成果物です。  
  発話→タグ→応答ペア→会話×話者集計（segments/pairs/metrics_*）の最小構成に変換し、analysis（summary/rank/examples/LLM説明）へ接続します。

- **宿題(1)：特徴量リスト**は、各テーブルの「**定義／出力粒度／分母（安定性）**」まで整理しました。  
  とくに `metrics_resp` は **分母 = n_pairs_after_NE** を明示し、analysis 側で **min_ne_events=20** により信頼性足切りする運用を根拠付きで説明できます。

- **宿題(2)：組み合わせてできること**は、(a) スコア化（例：NE後相槌率↑＋低エントロピー↑）、(b) クラスタリング（タイプ分け）、(c) LLM解釈＋provenance（prompt_features_used_json により根拠追跡）まで、実データから再現可能な出力として提示できます。

---

# gold(v13) 特徴量リスト（自動生成：列/粒度/分母候補）

## 0) raw→curated→gold の対応

- curated/v1 utterances（発話テーブル）から gold の各テーブル（segments/pairs/metrics_*）を生成

- gold は「分析可能な最小構成」（生データではなく中間成果物）

## 1) テーブル別：粒度・主キー・列一覧

### cejc_metrics_pausegap.parquet

- 粒度: **conversation×speaker（会話×話者 集計）**

- 行数: 1430

- 主キー候補: conversation_id, speaker_id

- 分母/安定性に効く列候補: n_segments, n_resp_events, total_time

- 列一覧（18）:

```text
dataset
conversation_id
speaker_id
src_variants
speech_extract_mode
total_time
speech_time
speech_ratio
n_segments
pause_mean
pause_p50
pause_p90
overlap_rate
resp_gap_mean
resp_gap_p50
resp_gap_p90
resp_overlap_rate
n_resp_events
```

### cejc_metrics_resp.parquet

- 粒度: **conversation×speaker（会話×話者 集計）**

- 行数: 2033

- 主キー候補: conversation_id, speaker_id

- 分母/安定性に効く列候補: n_pairs_total, n_pairs_after_NE, n_pairs_after_YO

- 列一覧（8）:

```text
conversation_id
speaker_id
n_pairs_total
n_pairs_after_NE
n_pairs_after_YO
RESP_NE_AIZUCHI_RATE
RESP_NE_ENTROPY
RESP_YO_ENTROPY
```

### cejc_metrics_sfp.parquet

- 粒度: **conversation×speaker（会話×話者 集計）**

- 行数: 2033

- 主キー候補: conversation_id, speaker_id

- 分母/安定性に効く列候補: coverage, n_utt, n_sfp_NE, n_sfp_NE_Q, n_sfp_YO, n_sfp_NO, n_sfp_NA, n_sfp_MON, n_sfp_NONLEX, n_sfp_NONE, n_sfp_OTHER, n_valid

- 列一覧（20）:

```text
conversation_id
speaker_id
n_utt
n_sfp_NE
n_sfp_NE_Q
n_sfp_YO
n_sfp_NO
n_sfp_NA
n_sfp_MON
n_sfp_NONLEX
n_sfp_NONE
n_sfp_OTHER
n_valid
coverage
rate_sfp_NE
rate_sfp_NE_Q
rate_sfp_YO
rate_question
rate_NE_valid
rate_YO_valid
```

### cejc_pairs.parquet

- 粒度: **pair（話者交替 prev→resp）**

- 行数: 378350

- 主キー候補: conversation_id, prev_speaker_id, resp_speaker_id

- 分母/安定性に効く列候補: (なし)

- 列一覧（11）:

```text
conversation_id
prev_utt_index
prev_speaker_id
prev_text
prev_sfp_group
resp_utt_index
resp_speaker_id
resp_text
resp_first_token
resp_is_aizuchi
resp_is_question
```

### cejc_segments.parquet

- 粒度: **utterance（発話+タグ）**

- 行数: 577885

- 主キー候補: conversation_id, speaker_id

- 分母/安定性に効く列候補: (なし)

- 列一覧（8）:

```text
conversation_id
utt_index
speaker_id
start_time
end_time
text
sfp_group
is_question
```

### cejc_utterances.parquet

- 粒度: **utterance（発話）**

- 行数: 577885

- 主キー候補: conversation_id, utterance_id, speaker_id

- 分母/安定性に効く列候補: (なし)

- 列一覧（8）:

```text
conversation_id
utterance_id
speaker_id
start_time
end_time
text
corpus
unit_type
```

### csj_metrics_pausegap.parquet

- 粒度: **conversation×speaker（会話×話者 集計）**

- 行数: 396

- 主キー候補: conversation_id, speaker_id

- 分母/安定性に効く列候補: n_segments, n_resp_events, total_time

- 列一覧（19）:

```text
dataset
conversation_id
speaker_id
speaker_lr
src_textgrid
speech_extract_mode
total_time
speech_time
speech_ratio
n_segments
pause_mean
pause_p50
pause_p90
overlap_rate
resp_gap_mean
resp_gap_p50
resp_gap_p90
resp_overlap_rate
n_resp_events
```

### csj_metrics_resp.parquet

- 粒度: **conversation×speaker（会話×話者 集計）**

- 行数: 36

- 主キー候補: conversation_id, speaker_id

- 分母/安定性に効く列候補: n_pairs_total, n_pairs_after_NE, n_pairs_after_YO

- 列一覧（8）:

```text
conversation_id
speaker_id
n_pairs_total
n_pairs_after_NE
n_pairs_after_YO
RESP_NE_AIZUCHI_RATE
RESP_NE_ENTROPY
RESP_YO_ENTROPY
```

### csj_metrics_sfp.parquet

- 粒度: **conversation×speaker（会話×話者 集計）**

- 行数: 219

- 主キー候補: conversation_id, speaker_id

- 分母/安定性に効く列候補: coverage, n_utt, n_sfp_NE, n_sfp_NE_Q, n_sfp_YO, n_sfp_NO, n_sfp_NA, n_sfp_MON, n_sfp_NONLEX, n_sfp_NONE, n_sfp_OTHER, n_valid

- 列一覧（20）:

```text
conversation_id
speaker_id
n_utt
n_sfp_NE
n_sfp_NE_Q
n_sfp_YO
n_sfp_NO
n_sfp_NA
n_sfp_MON
n_sfp_NONLEX
n_sfp_NONE
n_sfp_OTHER
n_valid
coverage
rate_sfp_NE
rate_sfp_NE_Q
rate_sfp_YO
rate_question
rate_NE_valid
rate_YO_valid
```

### csj_pairs.parquet

- 粒度: **pair（話者交替 prev→resp）**

- 行数: 5142

- 主キー候補: conversation_id, prev_speaker_id, resp_speaker_id

- 分母/安定性に効く列候補: (なし)

- 列一覧（11）:

```text
conversation_id
prev_utt_index
prev_speaker_id
prev_text
prev_sfp_group
resp_utt_index
resp_speaker_id
resp_text
resp_first_token
resp_is_aizuchi
resp_is_question
```

### csj_segments.parquet

- 粒度: **utterance（発話+タグ）**

- 行数: 66117

- 主キー候補: conversation_id, speaker_id

- 分母/安定性に効く列候補: (なし)

- 列一覧（8）:

```text
conversation_id
utt_index
speaker_id
start_time
end_time
text
sfp_group
is_question
```

### csj_utterances.parquet

- 粒度: **utterance（発話）**

- 行数: 66117

- 主キー候補: conversation_id, utterance_id, speaker_id

- 分母/安定性に効く列候補: (なし)

- 列一覧（8）:

```text
conversation_id
utterance_id
speaker_id
start_time
end_time
text
corpus
unit_type
```
### metrics_resp の式（1行で理解できる説明）
- `RESP_NE_AIZUCHI_RATE = mean(resp_is_aizuchi | prev_sfp_group ∈ {NE, NE_Q})`
- `RESP_NE_ENTROPY = H(resp_first_token | prev_sfp_group ∈ {NE, NE_Q})`（Shannon entropy, log2）
- `RESP_YO_ENTROPY = H(resp_first_token | prev_sfp_group = YO)`（Shannon entropy, log2）
- 信頼性の分母：`n_pairs_after_NE`（analysisでは `>=20` を reliable として運用）

## 1) 特徴量リスト（定義・出力粒度・分母）

※ **定義**は `scripts/build_pragmatics_gold_from_utterances.py` の処理意図に基づき、**列は parquet 実体**から自動取得しています。

| テーブル | 出力粒度 | キー（最小） | 定義（要約） | 分母・安定性 | 列（CEJC/CSJの実体） |
| --- | --- | --- | --- | --- | --- |
| curated/v1 utterances | 発話(utterance) | conversation_id, speaker_id | rawを正規化して「発話テーブル」にした入力。gold生成の唯一の入力。 | 分母なし（入力） | CEJC:577885行 / CSJ:66117行；CEJC/CSJで同一 |
| gold/v13 segments | 発話(utterance)+タグ | conversation_id, speaker_id, utt_index | 発話を会話内でソートし utt_index を付与。text→規則で `sfp_group`,`is_question` を付与。 | 分母=発話数（会話×話者で n_utt 等） | CEJC:577885行 / CSJ:66117行；CEJC/CSJで同一 |
| gold/v13 pairs | 応答ペア(prev→resp) | conversation_id, prev_speaker_id, resp_speaker_id | 隣接発話から**話者交替**のみ抽出。resp側に `resp_first_token`,`resp_is_aizuchi` 等を付与。 | 分母=n_pairs_total（応答側話者のペア数）。条件付きは n_pairs_after_NE 等 | CEJC:378350行 / CSJ:5142行；CEJC/CSJで同一 |
| gold/v13 metrics_sfp | 会話×話者 | conversation_id, speaker_id | segments（sfp_group/is_question）を会話×話者で集計（比率/疑問率/coverage 等）。 | 分母=n_utt（会話×話者の発話数） | CEJC:2033行 / CSJ:219行；CEJC/CSJで同一 |
| gold/v13 metrics_resp | 会話×話者 | conversation_id, speaker_id | pairsを条件（NE/NE_Q/YO 等）で絞り、応答側話者で集計（相槌率/語彙entropy 等）。 | 分母=n_pairs_after_NE / n_pairs_after_YO。analysisでは min_ne_events（例:20）で信頼性足切り。 | CEJC:2033行 / CSJ:36行；CEJC/CSJで同一 |

### metrics_pausegap（Phase4）

- goldに存在する場合のみ。TextGrid由来の pause/gap/overlap/speech の統計を会話×話者で集計。
- 分母例：n_segments / n_resp_events / total_time 等（列はparquet実体に依存）

- **cejc**: rows=1430 cols=18
```text
dataset
conversation_id
speaker_id
element
speech_extract_mode
total_time
speech_time
speech_ratio
n_segments
pause_mean
pause_p50
pause_p90
overlap_rate
resp_gap_mean
resp_gap_p50
resp_gap_p90
resp_overlap_rate
n_resp_events
```

- **csj**: rows=396 cols=19
```text
dataset
conversation_id
speaker_id
speaker_lr
src_textgrid
speech_extract_mode
total_time
speech_time
speech_ratio
n_segments
pause_mean
pause_p50
pause_p90
overlap_rate
resp_gap_mean
resp_gap_p50
resp_gap_p90
resp_overlap_rate
n_resp_events
```


### スキーマ（parquet実体）

- **curated/v1 utterances (CEJC)** rows=577885 cols=8
```text
conversation_id
utterance_id
speaker_id
start_time
end_time
text
corpus
unit_type
```

- **curated/v1 utterances (CSJ)** rows=66117 cols=8
```text
conversation_id
utterance_id
speaker_id
start_time
end_time
text
corpus
unit_type
```

- **gold/v13 segments (CEJC)** rows=577885 cols=8
```text
conversation_id
utt_index
speaker_id
start_time
end_time
text
sfp_group
is_question
```

- **gold/v13 segments (CSJ)** rows=66117 cols=8
```text
conversation_id
utt_index
speaker_id
start_time
end_time
text
sfp_group
is_question
```

- **gold/v13 pairs (CEJC)** rows=378350 cols=11
```text
conversation_id
prev_utt_index
prev_speaker_id
prev_text
prev_sfp_group
resp_utt_index
resp_speaker_id
resp_text
resp_first_token
resp_is_aizuchi
resp_is_question
```

- **gold/v13 pairs (CSJ)** rows=5142 cols=11
```text
conversation_id
prev_utt_index
prev_speaker_id
prev_text
prev_sfp_group
resp_utt_index
resp_speaker_id
resp_text
resp_first_token
resp_is_aizuchi
resp_is_question
```

- **gold/v13 metrics_sfp (CEJC)** rows=2033 cols=20
```text
conversation_id
speaker_id
n_utt
n_sfp_NE
n_sfp_NE_Q
n_sfp_YO
n_sfp_NO
n_sfp_NA
n_sfp_MON
n_sfp_NONLEX
n_sfp_NONE
n_sfp_OTHER
n_valid
coverage
rate_sfp_NE
rate_sfp_NE_Q
rate_sfp_YO
rate_question
rate_NE_valid
rate_YO_valid
```

- **gold/v13 metrics_sfp (CSJ)** rows=219 cols=20
```text
conversation_id
speaker_id
n_utt
n_sfp_NE
n_sfp_NE_Q
n_sfp_YO
n_sfp_NO
n_sfp_NA
n_sfp_MON
n_sfp_NONLEX
n_sfp_NONE
n_sfp_OTHER
n_valid
coverage
rate_sfp_NE
rate_sfp_NE_Q
rate_sfp_YO
rate_question
rate_NE_valid
rate_YO_valid
```

- **gold/v13 metrics_resp (CEJC)** rows=2033 cols=8
```text
conversation_id
speaker_id
n_pairs_total
n_pairs_after_NE
n_pairs_after_YO
RESP_NE_AIZUCHI_RATE
RESP_NE_ENTROPY
RESP_YO_ENTROPY
```

- **gold/v13 metrics_resp (CSJ)** rows=36 cols=8
```text
conversation_id
speaker_id
n_pairs_total
n_pairs_after_NE
n_pairs_after_YO
RESP_NE_AIZUCHI_RATE
RESP_NE_ENTROPY
RESP_YO_ENTROPY
```


## 2) 参考：今回確認した raw/curated の列（実体）

- **curated_utterances_cejc** cols=8
```text
conversation_id
utterance_id
speaker_id
start_time
end_time
text
corpus
unit_type
```

- **curated_utterances_csj** cols=8
```text
conversation_id
utterance_id
speaker_id
start_time
end_time
text
corpus
unit_type
```

- **gold_metrics_resp_cejc** cols=8
```text
conversation_id
speaker_id
n_pairs_total
n_pairs_after_NE
n_pairs_after_YO
RESP_NE_AIZUCHI_RATE
RESP_NE_ENTROPY
RESP_YO_ENTROPY
```

- **gold_metrics_resp_csj** cols=8
```text
conversation_id
speaker_id
n_pairs_total
n_pairs_after_NE
n_pairs_after_YO
RESP_NE_AIZUCHI_RATE
RESP_NE_ENTROPY
RESP_YO_ENTROPY
```


## 3) (2) 組み合わせてできること（スコア化／クラスタリング／LLM解釈＋provenance）

### 3.1 信頼性フィルタ（reliable の定義）

- 研究運用では **min_ne_events=20** を採用（= `metrics_resp.n_pairs_after_NE >= 20` の話者のみ対象）
- reliable rows（会話×話者）: **total=526**（CEJC=520, CSJ=6）

### 3.2 スコア化（例：NE後相槌率↑ ＋ 応答の型の固定化↑）

- 例スコア（試作）:
```text
score_example = z(RESP_NE_AIZUCHI_RATE) + (-z(RESP_NE_ENTROPY))
```
- 生成物: `tmp/_inspect/score_rank_preview_top20.csv`（top20）

top5（例）:

```text
corpus conversation_id speaker_id  n_pairs_total  n_pairs_after_NE  RESP_NE_AIZUCHI_RATE  RESP_NE_ENTROPY  RESP_YO_ENTROPY  z_aizuchi  z_low_entropy  score_example
  cejc        T006_005       IC01            381                39              1.000000         1.696182         1.370951   2.519035       3.008719       5.527754
  cejc        S002_005       IC02            333                20              0.850000         1.816642         1.370951   1.557348       2.829165       4.386513
  cejc        C001_004       IC01            209                21              0.857143         2.030087         2.820590   1.603143       2.511008       4.114151
  cejc        K009_012       IC03            466                24              0.833333         1.976287         1.000000   1.450494       2.591202       4.041697
  cejc        T006_009       IC01            227                23              0.826087         1.994841         2.558051   1.404036       2.563545       3.967581
```

### 3.3 クラスタリング（タイプ分け）

- 対象: CEJC reliable（`n_pairs_after_NE>=20`）
- 特徴: `[RESP_NE_AIZUCHI_RATE, RESP_NE_ENTROPY, RESP_YO_ENTROPY]`
- 手順: 標準化 → PCA(2D) → KMeans(k=4)
- 生成物: `tmp/_inspect/cejc_cluster_preview.parquet` / `tmp/_inspect/cejc_cluster_counts.csv`

クラスタ件数:

- cluster 0: 132
- cluster 1: 119
- cluster 2: 180
- cluster 3: 89

クラスタ平均プロファイル（説明用）:

| CL_cluster | count | RESP_NE_AIZUCHI_RATE | RESP_NE_ENTROPY | RESP_YO_ENTROPY | n_pairs_after_NE | n_pairs_total |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 132 | 0.7833 | 2.9165 | 1.7868 | 35.42 | 346.79 |
| 1 | 119 | 0.4248 | 4.4986 | 3.0586 | 40.47 | 490.27 |
| 2 | 180 | 0.6326 | 3.7374 | 3.0255 | 37.99 | 417.21 |
| 3 | 89 | 0.5523 | 3.8187 | 0.8778 | 32.33 | 309.30 |

### 3.4 LLMサマライズ解釈 + provenance（根拠追跡）

- labels に **説明文＋根拠特徴＋寄与上位** を保存し、後から「何を見てそう言ったか」を追跡できる
- labels parquet: `artifacts/phase56_full_20260104_024221/_llm500_opus45/labels_tb500_UIFINAL_opus45_WITHCL_WITHNEYO_WITHIX__FIXED.parquet`
- rows: **500**
- prompt_features_used_json non-null rate: **1.000**
- labels_json non-null rate: **1.000**
- top_contrib_json non-null rate: **1.000**

primary_label 上位（top10）:
- OTHER: 256
- BACKCHANNEL: 142
- HESITATION: 102

