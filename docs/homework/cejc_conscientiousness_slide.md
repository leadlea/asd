# CEJC自然対話（自宅2名）: 相互行為特徴 → LLM仮想教師C（誠実性）

## Data / Teacher
- CEJC「自宅・話者数2」 + HQ1品質条件（N=120）
  - n_pairs_total≥80 / text_len≥2000 / after_question≥10
- Teacher: IPIP-NEO C 24 items（Claude Sonnet 4, strict 5-choice）

## Model
- X: 相互行為特徴のみ（PG/FILL/IX/RESP, 18 vars）
  - ※会話量（発話量/ペア数）は説明変数から除外
- Ridge regression, 5-fold CV

## Main Result
- CV: **r=0.335**, **R²=0.111**
- Permutation test (5000): **p=0.0236**（偶然以上）
- Coef stability (Bootstrap 500):
  - top-k出現率が高い主因子
    - FILL_has_any 0.838 / sign一致 0.968
    - OIR after question 0.824 / 0.984
    - speech_ratio 0.804 / 0.932
    - resp_gap_mean 0.746 / 0.986（負）
    - NE aizuchi 0.626 / 0.914
    - YES/NO 0.568 / 0.896
    - pause_p50 0.564 / 0.886（負）

## Interpretation (C↑)
- 質問場面で確認する（修復）/ 相槌やYESNOで応答する
- 応答が滑らか（gap・pauseが短い）
- フィラー出現（計画・整序コストの支払い）を伴う可能性

## Audit note (why we drop drift)
- topic_drift は短発話・タグ・相槌で過大になりやすい（例文監査で確認）
- driftv2では **r=0.242 / p=0.165** → 主張軸から外す