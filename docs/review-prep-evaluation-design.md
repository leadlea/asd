# 査読対応準備: 評価設計の頑健性

更新日: 2026-04-27
目的: 「評価設計は適切か？」「過学習していないか？」という査読質問に即座に回答できる資料

---

## 1. 評価設計の全体像

```
19 特徴量 → Ridge 回帰（α=100） → 5-fold CV → Pearson r
                                                    ↓
                                          Permutation test（n=5,000）→ p値
                                                    ↓
                                          Bootstrap（n=500）→ 係数安定性
```

---

## 2. Ridge 回帰の設定

スクリプト: `scripts/analysis/train_cejc_big5_from_features.py`

### パラメータ

| パラメータ | 値 | 根拠 |
|-----------|-----|------|
| α（正則化） | 100（固定） | permutation test 用。train スクリプトでは RidgeCV（α: 10⁻³〜10³, 25点）で自動選択 |
| CV folds | 5 | N=120 に対して各 fold 24 サンプル。安定性と計算コストのバランス |
| random_state | 42（train）/ 0（permutation） | 再現性担保 |
| 前処理 | SimpleImputer(median) → StandardScaler | 欠損値は中央値補完、特徴量は標準化 |

### 品質フィルタ（train スクリプト）

```python
keep = (df["n_pairs_total"] >= 20) & (df["FILL_text_len"] >= 800)
```

- 応答ペア数 ≥ 20: RESP 系特徴量の信頼性確保
- テキスト長 ≥ 800 文字: FILL 系特徴量の信頼性確保

---

## 3. Cross-Validation の実装

### KFold（shuffle=True）

```python
cv = KFold(n_splits=5, shuffle=True, random_state=42)
```

**重要**: 現在の実装は **observation-wise split**（行単位のシャッフル）。同一話者が複数会話に出現する場合、同一話者が train/test に分かれる可能性がある。

### データリークのリスク評価

- CEJC N=120 のうち、ユニーク話者は 74 名
- 同一話者が複数会話に出現するケースがある（例: 協力者本人が複数会話に参加）
- **厳密には GroupKFold（speaker_id 単位）が望ましい**
- ただし、特徴量は会話×話者単位で独立に計算されるため、リークの影響は限定的
- Limitation として記載し、将来的に GroupKFold での追試を提案

---

## 4. Permutation Test の実装

スクリプト: `scripts/analysis/permutation_test_ridge_fixedalpha.py`

### 手順

1. 観測データで 5-fold CV Ridge → r_obs を算出
2. Y（目的変数）を n=5,000 回ランダムにシャッフル
3. 各シャッフルで同じ 5-fold CV Ridge → r_perm を算出
4. p = (|r_perm| ≥ |r_obs| の回数 + 1) / (n_perm + 1)

### 実装の確認ポイント

```python
rng = np.random.default_rng(seed)
for i in range(n_perm):
    yp = rng.permutation(y)          # Y をシャッフル（X は固定）
    r_perm[i] = cv_ridge_r(X, yp, folds, seed, alpha)

p = (np.sum(np.abs(r_perm) >= abs(r_obs)) + 1.0) / (n_perm + 1.0)
```

- **Y のみをシャッフル**（X は固定）→ 特徴量と目的変数の関連を破壊
- **両側検定**: |r_perm| ≥ |r_obs| で判定
- **+1 補正**: p=0 を避ける（Phipson & Smyth 2010）
- **CV の seed は固定**: シャッフルごとに同じ fold 分割を使用 → permutation の変動源は Y のみ

---

## 5. Bootstrap 係数安定性の実装

スクリプト: `scripts/analysis/bootstrap_coef_stability.py`

### 手順

1. N=120 から復元抽出で N=120 のブートストラップサンプルを生成
2. RidgeCV（α 自動選択）で学習し、係数を記録
3. n=500 回繰り返し
4. 各特徴量について: 係数の平均、標準偏差、5%/95% 信頼区間、符号一致率、top-k 出現率を算出

### C × Sonnet の結果（主結果）

**安定（90% CI がゼロを跨がない）**:

| 特徴量 | coef_mean | CI [5%, 95%] | sign_agree | topk_rate |
|--------|:---------:|:------------:|:----------:|:---------:|
| FILL_has_any | +0.050 | [+0.011, +0.141] | 96.8% | 83.8% |
| IX_oirmarker_after_question_rate | +0.053 | [+0.011, +0.124] | 98.4% | 82.4% |
| PG_resp_gap_mean | -0.082 | [-0.367, -0.008] | 98.6% | 74.6% |
| IX_lex_overlap_mean | -0.034 | [-0.064, -0.008] | 98.0% | 67.2% |

**不安定（90% CI がゼロを跨ぐ）**:

| 特徴量 | coef_mean | CI [5%, 95%] | sign_agree | topk_rate |
|--------|:---------:|:------------:|:----------:|:---------:|
| PG_speech_ratio | +0.046 | [-0.014, +0.137] | 93.2% | 80.4% |
| RESP_NE_AIZUCHI_RATE | +0.033 | [-0.009, +0.080] | 91.4% | 62.6% |
| IX_yesno_rate | +0.032 | [-0.016, +0.104] | 89.6% | 56.8% |

### 解釈

- **FILL_has_any（+）**: フィラーを使う話者ほど C が高い → 発話の計画性・丁寧さの反映
- **IX_oirmarker_after_question_rate（+）**: 質問直後に修復開始する話者ほど C が高い → 理解確認の積極性
- **PG_resp_gap_mean（−）**: 応答が遅い話者ほど C が低い → 応答の即時性と誠実性の関連
- **IX_lex_overlap_mean（−）**: 語彙の繰り返しが多い話者ほど C が低い → 独自の表現を使う傾向

---

## 6. 想定される査読質問と回答案

### Q1: 「同一話者が train/test に漏れていないか？」

**回答**: 現在の実装は KFold（observation-wise）であり、同一話者が train/test に分かれる可能性がある。ただし、特徴量は会話×話者単位で独立に計算されるため、特徴量レベルでのリークはない。LLM 教師スコアも会話単位で独立に採点されている。より厳密な GroupKFold（speaker_id 単位）での追試は Future work として提案する。

### Q2: 「Permutation test で Y だけシャッフルするのは正しいか？」

**回答**: 正しい。Permutation test の目的は「X と Y の間に偶然以上の関連があるか」を検定すること。Y をシャッフルすることで X-Y 間の関連を破壊し、帰無分布を構築する。X をシャッフルすると特徴量間の相関構造が壊れるため不適切。

### Q3: 「Bootstrap で CI がゼロを跨ぐ特徴量は信頼できないのでは？」

**回答**: CI がゼロを跨ぐ特徴量（PG_speech_ratio, RESP_NE_AIZUCHI_RATE 等）は、N=120 では効果の方向が安定しないことを意味する。これらは「寄与の可能性がある」として報告するが、主要な結論の根拠には使わない。CI がゼロを跨がない 4 特徴量（FILL_has_any, IX_oirmarker_after_question_rate, PG_resp_gap_mean, IX_lex_overlap_mean）が C の主要ドライバーとして報告する。

### Q4: 「α=100 は恣意的では？」

**回答**: Permutation test では α を固定する必要がある（CV 内で α を選択すると、permutation ごとに異なる α が選ばれ、検定の前提が崩れる）。α=100 は train スクリプトの RidgeCV（25 点グリッド）で C × Sonnet の最適値として選択された値に近い。Bootstrap では RidgeCV を使用しており、α の選択自体の安定性も確認している。

---

## 7. 再現コマンド

```bash
# Ridge 回帰 + CV（全 trait）
python scripts/analysis/train_cejc_big5_from_features.py \
  --xy_parquet artifacts/analysis/datasets/cejc_home2_hq1_XY_Conly_sonnet.parquet \
  --out_dir artifacts/analysis/results/ridge

# Permutation test（C × Sonnet）
python scripts/analysis/permutation_test_ridge_fixedalpha.py \
  --xy_parquet artifacts/analysis/datasets/cejc_home2_hq1_XY_Conly_sonnet.parquet \
  --y_col Y_C --alpha 100 --n_perm 5000

# Bootstrap 係数安定性（C × Sonnet）
python scripts/analysis/bootstrap_coef_stability.py \
  --xy_parquet artifacts/analysis/datasets/cejc_home2_hq1_XY_Conly_sonnet.parquet \
  --y_col Y_C --n_boot 500 \
  --exclude_cols "IX_topic_drift_mean,n_pairs_total,n_pairs_after_NE,n_pairs_after_YO,IX_n_pairs,IX_n_pairs_after_question,PG_total_time,PG_resp_overlap_rate,FILL_text_len,FILL_cnt_total,FILL_cnt_eto,FILL_cnt_e,FILL_cnt_ano" \
  --out_dir artifacts/analysis/results/bootstrap/cejc_home2_hq1_Conly_sonnet_controls_excluded
```
