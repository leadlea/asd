# NCNP共同研究者向けレビュー資料 v2
Date: 2026-07  
対象: 山下祐一先生（NCNP）、宗田卓史さん（NCNP）  
作成: 福原玄  

---

## 1. 研究の位置づけ

### 差別化ポイント

本研究は「**性格推定**」ではなく、「**会話の相互行為の再現可能な計測**」として位置づける。

- 先行研究（Hu et al. 2025, Altozano et al. 2026 等）は、LLMを用いた性格推定やASD分類を目的としているが、**会話の相互行為メカニズム**（タイミング・修復・応答型・フィラー）を体系的に計測する枠組みは提示していない。
- 本研究では、日本語会話コーパス（CEJC）から**18の相互行為特徴量**を再現可能に抽出し、LLM（4モデル）が推定したBig Fiveスコアを**仮想教師**として、どの特徴量が性格特性（特にConscientiousness）と関連するかを検証する。
- 主張の軸は「**Cが複数LLM教師で頑健に推定可能**」であり、その背景として**Teacher間一致度の高さ**（C: mean r=0.699）を示す。

### 研究の新規性

1. 日本語会話コーパスでの**初の体系的な相互行為特徴量の検証**
2. **複数LLM教師の頑健性検証**（4教師中3教師でCが有意）
3. **再現可能な評価設計**（subject-wise split、permutation test 5000回、bootstrap 500回）

---

## 2. 方法

### 2.1 データ

- **コーパス**: CEJC（日本語日常会話コーパス）home2サブセット、HQ1品質フィルタ済み
- **サンプルサイズ**: N=120（conversation × speaker ペア）
- **Big5採点**: IPIP-NEO-120（日本語120項目）、4 LLMモデルで採点
  - Sonnet4（Claude）、Qwen3-235B、DeepSeek-V3、GPT-OSS-120B

### 2.2 回帰モデル

- **モデル**: Ridge回帰 + 5-fold subject-wise CV
- **目的変数**: LLM教師が推定したBig Fiveスコア（trait別）
- **説明変数**: 18の相互行為特徴量（下記）
- **除外変数（EXCL3）**: 会話量に関わるcontrol変数（total_chars, n_turns, n_utterances等）は説明変数から除外

### 2.3 信頼性検証

- **Permutation test**: 目的変数を5000回シャッフルし、観測相関以上が偶然出る確率を算出
- **Bootstrap**: 500回リサンプリングによる係数安定性評価（topk_rate、sign_agree_rate）

### 2.4 18特徴量の定義

以下の18特徴量を4カテゴリ（PG: タイミング、FILL: フィラー、IX: 相互行為、RESP: 応答型）に分類して使用する。

#### 概要一覧

| # | 特徴量名 | カテゴリ | 概要 |
|--:|----------|----------|------|
| 1 | PG_speech_ratio | PG | 発話率（話者の発話時間 / 会話全体時間） |
| 2 | PG_pause_mean | PG | 沈黙の平均長（同一話者の連続発話間ギャップ） |
| 3 | PG_pause_p50 | PG | 沈黙の中央値 |
| 4 | PG_pause_p90 | PG | 沈黙の90パーセンタイル |
| 5 | PG_resp_gap_mean | PG | 応答遅れの平均（話者交替時のギャップ） |
| 6 | PG_resp_gap_p50 | PG | 応答遅れの中央値 |
| 7 | PG_resp_gap_p90 | PG | 応答遅れの90パーセンタイル |
| 8 | FILL_has_any | FILL | フィラー出現発話率（えっと/えー/あのを含む発話の割合） |
| 9 | FILL_rate_per_100chars | FILL | 100文字あたりフィラー率 |
| 10 | IX_oirmarker_rate | IX | 修復開始（OIR）率（え？/えっ/なに？等で始まる応答の割合） |
| 11 | IX_oirmarker_after_question_rate | IX | 質問直後のOIR率 |
| 12 | IX_yesno_rate | IX | YES/NO応答率（はい/うん/いいえ等で始まる応答の割合） |
| 13 | IX_yesno_after_question_rate | IX | 質問直後のYES/NO率 |
| 14 | IX_lex_overlap_mean | IX | 語彙重なり（前発話と応答の文字バイグラムJaccard係数の平均） |
| 15 | IX_topic_drift_mean | IX | 話題逸脱度（1 − IX_lex_overlap_mean、共線性に注意） |
| 16 | RESP_NE_AIZUCHI_RATE | RESP | 「ね」直後の相槌率 |
| 17 | RESP_NE_ENTROPY | RESP | 「ね」直後の応答多様性（Shannon entropy） |
| 18 | RESP_YO_ENTROPY | RESP | 「よ」直後の応答多様性（Shannon entropy） |

#### アルゴリズム詳細

**PG（タイミング）カテゴリ**

| 特徴量 | 計算アルゴリズム | 欠損値の扱い |
|--------|------------------|--------------|
| PG_speech_ratio | 話者の発話時間合計 / 会話全体時間 | total_timeが0または欠損の場合NaN |
| PG_pause_mean | 同一話者の連続発話間ギャップ（≥gap_tol秒）の平均 | 該当ギャップがない場合NaN |
| PG_pause_p50 | 同上の50パーセンタイル | 該当ギャップがない場合NaN |
| PG_pause_p90 | 同上の90パーセンタイル | 該当ギャップがない場合NaN |
| PG_resp_gap_mean | 話者交替時の前発話end→応答startギャップ（≥gap_tol秒）の平均 | 該当ギャップがない場合NaN |
| PG_resp_gap_p50 | 同上の50パーセンタイル | 該当ギャップがない場合NaN |
| PG_resp_gap_p90 | 同上の90パーセンタイル | 該当ギャップがない場合NaN |

**FILL（フィラー）カテゴリ**

| 特徴量 | 計算アルゴリズム | 欠損値の扱い |
|--------|------------------|--------------|
| FILL_has_any | フィラー（えっと/えー/あの）を1つ以上含む発話の割合 | 話者の発話が0件の場合NaN |
| FILL_rate_per_100chars | フィラー総数 / (テキスト文字数 / 100) | text_lenが0の場合NaN |

**IX（相互行為）カテゴリ**

| 特徴量 | 計算アルゴリズム | 欠損値の扱い |
|--------|------------------|--------------|
| IX_oirmarker_rate | OIRマーカー（え？/えっ/なに？等）で始まる応答の割合。話者が応答側となる全隣接ペアに対して計算 | — |
| IX_oirmarker_after_question_rate | 前発話が質問の場合に限定したOIRマーカー応答率 | 質問直後ペアが0件の場合NaN |
| IX_yesno_rate | YES/NOプレフィックス（はい/うん/えー/いいえ等）で始まる応答の割合 | — |
| IX_yesno_after_question_rate | 前発話が質問の場合に限定したYES/NO応答率 | 質問直後ペアが0件の場合NaN |
| IX_lex_overlap_mean | 前発話と応答の文字バイグラムJaccard係数の平均 | — |
| IX_topic_drift_mean | 1 − IX_lex_overlap_mean（IX_lex_overlap_meanと共線性あり） | — |

**RESP（応答型）カテゴリ**

| 特徴量 | 計算アルゴリズム | 欠損値の扱い |
|--------|------------------|--------------|
| RESP_NE_AIZUCHI_RATE | 前発話が「ね」終助詞で終わる場合に、応答が相槌プレフィックスで始まる割合 | n_pairs_after_NEが0の場合NaN |
| RESP_NE_ENTROPY | 「ね」終助詞直後の応答先頭トークンのShannon entropy（log2） | n_pairs_after_NEが0の場合NaN |
| RESP_YO_ENTROPY | 「よ」終助詞直後の応答先頭トークンのShannon entropy（log2） | n_pairs_after_YOが0の場合NaN |

> **注**: Ridge回帰パイプラインでは、NaN値は `SimpleImputer(strategy="median")` により中央値補完される。

---

## 3. 結果

### 3.1 Cの頑健性（Permutation test）

Conscientiousness（C: 誠実性）について、4つのLLM教師それぞれを仮想教師としたPermutation test（5000回）の結果を以下に示す。

| LLM教師 | r_obs | p(&#124;r&#124;) | 判定 |
|---------|------:|------:|------|
| Sonnet4 | 0.434 | 0.0008 | **有意** |
| Qwen3-235B | 0.390 | 0.001 | **有意** |
| GPT-OSS-120B | 0.447 | 0.0008 | **有意** |
| DeepSeek-V3 | 0.205 | 0.113 | 非有意 |

**4教師中3教師で有意**（p < 0.05）であり、Cは教師モデルに依存せず頑健に推定可能であることが示された。DeepSeekでは有意に至らなかったが、相関の方向は正である。

![Cの4教師Permutation test結果](../../reports/paper_figs_v2/fig_permutation_C_bar.png)

### 3.2 Teacher間一致度

同一（conversation_id, speaker_id）に対する4教師のスコア間Pearson相関の平均（off-diagonal mean r）を算出した。

| Trait | mean r（Teacher間一致度） |
|------:|-------------------------:|
| C | **0.699**（最高） |
| E | 0.640 |
| N | 0.603 |
| O | 0.559 |
| A | **0.435**（最低） |

Cはteacher間一致度が最も高く（≈0.70）、仮想教師として安定していることが、Cの頑健性の背景を説明する。一方、Aはteacher間一致度が最も低く（≈0.44）、teacher依存性が大きい。

![Teacher間一致度ヒートマップ（5 trait × 4 teacher）](../../reports/paper_figs_v2/fig_teacher_heatmap.png)

### 3.3 Bootstrap Top Drivers（C, Sonnet4基準）

Bootstrap 500回リサンプリングにおけるCの上位特徴量（topk_rate降順）を以下に示す。

| 特徴量 | 方向 | topk_rate | sign_agree_rate |
|--------|:----:|----------:|----------------:|
| FILL_has_any | + | 0.838 | 0.968 |
| IX_oirmarker_after_question_rate | + | 0.824 | 0.984 |
| PG_speech_ratio | + | 0.804 | 0.932 |
| PG_resp_gap_mean | − | 0.746 | 0.986 |
| PG_resp_gap_p50 | − | 0.678 | 0.864 |
| IX_lex_overlap_mean | − | 0.672 | 0.980 |
| IX_topic_drift_mean | + | 0.656 | 0.980 |
| RESP_NE_AIZUCHI_RATE | + | 0.626 | 0.914 |
| IX_yesno_rate | + | 0.568 | 0.896 |
| PG_pause_p50 | − | 0.564 | 0.886 |

上位3特徴量（**FILL_has_any**, **IX_oirmarker_after_question_rate**, **PG_speech_ratio**）はいずれも正の方向で安定しており、Cが高い話者は「フィラーを含む発話が多い」「質問直後に修復開始（OIR）が多い」「発話率が高い」傾向を示す。

![Bootstrap Top10 レーダーチャート（C, Sonnet4）](../../reports/paper_figs_v2/fig_bootstrap_C_radar.png)

---

## 4. 議論ポイント（NCNPミーティング用）

### 4.1 Cの頑健性の解釈

- **なぜCだけが頑健か？**: Teacher間一致度が最も高い（mean r=0.699）ことから、LLM教師がCを推定する際に会話テキストから得る手がかりが比較的一貫していると考えられる。
- **臨床的意味**: 誠実性（C）は「計画性・規律性・注意深さ」に関わる特性であり、会話の相互行為（フィラーの使い方、応答のタイミング、修復行動）に反映されやすい可能性がある。

### 4.2 Top Driversの解釈

- **FILL_has_any（+）**: フィラーを含む発話が多い → 発話計画のコストを示す可能性。Cが高い人は「考えてから話す」傾向？
- **IX_oirmarker_after_question_rate（+）**: 質問直後のOIR（聞き返し）が多い → 正確に理解しようとする姿勢の反映？
- **PG_speech_ratio（+）**: 発話率が高い → 会話への積極的な参加。
- **PG_resp_gap_mean（−）**: 応答遅れが短い → テンポよく応答する傾向。

### 4.3 A/E/N/Oの探索的結果

- A/E/N/Oはteacher依存性が大きく、本論では探索的結果としてAppendixに配置する方針。
- 特にAはteacher間一致度が最低（0.435）であり、LLM教師の採点が不安定。
- 一部のteacher×trait組み合わせで有意な結果が出るが、一般因子混入の可能性に注意が必要。

### 4.4 限界と今後

- **小標本（N=120）**: 外部検証（別コーパス・別集団）が未了。
- **LLM教師の妥当性**: 自己報告（self-report）との相関は未検証。仮想教師の妥当性を担保するには外部基準が必要。
- **特徴量の範囲**: 現在はテキスト＋タイミングのみ。音声特徴（韻律・声質）の追加で精度向上の余地がある。
- **次ステップ候補**:
  - 国語研データ（鈴木あすみさん）との紐づけによる外部妥当性検証
  - CSJデータでの追試（N=36で予備的に実施済み）
  - 修復（OIR）の成功率・コストまで踏み込んだ分析

### 4.5 論文化の方針確認

- **本論**: C中心（teacher頑健性 + 一致度の裏付け + bootstrap top drivers）
- **Appendix**: A/E/N/O（探索的結果、teacher依存性の検証）
- **差別化**: 「性格推定」ではなく「会話の相互行為の計測」として立て付ける
- **対象学会**: 発達支援学会（2026年9月）等、NLPガチ勢と直接競合しない場を想定
