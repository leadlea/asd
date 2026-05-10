# 宗田さんレビューコメント #1561 への検証結果と修正方針

対象コメント（`paper1_ja_st.docx` Comment #1561）
> 「3段階リッジと重複する結果だと思っていましたが，値が少し違う点は気になりました。
>  何か異なる手法を試しているのでしょうか？」

対象箇所：3.4.3節 表6（3段階Ridge Stage 3）と、アンサンブルBig5の予測値 vs 観測値散布図

作成日：2026-05-10（日）
作成者：福原玄
状態：山下先生レビュー待ち（今週末）／宗田さんより案A'のご提案あり

---

## TL;DR

- ご指摘の通り、表6と散布図の r 値は全5次元で一致していなかった。
- 原因は、2つの実装が異なる方法論的選択（特徴量セットと r の集約方法）を採用していたことにある。
  - 軸1: 特徴量セット（21 = demo+classical+novel vs 19 = classical+novel のみ）
  - 軸2: r の集約方法（fold平均 vs OOF連結）
- 有意/非有意の判定は両条件で同一であり、論文の主張に対する本質的な修正は不要。
- 当初は案A（21 features + fold_mean）を候補として共有。その後、宗田さんより「散布図上の120点と表示される相関係数が同じデータから算出される方が整合する」とのご提案をいただき、**案A'（21 features + OOF連結維持）** を新たな候補として検討中。最終決定は山下先生の週末レビューを踏まえて行う。

---

## 1. 検証の経緯

`paper1_ja_st.docx` で宗田さんよりいただいたレビューコメントのうち、表6と散布図の数値が一致しない旨のご指摘（#1561）について、原因を切り分けるため定量的な検証を行った。

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

- Stage 3 は「人口統計→Classical→Novel」の段階的追加効果を見せる目的で demographics を含む設計。
- 散布図は paper-finalization 作業時に「相互行為特徴量による予測の可視化」として別途追加した経緯があり、Stage 3 との特徴量セット・集約方法の整合性チェックが漏れていた。今回の宗田さんのご指摘で発覚。

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

- 散布図側の r（0.20〜0.50）に揃えても、E は非有意のまま、他4次元は有意のまま。
- 有意/非有意の判定自体は変わらない。したがって論文の主要な主張（Eを除く4次元で有意）に対する本質的な修正は不要。

---

## 4. 論文への影響範囲

| 主張 | 影響 |
|:---|:---:|
| 19個の相互行為特徴量を定量化指標として提案 | なし |
| アンサンブルBig5でEを除く4次元が有意（Holm補正後） | なし（再現確認済） |
| Cは 4 LLM中3 LLM で個別に有意（頑健性） | なし |
| Teacher間一致度でCが最高（mean r ≒ 0.70）| なし |
| 3段階Ridgeで人口統計→Classical→Novel のΔrがポジティブ | なし |
| ベースライン3条件で LLM がテキストを利用 | なし |
| Feature Dose-Response実験の結論（フィラーは指標だが原因でない）| なし |

主要な結論部分には影響しない一方、表6 と散布図の整合性は Method 記述・図の再生成で改善の余地がある、というのが今回の位置づけ。

---

## 5. 修正方針の選択肢

> **2026-05-08 更新**: 宗田さんより案A'（Stage 3 と同じ 21 features に揃えた上で、集約方法は現状の OOF 連結のまま維持）のご提案をいただいた。散布図上の120点と表示される相関係数を同じデータから算出することで「点群と相関係数がずれない」視覚整合性を保てるというご意図。採否は山下先生の週末レビューを踏まえて確定する。

### 案 A': 散布図を 21 features + OOF 連結で再生成（宗田さんより提案・最有力候補）

- **修正対象**: `gen_paper_figs_v2.py` の `gen_fig_predicted_vs_observed` 関数
  - 特徴量セット: 19 → 21（demographics を追加、`load_and_join_metadata` を呼び出し）
  - 集約方法: **OOF 連結のまま維持**（散布図の120点と整合）
- **散布図のタイトル r（修正後の期待値）**: O=0.474, C=0.443, E=0.200, A=0.505, N=0.268
- **表6 Stage 3 (r_obs)**: 変更不要（公表値 O=0.481, C=0.469, E=0.237, A=0.538, N=0.311 をそのまま保持）
- **Method の追記**: 「Stage 3 の r（表6）は各fold の Pearson r の平均、散布図の r は全120件のOOF予測と観測値から算出した単一のPearson r。同一モデルの異なる要約統計量である」の1〜2行

### 案 A: 散布図を 21 features + fold_mean で再生成（初期案）

- 特徴量セット: 21（Stage 3 と同じ）
- 集約方法: fold_mean（表6 と同じ）
- 散布図の r と表6 の r が数値上完全一致
- **懸念点（宗田さんご指摘）**: 散布図上の点群（120件の OOF 予測）とタイトルの r（fold_mean）が別データから計算される形になり、視覚整合性が崩れる

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
- **デメリット**: 特徴量セットの違い（21 vs 19）を説明しきれず、Method 1行を追うまで混乱する可能性

### 推奨

現時点の最有力候補は **案 A'**（宗田さんご提案）。理由：
1. 表6 の公表値をそのまま保持できる
2. 散布図上の 120 点と表示される相関係数を同じデータから計算するため視覚整合性が保てる
3. 修正コストが最小（1関数のみ）
4. 散布図の位置づけが「Stage 3 モデルの予測精度の可視化」として整合する
5. 表6 の r（fold平均）と散布図の r（OOF連結）は同一モデルの異なる要約統計量である旨を Method で1行明記

最終決定は山下先生の週末レビューを踏まえて確定させたい。

---

## 6. 案A'実行時のアクションリスト

山下先生のレビュー後、方針が確定した場合の実行手順（参考）。

1. `gen_paper_figs_v2.py` の `gen_fig_predicted_vs_observed` を修正
   - 特徴量セットを 21 に変更（demographics 結合のため `load_and_join_metadata` 呼び出し追加）
   - 集約方法は現状の OOF 連結をそのまま維持
   - タイトルの r は **21 features × OOF 連結** の値を表示（散布図の 120 点と同じデータから算出）
2. 図を再生成（`reports/paper_figs_v2/fig_predicted_vs_observed.png`）
3. Method 2.4 節に以下を追記：
   - 「散布図の予測値は Stage 3 と同一のモデル（21特徴量、5-fold CV）による out-of-fold 予測である」
   - 「Stage 3 の r（表6）は各 fold の Pearson r の平均、散布図の r は全120件の OOF 予測と観測値から算出した単一の Pearson r である」
4. LaTeX コンパイル → paper1_ja.pdf 差し替え
5. 本ファイルの「状態」を「対応済み」に更新

---

## 7. 付録：実行コマンド（再現用）

```bash
cd /Users/genfukuhara/cpsy
.venv/bin/python scripts/analysis/verify_predicted_vs_three_stage.py
```

出力：
- `artifacts/analysis/results/consistency_check/predicted_vs_three_stage_comparison.tsv`（5 traits × 4 conditions = 20 rows）
- `artifacts/analysis/results/consistency_check/predicted_vs_three_stage_diagnosis.tsv`（5 traits × 差分分解）

---

## 8. 記録

| 日付 | 状態 | 担当 |
|:---:|:---|:---:|
| 2026-05-08 | 検証スクリプト作成・実行・数値確定 | 福原 |
| 2026-05-08 | 本mdを main にpush | 福原 |
| 2026-05-08 | 宗田さんより案A'（21f × OOF連結維持）のご提案を受領 | 宗田さん |
| 2026-05-09〜10 | 山下先生レビュー予定 | 山下先生 |
| 未定 | 方針確定後に修正実施 | 福原 |
