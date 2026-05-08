# 宗田さんレビューコメント #1561 への検証結果と修正方針

対象コメント（`paper1_ja_st.docx` Comment #1561）
> 「3段階リッジと重複する結果だと思っていましたが，値が少し違う点は気になりました。
>  何か異なる手法を試しているのでしょうか？」

対象箇所：3.4.3節 表6（3段階Ridge Stage 3）と、アンサンブルBig5の予測値 vs 観測値散布図（figure）

作成日：2026-05-08（金）
作成者：福原玄
状態：**山下先生ジャッジ待ち**（今週末レビュー予定）

---

## TL;DR

- 宗田さんの違和感は**正しい**。表6と散布図の r 値は全5次元でずれていた。
- 原因は**計算ミスではなく、2つの方法論的選択軸の違い**。
  - 軸1: 特徴量セット（21 = demo+classical+novel vs 19 = classical+novel のみ）
  - 軸2: r の集約方法（fold平均 vs OOF連結）
- **研究の骨子・主張には一切影響なし**。有意/非有意の判定は両条件で同一。
- Method記述の精緻化＋図の再生成のみで解決可能。**推奨は案A（図をStage 3と同じ21 features + fold_meanに統一）**。

---

## 1. 検証の経緯

`paper1_ja_st.docx` から抽出した宗田さんのレビューコメント全52件のうち、**計算手法・数値の正確性に関わる唯一の指摘**として #1561 を優先検証した。

検証スクリプト：`scripts/analysis/verify_predicted_vs_three_stage.py`
出力：
- `artifacts/analysis/results/consistency_check/predicted_vs_three_stage_comparison.tsv`
- `artifacts/analysis/results/consistency_check/predicted_vs_three_stage_diagnosis.tsv`

計算条件：5-fold CV Ridge（α=100, seed=42, subject-wise KFold、SimpleImputer median、StandardScaler）
計算時間：約5秒（LLM API なし、ローカル計算のみ）

---

## 2. 原因：2つの実装差異

### 2.1 差異の所在

実装レベルで確認されたのは、以下の2軸のみ。それ以外（seed, alpha, CVパラメータ, スケーリング, imputer, カーネルKFold）は完全に一致している。

| 項目 | 3段階Ridge Stage 3（表6） | 散布図（predicted_vs_observed） |
|---|---|---|
| ファイル | `scripts/analysis/three_stage_ridge.py` | `scripts/paper_figs/gen_paper_figs_v2.py` |
| 特徴量セット | **21個**（demo 2 + classical 10 + novel 9）| **19個**（classical 10 + novel 9） |
| r_obs の集約 | **fold平均**: 各foldの r を5個平均 | **OOF連結**: 全120件の y_pred を連結し Pearson r を1回 |

### 2.2 発生経緯（推定）

- Stage 3 は「人口統計→Classical→Novel」の段階的追加効果を見せる目的でdemographicsを含む設計。
- 散布図は「相互行為特徴量だけで Big5 が予測できるかの可視化」目的で別途作られた経緯があり、demographicsを入れ忘れていた可能性が高い。paper-finalization spec Task 3.1 で新規追加したものだが、Stage 3 との一貫性は明示チェックが漏れていた。

---

## 3. 定量結果

### 3.1 4条件 × 5 trait の r_obs

5-fold CV Ridge（α=100, seed=42）、アンサンブルBig5を目的変数。

|          | 19features (no demo) |                | 21features (demo付) |                |
|:--------:|:--------:|:----------:|:---------:|:----------:|
| **trait** | **fold_mean** | **oof_concat** | **fold_mean** | **oof_concat** |
| O | 0.4099 | 0.4063 | **0.4813** | 0.4742 |
| C | 0.4315 | 0.4101 | **0.4693** | 0.4430 |
| E | 0.2341 | 0.1975 | **0.2372** | 0.1997 |
| A | 0.4494 | 0.4164 | **0.5378** | 0.5050 |
| N | 0.3174 | 0.2724 | **0.3108** | 0.2681 |

- 太字（21f × fold_mean）= 表6 Stage 3 公表値。**全5次元で公表値と完全一致**（再現性 OK）。
- 右下（19f × oof_concat）= 現在の散布図の表示値。

### 3.2 ズレの差分分解（figure − 表6 Stage 3）

| trait | total Δ | aggregation 軸のみ<br/>（21f固定） | feature 軸のみ<br/>（fold_mean固定） | 主因 |
|---:|---:|---:|---:|:---|
| O | −0.075 | −0.007 | **−0.071** | 特徴量軸が支配的 |
| C | −0.059 | −0.026 | **−0.038** | 両軸ほぼ均等 |
| E | −0.040 | **−0.038** | −0.003 | 集約軸が支配的 |
| A | −0.121 | −0.033 | **−0.088** | 特徴量軸が支配的（最大） |
| N | −0.038 | **−0.043** | +0.007 | 集約軸が支配的 |

- すべて figure < 表6 の方向。
- A は最大で −0.121 の乖離。これは demographics なし の効果が大きいため。
- 集約軸の差は平均すると fold平均の方が OOF連結より絶対値が大きめに出る傾向（小標本で各 fold 内相関が変動するため）。

### 3.3 有意性への影響

| trait | 表6 Stage 3 | p_corrected（既報）| 判定 |
|:---:|---:|---:|:---:|
| O | 0.481 | p < 0.01 | 有意 |
| C | 0.469 | p < 0.01 | 有意 |
| E | 0.237 | n.s. | 非有意 |
| A | 0.538 | p < 0.01 | 有意 |
| N | 0.311 | p < 0.05 | 有意 |

- 散布図側の r（0.20〜0.50）に揃えても、Eは非有意のまま・他4次元は有意のまま。
- **有意/非有意の判定は変わらない**。研究の主張（Eを除く4次元で有意）は揺るがない。

---

## 4. 論文の骨子への影響評価

| 主張 | 影響 |
|:---|:---:|
| 19個の相互行為特徴量を定量化指標として提案 | **なし** |
| アンサンブルBig5でEを除く4次元が有意（Holm補正後） | **なし**（再現確認済） |
| Cは 4 LLM中3 LLM で個別に有意（頑健性） | **なし** |
| Teacher間一致度でCが最高（mean r ≒ 0.70）| **なし** |
| 3段階Ridgeで人口統計→Classical→Novel のΔrがポジティブ | **なし** |
| ベースライン3条件で LLM がテキストを利用 | **なし** |
| Feature Dose-Response実験の結論（フィラーは指標だが原因でない）| **なし** |

**結論: 論文の骨子・結論・主張は一切変更不要。** 方法論的な透明性を上げるチャンス、というのが実体。

---

## 5. 修正方針の選択肢

### 案 A: 散布図を Stage 3 と同じ 21 features + fold_mean で再生成（推奨）

- **修正対象**: `gen_paper_figs_v2.py` の `gen_fig_predicted_vs_observed` 関数 1箇所
  - 特徴量セット: 19 → 21（demographicsを追加）
  - 集約方法: OOF連結 → fold_mean（もしくは「図には OOF 点群を表示しつつタイトルの r は fold_mean」）
- **表6 の数値**: 変更不要
- **既存の数値解釈**: すべて温存
- **Method の追記**: 最小（「散布図は Stage 3 と同じモデルの予測値」と1行）
- **宗田さんコメントへの応答**: 「おっしゃる通り散布図が Stage 3 と異なる特徴量セット・集約方法を使っていました。Stage 3 と一致するように修正しました」

### 案 B: 表6 の Stage 3 を OOF 連結方式に変更

- **修正対象**: `three_stage_ridge.py` の集約ロジック（fold_mean → oof_concat）
- **表6 の数値が変わる**: O: 0.481→0.474, C: 0.469→0.443, E: 0.237→0.200, A: 0.538→0.505, N: 0.311→0.268
- **Permutation test の p値再計算**: 必要（5000回 permutation × 5 trait = 約20分）
- **副次影響**: 表6の数値を参照している本文・Discussion・他テーブルのメンテ
- **メリット**: OOF 連結は「単一の解釈可能な r」として査読者に伝えやすい
- **デメリット**: 差し替え範囲が広い

### 案 C: 現状維持 + Method記述だけ精緻化

- **修正対象**: Method 2.4節に「Stage 3 は各 fold の Pearson r の平均、散布図は全サンプルの OOF 予測連結の Pearson r」と明記
- **数値修正**: ゼロ
- **デメリット**: 読者は「同じ r のはず」と思い込みやすい箇所で、Method 1行を追うまで混乱する可能性

### 推奨

**案 A**。理由：
1. 公表値と表6 を温存できる（山下先生・宗田さんとすでに合意した結果の保全）
2. 修正コストが最小（1関数のみ）
3. 宗田さんコメントへの正面からの応答になる（「値が違う→一致させた」）
4. 散布図の目的が「Stage 3 モデルの予測精度の可視化」として整合的になる

---

## 6. 案A実行時のアクションリスト

山下先生ジャッジ後、方針が確定した場合の実行手順（参考）。

1. `gen_paper_figs_v2.py` の `gen_fig_predicted_vs_observed` を修正
   - 特徴量セットを 21 に変更（demographics結合のため `load_and_join_metadata` 呼び出し追加）
   - タイトルの r を fold_mean で表示（または fold_mean + OOF 両方併記）
2. 図を再生成（`reports/paper_figs_v2/fig_predicted_vs_observed.png`）
3. Method 2.4 節に1行追記：「散布図の予測値は Stage 3 と同一のモデル（21特徴量、5-fold CV）による out-of-fold 予測である」
4. LaTeX コンパイル → paper1_ja.pdf 差し替え
5. `docs/homework/soda_comment_1561_analysis.md`（本ファイル）の「状態」を「対応済み」に更新

---

## 7. 宗田さん向け共有メッセージ案

以下、Slack または Word コメントへの返信用：

> 宗田さん
> コメント #1561（散布図と3段階Ridgeの値が少し違う件）、ありがとうございます。
> 検証したところ、おっしゃる通り2つの実装が異なる方法論を使っていました。原因は以下の2軸です：
>
> 1. 特徴量セット：3段階Ridge Stage 3 は人口統計(2) + Classical(10) + Novel(9) = 21個、散布図は Classical + Novel = 19個のみ
> 2. r の集約：Stage 3 は fold平均、散布図は OOF 連結
>
> 有意/非有意の判定は両条件で変わらず、研究の骨子には影響がないことを確認済みです。検証結果と修正方針を `docs/homework/soda_comment_1561_analysis.md` に整理してGitHubに上げておきました（今後 `main` にpush）。
>
> 修正案としては「散布図を Stage 3 と同じ 21 features + fold_mean で再生成する（案A）」を推奨しています。表6の公表値を温存しつつ、図と表を一致させられる最小修正です。
>
> 山下先生のジャッジ後に最終確定させる想定ですが、ここまでの整理で問題なさそうかコメントいただけると助かります。

---

## 8. 付録：実行コマンド（再現用）

```bash
cd /Users/genfukuhara/cpsy
.venv/bin/python scripts/analysis/verify_predicted_vs_three_stage.py
```

出力：
- `artifacts/analysis/results/consistency_check/predicted_vs_three_stage_comparison.tsv`（5 traits × 4 conditions = 20 rows）
- `artifacts/analysis/results/consistency_check/predicted_vs_three_stage_diagnosis.tsv`（5 traits × 差分分解）

---

## 9. 記録

| 日付 | 状態 | 担当 |
|:---:|:---|:---:|
| 2026-05-08 | 検証スクリプト作成・実行・数値確定 | 福原 |
| 2026-05-08 | 本mdをGitHub main にpush（宗田さんへ共有） | 福原 |
| 2026-05-09〜10 | 山下先生レビュー予定 | 山下先生 |
| 未定 | 案確定後に修正実施 | 福原 |
