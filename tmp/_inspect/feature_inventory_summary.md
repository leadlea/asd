# 特徴量棚卸し - クイックサマリー

## gold/v13 実テーブル

### metrics_resp (8列) ⚠️ dataset列なし
```
conversation_id, speaker_id, n_pairs_total, n_pairs_after_NE, n_pairs_after_YO,
RESP_NE_AIZUCHI_RATE, RESP_NE_ENTROPY, RESP_YO_ENTROPY
```

### metrics_pausegap (12列) ⚠️ PG_接頭辞なし
```
dataset, speaker_id, total_time, pause_mean, pause_p50, pause_p90,
resp_gap_mean, resp_gap_p50, resp_gap_p90, overlap_rate, resp_overlap_rate, n_resp_events
```

### metrics_sfp (不明) ⚠️ S3のみ
```
conversation_id, speaker_id, + SFP分布列
```

---

## analysis/v1 話者特徴量 (49列)

### FILL_系 (13列)
```
FILL_cnt_e, FILL_cnt_eto, FILL_cnt_ano, FILL_cnt_sono, FILL_cnt_maa,
FILL_cnt_nanka, FILL_cnt_hora, FILL_cnt_total, FILL_has_any, FILL_n_rows,
FILL_rate_per_100chars, FILL_text_len, FILL_z_log_rate_per_100chars
```

### PG_系 (18列) ✅ gold metrics_pausegap から統合
```
PG_conversation_id, PG_speaker_lr, PG_src_textgrid, PG_speech_extract_mode,
PG_total_time, PG_speech_time, PG_speech_ratio, PG_n_segments,
PG_pause_mean, PG_pause_p50, PG_pause_p90, PG_overlap_rate,
PG_resp_gap_mean, PG_resp_gap_p50, PG_resp_gap_p90, PG_resp_overlap_rate,
PG_n_resp_events, PG_src_variants
```

### CL_系 (3列)
```
CL_pca_x, CL_pca_y, CL_fillpg_cluster
```

### LLM系 (3列)
```
labels_json, primary_label, prompt_features_used_json
```

### identity系 (4列)
```
dataset, conversation_id, speaker_id, speaker_key
```

### その他 (8列)
```
n_utt_total, n_pairs_total, atypicality_v0, top_contrib_json,
is_outlier_p99, score, tb, examples_json
```

---

## 存在しない特徴量

- ❌ **IX_系**: 0列（未実装）
- ❌ **RESP_系**: analysis側に未統合（gold側のみ）
- ❌ **SFP_系**: analysis側に未統合（gold側のみ）

---

## 重要事項

1. **dataset列**: gold/v13 の metrics_resp には存在しない
   - analysis側で n_speakers から動的生成
   - cejc_all, cejc_dyad (n==2), csj_all, csj_dialog (n>=2)

2. **PG_接頭辞**: 
   - gold: 接頭辞なし (pause_mean, resp_gap_mean, ...)
   - analysis: 接頭辞あり (PG_pause_mean, PG_resp_gap_mean, ...)

3. **統合状況**:
   - ✅ FILL: 統合済み (13列)
   - ✅ PG: 統合済み (18列)
   - ✅ CL: 追加済み (3列)
   - ✅ LLM: 追加済み (3列)
   - ❌ RESP: 未統合
   - ❌ SFP: 未統合
   - ❌ IX: 未実装
