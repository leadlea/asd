# ADR-0012: 3.1の変数数を2.2（正）・図1・記述統計表に同期

- 状態: Accepted
- 日付: 2026-06-22
- 決定者: 福原玄（NCNP共同研究・筆頭）
- 関連: `paper1_ja.tex`（2.2/3.1）, `scripts/paper_figs/feature_definitions.py`, `scripts/paper_figs/gen_paper_figs_v2.py`, `reports/paper_figs_v2/tab_descriptive_stats_full.tex`, ADR-0011

## コンテキスト

3.1（記述統計）でPGを「タイミング系7変数」、IXを「相互行為系6変数」と記載していたが、2.2（方法）・図1生成定義・記述統計表と不一致だった。

### 正しい構成（2.2・図1・表で一致）

- PG: タイミング系8変数（Classical: speech_ratio, pause_mean/p50/p90, resp_gap_mean/p50/p90, overlap_rate）＋ PG_pause_variability（Novel, 1）→ PGパネルは9本。
- FILL: 2 / IX: 5（oirmarker_rate, oirmarker_after_question_rate, yesno_rate, yesno_after_question_rate, lex_overlap_mean）/ RESP: 3。合計19。

## 狂った原因（根本原因）

3.1の変数数が**過去の特徴量セットのまま更新されていなかった**ためのドリフト。3点の変更が3.1へ反映されていなかった。

1. `PG_overlap_rate` を統制変数(CTRL)→説明変数(Classical)へ移動（feature_definitions.py の「PG_overlap_rate moved to explanatory」）。PGタイミングが 7→8 に増加。3.1は「7」のまま。
2. `IX_topic_drift_mean` を説明変数から除外（IX_lex_overlap_meanと完全共線 r=−1.00）。IXが 6→5 に減少。3.1は「6」のまま。
3. `PG_pause_variability`（Novel）を追加し図1のPGパネルに表示（9本目）。3.1の概況文が未反映。

2.2・図1生成定義（gen_paper_figs_v2.py の19特徴量リスト）・記述統計表は整合しており、**3.1本文のカウントのみが取り残されていた**。

## 決定（2.2を正として3.1を同期）

| 3.1 箇所 | 旧 | 新 |
|------|----|----|
| PG | タイミング系7変数 | タイミング系8変数および沈黙変動性1変数 |
| IX | 相互行為系6変数 | 相互行為系5変数 |

## 検証

- 古いカウント（タイミング系7／相互行為系6）の残存: 0。
- uplatex 2パス＋dvipdfmx: 正常、47ページ、未解決の参照・引用なし。

## 申し送り（要確認・未対応）

- 3.1（524行）に除外変数 `IX_topic_drift_mean（M=0.958）` を引用する一文が残る。IXを5変数に同期した一方、補数関係（鏡像）の説明として除外変数を挙げており、記述統計表には当該行がない。説明として残すか、注記化/削除するか次ターンで判断推奨。

## 次の1手

最新PDFで3.1のカウントと図1パネル本数の一致を確認。上記topic_drift言及の扱いを指示いただきたい。
