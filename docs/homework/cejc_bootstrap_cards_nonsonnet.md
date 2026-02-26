# Bootstrap stability cards (non-sonnet teachers)

- topk_rate = Top10 inclusion frequency (Bootstrap 500)
- sign_agree_rate = sign agreement frequency (Bootstrap 500)

## Teacher: qwen3-235b

<table>
<tr>
<td valign="top" width="62%">

### C Top10（qwen3-235b）
| Feature | Dir | topk_rate | sign_agree |
|---|:---:|---:|---:|
| FILL_has_any | + | 0.988 | 1.000 |
| IX_yesno_rate | + | 0.854 | 0.978 |
| PG_pause_p50 | − | 0.840 | 0.982 |
| PG_speech_ratio | + | 0.830 | 0.940 |
| IX_topic_drift_mean | + | 0.738 | 0.994 |
| IX_lex_overlap_mean | − | 0.726 | 0.994 |
| PG_resp_gap_p90 | + | 0.700 | 0.950 |
| IX_oirmarker_after_question_rate | + | 0.698 | 0.952 |
| IX_oirmarker_rate | + | 0.518 | 0.858 |
| FILL_rate_per_100chars | + | 0.492 | 0.642 |

</td>
<td valign="top" width="38%" align="center">

<a href="assets/figs/radar_qwen3-235b_C_topk_rate.png"><img src="assets/figs/radar_qwen3-235b_C_topk_rate.png" width="280"></a><br>
<sub><b>topk_rate</b>（クリックで拡大）</sub>
<br><br>
<a href="assets/figs/radar_qwen3-235b_C_sign_agree.png"><img src="assets/figs/radar_qwen3-235b_C_sign_agree.png" width="280"></a><br>
<sub><b>sign_agree_rate</b>（クリックで拡大）</sub>

</td>
</tr>
</table>

<table>
<tr>
<td valign="top" width="62%">

### A Top10（qwen3-235b）
| Feature | Dir | topk_rate | sign_agree |
|---|:---:|---:|---:|
| FILL_rate_per_100chars | + | 0.974 | 0.998 |
| PG_pause_p90 | − | 0.914 | 0.976 |
| PG_pause_mean | − | 0.806 | 0.886 |
| PG_speech_ratio | + | 0.748 | 0.914 |
| RESP_NE_ENTROPY | − | 0.746 | 0.918 |
| RESP_NE_AIZUCHI_RATE | + | 0.742 | 0.946 |
| FILL_has_any | − | 0.702 | 0.436 |
| IX_yesno_after_question_rate | + | 0.686 | 0.908 |
| PG_pause_p50 | − | 0.668 | 0.830 |
| IX_yesno_rate | − | 0.554 | 0.820 |

</td>
<td valign="top" width="38%" align="center">

<a href="assets/figs/radar_qwen3-235b_A_topk_rate.png"><img src="assets/figs/radar_qwen3-235b_A_topk_rate.png" width="280"></a><br>
<sub><b>topk_rate</b>（クリックで拡大）</sub>
<br><br>
<a href="assets/figs/radar_qwen3-235b_A_sign_agree.png"><img src="assets/figs/radar_qwen3-235b_A_sign_agree.png" width="280"></a><br>
<sub><b>sign_agree_rate</b>（クリックで拡大）</sub>

</td>
</tr>
</table>

<table>
<tr>
<td valign="top" width="62%">

### E Top10（qwen3-235b）
| Feature | Dir | topk_rate | sign_agree |
|---|:---:|---:|---:|
| PG_pause_p90 | − | 0.990 | 0.998 |
| PG_pause_mean | − | 0.890 | 0.950 |
| RESP_YO_ENTROPY | + | 0.846 | 0.982 |
| FILL_rate_per_100chars | + | 0.732 | 0.898 |
| PG_pause_p50 | − | 0.714 | 0.824 |
| PG_resp_gap_p90 | + | 0.672 | 0.934 |
| IX_oirmarker_rate | + | 0.666 | 0.902 |
| IX_yesno_after_question_rate | − | 0.642 | 0.898 |
| PG_resp_gap_p50 | − | 0.640 | 0.880 |
| FILL_has_any | + | 0.640 | 0.894 |

</td>
<td valign="top" width="38%" align="center">

<a href="assets/figs/radar_qwen3-235b_E_topk_rate.png"><img src="assets/figs/radar_qwen3-235b_E_topk_rate.png" width="280"></a><br>
<sub><b>topk_rate</b>（クリックで拡大）</sub>
<br><br>
<a href="assets/figs/radar_qwen3-235b_E_sign_agree.png"><img src="assets/figs/radar_qwen3-235b_E_sign_agree.png" width="280"></a><br>
<sub><b>sign_agree_rate</b>（クリックで拡大）</sub>

</td>
</tr>
</table>

<table>
<tr>
<td valign="top" width="62%">

### N Top10（qwen3-235b）
| Feature | Dir | topk_rate | sign_agree |
|---|:---:|---:|---:|
| RESP_NE_AIZUCHI_RATE | − | 0.980 | 1.000 |
| PG_resp_gap_p50 | + | 0.972 | 0.994 |
| IX_yesno_rate | − | 0.728 | 0.876 |
| PG_resp_gap_p90 | + | 0.702 | 0.948 |
| IX_oirmarker_after_question_rate | − | 0.650 | 0.888 |
| RESP_YO_ENTROPY | − | 0.612 | 0.862 |
| FILL_has_any | + | 0.610 | 0.924 |
| IX_yesno_after_question_rate | − | 0.546 | 0.790 |
| IX_oirmarker_rate | + | 0.508 | 0.596 |
| PG_pause_p90 | − | 0.496 | 0.816 |

</td>
<td valign="top" width="38%" align="center">

<a href="assets/figs/radar_qwen3-235b_N_topk_rate.png"><img src="assets/figs/radar_qwen3-235b_N_topk_rate.png" width="280"></a><br>
<sub><b>topk_rate</b>（クリックで拡大）</sub>
<br><br>
<a href="assets/figs/radar_qwen3-235b_N_sign_agree.png"><img src="assets/figs/radar_qwen3-235b_N_sign_agree.png" width="280"></a><br>
<sub><b>sign_agree_rate</b>（クリックで拡大）</sub>

</td>
</tr>
</table>

<table>
<tr>
<td valign="top" width="62%">

### O Top10（qwen3-235b）
| Feature | Dir | topk_rate | sign_agree |
|---|:---:|---:|---:|
| PG_pause_p50 | + | 0.898 | 0.988 |
| PG_pause_p90 | − | 0.882 | 0.958 |
| PG_resp_gap_p90 | + | 0.880 | 0.988 |
| PG_pause_mean | − | 0.810 | 0.978 |
| IX_oirmarker_rate | + | 0.804 | 0.978 |
| IX_yesno_after_question_rate | − | 0.734 | 0.896 |
| PG_speech_ratio | + | 0.654 | 0.926 |
| RESP_NE_AIZUCHI_RATE | − | 0.592 | 0.942 |
| PG_resp_gap_p50 | + | 0.566 | 0.880 |
| IX_yesno_rate | + | 0.552 | 0.438 |

</td>
<td valign="top" width="38%" align="center">

<a href="assets/figs/radar_qwen3-235b_O_topk_rate.png"><img src="assets/figs/radar_qwen3-235b_O_topk_rate.png" width="280"></a><br>
<sub><b>topk_rate</b>（クリックで拡大）</sub>
<br><br>
<a href="assets/figs/radar_qwen3-235b_O_sign_agree.png"><img src="assets/figs/radar_qwen3-235b_O_sign_agree.png" width="280"></a><br>
<sub><b>sign_agree_rate</b>（クリックで拡大）</sub>

</td>
</tr>
</table>

## Teacher: deepseek-v3

<table>
<tr>
<td valign="top" width="62%">

### C Top10（deepseek-v3）
| Feature | Dir | topk_rate | sign_agree |
|---|:---:|---:|---:|
| IX_yesno_rate | + | 0.876 | 0.988 |
| PG_speech_ratio | + | 0.852 | 0.974 |
| IX_oirmarker_after_question_rate | + | 0.822 | 0.958 |
| PG_pause_p90 | − | 0.694 | 0.978 |
| FILL_has_any | + | 0.678 | 0.942 |
| RESP_NE_AIZUCHI_RATE | + | 0.646 | 0.888 |
| IX_yesno_after_question_rate | + | 0.602 | 0.838 |
| IX_lex_overlap_mean | − | 0.572 | 0.942 |
| PG_resp_gap_p50 | − | 0.556 | 0.772 |
| IX_topic_drift_mean | + | 0.556 | 0.942 |

</td>
<td valign="top" width="38%" align="center">

<a href="assets/figs/radar_deepseek-v3_C_topk_rate.png"><img src="assets/figs/radar_deepseek-v3_C_topk_rate.png" width="280"></a><br>
<sub><b>topk_rate</b>（クリックで拡大）</sub>
<br><br>
<a href="assets/figs/radar_deepseek-v3_C_sign_agree.png"><img src="assets/figs/radar_deepseek-v3_C_sign_agree.png" width="280"></a><br>
<sub><b>sign_agree_rate</b>（クリックで拡大）</sub>

</td>
</tr>
</table>

<table>
<tr>
<td valign="top" width="62%">

### A Top10（deepseek-v3）
| Feature | Dir | topk_rate | sign_agree |
|---|:---:|---:|---:|
| RESP_NE_ENTROPY | − | 0.964 | 0.998 |
| FILL_rate_per_100chars | + | 0.922 | 0.984 |
| RESP_YO_ENTROPY | + | 0.824 | 0.962 |
| IX_yesno_rate | + | 0.730 | 0.904 |
| PG_speech_ratio | + | 0.660 | 0.896 |
| RESP_NE_AIZUCHI_RATE | + | 0.638 | 0.858 |
| IX_oirmarker_after_question_rate | − | 0.632 | 0.862 |
| PG_pause_mean | − | 0.590 | 0.908 |
| PG_resp_gap_p50 | − | 0.556 | 0.854 |
| PG_pause_p50 | + | 0.516 | 0.556 |

</td>
<td valign="top" width="38%" align="center">

<a href="assets/figs/radar_deepseek-v3_A_topk_rate.png"><img src="assets/figs/radar_deepseek-v3_A_topk_rate.png" width="280"></a><br>
<sub><b>topk_rate</b>（クリックで拡大）</sub>
<br><br>
<a href="assets/figs/radar_deepseek-v3_A_sign_agree.png"><img src="assets/figs/radar_deepseek-v3_A_sign_agree.png" width="280"></a><br>
<sub><b>sign_agree_rate</b>（クリックで拡大）</sub>

</td>
</tr>
</table>

<table>
<tr>
<td valign="top" width="62%">

### E Top10（deepseek-v3）
| Feature | Dir | topk_rate | sign_agree |
|---|:---:|---:|---:|
| PG_pause_p90 | − | 0.958 | 0.996 |
| PG_pause_mean | − | 0.828 | 0.974 |
| FILL_rate_per_100chars | + | 0.788 | 0.942 |
| IX_oirmarker_rate | + | 0.666 | 0.864 |
| RESP_YO_ENTROPY | + | 0.658 | 0.906 |
| IX_oirmarker_after_question_rate | − | 0.654 | 0.810 |
| PG_resp_gap_mean | + | 0.600 | 0.896 |
| IX_yesno_after_question_rate | − | 0.586 | 0.872 |
| PG_pause_p50 | − | 0.576 | 0.762 |
| PG_resp_gap_p90 | + | 0.548 | 0.820 |

</td>
<td valign="top" width="38%" align="center">

<a href="assets/figs/radar_deepseek-v3_E_topk_rate.png"><img src="assets/figs/radar_deepseek-v3_E_topk_rate.png" width="280"></a><br>
<sub><b>topk_rate</b>（クリックで拡大）</sub>
<br><br>
<a href="assets/figs/radar_deepseek-v3_E_sign_agree.png"><img src="assets/figs/radar_deepseek-v3_E_sign_agree.png" width="280"></a><br>
<sub><b>sign_agree_rate</b>（クリックで拡大）</sub>

</td>
</tr>
</table>

<table>
<tr>
<td valign="top" width="62%">

### N Top10（deepseek-v3）
| Feature | Dir | topk_rate | sign_agree |
|---|:---:|---:|---:|
| PG_resp_gap_p50 | + | 0.934 | 0.986 |
| PG_pause_p50 | − | 0.790 | 0.962 |
| RESP_YO_ENTROPY | − | 0.726 | 0.940 |
| FILL_rate_per_100chars | − | 0.724 | 0.922 |
| IX_oirmarker_rate | + | 0.716 | 0.880 |
| IX_yesno_rate | − | 0.674 | 0.830 |
| PG_resp_gap_mean | − | 0.642 | 0.254 |
| FILL_has_any | + | 0.640 | 0.918 |
| RESP_NE_AIZUCHI_RATE | − | 0.624 | 0.858 |
| IX_yesno_after_question_rate | − | 0.564 | 0.804 |

</td>
<td valign="top" width="38%" align="center">

<a href="assets/figs/radar_deepseek-v3_N_topk_rate.png"><img src="assets/figs/radar_deepseek-v3_N_topk_rate.png" width="280"></a><br>
<sub><b>topk_rate</b>（クリックで拡大）</sub>
<br><br>
<a href="assets/figs/radar_deepseek-v3_N_sign_agree.png"><img src="assets/figs/radar_deepseek-v3_N_sign_agree.png" width="280"></a><br>
<sub><b>sign_agree_rate</b>（クリックで拡大）</sub>

</td>
</tr>
</table>

<table>
<tr>
<td valign="top" width="62%">

### O Top10（deepseek-v3）
| Feature | Dir | topk_rate | sign_agree |
|---|:---:|---:|---:|
| PG_pause_p90 | − | 0.918 | 0.984 |
| RESP_NE_AIZUCHI_RATE | − | 0.864 | 0.974 |
| IX_oirmarker_rate | + | 0.862 | 0.978 |
| IX_yesno_rate | − | 0.840 | 0.948 |
| FILL_rate_per_100chars | − | 0.768 | 0.950 |
| RESP_NE_ENTROPY | − | 0.750 | 0.948 |
| IX_yesno_after_question_rate | − | 0.732 | 0.892 |
| PG_pause_p50 | + | 0.666 | 0.870 |
| PG_resp_gap_mean | + | 0.576 | 0.926 |
| IX_oirmarker_after_question_rate | − | 0.506 | 0.662 |

</td>
<td valign="top" width="38%" align="center">

<a href="assets/figs/radar_deepseek-v3_O_topk_rate.png"><img src="assets/figs/radar_deepseek-v3_O_topk_rate.png" width="280"></a><br>
<sub><b>topk_rate</b>（クリックで拡大）</sub>
<br><br>
<a href="assets/figs/radar_deepseek-v3_O_sign_agree.png"><img src="assets/figs/radar_deepseek-v3_O_sign_agree.png" width="280"></a><br>
<sub><b>sign_agree_rate</b>（クリックで拡大）</sub>

</td>
</tr>
</table>

## Teacher: gpt-oss-120b

<table>
<tr>
<td valign="top" width="62%">

### C Top10（gpt-oss-120b）
| Feature | Dir | topk_rate | sign_agree |
|---|:---:|---:|---:|
| IX_yesno_rate | + | 0.974 | 0.996 |
| FILL_has_any | + | 0.894 | 0.984 |
| IX_oirmarker_after_question_rate | + | 0.870 | 0.990 |
| PG_pause_p50 | − | 0.862 | 0.986 |
| PG_resp_gap_p50 | − | 0.736 | 0.908 |
| PG_speech_ratio | + | 0.698 | 0.802 |
| PG_resp_gap_p90 | + | 0.556 | 0.794 |
| RESP_NE_AIZUCHI_RATE | + | 0.548 | 0.912 |
| PG_pause_mean | + | 0.536 | 0.756 |
| PG_pause_p90 | − | 0.500 | 0.824 |

</td>
<td valign="top" width="38%" align="center">

<a href="assets/figs/radar_gpt-oss-120b_C_topk_rate.png"><img src="assets/figs/radar_gpt-oss-120b_C_topk_rate.png" width="280"></a><br>
<sub><b>topk_rate</b>（クリックで拡大）</sub>
<br><br>
<a href="assets/figs/radar_gpt-oss-120b_C_sign_agree.png"><img src="assets/figs/radar_gpt-oss-120b_C_sign_agree.png" width="280"></a><br>
<sub><b>sign_agree_rate</b>（クリックで拡大）</sub>

</td>
</tr>
</table>

<table>
<tr>
<td valign="top" width="62%">

### A Top10（gpt-oss-120b）
| Feature | Dir | topk_rate | sign_agree |
|---|:---:|---:|---:|
| IX_yesno_rate | + | 0.916 | 0.982 |
| RESP_NE_ENTROPY | − | 0.912 | 0.990 |
| PG_pause_p50 | − | 0.836 | 0.966 |
| PG_speech_ratio | + | 0.788 | 0.954 |
| PG_pause_p90 | − | 0.780 | 0.974 |
| IX_yesno_after_question_rate | + | 0.774 | 0.926 |
| RESP_NE_AIZUCHI_RATE | + | 0.674 | 0.942 |
| PG_pause_mean | − | 0.658 | 0.928 |
| PG_resp_gap_p50 | − | 0.600 | 0.928 |
| FILL_rate_per_100chars | + | 0.540 | 0.856 |

</td>
<td valign="top" width="38%" align="center">

<a href="assets/figs/radar_gpt-oss-120b_A_topk_rate.png"><img src="assets/figs/radar_gpt-oss-120b_A_topk_rate.png" width="280"></a><br>
<sub><b>topk_rate</b>（クリックで拡大）</sub>
<br><br>
<a href="assets/figs/radar_gpt-oss-120b_A_sign_agree.png"><img src="assets/figs/radar_gpt-oss-120b_A_sign_agree.png" width="280"></a><br>
<sub><b>sign_agree_rate</b>（クリックで拡大）</sub>

</td>
</tr>
</table>

<table>
<tr>
<td valign="top" width="62%">

### E Top10（gpt-oss-120b）
| Feature | Dir | topk_rate | sign_agree |
|---|:---:|---:|---:|
| FILL_has_any | + | 0.960 | 0.996 |
| PG_pause_p50 | − | 0.824 | 0.930 |
| PG_speech_ratio | + | 0.784 | 0.918 |
| RESP_YO_ENTROPY | + | 0.742 | 0.916 |
| PG_pause_mean | − | 0.734 | 0.946 |
| PG_pause_p90 | − | 0.724 | 0.938 |
| RESP_NE_AIZUCHI_RATE | + | 0.724 | 0.926 |
| PG_resp_gap_p50 | − | 0.700 | 0.868 |
| FILL_rate_per_100chars | + | 0.650 | 0.776 |
| PG_resp_gap_p90 | + | 0.452 | 0.746 |

</td>
<td valign="top" width="38%" align="center">

<a href="assets/figs/radar_gpt-oss-120b_E_topk_rate.png"><img src="assets/figs/radar_gpt-oss-120b_E_topk_rate.png" width="280"></a><br>
<sub><b>topk_rate</b>（クリックで拡大）</sub>
<br><br>
<a href="assets/figs/radar_gpt-oss-120b_E_sign_agree.png"><img src="assets/figs/radar_gpt-oss-120b_E_sign_agree.png" width="280"></a><br>
<sub><b>sign_agree_rate</b>（クリックで拡大）</sub>

</td>
</tr>
</table>

<table>
<tr>
<td valign="top" width="62%">

### N Top10（gpt-oss-120b）
| Feature | Dir | topk_rate | sign_agree |
|---|:---:|---:|---:|
| IX_oirmarker_after_question_rate | − | 0.998 | 1.000 |
| IX_yesno_rate | − | 0.996 | 1.000 |
| PG_pause_p50 | − | 0.694 | 0.840 |
| PG_resp_gap_p50 | + | 0.656 | 0.832 |
| IX_yesno_after_question_rate | − | 0.624 | 0.778 |
| RESP_NE_AIZUCHI_RATE | − | 0.612 | 0.866 |
| IX_oirmarker_rate | + | 0.600 | 0.830 |
| PG_resp_gap_mean | + | 0.594 | 0.812 |
| PG_resp_gap_p90 | + | 0.592 | 0.818 |
| FILL_rate_per_100chars | − | 0.548 | 0.818 |

</td>
<td valign="top" width="38%" align="center">

<a href="assets/figs/radar_gpt-oss-120b_N_topk_rate.png"><img src="assets/figs/radar_gpt-oss-120b_N_topk_rate.png" width="280"></a><br>
<sub><b>topk_rate</b>（クリックで拡大）</sub>
<br><br>
<a href="assets/figs/radar_gpt-oss-120b_N_sign_agree.png"><img src="assets/figs/radar_gpt-oss-120b_N_sign_agree.png" width="280"></a><br>
<sub><b>sign_agree_rate</b>（クリックで拡大）</sub>

</td>
</tr>
</table>

<table>
<tr>
<td valign="top" width="62%">

### O Top10（gpt-oss-120b）
| Feature | Dir | topk_rate | sign_agree |
|---|:---:|---:|---:|
| PG_speech_ratio | + | 0.996 | 0.998 |
| FILL_rate_per_100chars | − | 0.988 | 1.000 |
| RESP_NE_AIZUCHI_RATE | − | 0.900 | 0.986 |
| RESP_NE_ENTROPY | − | 0.714 | 0.936 |
| PG_pause_mean | − | 0.678 | 0.862 |
| PG_resp_gap_p50 | + | 0.664 | 0.902 |
| PG_pause_p90 | − | 0.632 | 0.874 |
| IX_yesno_rate | − | 0.622 | 0.708 |
| IX_oirmarker_rate | − | 0.556 | 0.832 |
| RESP_YO_ENTROPY | − | 0.526 | 0.858 |

</td>
<td valign="top" width="38%" align="center">

<a href="assets/figs/radar_gpt-oss-120b_O_topk_rate.png"><img src="assets/figs/radar_gpt-oss-120b_O_topk_rate.png" width="280"></a><br>
<sub><b>topk_rate</b>（クリックで拡大）</sub>
<br><br>
<a href="assets/figs/radar_gpt-oss-120b_O_sign_agree.png"><img src="assets/figs/radar_gpt-oss-120b_O_sign_agree.png" width="280"></a><br>
<sub><b>sign_agree_rate</b>（クリックで拡大）</sub>

</td>
</tr>
</table>

