# 作業ログ: 3段階Ridgeのsubject-wise統一と仕上げ（2026-06-26）

> 対象論文: `paper1_ja.tex` / 図表: `reports/paper_figs_v2/` / 分析: `scripts/analysis/`
> リポジトリ: https://github.com/leadlea/asd （main にpush済み）
> 期間: 2026-06-22〜06-26 のファイナライズ作業の記録（中核は 6/26 のGroupKFold統一）

---

## 0. このログの位置づけ

宗田さんからの宿題（3段階Ridgeの「OOF予測の全標本連結」「paired bootstrap検定」の手続き補足）に
答える過程で、**3段階Ridge系スクリプトが本文記述(subject-wise/GroupKFold)に反して通常KFoldで
回っていた不整合**を発見し、修正した。あわせて 6/22〜25 の仕上げ作業も記録する。

---

## 1. 中核: 3段階RidgeのCVをGroupKFold(subject-wise)に統一（commit `6b0435c`）

### 1.1 発見した不整合
- 本文は3.4.3節および付録で繰り返し「5-fold subject-wise CV / GroupKFold(cejc\_person\_id)」と記述。
- しかし実装3スクリプト（`three_stage_ridge.py` の `cv_ridge_r`、`three_stage_metrics_diag.py` /
  `three_stage_paired_test.py` の `cv_oof_predictions`）は **通常 `KFold(shuffle, seed=42)`** を使用。
- 話者重複59.2%のため、通常KFoldは同一話者が訓練・検証に跨りリーク→R²が楽観側に出るリスク。
  本研究が他解析でGroupKFoldを採用した理由そのものに反していた。

### 1.2 修正内容
- `load_and_join_metadata`（`three_stage_ridge.py`）のmerge列に `cejc_person_id` を追加し、
  groupsを下流へ供給可能にした。
- `cv_oof_predictions`（`three_stage_metrics_diag.py`）に `groups` 引数を追加し、
  与えられた場合は `GroupKFold(n_splits=5).split(X, y, groups)` を使用（本流と同一パターン）。
- `three_stage_metrics_diag.py` / `three_stage_paired_test.py` の `run_one_trait` で
  `groups = merged["cejc_person_id"]` を抽出して渡すよう変更。
- 両スクリプトの docstring を GroupKFold subject-wise に修正。

### 1.3 再実行・再生成（再現コマンド）
```bash
PYTHONPATH=. .venv/bin/python -m scripts.analysis.three_stage_metrics_diag --teacher ensemble
PYTHONPATH=. .venv/bin/python -m scripts.analysis.three_stage_paired_test  --teacher ensemble
PYTHONPATH=. .venv/bin/python scripts/paper_figs/gen_fig_three_stage_r2.py --teacher ensemble
PYTHONPATH=. .venv/bin/python scripts/paper_figs/gen_tab_three_stage_r2.py --teacher ensemble
uplatex -interaction=nonstopmode paper1_ja.tex   # ×2
dvipdfmx paper1_ja.dvi
```
- 生成物: `fig_three_stage_comparison.png`, `tab_three_stage.tex`(本文R²/RMSE),
  `tab_three_stage_r.tex`(付録r版)。
- TSV（gitignore対象）: `artifacts/analysis/results/three_stage_metrics/three_stage_metrics_ensemble.tsv`,
  `three_stage_paired_test_ensemble.tsv`。

### 1.4 統一後の結果（KFold→GroupKFoldで変化）
- Stage2→3（Novel追加）ΔR²: O +0.010 / C +0.048 / N +0.069（上昇）, E −0.026 / A −0.014（低下）。
- paired bootstrap で名目有意は **N のみ**（ΔR²=+0.069, p_boot=0.044）。ただし Wilcoxon は非有意
  （p=0.19）で検定間が一致せず頑健でない。他4次元は有意でなく、**有意な悪化も無し**。
- 旧KFold版で出ていた「Eのみ有意な悪化(p_boot=0.030)」は消失。
- 立て付け（Novelはモデル全体の増分妥当性として主張せず、寄与は係数レベル3.4.4で担保）は維持。

### 1.5 本文の再整合（更新箇所）
- 3.4.3本文・表6キャプション: 数値、「5次元中4次元」→「3次元(O/C/N)」、有意性記述を更新。
- 「被験者ごと/被験者単位」→「各レコード（会話×話者）単位」に正確化（bootstrapはレコード単位再標本）。
- 考察「3段階Ridge回帰比較の含意」: 数値・有意性を更新。
- 考察3.4.4「付加価値と整合」: モデル全体では非有意・係数レベルで寄与、という誠実な接続へ書換。
- 結論 第四の知見: 「頑健な統計的有意性を示さなかった」に更新。
- 付録r版: O の Δr_oof を −0.017→−0.016 に訂正。

### 1.6 申し送り
- bootstrapは**レコード単位**の再標本。より厳密にするなら**話者単位クラスターbootstrap**へ
  上げる選択肢あり（p値が変わる）。宗田さん・山下先生の意向待ち。
- `three_stage_ridge.py`（r版・perm版の旧スクリプト）も `cv_ridge_r` は通常KFoldのまま。
  現行の図表パイプラインは diag/paired 経由なので影響は無いが、将来使う場合は要GroupKFold化。

---

## 2. 6/22〜25 の仕上げ作業（関連commit）

| commit | 内容 |
|--------|------|
| `8b3b169` | 参考文献の書誌誤り3件を実在文献に訂正（kita2007誌名/巻号、dindar2022→wehrle2024著者、meylan2014→brennan1996）。最良状態をmainに凍結 |
| `05e91b6` | README更新（3.4.3 R²化・教師間一致度の付録移設・参考文献訂正・BRM確定を反映） |
| `ac1fb4d` | 図4をr→R²版に復旧（一括生成がr版で上書きする先祖返りを修正）、表9(相関行列)の可読性改善 |
| `65b2f11` | 本文の強調太字 `\textbf` 36箇所を全除去（宗田さん指摘・共有前クリーンアップ） |
| `5f75138` | BRM要件md・glossaryを最新化(2026-06-25)、6/22議事録の出席者誤記とスケジュール記述を修正 |
| `c92772f` | glossary: IXカテゴリ改名を反映（相互行為構造系→連鎖組織系/Sequence-organization） |
| `6b0435c` | 【本ログ中核】3段階RidgeのCVをGroupKFoldに統一し本文を再整合 |

---

## 3. 現在地と次アクション

- 状態: 日本語版 `paper1_ja.pdf` は本文・図表・参考文献・CVが整合。mainに反映済み。
- レビュー: 山下先生・宗田さんがチェック中。宗田さんが約1週間でLaTeXリバイズ予定（最新版＝main の paper1_ja.tex で合意済み）。
- 次アクション:
  1. 宗田さんへ宿題回答（OOF連結・paired bootstrapの手続き／GroupKFold統一済みの旨）を返信。
  2. レビュー反映後、英語化 Phase 1（Declarations雛形・keywords・APA7th bib化）。
  3. BRM再現パッケージ（OSF＋GitHub、合成サンプルデータ同梱）の準備（別spec/別セッション推奨）。
