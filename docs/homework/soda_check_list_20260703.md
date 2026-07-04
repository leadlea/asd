# 宗田さんレビュー対応チェックリスト（paper1_ja_st.tex / 2026-07-03差し戻し版）

差し戻し版 `paper1_ja_st.tex` に埋め込まれた宗田さんのコメントの対応管理表。
- 差分パッチ: `docs/homework/soda_diff_20260703.patch`（`paper1_ja.tex` → `paper1_ja_st.tex`）
- [CHECK] = 福原が確認・加筆・修正する事項（要対応）
- [NOTE] = 宗田さんの編集意図メモ（原則そのまま維持、参考にする）
- 状態: ⬜未着手 / 🔧作業中 / ✅完了 / 💬全体相談待ち

## [CHECK] 要対応事項

カテゴリは `paper1_ja_st.tex` のセクション構成に基づく（方法／結果／考察／補足=Appendix）。
「理由・意思決定」列には、なぜその対応（または保留）にしたのかの根拠を簡潔に記す（宗田さん・山下先生が判断を追えるように）。未着手項目は `—`。

> 「理由・意思決定」列は横スクロール防止のためセル内改行（`<br>`）で複数行に分けて記載する（1行あたりを短く保ち列幅の膨張を防ぐ）。さらに詳しい修正箇所・検証は本ファイル下部の「作業ログ」を参照。

| # | 行 | カテゴリ | 内容（要約） | 状態 | 理由・意思決定（詳細は作業ログ） |
|---|-----|------|------|------|------|
| 1 | 155 | 方法・会話データ | レコード280想定に対しズレる理由の説明 | ⬜ | — |
| 2 | 157 | 方法・会話データ | 発話タイミング情報の出所・重要性・欠損の説明 | ⬜ | — |
| 3 | 167 | 方法・会話データ | 「66会話中2会話」の66会話とは何か | ⬜ | — |
| 4 | 175 | 方法・特徴量 | 削除変数含め合計18種になるか確認 | ✅ | 正：説明変数は**19種**<br>（Classical10＝PG8+FILL2／Novel9＝IX5+RESP3+PG_pause_variability1）<br>PGカテゴリ総数は沈黙変動性を含め9<br>「18」との差＝PGを古典的特徴量8種で捉えた場合の値<br>IX_topic_drift_meanはr=−1.00で除外済みの候補（19に非包含）<br>実装3本・定義表・本文L126・付録L459(21変数)と一致<br>本文L177/L181/L231を19基準に統一（数値不変） |
| 5 | 189 | 方法・特徴量 | 性別・年齢の相関分析の欠損補完を加筆 | ✅ | 実装確認：関連分析（性別U/年齢ρ）は特徴量ごとに`.dropna()`<br>＝pairwise deletion（補完なし）<br>回帰のfold内中央値補完とは別扱い<br>有効Nが特徴量ごとに異なりうる旨も2.2に明記 |
| 6 | 233 | 方法・回帰分析 | 相関1の変数を一方の指標に統一 | ✅ | 完全共線（r=−1.00）はIX_topic_drift_mean（=1−IX_lex_overlap_mean）のみ<br>IX_lex_overlap_meanに統一しtopic_driftを除外済み<br>実装3本と一致、2.4に統一方針を明示 |
| 7 | 234 | 方法・回帰分析 | 「除外された変数」の言及確認・説明or削除 | ✅ | EXCL3統制変数12個は本文他所で未言及・非説明変数（中間量/分母）<br>これらの量は特徴量の計算式（例「発話時間/総時間」「100文字あたり」）に内在し別途注記は不要<br>宗田さん方針に沿い**全削除**（概念文も残さない）<br>#6の共線性(IX_topic_drift_mean)一文と「19変数を用いる」結論は維持 |
| 8 | 243 | 方法・回帰分析 | 予測指標の説明を方法へ・Slack齟齬確認 | ✅ | **方法2.4記述はSlack①②と一致**（OOF連結R²/RMSE＋GroupKFold／paired bootstrap詳細）<br>**別の齟齬を発見・修正**: §3.4の3段階Ridge結果本文が旧数値で表・Slackと矛盾していた<br>実データTSVを正に書き直し（Stage2→3上昇はO/C/N・低下E/A、名目有意はNのみ p_boot=0.044/Wilcoxon非有意、旧「E有意悪化p=0.030」は誤りで削除）<br>Stage1→2も旧値を修正。RMSE主指標化（[NOTE]239）は保留 |
| 9 | 249 | 方法・回帰分析 | Bootstrap検定の記述を加筆 | ✅ | three_stage_paired_test.pyを正に2.4へ詳細加筆<br>d_i=SE²(2)−SE²(3)、5000回paired bootstrap（レコード復元抽出）<br>95%CI(2.5/97.5%ile)・両側p=min(1,2min(P≤0,P≥0))＋(k+1)/(B+1)平滑化<br>Wilcoxon(両側)・ΔRMSE併記<br>単位「被験者→レコード」を本文L242・表L456で統一 |
| 10 | 314 | 結果・記述統計量 | 特徴量の英/日表記を統一 | ✅ | 正式参照＝コード識別子に統一<br>定義（方法＋定義表）は`code（日本語名）`順に統一<br>導入の概念語・メタデータ節の説明述語は可読性優先で維持<br>数値・意味は不変 |
| 11 | 315 | 結果・記述統計量 | PG系分布の主張を具体値の根拠付きで修正 | ⬜ | — |
| 12 | 374 | 結果・相関分析 | 多重共線性/相関1の記述削除検討 | ⬜ | — |
| 13 | 406 | 結果・属性情報との関連 | 表Feature列を2行化・添字削除 | ✅ | Feature列をGender/Age見出しで2行グループ化<br>添字（gender/Spearman等）を簡素化<br>生成元gen_tab_metadata_testsも修正し再生成（数値不変） |
| 14 | 505 | 結果・性格特性との関連 | 本文と表で数字が異なる点を確認 | ✅ | 本文値が集計元TSV（ensemble_summary.tsv）・表と不一致だった<br>集計元を正として本文を修正（A0.465→0.449 等）<br>順位A>C>O>N>Eは不変 |
| 15 | 506 | 結果・性格特性との関連 | 表r/p添字を斜体→ブロック体 | ✅ | r/p右下の添字はラベル（obs, corrected）<br>正書法としてローマン体（`\mathrm`）に<br>生成元も修正 |
| 16 | 574 | 結果・予測に重要な特徴量 | 表はチェックマーク不要（太字のみ） | ✅ | Sig.チェックマーク列を2表から削除<br>有意はキャプション通り太字で表示<br>生成元も修正、数値不変 |
| 17 | 606 | 結果・予測に重要な特徴量 | 図の凡例位置調整 | ✅ | fig_bootstrap_varianceの凡例がCIバーと重なっていた<br>凡例を軸外（右・中央）へ移動、bbox_inches="tight"でクリップ回避<br>生成元も修正し再生成 |
| 18 | 641 | 考察 | 考察を一般的な構造に修正 | ⬜ | — |
| 19 | 992 | 補足・付録A(会話データ) | 「推定が不安定」表現の補足・修正 | ⬜ | — |
| 20 | 1010 | 補足・付録A(会話データ) | 当該セクション説明の要否 | ⬜ | — |
| 21 | 1049 | 補足・LLM仮想Big5 | 各モデルの記述粒度を統一 | ✅ | Wright2026（PMC12974486）準拠の表記に統一<br>「ベンダー名+公式識別子+公開区分」でパラメータ数併記を廃止<br>本文モデルリスト・全図ラベル・「Sonnet4」表記を統一<br>生成元も修正・再生成 |
| 22 | 1232 | 補足・感度分析 | 補足として提示するなら結果も示す | ⬜ | — |
| 23 | 1237 | 補足・感度分析 | 「特徴量サブセットの感度」記述の適否 | ⬜ | — |
| 24 | 1241 | 補足・感度分析 | 3段階リッジとの差異を明確化 | ⬜ | — |
| 25 | 1311 | 補足・LLMモデル間の差異 | Big5次元の呼称を統一 | ✅ | 5次元一律で英語スキームに統一<br>初出フルネーム＋略字定義→以降は略字(O/C/E/A/N)<br>日本語グロス`X（Letter:日本語）`を全削除<br>定義リスト・図キャプションのO/C/E/A/Nは維持（数値不変） |
| 26 | 1331 | 補足・LLMモデル間の差異 | 本文値と図の値の不一致を確認 | ✅ | 本文0.699は正（集計元TSV C上三角平均0.6987→0.699）<br>掲載図が旧版で0.69に切り捨て表示だった<br>現行スクリプトで図を再生成し0.699表示に統一 |
| 27 | 1350 | 補足・LLMモデル間の差異 | C因子の粒度／頑健性主張の方針 | 💬 | 全体相談待ち<br>全次元掲載か頑健性主張かはMTGで決定<br>原稿修正は保留 |
| 28 | 1368 | 補足・LLMモデル間の差異 | 図 fig:perm_C の削除検討 | ⬜ | — |
| 29 | 1402 | 補足・LLMモデル間の差異(考察) | 考察でC因子を過度に強調しない | ⬜ | — |

## 全体相談事項（原稿修正は保留、MTGで議論）

| 論点 | 宗田さんの意向 | 福原の一次見解 |
|------|------|------|
| 3段階リッジの掲載可否 | 残して良いのでは（NOTE 812, 1167, 1468 で判断依存） | 残す方向に一票 |
| C次元のみ報告→全次元掲載 | 全次元掲載が素直（NOTE 556, CHECK 1350/1402） | 全次元で揃える方向 |
| ベースライン/Dose-Response の本文or補足 | 未定 | 次MTGで決定 |

## [NOTE] 一覧（種別つき）

宗田さんが `paper1_ja_st.tex` に残した[NOTE]。種別で福原の対応要否を区別する。

- 📢 **注意喚起/報告** = 宗田さんが実施済みの編集説明、または一般的な注意。福原の追加対応は原則不要（構成はそのまま維持）。
- 🔧 **要対応（福原）** = 福原の対応・判断が必要（削除・加筆・移動、または保留/全体相談を含む）。

> 種別は福原による一次解釈。曖昧なものは宗田さんに意図を確認する。集計: 📢 19件 / 🔧 17件（うち💬全体相談=556/812）。

| 行 | カテゴリ | 種別 | 内容（要約） |
|-----|------|------|------|
| 9 | 全体（メタ） | 📢 | [NOTE]と[CHECK]の記法の説明（宗田さんの運用メモ） |
| 156 | 方法・会話データ | 🔧 | 交差検証の話はデータセット節から交差検証節へ移すのが望ましい（重複・冗長） |
| 161 | 方法・会話データ | 🔧 | 「レコード」の定義が複数箇所で揺れ。混乱防止のため通し読みで統一 |
| 173 | 方法・特徴量 | 📢 | 「新規/提案」枠を撤廃しカテゴリのみに再構成（各カテゴリ内で新旧に言及） |
| 187 | 方法・特徴量 | 📢 | 欠損値は独立節を廃し「特徴量」節冒頭へ移動 |
| 188 | 方法・特徴量 | 📢 | 統制変数を回帰分析節へ移動。見出しと内容の一致に注意 |
| 241 | 方法・回帰分析 | 📢 | CVの内容は重複が多く補足向きでないため本文へ戻した |
| 244 | 方法・回帰分析 | 🔧 | 主指標はr²よりRMSEが妥当との意見。主張方針は全体相談のため一旦保留 |
| 267 | 方法・置換検定 | 📢 | Holm法の一般的説明は削除（コメントアウト） |
| 272 | 方法・Bootstrap | 🔧 | Bootstrap記述を一箇所に集約する可能性、一旦保留 |
| 279 | 方法・仮想Big5 | 📢 | Big5スコア推定は極力補足資料へ移動（6月MTG方針） |
| 280 | 方法・仮想Big5 | 📢 | 「仮想教師」→「仮想Big5スコア」等へ改称、「アンサンブル」語を排除 |
| 313 | 結果・記述統計量 | 📢 | 歪度未提示で「正の歪度」は違和感のため調整済み |
| 396 | 結果・属性情報との関連 | 📢 | 重複情報・方法に関する情報は結果に極力書かない（一般方針） |
| 405 | 結果・属性情報との関連 | ✅ | 表の有意表示を太字→アスタリスク統一（#13と同じ表なので同時対応済み） |
| 439 | 結果・属性情報との関連 | 🔧 | 「表面的妥当性」の用法に違和感、削除 |
| 444 | 結果・性格特性との関連 | 🔧 | 冒頭のメソッド説明は最低限に。表面的/構成概念妥当性は削除でOK |
| 445 | 結果・性格特性との関連 | 🔧 | この節の結果は全体で先に相談したいのでほぼ未着手（相談要） |
| 502 | 結果・性格特性との関連 | 📢 | 考察寄り＋脈絡のない記載を削除済み |
| 542 | 結果・性格特性との関連 | 🔧 | 短い論文に導入向け記載は不要（削除確認） |
| 555 | 結果・予測に重要な特徴量 | 📢 | 冗長な説明を大きく削除済み |
| 556 | 結果・予測に重要な特徴量 | 🔧 | Cのみ選択の根拠が弱い。全次元掲載を提案、全体相談のため保留（💬） |
| 607 | 結果・予測に重要な特徴量 | 🔧 | 「負の寄与」等は直前の数字で自明のため削除で良い |
| 631 | 結果・予測に重要な特徴量 | 🔧 | 考察寄りの内容は考察へ移す。結果は事実を淡々と |
| 812 | 考察 | 🔧 | 当節は結論中心の簡易記述に。3段階リッジ掲載可否に依存（保留・💬） |
| 989 | 補足・付録A(会話データ) | 📢 | 「話者の重複と性別内訳」は本文と重複のため本文へ移動済み |
| 1039 | 補足・LLM仮想Big5 | 📢 | 重複・読者に不要な記載を修正済み |
| 1055 | 補足・LLM仮想Big5 | 📢 | 意義的な記載を短縮（意義は背景/考察へ） |
| 1167 | 補足・3段階Ridge(r版) | 🔧 | 相関係数の結果は本文表に合流が良い。3段階リッジ掲載決定後に調整（後回し） |
| 1190 | 補足・3段階Ridge(r版) | 📢 | 「Bootstrap安定性分析の詳細」は重複のため削除済み |
| 1240 | 補足・感度分析 | 📢 | 交絡統制の内容を「特徴量サブセットの感度」へ移動済み |
| 1259 | 補足・LLMモデル間の差異 | 🔧 | 分野で当然の情報は不要（削除確認） |
| 1341 | 補足・LLMモデル間の差異 | 📢 | 頑健性の考察を回帰分析の考察へ合流・移動済み |
| 1347 | 補足・LLMモデル間の差異 | 📢 | LLM個別結果を感度分析の節として構造整理済み |
| 1349 | 補足・LLMモデル間の差異 | 🔧 | 本文3段階リッジに揃え相関でなくRMSE評価が良い（3段階リッジ扱い依存） |
| 1468 | 補足・ベースライン検証 | 🔧 | メイン指標(RMSE)に揃えるのが良い。3段階リッジの扱い未定のため後回し可 |

## 作業ログ 2026-07-03（数値整合・書式）

方針依存しない機械的な[CHECK]から着手。実データ（集計元）を正として本文・図表を突き合わせた。

### #26 教師間一致度 図の値不一致（本文0.699 vs 図0.69）
- 正: `docs/homework/teacher_agreement_big5.md` / TSV `docs/homework/assets/teacher_corr_C.tsv`（C上三角平均=0.6987→0.699）。本文は正しかった。
- 原因: 掲載図 `reports/paper_figs_v2/fig_teacher_heatmap.png`（6/24生成）が旧版で切り捨て表示(0.69)になっていた。現行スクリプトは`.3f`。
- 対応: `scripts/paper_figs/gen_paper_figs_v2.py::gen_fig_teacher_heatmap` で図を再生成し差し替え（mean r = 0.699 表示を確認）。

### #14 置換検定 本文の相関値が誤り
- 正: 集計元 `artifacts/analysis/results/ensemble_perm_v4/ensemble_summary.tsv`。表 `reports/paper_figs_v2/tab_ensemble_permutation.tex` はこれと一致していた。
- 本文(誤)→正: A 0.465→0.449 / C 0.447→0.432 / O 0.360→0.410 / N 0.309→0.317 / E 0.217→0.234（p, p_corrected も集計元に合わせて修正）。順位 A>C>O>N>E は不変。
- 生成元スクリプト: `scripts/analysis/ensemble_permutation.py`（出力 `ensemble_perm_v4/`）。

### #15・#506 表の添字を斜体→ローマン体
- `tab_ensemble_permutation.tex` の `$r_{obs}$ $p_{corrected}$` を `$r_{\mathrm{obs}}$ $p_{\mathrm{corrected}}$` に。
- 恒久修正: 生成元 `scripts/paper_figs/gen_paper_figs_v2.py::gen_tab_ensemble_permutation` も同様に修正（再生成しても維持される）。

### 検証
- `uplatex paper1_ja_st.tex` がexit 0でコンパイル成功（45ページ）。ビルド一時ファイルは削除済み。

### 図表 ↔ 解析ファイル 対応表（着手分）
| 原稿の図表 | 生成スクリプト | 集計元データ |
|---|---|---|
| fig_teacher_heatmap.png | gen_paper_figs_v2.py::gen_fig_teacher_heatmap | docs/homework/assets/teacher_corr_*.tsv |
| tab_ensemble_permutation.tex | gen_paper_figs_v2.py::gen_tab_ensemble_permutation | artifacts/analysis/results/ensemble_perm_v4/ensemble_summary.tsv |

### #13・[NOTE]405 属性情報の表（tab_metadata_tests）の体裁修正
- #13: Feature列を2行グループ見出しに変更。`\multicolumn{2}{c}{Gender}`（U, p）/`\multicolumn{2}{c}{Age}`（ρ, p）＋`\cmidrule(lr){2-3}{4-5}`。添字（`p_{gender}` / `\rho_{Spearman}` / `p_{Spearman}`）を削除し `p` / `\rho` / `p` に。
- [NOTE]405: 同じ表なので同時対応。有意セルの `\textbf{}` を除去し、有意はp値末尾の `*` のみで表示（キャプションの `* p<0.05` と整合）。数値は不変。
- 恒久修正: 生成元 `gen_paper_figs_v2.py::gen_tab_metadata_tests` を修正し、`tab_metadata_tests.tex` を再生成（再生成しても維持）。
- 検証: `uplatex paper1_ja_st.tex` exit 0（45ページ、`\cmidrule`等エラーなし）。

### #16 置換検定/Bootstrap表の「Sig.」列（チェックマーク）を削除
- 対象2表: `tab_permutation_coef.tex`（置換検定C）/ `tab_bootstrap_variance.tex`（Bootstrap SD/CI）。
- `\checkmark` の Sig. 列を削除。有意は太字で表示（キャプションの「太字は…」と整合、追加変更なし）。数値は不変。
- ついでに `tab_permutation_coef` の添字 `$\beta_{obs}$` を本文の `$\beta_{\text{obs}}$` に合わせ `$\beta_{\mathrm{obs}}$` にローマン体化（#15/#506と同方針）。
- 恒久修正: 生成元 `gen_tab_permutation_coef` / `gen_tab_bootstrap_variance` を修正し両表を再生成。
- 検証: `uplatex paper1_ja_st.tex` exit 0（45ページ）。

### #21 LLMモデル記述粒度の統一 — 出典調査と方針決定（未実装）
- 論点: 本文L1043-1048のモデルリストが粒度バラバラ（Qwen/GPT-OSSはパラメータ数併記、Sonnet/DeepSeekは無し）。Sonnetは非公開でパラメータ数を揃えられない、という制約があった。
- 意思決定の根拠: モデル選定の出典 Wright ら2026（`\cite{wright2026}`, DOI 10.1038/s41562-025-02389-x）の表記法に合わせる方針を採用。オープンアクセス版 PMC12974486 のMethodsで確認したところ、Wrightは7モデル（OpenAI GPT-4.1/GPT-4.1-Mini, Anthropic Claude-3.7-Sonnet, Google Gemini-2.5-Flash-Thinking, xAI Grok-3-Beta, Meta Llama-4-Maverick, Alibaba Qwen3-235B）を「ベンダー名+公式識別子」で記載し、パラメータ数ではなく「オープンソース/プロプライエタリ」で区別していた。
- 重要な留意: 使用モデルの直接一致は Qwen3-235B のみ。他3モデル（Claude Sonnet 4／DeepSeek-V3／GPT-OSS-120B）はWright未使用。よって「モデル名のコピー」は不可、流用するのは**表記の作法のみ**。
- 決定した統一形（本文）: `Anthropic Claude Sonnet 4（プロプライエタリ）` / `Alibaba Qwen3-235B（オープンウェイト）` / `DeepSeek DeepSeek-V3（オープンウェイト）` / `OpenAI GPT-OSS-120B（オープンウェイト）`。パラメータ数の不揃い併記を廃止。
- 依存関係: 図のモデル名ラベル（#26の fig_teacher_heatmap ほか teacher_corr_matrix / ensemble_permutation / permutation_C_bar）は本統一形に合わせて短縮ラベルで再描画が必要。`gen_paper_figs_v2.py` のラベル定義（`TEACHER_DISPLAY` と `fig_teacher_corr_matrix` 独自ラベル）を一本化して一括再生成する。
- 状態: 表記統一形は福原の確認済み。実装（本文修正＋全図再生成＋uplatex検証）は次アクション。

### #21 実装完了（2026-07-03）
- 本文L1043-1048のモデルリストをWright準拠に統一: `Anthropic Claude Sonnet 4（プロプライエタリ）` / `Alibaba Qwen3-235B（オープンウェイト）` / `DeepSeek DeepSeek-V3（オープンウェイト）` / `OpenAI GPT-OSS-120B（オープンウェイト）`。粒度の根拠を1文で明記し、解決済みの[CHECK]コメントを削除。
- 本文中の全「Sonnet4」表記（散文＋IPIP例示表、計15箇所）を「Claude Sonnet 4」に統一。他3モデルは既に図表と一致。
- 図ラベルを一本化: `gen_paper_figs_v2.py` の `TEACHER_DISPLAY["sonnet"]` を `Claude Sonnet 4` に変更（fig_permutation_C_bar / fig_teacher_heatmap / tab_permutation_all に波及）。`fig_teacher_corr_matrix` の独自ラベルも両軸で同一の統一ラベル（2行折返し）に修正（従来はx軸がファミリ名のみで粒度不一致だった）。
- 再生成した成果物: fig_permutation_C_bar.png / fig_teacher_heatmap.png / fig_teacher_corr_matrix.png / tab_permutation_all.tex。
- 検証: `uplatex paper1_ja_st.tex` exit 0（45ページ）。leftover「Sonnet4」0件、二重接頭辞なしを確認。一時ファイル削除済み。
- 図表↔解析ファイル対応表（追加分）:

| 原稿の図表 | 生成スクリプト | 集計元データ |
|---|---|---|
| fig_permutation_C_bar.png | gen_paper_figs_v2.py::gen_fig_permutation_C_bar | artifacts/analysis/results/cejc_home2_hq1_Conly_*_controls_excluded |
| fig_teacher_corr_matrix.png | gen_paper_figs_v2.py::gen_fig_teacher_corr_matrix | docs/homework/assets/teacher_corr_*.tsv |
| tab_permutation_all.tex | gen_paper_figs_v2.py::gen_tab_permutation_all | artifacts/analysis/results/cejc_home2_hq1_*only_*_controls_excluded |

### #17 図の凡例位置調整（fig_bootstrap_variance）
- 対象: `fig_bootstrap_variance.png`（本文L619で使用、フォレストプロット）。凡例（CI excludes zero / CI includes zero）がプロット領域内でCIバーと重なっていた。
- 対応: 生成元 `gen_paper_figs_v2.py::gen_fig_bootstrap_variance` の凡例を `loc="lower right"`（軸内）から `loc="center left", bbox_to_anchor=(1.02, 0.5)`（軸の外・右側中央）に変更。`savefig(bbox_inches="tight")` により軸外凡例もクリップされない。データ・数値は不変。
- 隣接する解決済み[CHECK]コメント（L607）を削除。同位置の[NOTE]（「負の寄与」等の削除提案）は別項目のため保持。
- 再生成物: fig_bootstrap_variance.png。検証: `uplatex paper1_ja_st.tex` exit 0（45ページ）。

### #25 Big5次元名の統一（5次元一律・英語スキーム）
- 方針（山下先生含め相談済みの推奨案）: 英語スキームに統一。「初出でフルネーム＋略字定義 → 以降は略字(O/C/E/A/N)」。定義リスト(L282, L1033)・図キャプションの `O,C,E,A,N` は略字定義として維持。
- 対象は宗田さんが例に挙げたC限定ではなく5次元すべて（本人意図＝Big5全体の一貫化）。
- 実施内容:
  - 日本語グロス `英語名（Letter: 日本語名）` を全削除 → `英語名（Letter）`（結果L511-517ブロック、Abstract L51、考察 L732、結論 L949、IPIP例 L1066-1070、付録 L1380/1386/1391/1394）。
  - 標準日本語の単独使用を略字へ: `性格的側面（誠実性に関連する…）`→`（Cに関連する…）`、`誠実性の高い話者`（2箇所）→`Cの高い話者`。
  - `Agreeableness（A: $r=0.465$）`→`Agreeableness（A，$r=0.465$）`（結果ブロックの `O，/N，` と体裁統一）。
  - 解決済みの[CHECK]コメント（L1311）を削除。宗田さんの[NOTE]引用（`% >` L542、誠実性（C）を含む）はコメントのため保持。
- 留意: 「統制性」「C次元」は本文に存在せず、宗田さんコメント内の一般例だった。実際の食い違いは「英語フルネーム ⇄ 略字 ⇄ 日本語名」の混在で、日本語名の排除と英語スキーム一本化で解消。
- 検証: 非コメント行に日本語次元名の残存ゼロを確認。`uplatex paper1_ja_st.tex` exit 0（45ページ）。一時ファイル削除済み。

### #10 特徴量の英/日表記の統一（コード識別子を正式名に）
- 方針（推奨案、承認済み）: 正式参照＝コード識別子（例 PG_speech_ratio）。定義（方法＋定義表）は `code（日本語名）` に統一。導入・背景の概念語（発話率・フィラー等、定義前の概念説明）は日本語のまま維持。コード主導で参照した上での日本語の説明述語（メタデータ節「…は女性の方が語彙重なりが高い」等）は可読性優先で維持。
- 実施内容:
  - 方法セクションの定義順 `日本語名（code）`→`code（日本語名）` に反転: L194 PG_speech_ratio、L196 PG_overlap_rate、L204 IX_oirmarker_rate（同時にmalformedな括弧を修正）、L206 IX_yesno_rate/IX_yesno_after_question_rate、L208 IX_lex_overlap_mean、L183 PG_pause_variability。
  - 個別特徴量の日本語主導参照をコード主導へ: L335 `RESP系3変数（RESP_NE_AIZUCHI_RATE, RESP_NE_ENTROPY, RESP_YO_ENTROPY）`、L647 `RESP_NE_AIZUCHI_RATE（$SD=0.229$）`、L962 `RESP_NE_ENTROPY（「ね」直後応答多様性）`、結果・結論の `発話率（PG_speech_ratio）`→`PG_speech_ratio（発話率）`（2箇所）。
  - 維持: カテゴリ群記述（沈黙系指標／FILL系指標／OIR関連指標 等の `群名（code list）`）、導入の概念語、メタデータ節のコード主導＋日本語述語。
  - 解決済み[CHECK]コメント（旧L314）を削除。
- 検証: 非コメント行の「個別特徴量の日本語主導参照」の残存ゼロを確認（残りは群記述のみ）。`uplatex paper1_ja_st.tex` exit 0（45ページ）。一時ファイル削除済み。

### #4 特徴量の合計種類数の確認（18か19か）— 19に統一

- 論点（宗田さんL175）: 「多重共線性で削除した変数があるので合計18種になるか確認」。
- 実データ（正）: 解析で使用する説明変数は **19種**。内訳は Classical 10（PG 8 + FILL 2）+ Novel 9（IX 5 + RESP 3 + PG_pause_variability 1）。PGカテゴリの総数は沈黙変動性(PG_pause_variability)を含め **9**（Classical 8 + Novel 1）。
- 出典の突き合わせ（全て19基準で一致）:
  - `scripts/analysis/three_stage_ridge.py` / `baseline_vs_extended.py`: `ALL_FEATURES = CLASSICAL(10) + NOVEL(9) = 19`。Stage 3 = 2(人口統計) + 19 = 21変数（docstring明記）。
  - `scripts/paper_figs/feature_definitions.py`: `get_explanatory_features()` = 19（`IX_topic_drift_mean` は `is_control=True` の候補で19に含まれない）。
  - 表 `tab_feature_definitions.tex`: キャプション「19特徴量」・本体19行。
  - 本文 導入 L126「Classical 10個 + Novel 9個 = 計19」／付録 3段階Ridge表 L459「Stage 3: +Novel（21変数）」。
- 「18」との差の由来: PGカテゴリを古典的特徴量の8種で捉えると総数は18となるが、カテゴリ総数としては新規の PG_pause_variability を含め PG=9・総計19となる。`IX_topic_drift_mean` は `IX_lex_overlap_mean` と完全共線（$r=-1.00$）で除外済みだが、これは元々19に含まれない候補のため「19−1=18」にもならない。原稿側の表記を19基準に統一して齟齬を解消した。
- 修正（方法2.2の食い違い3箇所を19基準に統一。数値・解析結果は不変）:
  - L177: 「18の特徴量を構築した」→「19の特徴量を構築した」＋ `IX_topic_drift_mean` 除外（完全共線）で19変数を対象とする旨を1文追記（2.4節へ参照）。解決済み[CHECK]コメント削除。
  - L181: カテゴリ分類「タイミング系（PG，8変数）」→「9変数」（Cat.列基準でPG=9）。同文の誤字「）系の4つ」→「）の4つ」も修正。
  - L231: Stage 3「全20変数」→「全21変数」（2+19。付録表L459と一致）。
- 留意: L183「古典的特徴量は…発話タイミング系8変数（PG）」はClass.列（Classical）基準の記述で8が正。カテゴリ総数(L181, 9)と役割が異なるため変更しない。
- 検証: `uplatex paper1_ja_st.tex` exit 0（45ページ）。一時ファイル削除済み。

| 原稿の記述 | 生成/定義元 | 正 |
|---|---|---|
| 特徴量総数（19）・Cat.列PG=9 | feature_definitions.py / tab_feature_definitions.tex | 19（PG 9/FILL 2/IX 5/RESP 3） |
| Stage 3 変数数（21） | three_stage_ridge.py / fig:three_stage 表(L459) | 2+19=21 |

### #5–#9 方法セクション系（B群）— 実装を正として整合・加筆（2026-07-03）

方法（2.2特徴量・2.4回帰）の[CHECK]を、解析スクリプトを一次ソースとして突き合わせて解消。数値・解析結果は不変。

- **#5 相関分析の欠損処理**: 実装確認 → 性別(Mann-Whitney U)・年齢(Spearman ρ)の関連分析は各特徴量ごとの `.dropna()`（pairwise deletion／利用可能ケース分析）で補完なし。回帰分析（fold内中央値補完）との違いを2.2の欠損値記述に明記。有効標本サイズが特徴量ごとに異なりうる旨も追記。
- **#6 完全共線変数の統一**: 完全共線（$r=-1.00$）は IX_topic_drift_mean（定義上 $1-$IX_lex_overlap_mean）のみ。既に lex_overlap に統一・topic_drift 除外済み。2.4に統一方針を1文で明示（#4の2.2記述と二重化せず役割分担: 2.2=事実/カウント、2.4=分析上の理由）。
- **#7 除外変数（EXCL3）の扱い**: EXCL3統制変数12個は本文他所で未言及・実解析でも説明変数でない中間量。これらの量は特徴量の計算式（例「発話時間/総時間」「100文字あたり」）に既に内在するため別途注記は不要と判断し、**該当一文を全削除**（当初の概念文への置換から方針変更）。#6の共線性一文と「19変数を用いる」結論のみ残す。
- **#8 予測指標の方法節移設・整合**: r/R²/RMSE は方法2.4に移設済み。集約は表6=OOF連結（three_stage_metrics_diag.py で確認）で本文と一致、散布図とも整合。記述正確につき本文改変なし・[CHECK]のみ削除。RMSEを主指標にするかは[NOTE]239の通り全体相談＝保留（NOTE維持）。
- **#9 Bootstrap検定の加筆＋単位修正**: three_stage_paired_test.py を正として詳細化。手順=レコード単位OOF二乗誤差差 $d_i$ → 5000回paired bootstrap（レコード復元抽出, seed固定）→ 95%CI(2.5/97.5%ile)・両側$p=\min(1,2\min(P_{\le0},P_{\ge0}))$＋$(k+1)/(B+1)$平滑化 → Wilcoxon(両側)・$\Delta$RMSE併記。**単位の誤り「被験者→レコード」を本文(L242)と表キャプション(L456)で統一**（誤差/リサンプル単位はレコード、CV分割のみ subject-wise GroupKFold(cejc_person_id)）。

### 検証（#4–#9 まとめ）
- `uplatex paper1_ja_st.tex` exit 0（46ページ。#9加筆で+1ページ）。一時ファイル削除済み。
- 図表↔解析ファイル対応（B群 追加分）:

| 原稿の記述 | 生成/定義元 | 集計元 |
|---|---|---|
| 表\ref{tab:metadata_tests}（性別U/年齢ρ・pairwise） | gen_paper_figs_v2.py::gen_tab_metadata_tests | features_min + cejc_speaker_metadata.tsv |
| 表6 R²/RMSE（OOF連結） | three_stage_metrics_diag.py | three_stage_metrics_{teacher}.tsv |
| Stage2→3 paired bootstrap（$p_{boot}$） | three_stage_paired_test.py | three_stage_paired_test_{teacher}.tsv |

### #8 追補: Slack突き合わせで3段階Ridge結果本文の旧数値を修正（2026-07-03）

宗田さんから共有されたSlack（6/26、CVをsubject-wise GroupKFoldに統一し図4・表6・数値を更新した旨）と本文を突き合わせ。

- **方法2.4は齟齬なし**: ①OOF連結（全fold予測を連結しR²/RMSEを1回算出、R²=1−SS_res/SS_tot）②paired bootstrap（d_i=SE2−SE3、5000回レコード復元抽出、95%CI・両側p=2·min(P≤0,P≥0)＋(k+1)/(B+1)平滑化、Wilcoxon、ΔRMSE）とも本文記述と一致。
- **発見した齟齬**: §3.4の3段階Ridge**結果本文**が旧計算のままで、**表`tab:three_stage`・図・Slack（いずれも現行データ）と矛盾**していた（宗田さんが警告した「本文とテーブルで数字が異なる」に該当）。表・図は現行データで正しかった。
- 実データ `three_stage_metrics_ensemble.tsv` / `three_stage_paired_test_ensemble.tsv` を正として結果本文を修正:

| 項目 | 旧本文（誤） | 修正後＝表・実データ・Slack（正） |
|---|---|---|
| Stage2→3 上昇次元 | 4次元 O・C・A・N | 3次元 **O・C・N**（E・Aは低下） |
| A の増分 | +0.031（上昇） | **−0.014（低下）** |
| N の増分 | +0.040 | **+0.069** |
| 有意性 | 「4次元非有意」「E有意悪化 p=0.030」 | **名目有意はNのみ p_boot=0.044（Wilcoxon p=0.19で非頑健）**、E は p_boot=0.10で非有意（悪化は有意でない） |
| Stage1→2 | O 0.064→0.193(+0.129), C +0.018 等 | O 0.037→0.144(+0.107), C +0.056, E +0.115 等 |

- 立て付けはSlack通り「Novelは大部分の次元で予測を劣化させないが、モデル全体の増分としては頑健な改善に至らず」に統一（係数レベルの寄与は考察側、[NOTE]方針で結果からは除外）。
- 考察・結論に同種の旧数値・旧主張（E有意悪化/過学習）は残存なしを確認。
- 検証: `uplatex paper1_ja_st.tex` exit 0（45ページ）。一時ファイル削除済み。
