# 山下先生フィードバック対応ログ（v3, 2026-03）

山下先生（NCNP）から受けた論文（paper1_ja.tex v2）に対する11項目のフィードバックへの対応記録。

## 対応状況一覧

| # | フィードバック | 状態 | 対応内容 | Before → After |
|---|---|:---:|---|---|
| 1 | スライドにMethodsを含める | ✅ | Methods 2枚（データと手法 + 特徴量分類テーブル）を冒頭に追加 | 6枚（Resultsのみ）→ **8枚（Methods 2 + Results 6）** |
| 2 | 既存研究ベース vs 新規提案を明示 | ✅ | feature_definitions.pyにclassificationフィールド追加、Method節・テーブル・スライドに反映 | 18特徴量を一括記述 → **Classical 9個 / Novel 9個の2群に分類** |
| 3 | 図の可読性改善 | ✅ | 全図表のフォントサイズ引き上げ（軸≥12pt, 凡例≥10pt, アノテーション≥9pt, 相関行列≥7pt）、DPI=300 | フォント小・DPI=200 → **閾値準拠・DPI=300** |
| 4 | Big5全次元を本文で報告 | ✅ | Results 3.4.1でアンサンブル全5次元、3.4.2で個別教師全次元を本文報告。A/E/N/OをAppendixから本文に移動 | Cのみ本文、AENO Appendix → **全5次元を本文で報告、Cを主結果として強調** |
| 5 | AENOは「予測できてない」ではない | ✅ | 「教師モデル依存性がある」に表現統一。GPT-OSS-120B全5次元有意を明示。各次元の有意教師数を報告 | 「予測できていない」→ **「教師モデル依存性がある」（GPT-OSS-120Bは全次元有意）** |
| 6 | アンサンブルでAENOの有意は消えるか | ✅ | ensemble_permutation.py新規作成。4教師item-level平均で5次元permutation test実行 | 個別教師4本の結果一覧 → **アンサンブル主結果: O,C,A,N有意（4/5次元）、Eのみ非有意** |
| 7 | 教師間一致度はサプリメンタル的 | ✅ | Results 3.4節を再構成: アンサンブル→個別教師→ベースライン比較→Bootstrap→教師間一致度（末尾） | Permutation→Teacher Agreement→Bootstrap → **アンサンブル→Bootstrap→Teacher Agreement（サプリメンタル化）** |
| 8 | ベースライン vs 拡張モデル比較 | ✅ | baseline_vs_extended.py新規作成。全5次元×4教師（20パターン）で実行、Δr報告、図表生成 | 比較なし → **Classical 9個 vs 全18個のΔrを全次元で定量報告** |
| 9 | 交絡対策 | ✅ | confound_analysis.py新規作成。18特徴量のみ vs 18特徴量+性別+年齢の2条件で全20パターン実行 | 交絡未検討 → **Cは3/4教師で交絡統制後も有意維持（平均Δr=+0.026）** |
| 10 | イントロ構成改訂 | ✅ | 5段落構成に改訂: (a)会話分析の伝統 → (b)LLM+説明可能性 → (c)Classical/Novel 2群 → (d)相互補完アプローチ → (e)目的と貢献 | LLMギャップ提示型 → **古典CA→LLM説明可能性→2群特徴量→行ったり来たり→貢献** |
| 11 | LLM特徴量着目検証（理想） | ✅ | Discussion 4.5節で実現可能性の課題（テキスト操作の非自明性等）と3つの将来方向性を論じ、今後の課題として位置づけ | 未言及 → **Discussion内で方法論・課題・将来方向性を記述（今後の課題）** |

## 新規作成ファイル

| ファイル | 内容 |
|---------|------|
| `scripts/analysis/ensemble_permutation.py` | アンサンブルBig5（4教師item-level平均）permutation test |
| `scripts/analysis/baseline_vs_extended.py` | ベースライン（Classical 9個）vs 拡張（全18個）比較 |
| `scripts/analysis/confound_analysis.py` | 交絡変数（性別・年齢）統制分析 |

## 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `scripts/paper_figs/feature_definitions.py` | classificationフィールド追加（Classical/Novel/Control）、get_classical_features() / get_novel_features() API追加 |
| `scripts/paper_figs/gen_paper_figs_v2.py` | フォントサイズ・DPI改善、新規図表4種追加（ensemble_permutation, baseline_vs_extended, 対応LaTeXテーブル2種）、tab_feature_definitionsにClassification列追加 |
| `scripts/paper_figs/gen_kamishibai_slides.py` | Methods 2枚追加、Results構成改訂（アンサンブル・ベースライン比較スライドに差替） |
| `paper1_ja.tex` | Introduction 5段落構成、Method Classical/Novel分類、Results 3.4節5サブセクション再構成、Discussion交絡統制+LLM着目検証、Appendix 3セクション化、全プレースホルダーを実データに差替 |

## 想定外の結果

山下先生は「アンサンブルでAENOの有意は消えるか？」と問うたが、実際にはO, A, Nもアンサンブルで有意（p<0.05）であった。

| Trait | r_obs | p値 | 有意? |
|-------|-------|-----|-------|
| O（開放性） | 0.360 | 0.0048 | ✅ |
| **C（誠実性）** | **0.447** | **0.0004** | ✅ |
| E（外向性） | 0.217 | 0.0902 | ❌ |
| A（協調性） | 0.465 | 0.0004 | ✅ |
| N（神経症傾向） | 0.309 | 0.0152 | ✅ |

これにより、研究の主張は「Cだけが特別」から「**Eを除く4次元で相互行為特徴量との有意な関連が認められる**」に格上げされた。
Aがr=0.465でCを上回っている点も注目に値する（ただしAの教師間一致度はCより低い）。

## 交絡統制結果（C, 性別・年齢追加後）

| 教師 | r_features | p_features | r_confounds | p_confounds | Δr |
|------|-----------|-----------|-------------|-------------|-----|
| Sonnet4 | 0.384 | 0.0034 | 0.407 | 0.0016 | +0.023 |
| Qwen3-235B | 0.366 | 0.0042 | 0.403 | 0.0020 | +0.037 |
| GPT-OSS-120B | 0.445 | 0.0008 | 0.489 | 0.0002 | +0.045 |
| DeepSeek-V3 | 0.168 | 0.1956 | 0.167 | 0.1946 | -0.001 |

3/4教師で交絡統制後も有意維持。むしろ精度向上（平均Δr=+0.026）。
特徴量とCの関連は性別・年齢の交絡ではないことが確認された。
