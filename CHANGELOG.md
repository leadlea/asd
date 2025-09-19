# CHANGELOG

### 2025-09-19 22:58:06 — LoCO evaluation
- Groups=6 | Features=8
- metrics: AUC=nan, F1=0.410
- params: `{"feat_csv": "data/processed/features_merged.csv", "out_json": "reports/loco_report.json"}`

### 2025-09-19 23:06:20 — LoCO evaluation
- Groups=6 | single-class folds=6 | Features=8
- metrics: AUC=NA, F1=0.410, BA=0.717
- params: `{"feat_csv": "data/processed/features_merged.csv", "out_json": "reports/loco_report.json", "mode": "loco"}`

### 2025-09-19 23:10:09 — LoCO evaluation
- Groups=6 | single-class folds=6 | Features=8
- metrics: AUC=NA, F1=0.000, BA=0.500
- params: `{"feat_csv": "data/processed/features_merged.csv", "out_json": "reports/loco_report.json", "mode": "loco"}`

### 2025-09-19 23:14:26 — StratifiedGroupKFold(5) evaluation
- Groups=6 | single-class folds=4 | Features=8
- metrics: AUC=0.730, F1=0.174, BA=0.570
- params: `{"feat_csv": "data/processed/features_merged.csv", "out_json": "reports/loco_report.json", "mode": "sgkf"}`

### 2025-09-19 23:18:25 — StratifiedGroupKFold(2) evaluation
- Groups=6 | single-class folds=0 | Features=8
- metrics: AUC=0.768, F1=0.489, BA=0.637, MCC=0.234
- params: `{"feat_csv": "data/processed/features_merged.csv", "out_json": "reports/loco_report.json", "mode": "sgkf", "splits": 2}`

### 2025-09-19 23:22:56 — StratifiedGroupKFold(3) evaluation
- Groups=6 | single-class folds=2 | Features=8
- metrics: AUC=0.730, F1=0.290, BA=0.617, MCC=0.245
- params: `{"feat_csv": "data/processed/features_merged.csv", "out_json": "reports/loco_report.json", "mode": "sgkf", "splits": 3}`

### 2025-09-19 23:23:30 — StratifiedGroupKFold(5) evaluation
- Groups=6 | single-class folds=4 | Features=8
- metrics: AUC=0.730, F1=0.174, BA=0.570, MCC=0.147
- params: `{"feat_csv": "data/processed/features_merged.csv", "out_json": "reports/loco_report.json", "mode": "sgkf", "splits": 5}`

### 2025-09-19 23:24:34 — Feature ablation (leave-1-out)
- Base AUC=0.939, F1=0.863 | Features=8
- metrics: AUC=0.939, F1=0.863
- params: `{"feat_csv": "data/processed/features_merged.csv", "out_json": "reports/ablation_report.json"}`

### 2025-09-19 23:27:40 — Threshold sweep (CV probs)
- splits=3
- metrics: F1*=0.793, BA*=0.800
- params: `{"best_threshold": 0.55, "feat_csv": "data/processed/features_merged.csv"}`

### 2025-09-19 23:30:27 — Freeze decision threshold
- 最適しきい値をモデル設定に固定
- metrics: threshold=0.550, F1*=0.793, BA*=0.800
- params: `{"config": "config/model_config.json"}`

### 2025-09-19 23:38:29 — Feature ablation (leave-1-out)
- Base AUC=0.939, F1=0.824, thr=0.55 | Features=8 | splits=5
- metrics: AUC=0.939, F1=0.824
- params: `{"feat_csv": "data/processed/features_merged.csv", "out_json": "reports/ablation_report.json", "threshold": 0.55, "splits": 5}`

### 2025-09-19 23:42:03 — StratifiedGroupKFold(2) evaluation
- Groups=6 | single-class folds=0 | Features=8 | thr=0.55
- metrics: AUC=0.768, F1=0.492, BA=0.662, MCC=0.292
- params: `{"feat_csv": "data/processed/features_merged.csv", "out_json": "reports/loco_report.json", "mode": "sgkf", "splits": 2, "threshold": 0.55}`

### 2025-09-19 23:54:51 — StratifiedGroupKFold(2) evaluation
- Groups=6 | single-class folds=0 | Features=8 | thr=0.55 | calib=platt
- metrics: AUC=0.762, F1=0.403, BA=0.638, MCC=0.241
- params: `{"feat_csv": "data/processed/features_merged.csv", "out_json": "reports/loco_report.json", "mode": "sgkf", "splits": 2, "threshold": 0.55, "calibrate": "platt"}`

### 2025-09-19 23:59:44 — StratifiedGroupKFold(2) evaluation
- Groups=6 | single-class folds=0 | Features=8 | thr=0.55 | calib=isotonic
- metrics: AUC=0.741, F1=0.417, BA=0.600, MCC=0.168
- params: `{"feat_csv": "data/processed/features_merged.csv", "out_json": "reports/loco_report.json", "mode": "sgkf", "splits": 2, "threshold": 0.55, "calibrate": "isotonic"}`

### 2025-09-20 00:03:05 — StratifiedGroupKFold(2) evaluation
- Groups=6 | single-class folds=0 | Features=8 | thr=0.55 | calib=platt
- metrics: AUC=0.762, F1=0.403, BA=0.638, MCC=0.241
- params: `{"feat_csv": "data/processed/features_merged.csv", "out_json": "reports/loco_report.json", "mode": "sgkf", "splits": 2, "threshold": 0.55, "calibrate": "platt"}`

### 2025-09-20 00:03:08 — StratifiedGroupKFold(2) evaluation
- Groups=6 | single-class folds=0 | Features=8 | thr=0.5 | calib=platt
- metrics: AUC=0.762, F1=0.420, BA=0.625, MCC=0.250
- params: `{"feat_csv": "data/processed/features_merged.csv", "out_json": "reports/loco_report.json", "mode": "sgkf", "splits": 2, "threshold": 0.5, "calibrate": "platt"}`

### 2025-09-20 00:03:10 — StratifiedGroupKFold(2) evaluation
- Groups=6 | single-class folds=0 | Features=8 | thr=0.45 | calib=platt
- metrics: AUC=0.762, F1=0.406, BA=0.588, MCC=0.162
- params: `{"feat_csv": "data/processed/features_merged.csv", "out_json": "reports/loco_report.json", "mode": "sgkf", "splits": 2, "threshold": 0.45, "calibrate": "platt"}`

### 2025-09-20 00:09:21 — StratifiedGroupKFold(2) eval (thr=0.55, calib=platt, gnorm=corpus)
- Groups=6 | single-class folds=0 | Features=8
- metrics: AUC=0.642, F1=0.263, BA=0.525, MCC=0.094
- params: `{"feat_csv": "data/processed/features_merged.csv", "mode": "sgkf", "splits": 2, "threshold": 0.55, "calibrate": "platt", "group_norm": "corpus"}`

### 2025-09-20 00:13:44 — StratifiedGroupKFold(2) eval (thr=0.55, calib=platt, gnorm=none)
- Groups=6 | single-class folds=0 | Features=8
- metrics: AUC=0.762, F1=0.403, BA=0.638, MCC=0.241
- params: `{"feat_csv": "data/processed/features_merged.csv", "mode": "sgkf", "splits": 2, "threshold": 0.55, "calibrate": "platt", "group_norm": "none"}`

### 2025-09-20 00:16:05 — Save eval preset
- 固定設定を保存（再現用）
- metrics: 
- params: `{"decision_threshold": 0.55, "calibrate": "platt", "cv_mode": "sgkf", "cv_splits": 2}`

### 2025-09-20 00:22:08 — StratifiedGroupKFold(2) eval (thr=0.55, calib=platt, gnorm=none)
- Groups=6 | single-class folds=0 | Features=8
- metrics: AUC=0.762, F1=0.403, BA=0.638, MCC=0.241
- params: `{"feat_csv": "data/processed/features_merged.csv", "mode": "sgkf", "splits": 2, "threshold": 0.55, "calibrate": "platt", "group_norm": "none"}`

### 2025-09-20 00:26:51 — Feature ablation (leave-1-out)
- Base AUC=0.939, F1=0.824, thr=0.55 | Features=8 | splits=5
- metrics: AUC=0.939, F1=0.824
- params: `{"feat_csv": "data/processed/features_merged.csv", "out_json": "reports/ablation_report.json", "threshold": 0.55, "splits": 5}`

### 2025-09-20 00:31:36 — Feature subset eval
- top3 | k=2, thr=0.55, calib=platt, C=1.0
- metrics: AUC=0.875, BA=0.700, F1=0.417, MCC=0.378
- params: `{"features": ["propernoun_ratio", "pronoun_ratio", "verb_ratio"]}`

### 2025-09-20 00:31:56 — Feature subset eval
- top5 | k=2, thr=0.55, calib=platt, C=1.0
- metrics: AUC=0.863, BA=0.725, F1=0.482, MCC=0.470
- params: `{"features": ["propernoun_ratio", "pronoun_ratio", "verb_ratio", "discourse_marker_rate", "mental_state_rate"]}`

### 2025-09-20 00:35:36 — Feature subset eval
- top5_C1.0_thr0.55 | k=2, thr=0.55, calib=platt, C=1.0
- metrics: AUC=0.863, BA=0.725, F1=0.482, MCC=0.470
- params: `{"features": ["propernoun_ratio", "pronoun_ratio", "verb_ratio", "discourse_marker_rate", "mental_state_rate"]}`

### 2025-09-20 00:35:38 — Feature subset eval
- top5_C1.0_thr0.50 | k=2, thr=0.5, calib=platt, C=1.0
- metrics: AUC=0.863, BA=0.700, F1=0.476, MCC=0.425
- params: `{"features": ["propernoun_ratio", "pronoun_ratio", "verb_ratio", "discourse_marker_rate", "mental_state_rate"]}`

### 2025-09-20 00:35:39 — Feature subset eval
- top5_C0.5_thr0.55 | k=2, thr=0.55, calib=platt, C=0.5
- metrics: AUC=0.853, BA=0.700, F1=0.417, MCC=0.378
- params: `{"features": ["propernoun_ratio", "pronoun_ratio", "verb_ratio", "discourse_marker_rate", "mental_state_rate"]}`

### 2025-09-20 00:35:41 — Feature subset eval
- top5_C0.5_thr0.50 | k=2, thr=0.5, calib=platt, C=0.5
- metrics: AUC=0.853, BA=0.688, F1=0.461, MCC=0.404
- params: `{"features": ["propernoun_ratio", "pronoun_ratio", "verb_ratio", "discourse_marker_rate", "mental_state_rate"]}`

### 2025-09-20 00:35:42 — Feature subset eval
- top5_C0.25_thr0.55 | k=2, thr=0.55, calib=platt, C=0.25
- metrics: AUC=0.833, BA=0.688, F1=0.400, MCC=0.354
- params: `{"features": ["propernoun_ratio", "pronoun_ratio", "verb_ratio", "discourse_marker_rate", "mental_state_rate"]}`

### 2025-09-20 00:35:44 — Feature subset eval
- top5_C0.25_thr0.50 | k=2, thr=0.5, calib=platt, C=0.25
- metrics: AUC=0.833, BA=0.675, F1=0.418, MCC=0.375
- params: `{"features": ["propernoun_ratio", "pronoun_ratio", "verb_ratio", "discourse_marker_rate", "mental_state_rate"]}`

### 2025-09-20 00:53
- Fix preset: SGKF2 + Platt + thr=0.55 + TOP5 features
- Eval: see reports/loco_report.json / figures
- Sanity (all predictions): TP=26 FP=3 FN=4 TN=27 | BA=0.883
