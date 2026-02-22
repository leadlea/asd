# Table 1. CEJC home2 HQ1: Interaction features → LLM teacher (C)

**Dataset**: CEJC (home, 2 speakers), HQ1 (n_pairs_total≥80, text_len≥2000, after_question≥10)  
**N**=120 (conversation×speaker)  
**Teacher**: IPIP-NEO C (24 items), Claude Sonnet 4 (strict 5-choice)  
**X**: Interaction features only (PG/FILL/IX/RESP), **Xdim**=18 (volume features excluded)  
**Model**: Ridge regression, 5-fold CV  

## Main performance
| Metric | Value |
|---|---:|
| CV Pearson r | 0.335 |
| CV R² | 0.111 |
| Permutation test (5000) p(|r|) | 0.0236 |

## Top drivers + stability (Bootstrap 500)
| Feature | Direction | top10-inclusion rate | sign agreement |
|---|:---:|---:|---:|
| FILL_has_any | + | 0.838 | 0.968 |
| IX_oirmarker_after_question_rate | + | 0.824 | 0.984 |
| PG_speech_ratio | + | 0.804 | 0.932 |
| PG_resp_gap_mean | − | 0.746 | 0.986 |
| IX_lex_overlap_mean | − | 0.672 | 0.980 |
| RESP_NE_AIZUCHI_RATE | + | 0.626 | 0.914 |
| IX_yesno_rate | + | 0.568 | 0.896 |
| PG_pause_p50 | − | 0.564 | 0.886 |

## Audit note (excluded from main claim)
`IX_topic_drift_mean` was found to be sensitive to short utterances / corpus tags / aizuchi; a cleaned variant (driftv2) reduced performance (r=0.242, p=0.165), so drift is excluded from the main claim.