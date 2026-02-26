# Teacher robustness check (A/E/N/O): non-Claude 3 models

Permutation test (fixed α / 5000) summary.

| model | trait | alpha | r_obs | p(|r|) | note |
|---|:---:|---:|---:|---:|---|
| qwen3-235b | A | 100.0 | 0.365 | 0.0032 | sig |
| qwen3-235b | E | 316.227766016838 | 0.300 | 0.0224 | sig |
| qwen3-235b | N | 177.82794100389228 | 0.239 | 0.0634 |  |
| qwen3-235b | O | 3.1622776601683795 | 0.350 | 0.0060 | sig |
| deepseek-v3 | A | 100.0 | 0.339 | 0.0070 | sig |
| deepseek-v3 | E | 1000.0 | 0.136 | 0.3033 |  |
| deepseek-v3 | N | 316.227766016838 | 0.202 | 0.1154 |  |
| deepseek-v3 | O | 177.82794100389228 | 0.323 | 0.0086 | sig |
| gpt-oss-120b | A | 100.0 | 0.461 | 0.0002 | sig |
| gpt-oss-120b | E | 562.341325190349 | 0.257 | 0.0460 | sig |
| gpt-oss-120b | N | 100.0 | 0.401 | 0.0010 | sig |
| gpt-oss-120b | O | 100.0 | 0.345 | 0.0088 | sig |
