# Bootstrap top drivers: teacher comparison

- topk_rate = Top10 inclusion frequency (Bootstrap 500)
- sign_agree_rate = sign agreement frequency (Bootstrap 500)

## Teacher: sonnet

### C

| feature | topk_rate | sign_agree | coef_mean |
|---|---:|---:|---:|
| FILL_has_any | 0.838 | 0.968 | 0.0502 |
| IX_oirmarker_after_question_rate | 0.824 | 0.984 | 0.0527 |
| PG_speech_ratio | 0.804 | 0.932 | 0.0465 |
| PG_resp_gap_mean | 0.746 | 0.986 | -0.0817 |
| PG_resp_gap_p50 | 0.678 | 0.864 | -0.0297 |
| IX_lex_overlap_mean | 0.672 | 0.980 | -0.0338 |
| IX_topic_drift_mean | 0.656 | 0.980 | 0.0338 |
| RESP_NE_AIZUCHI_RATE | 0.626 | 0.914 | 0.0331 |
| IX_yesno_rate | 0.568 | 0.896 | 0.0320 |
| PG_pause_p50 | 0.564 | 0.886 | -0.0458 |

### A

| feature | topk_rate | sign_agree | coef_mean |
|---|---:|---:|---:|
| PG_pause_p50 | 0.948 | 0.996 | -0.0412 |
| IX_yesno_after_question_rate | 0.888 | 0.974 | 0.0298 |
| PG_speech_ratio | 0.834 | 0.934 | 0.0198 |
| RESP_YO_ENTROPY | 0.728 | 0.910 | -0.0227 |
| IX_yesno_rate | 0.724 | 0.930 | 0.0186 |
| PG_pause_p90 | 0.710 | 0.902 | -0.0176 |
| PG_resp_gap_mean | 0.708 | 0.934 | 0.0286 |
| PG_pause_mean | 0.666 | 0.908 | -0.0134 |
| RESP_NE_ENTROPY | 0.580 | 0.782 | -0.0139 |
| RESP_NE_AIZUCHI_RATE | 0.532 | 0.838 | 0.0138 |

### E

| feature | topk_rate | sign_agree | coef_mean |
|---|---:|---:|---:|
| PG_resp_gap_p50 | 0.960 | 0.992 | -0.0568 |
| PG_pause_p50 | 0.816 | 0.950 | -0.0392 |
| RESP_YO_ENTROPY | 0.800 | 0.946 | 0.0316 |
| RESP_NE_AIZUCHI_RATE | 0.680 | 0.928 | 0.0221 |
| IX_oirmarker_after_question_rate | 0.674 | 0.866 | 0.0289 |
| FILL_rate_per_100chars | 0.644 | 0.870 | 0.0185 |
| FILL_has_any | 0.588 | 0.872 | 0.0205 |
| PG_speech_ratio | 0.574 | 0.658 | -0.0258 |
| RESP_NE_ENTROPY | 0.568 | 0.850 | 0.0158 |
| PG_pause_mean | 0.564 | 0.904 | -0.0204 |

### N

| feature | topk_rate | sign_agree | coef_mean |
|---|---:|---:|---:|
| IX_yesno_rate | 0.962 | 0.994 | -0.0365 |
| IX_oirmarker_after_question_rate | 0.808 | 0.970 | -0.0295 |
| RESP_NE_AIZUCHI_RATE | 0.804 | 0.948 | -0.0253 |
| PG_pause_p50 | 0.736 | 0.884 | -0.0200 |
| PG_resp_gap_p50 | 0.700 | 0.714 | 0.0111 |
| RESP_YO_ENTROPY | 0.620 | 0.884 | -0.0185 |
| FILL_rate_per_100chars | 0.578 | 0.818 | -0.0175 |
| IX_yesno_after_question_rate | 0.556 | 0.770 | -0.0059 |
| IX_oirmarker_rate | 0.534 | 0.716 | 0.0150 |
| PG_pause_mean | 0.468 | 0.838 | -0.0138 |

### O

| feature | topk_rate | sign_agree | coef_mean |
|---|---:|---:|---:|
| FILL_rate_per_100chars | 0.932 | 0.992 | -0.0678 |
| PG_speech_ratio | 0.886 | 0.972 | 0.0420 |
| RESP_YO_ENTROPY | 0.874 | 0.990 | -0.0479 |
| PG_resp_gap_mean | 0.782 | 0.966 | -0.0404 |
| RESP_NE_AIZUCHI_RATE | 0.756 | 0.934 | -0.0348 |
| PG_pause_p90 | 0.586 | 0.900 | -0.0259 |
| IX_yesno_rate | 0.544 | 0.708 | -0.0117 |
| IX_oirmarker_after_question_rate | 0.534 | 0.768 | 0.0177 |
| PG_resp_gap_p50 | 0.528 | 0.852 | 0.0231 |
| FILL_has_any | 0.500 | 0.886 | 0.0319 |

## Teacher: qwen3-235b

### C

| feature | topk_rate | sign_agree | coef_mean |
|---|---:|---:|---:|
| FILL_has_any | 0.988 | 1.000 | 0.0598 |
| IX_yesno_rate | 0.854 | 0.978 | 0.0484 |
| PG_pause_p50 | 0.840 | 0.982 | -0.0397 |
| PG_speech_ratio | 0.830 | 0.940 | 0.0350 |
| IX_topic_drift_mean | 0.738 | 0.994 | 0.0275 |
| IX_lex_overlap_mean | 0.726 | 0.994 | -0.0275 |
| PG_resp_gap_p90 | 0.700 | 0.950 | 0.0343 |
| IX_oirmarker_after_question_rate | 0.698 | 0.952 | 0.0269 |
| IX_oirmarker_rate | 0.518 | 0.858 | 0.0211 |
| FILL_rate_per_100chars | 0.492 | 0.642 | 0.0014 |

### A

| feature | topk_rate | sign_agree | coef_mean |
|---|---:|---:|---:|
| FILL_rate_per_100chars | 0.974 | 0.998 | 0.0481 |
| PG_pause_p90 | 0.914 | 0.976 | -0.0269 |
| PG_pause_mean | 0.806 | 0.886 | -0.0102 |
| PG_speech_ratio | 0.748 | 0.914 | 0.0202 |
| RESP_NE_ENTROPY | 0.746 | 0.918 | -0.0229 |
| RESP_NE_AIZUCHI_RATE | 0.742 | 0.946 | 0.0211 |
| FILL_has_any | 0.702 | 0.436 | -0.0135 |
| IX_yesno_after_question_rate | 0.686 | 0.908 | 0.0245 |
| PG_pause_p50 | 0.668 | 0.830 | -0.0079 |
| IX_yesno_rate | 0.554 | 0.820 | -0.0247 |

### E

| feature | topk_rate | sign_agree | coef_mean |
|---|---:|---:|---:|
| PG_pause_p90 | 0.990 | 0.998 | -0.0723 |
| PG_pause_mean | 0.890 | 0.950 | -0.0270 |
| RESP_YO_ENTROPY | 0.846 | 0.982 | 0.0418 |
| FILL_rate_per_100chars | 0.732 | 0.898 | 0.0242 |
| PG_pause_p50 | 0.714 | 0.824 | -0.0192 |
| PG_resp_gap_p90 | 0.672 | 0.934 | 0.0487 |
| IX_oirmarker_rate | 0.666 | 0.902 | 0.0310 |
| IX_yesno_after_question_rate | 0.642 | 0.898 | -0.0357 |
| PG_resp_gap_p50 | 0.640 | 0.880 | -0.0273 |
| FILL_has_any | 0.640 | 0.894 | 0.0247 |

### N

| feature | topk_rate | sign_agree | coef_mean |
|---|---:|---:|---:|
| RESP_NE_AIZUCHI_RATE | 0.980 | 1.000 | -0.0490 |
| PG_resp_gap_p50 | 0.972 | 0.994 | 0.0491 |
| IX_yesno_rate | 0.728 | 0.876 | -0.0144 |
| PG_resp_gap_p90 | 0.702 | 0.948 | 0.0220 |
| IX_oirmarker_after_question_rate | 0.650 | 0.888 | -0.0209 |
| RESP_YO_ENTROPY | 0.612 | 0.862 | -0.0152 |
| FILL_has_any | 0.610 | 0.924 | 0.0200 |
| IX_yesno_after_question_rate | 0.546 | 0.790 | -0.0107 |
| IX_oirmarker_rate | 0.508 | 0.596 | 0.0088 |
| PG_pause_p90 | 0.496 | 0.816 | -0.0123 |

### O

| feature | topk_rate | sign_agree | coef_mean |
|---|---:|---:|---:|
| PG_pause_p50 | 0.898 | 0.988 | 0.1058 |
| PG_pause_p90 | 0.882 | 0.958 | -0.0460 |
| PG_resp_gap_p90 | 0.880 | 0.988 | 0.0569 |
| PG_pause_mean | 0.810 | 0.978 | -0.0523 |
| IX_oirmarker_rate | 0.804 | 0.978 | 0.0384 |
| IX_yesno_after_question_rate | 0.734 | 0.896 | -0.0330 |
| PG_speech_ratio | 0.654 | 0.926 | 0.0440 |
| RESP_NE_AIZUCHI_RATE | 0.592 | 0.942 | -0.0268 |
| PG_resp_gap_p50 | 0.566 | 0.880 | 0.0220 |
| IX_yesno_rate | 0.552 | 0.438 | 0.0028 |

## Teacher: deepseek-v3

### C

| feature | topk_rate | sign_agree | coef_mean |
|---|---:|---:|---:|
| IX_yesno_rate | 0.876 | 0.988 | 0.0454 |
| PG_speech_ratio | 0.852 | 0.974 | 0.0470 |
| IX_oirmarker_after_question_rate | 0.822 | 0.958 | 0.0356 |
| PG_pause_p90 | 0.694 | 0.978 | -0.0440 |
| FILL_has_any | 0.678 | 0.942 | 0.0227 |
| RESP_NE_AIZUCHI_RATE | 0.646 | 0.888 | 0.0238 |
| IX_yesno_after_question_rate | 0.602 | 0.838 | 0.0096 |
| IX_lex_overlap_mean | 0.572 | 0.942 | -0.0205 |
| PG_resp_gap_p50 | 0.556 | 0.772 | -0.0182 |
| IX_topic_drift_mean | 0.556 | 0.942 | 0.0205 |

### A

| feature | topk_rate | sign_agree | coef_mean |
|---|---:|---:|---:|
| RESP_NE_ENTROPY | 0.964 | 0.998 | -0.0562 |
| FILL_rate_per_100chars | 0.922 | 0.984 | 0.0479 |
| RESP_YO_ENTROPY | 0.824 | 0.962 | 0.0342 |
| IX_yesno_rate | 0.730 | 0.904 | 0.0263 |
| PG_speech_ratio | 0.660 | 0.896 | 0.0320 |
| RESP_NE_AIZUCHI_RATE | 0.638 | 0.858 | 0.0182 |
| IX_oirmarker_after_question_rate | 0.632 | 0.862 | -0.0249 |
| PG_pause_mean | 0.590 | 0.908 | -0.0307 |
| PG_resp_gap_p50 | 0.556 | 0.854 | -0.0208 |
| PG_pause_p50 | 0.516 | 0.556 | 0.0201 |

### E

| feature | topk_rate | sign_agree | coef_mean |
|---|---:|---:|---:|
| PG_pause_p90 | 0.958 | 0.996 | -0.0433 |
| PG_pause_mean | 0.828 | 0.974 | -0.0315 |
| FILL_rate_per_100chars | 0.788 | 0.942 | 0.0335 |
| IX_oirmarker_rate | 0.666 | 0.864 | 0.0318 |
| RESP_YO_ENTROPY | 0.658 | 0.906 | 0.0298 |
| IX_oirmarker_after_question_rate | 0.654 | 0.810 | -0.0338 |
| PG_resp_gap_mean | 0.600 | 0.896 | 0.0320 |
| IX_yesno_after_question_rate | 0.586 | 0.872 | -0.0290 |
| PG_pause_p50 | 0.576 | 0.762 | -0.0089 |
| PG_resp_gap_p90 | 0.548 | 0.820 | 0.0233 |

### N

| feature | topk_rate | sign_agree | coef_mean |
|---|---:|---:|---:|
| PG_resp_gap_p50 | 0.934 | 0.986 | 0.0848 |
| PG_pause_p50 | 0.790 | 0.962 | -0.0683 |
| RESP_YO_ENTROPY | 0.726 | 0.940 | -0.0434 |
| FILL_rate_per_100chars | 0.724 | 0.922 | -0.0547 |
| IX_oirmarker_rate | 0.716 | 0.880 | 0.0574 |
| IX_yesno_rate | 0.674 | 0.830 | -0.0204 |
| PG_resp_gap_mean | 0.642 | 0.254 | -0.0027 |
| FILL_has_any | 0.640 | 0.918 | 0.0500 |
| RESP_NE_AIZUCHI_RATE | 0.624 | 0.858 | -0.0291 |
| IX_yesno_after_question_rate | 0.564 | 0.804 | -0.0207 |

### O

| feature | topk_rate | sign_agree | coef_mean |
|---|---:|---:|---:|
| PG_pause_p90 | 0.918 | 0.984 | -0.0837 |
| RESP_NE_AIZUCHI_RATE | 0.864 | 0.974 | -0.0747 |
| IX_oirmarker_rate | 0.862 | 0.978 | 0.0728 |
| IX_yesno_rate | 0.840 | 0.948 | -0.0692 |
| FILL_rate_per_100chars | 0.768 | 0.950 | -0.0662 |
| RESP_NE_ENTROPY | 0.750 | 0.948 | -0.0559 |
| IX_yesno_after_question_rate | 0.732 | 0.892 | -0.0462 |
| PG_pause_p50 | 0.666 | 0.870 | 0.0690 |
| PG_resp_gap_mean | 0.576 | 0.926 | 0.0511 |
| IX_oirmarker_after_question_rate | 0.506 | 0.662 | -0.0315 |

## Teacher: gpt-oss-120b

### C

| feature | topk_rate | sign_agree | coef_mean |
|---|---:|---:|---:|
| IX_yesno_rate | 0.974 | 0.996 | 0.1830 |
| FILL_has_any | 0.894 | 0.984 | 0.1629 |
| IX_oirmarker_after_question_rate | 0.870 | 0.990 | 0.1191 |
| PG_pause_p50 | 0.862 | 0.986 | -0.2045 |
| PG_resp_gap_p50 | 0.736 | 0.908 | -0.0989 |
| PG_speech_ratio | 0.698 | 0.802 | 0.0541 |
| PG_resp_gap_p90 | 0.556 | 0.794 | 0.1111 |
| RESP_NE_AIZUCHI_RATE | 0.548 | 0.912 | 0.0632 |
| PG_pause_mean | 0.536 | 0.756 | 0.3487 |
| PG_pause_p90 | 0.500 | 0.824 | -0.2411 |

### A

| feature | topk_rate | sign_agree | coef_mean |
|---|---:|---:|---:|
| IX_yesno_rate | 0.916 | 0.982 | 0.0820 |
| RESP_NE_ENTROPY | 0.912 | 0.990 | -0.0918 |
| PG_pause_p50 | 0.836 | 0.966 | -0.0690 |
| PG_speech_ratio | 0.788 | 0.954 | 0.0659 |
| PG_pause_p90 | 0.780 | 0.974 | -0.0631 |
| IX_yesno_after_question_rate | 0.774 | 0.926 | 0.0569 |
| RESP_NE_AIZUCHI_RATE | 0.674 | 0.942 | 0.0510 |
| PG_pause_mean | 0.658 | 0.928 | -0.0358 |
| PG_resp_gap_p50 | 0.600 | 0.928 | -0.0450 |
| FILL_rate_per_100chars | 0.540 | 0.856 | 0.0454 |

### E

| feature | topk_rate | sign_agree | coef_mean |
|---|---:|---:|---:|
| FILL_has_any | 0.960 | 0.996 | 0.0493 |
| PG_pause_p50 | 0.824 | 0.930 | -0.0309 |
| PG_speech_ratio | 0.784 | 0.918 | 0.0206 |
| RESP_YO_ENTROPY | 0.742 | 0.916 | 0.0347 |
| PG_pause_mean | 0.734 | 0.946 | -0.0223 |
| PG_pause_p90 | 0.724 | 0.938 | -0.0230 |
| RESP_NE_AIZUCHI_RATE | 0.724 | 0.926 | 0.0291 |
| PG_resp_gap_p50 | 0.700 | 0.868 | -0.0270 |
| FILL_rate_per_100chars | 0.650 | 0.776 | 0.0039 |
| PG_resp_gap_p90 | 0.452 | 0.746 | 0.0219 |

### N

| feature | topk_rate | sign_agree | coef_mean |
|---|---:|---:|---:|
| IX_oirmarker_after_question_rate | 0.998 | 1.000 | -0.1257 |
| IX_yesno_rate | 0.996 | 1.000 | -0.1519 |
| PG_pause_p50 | 0.694 | 0.840 | -0.0371 |
| PG_resp_gap_p50 | 0.656 | 0.832 | 0.0406 |
| IX_yesno_after_question_rate | 0.624 | 0.778 | -0.0215 |
| RESP_NE_AIZUCHI_RATE | 0.612 | 0.866 | -0.0376 |
| IX_oirmarker_rate | 0.600 | 0.830 | 0.0467 |
| PG_resp_gap_mean | 0.594 | 0.812 | 0.0260 |
| PG_resp_gap_p90 | 0.592 | 0.818 | 0.0304 |
| FILL_rate_per_100chars | 0.548 | 0.818 | -0.0297 |

### O

| feature | topk_rate | sign_agree | coef_mean |
|---|---:|---:|---:|
| PG_speech_ratio | 0.996 | 0.998 | 0.1285 |
| FILL_rate_per_100chars | 0.988 | 1.000 | -0.1250 |
| RESP_NE_AIZUCHI_RATE | 0.900 | 0.986 | -0.0721 |
| RESP_NE_ENTROPY | 0.714 | 0.936 | -0.0453 |
| PG_pause_mean | 0.678 | 0.862 | -0.0393 |
| PG_resp_gap_p50 | 0.664 | 0.902 | 0.0436 |
| PG_pause_p90 | 0.632 | 0.874 | -0.0342 |
| IX_yesno_rate | 0.622 | 0.708 | -0.0179 |
| IX_oirmarker_rate | 0.556 | 0.832 | -0.0302 |
| RESP_YO_ENTROPY | 0.526 | 0.858 | -0.0295 |

## Overlap with C (Top10)

| teacher | A overlap | E overlap | N overlap | O overlap |
|---|---:|---:|---:|---:|
| sonnet | 5 | 6 | 5 | 7 |
| qwen3-235b | 5 | 5 | 5 | 5 |
| deepseek-v3 | 5 | 3 | 5 | 5 |
| gpt-oss-120b | 7 | 8 | 6 | 6 |
