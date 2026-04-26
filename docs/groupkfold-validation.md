# GroupKFold（subject-wise split）検証結果

更新日: 2026-04-27
目的: 論文の第八の限界で記載した「subject-wise split」を実装し、全 trait × 全 teacher で KFold vs GroupKFold を比較

---

## 背景

論文に「subject-wise split により同一話者のレコードが訓練セットとテストセットに分割されないよう制御している」と記載していたが、実際のコード（`permutation_test_ridge_fixedalpha.py` 等）は `KFold`（observation-wise）を使用していた。この齟齬を解消するため、`GroupKFold(groups=cejc_person_id)` による再検証を実施した。

- N=120 レコード、74 名のユニーク話者
- 25 名が複数会話に参加（71 レコード = 59.2%）
- GroupKFold は同一 cejc_person_id の全レコードを同じ fold に配置

スクリプト: `scripts/analysis/groupkfold_all.py`
結果TSV: `artifacts/analysis/results/groupkfold_vs_kfold_all.tsv`

---

## C（誠実性）— 主結果: 3/4 教師で有意性維持

| Teacher | KFold r | KFold p | GroupKFold r | GroupKFold p | Δr |
|---------|:-------:|:-------:|:------------:|:------------:|:---:|
| Sonnet 4 | 0.430 | **0.001** | 0.360 | **0.006** | -0.070 |
| Qwen3-235B | 0.377 | **0.001** | 0.403 | **0.002** | +0.026 |
| GPT-OSS-120B | 0.432 | **0.001** | 0.452 | **0.001** | +0.020 |
| DeepSeek-V3 | 0.165 | 0.205 | 0.229 | 0.068 | +0.064 |

**結論: C は GroupKFold でも 3/4 教師で有意（p<0.01）。論文の主張は維持される。**

---

## 全 trait × 全 teacher 結果一覧

| Trait | Teacher | KFold r | KFold p | KFold sig | GKF r | GKF p | GKF sig | Δr |
|-------|---------|:-------:|:-------:|:---------:|:-----:|:-----:|:-------:|:---:|
| A | deepseek-v3 | 0.299 | 0.028 | ** | 0.278 | 0.032 | ** | -0.021 |
| A | gpt-oss-120b | 0.451 | 0.001 | ** | 0.394 | 0.004 | ** | -0.057 |
| A | qwen3-235b | 0.351 | 0.006 | ** | 0.285 | 0.019 | ** | -0.066 |
| A | sonnet | 0.202 | 0.116 | n.s. | 0.188 | 0.157 | n.s. | -0.014 |
| **C** | **deepseek-v3** | 0.165 | 0.205 | n.s. | 0.229 | 0.068 | n.s. | +0.064 |
| **C** | **gpt-oss-120b** | **0.432** | **0.001** | **\*\*** | **0.452** | **0.001** | **\*\*** | +0.020 |
| **C** | **qwen3-235b** | **0.377** | **0.001** | **\*\*** | **0.403** | **0.002** | **\*\*** | +0.026 |
| **C** | **sonnet** | **0.430** | **0.001** | **\*\*** | **0.360** | **0.006** | **\*\*** | -0.070 |
| E | deepseek-v3 | 0.173 | 0.186 | n.s. | 0.236 | 0.065 | n.s. | +0.063 |
| E | gpt-oss-120b | 0.220 | 0.079 | n.s. | 0.231 | 0.071 | n.s. | +0.011 |
| E | qwen3-235b | 0.275 | 0.028 | ** | 0.281 | 0.031 | ** | +0.006 |
| E | sonnet | 0.205 | 0.107 | n.s. | 0.214 | 0.097 | n.s. | +0.009 |
| N | deepseek-v3 | 0.201 | 0.109 | n.s. | 0.267 | 0.031 | ** | +0.066 |
| N | gpt-oss-120b | 0.396 | 0.004 | ** | 0.539 | 0.001 | ** | +0.143 |
| N | qwen3-235b | 0.269 | 0.030 | ** | 0.291 | 0.021 | ** | +0.022 |
| N | sonnet | 0.093 | 0.474 | n.s. | 0.111 | 0.387 | n.s. | +0.018 |
| O | deepseek-v3 | 0.377 | 0.003 | ** | 0.411 | 0.001 | ** | +0.034 |
| O | gpt-oss-120b | 0.370 | 0.005 | ** | 0.322 | 0.007 | ** | -0.048 |
| O | qwen3-235b | 0.341 | 0.010 | ** | 0.315 | 0.012 | ** | -0.026 |
| O | sonnet | 0.144 | 0.287 | n.s. | 0.239 | 0.065 | n.s. | +0.094 |

---

## 有意性が変化したケース

| Trait | Teacher | KFold | GroupKFold | 変化 |
|-------|---------|:-----:|:----------:|------|
| N | deepseek-v3 | n.s. (p=0.109) | ** (p=0.031) | 有意に転じた |

他の19条件は有意性の方向が変わらなかった。

---

## 解釈

1. **C の主張は完全に維持**: 3/4 教師で GroupKFold でも有意。GPT-OSS と Qwen3 では r がむしろ上昇
2. **observation-wise の楽観バイアスは限定的**: 20 条件中、r が下がったのは 8 条件、上がったのは 12 条件。一方向のバイアスではない
3. **N × deepseek-v3 が有意に転じた**: GroupKFold で fold 構成が変わったことによる偶然の可能性もあるが、n_perm=1000 での結果なので参考値
4. **論文の第八の限界の記述を修正する必要がある**: 「subject-wise split で制御している」→「GroupKFold（cejc_person_id 単位）で制御した」に修正し、本検証結果を根拠として記載

---

## 再現コマンド

```bash
python scripts/analysis/groupkfold_all.py \
  --datasets_dir artifacts/analysis/datasets \
  --metadata_tsv artifacts/analysis/cejc_speaker_metadata.tsv \
  --out_tsv artifacts/analysis/results/groupkfold_vs_kfold_all.tsv \
  --n_perm 1000
```
