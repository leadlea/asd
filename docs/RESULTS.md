# 最終結果サマリ

**Preset**: SGKF(k=2) + Platt + threshold=0.55  
**Features (top5)**: propernoun_ratio / pronoun_ratio / verb_ratio / discourse_marker_rate / mental_state_rate

## 指標（評価）
- AUC ≈ 0.863, BA ≈ 0.725, MCC ≈ 0.470（feature-subset評価, k=2, Platt, thr=0.55）

## サニティチェック（全件推論）
- 混同行列: TP=26, FP=3, FN=4, TN=27 → **BA=0.883**
- 予測CSV: `reports/pred_top5.csv`

## 図版
- AUC by fold: `reports/figures/loco_auc.png`
- Balanced Acc. by fold: `reports/figures/loco_ba.png`
- Ablation ΔAUC: `reports/figures/ablation_delta.png`

## 再現手順
make eval_best
make ablate_best
make infer_best
