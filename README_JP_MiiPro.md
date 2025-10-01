# JP 日本語コーパス 9分窓パイプライン（MiiPro / CHILDES）

このREADMEは、英語版ダッシュボード互換の **日本語パイプライン**（fugashi+UniDic / SudachiPy 補強）について、
再現コマンド、設定、出力物、読める結果、トラブル対処、拡張方法をまとめたものです。

---

## 1. 概要（何をするもの？）
- **対象**: CHILDES 「MiiPro」コーパス（例：Nanami/Asato/Tomito）。`.cha` を直接読み込み。
- **時間窓**: セッション内の **9分相当**を自動抽出（発話タイムスタンプが無い場合は発話数近似）。
- **形態素**:
  - **主系**: `fugashi(MeCab)+UniDic`（短単位語）→ **lemma 集計**（語彙は基本レマで数える）
  - **補強**: `SudachiPy(dict_full, mode=C)`（未知語/表記ゆらぎを再解析）
- **フィラー除外**: `fillers_ja.txt` の語は語彙から除外し、ヒットは `filler_hits.csv` にログ。
- **品質ゲート**: `CHI（子）発話数 >= min_utt_child` のセッションのみ集計（既定20）。下回るものは `jp_dropped.csv` に理由つき出力。
- **メトリクス**: NDW(Types), Tokens, **MLU**（= トークン数/発話数, lemma基準）を **CHI と親（MOT等）**で同一窓に対して算出。
- **メタ解析**: `MOT_MLU - CHI_MLU` の **Hedges g** を出力（セッション内差の大きさ）。
- **年齢**: `@Age:` または `@ID: ...|CHI|<AGE>|...` の **年齢を月齢**に変換 → **年齢バケット**別の記述統計を出力。
- **語用論（追加タブ）**: 質問率 / 談話標識 / 心的状態語
  - **質問率**: 末尾の `?`/`？` や 「か/かな/…」終助詞で検出
  - **談話標識**: でも/だから/それで/ところで/じゃあ/つまり/… など（辞書は `pragmatics_ja.py` 内の集合）
  - **心的状態語**: 思う/分かる/感じる/好き/嫌い/嬉しい/… など（同上）
  - 正規化: 100語あたりヒット数（`*_per_100t`）

---

## 2. セットアップ

### 2.1 依存関係（既存の仮想環境でOK）
```bash
# 推奨: 既存の venv を利用
python -m pip install -U fugashi unidic-lite sudachipy sudachidict-full pandas numpy pyyaml
```
> ※ もし `scipy` 由来の NumPy 依存エラーが出る場合は、scipyをアンインストール（または numpy を <1.28 にピン止め）するか、scipyを使わない環境で実行してください。パイプライン自体は `scipy` 非依存です。

### 2.2 コーパス配置
```
cpsy/
└─ MiiPro/
   ├─ Nanami/*.cha
   ├─ Asato/*.cha
   └─ Tomito/*.cha
```
> 例: `MiiPro/Nanami/10129.cha` など

### 2.3 設定ファイル（例）
`jp_pipeline/config_jp.yaml`
```yaml
# JP pipeline config
corpus_dir: "./MiiPro/Nanami"   # 読み込み対象（Nanami/Asato/Tomito を切替可）
tiers:
  child: ["CHI"]
  parent: ["MOT","MOM","FAT","FTH","FA","PAR"]
window:
  mode: "auto"                  # "auto"=タイムスタンプ優先/無ければ発話数近似
  minutes: 9
  assume_session_minutes: 70
tokenizer:
  primary: "fugashi_unidic"
  fallback: "sudachipy_full_C"
lexicon:
  filler_path: "./jp_pipeline/fillers_ja.txt"
filters:
  min_utt_child: 20
  drop_if_below_min_child_utts: true
age_bins: [12,24,36,48,60,72,84]  # 月齢バケット。必要に応じて調整
output:
  outdir: "./out/jp"
  dashboard_html: "docs/jp_miipro_dashboard.html"
```

---

## 3. 実行方法（再現コマンド）

### 3.1 シェルスクリプトから（推奨）
```bash
# リポジトリのルート（cpsy/）で
./jp_pipeline/run_jp_pipeline.sh ./jp_pipeline/config_jp.yaml

# 実行後のメッセージ例
# Done. Dashboard -> "docs/jp_miipro_dashboard.html"
# ↑ これが出たら成功。HTMLはそのままブラウザで開けます。
```

### 3.2 Pythonモジュールとして直実行
```bash
PYTHONPATH=./jp_pipeline python -m jp_pipeline.compute_metrics ./jp_pipeline/config_jp.yaml
```

---

## 4. 生成される成果物

`out/jp/`（CSV群）と `docs/`（ダッシュボードHTML）。主なCSVのカラム仕様：

- `out/jp/jp_sessions.csv`（**included only** = フィルタ通過）  
  - `file, child_id, age_months, n_utts_child_win, n_tokens_child, n_types_child, mlu_child, n_utts_parent_win, n_tokens_parent, n_types_parent, mlu_parent, chi_utt_low`
- `out/jp/jp_dropped.csv`（**フィルタ落ち**のログ）  
  - `file, child_id, reason, n_utts_child_win, n_tokens_child, n_types_child, mlu_child`
- `out/jp/jp_descriptives.csv`（記述統計: included only）  
  - `metric, n, mean, sd, min, max`（CHI/MOT の MLU・Types・Tokens）
- `out/jp/jp_meta.csv`（メタ解析: included only）  
  - `contrast, g, se, ci95_lo, ci95_hi, n_sessions, dropped_n, min_utt_child, drop_if_below`
- `out/jp/jp_pragmatics.csv`（語用論: 役割別）  
  - `file, child_id, role, n_utts, n_tokens, question_utts, question_rate, dm_hits, dm_per_100t, mental_hits, mental_per_100t`
- `out/jp/jp_age_bins.csv`（**年齢バケット別**: CHI, included only）  
  - `bin, n, CHI_MLU_mean, CHI_MLU_sd, CHI_NDW_mean, CHI_NDW_sd`
- `out/jp/filler_hits.csv`（フィラーヒットの記録: 任意）

- `docs/jp_miipro_dashboard.html`（ダッシュボード）  
  - ヘッダに **included / dropped** とフィルタ設定  
  - **セッション表** / **記述統計** / **メタ解析（MOT−CHI MLU）**  
  - **年齢バケット別**（CHI）  
  - **語用論サマリ（CHI/PARENT）**（質問率・談話標識/心的語の100語あたり）

---

## 5. 何が調べられて、どんな結果が見える？（サンプルランの例）

> 下記は `MiiPro/Nanami` での一例（しきい=20発話, 9分窓, lemma, フィラー除外）。

- **品質ゲート**: dropped=3（`CHI_utts<20`）、included=178  
- **メタ解析（MOT−CHI MLU）**: g ≈ **1.55**（SE≈0.121、95%CI≈[1.32,1.79]、n=178）  
  → **親のMLUは子より約1.5 SD 長い**強い効果。
- **記述統計（included only）**  
  - CHI_MLU 平均 ≈ **2.94**、NDW 平均 ≈ **84.7**  
  - MOT_MLU 平均 ≈ **4.56**、Types 平均 ≈ **202.6**
- **年齢バケット（例：12–24, 24–36, 36–48, …）**  
  - 月齢が上がるにつれ **CHIの MLU / NDW が概ね上昇**（自然な発達パターン）。
- **語用論**  
  - **質問率**：親 > 子 の傾向（親の問いかけが多い）。  
  - **談話標識/心的状態語**：親でのヒットが相対的に多い（家庭ごとの差も確認可能）。

> 自分のデータではどうか？ → 上記CSVを見れば**数値で**、ダッシュボードなら**視覚的に**一目で確認できます。

---

## 6. よくある質問 / トラブルシューティング

- **年齢がNAになる**  
  - `.cha` に `@Age:` か、`@ID: ...|CHI|<AGE>|...` が無い/特殊表記だとNAになります。  
  - MiiPro標準の `1;01.29` 形式は対応済みです（関数 `parse_age_months()` が **@Age / @ID 両対応**）。
  - **24ヶ月未満**は `age_bins` の下限が24だと **NAバケット**に落ちます。→ `age_bins` を `[12,24,36,...]` などに広げてください。
- **フィラー辞書を増やしたい**  
  - `jp_pipeline/fillers_ja.txt` に追記 → 再実行で反映。ヒットは `filler_hits.csv` に出ます。
- **語用論の辞書を増やしたい**  
  - `jp_pipeline/jp_pipeline/pragmatics_ja.py` の集合（`DISCOURSE_MARKERS`, `MENTAL_STATE`）に単語を追加。
- **SciPyがNumPyに文句を言う**  
  - 本パイプラインは `scipy` 非依存。トラブル時は `pip uninstall scipy` か `numpy<1.28` に下げてください。

---

## 7. 発展（カスタム）

- **しきい値**: `filters.min_utt_child` を 20→30 に上げると外れ値がさらに減り、安定度UP（サンプル数は減少）。
- **年齢刻み**: `[12,18,24,30,36,42,48,54,60,72]` のように **6ヶ月刻み**も便利。
- **別の子のフォルダ**: `corpus_dir` を `./MiiPro/Asato` や `./MiiPro/Tomito` に変更して再実行。

---

## 8. Git に同期（main）

> **生データ（`MiiPro/`）や `out/` は原則コミットしない** ことを推奨。HTMLはドキュメントとしてコミット可。

```bash
# ルートで
cd /Users/genfukuhara/cpsy

# 必要なら .gitignore を拡張
printf "
# JP pipeline
MiiPro/
out/
*.bak
__pycache__/
" >> .gitignore

# 追加する主なファイル/ディレクトリ
git add README_JP_MiiPro.md         jp_pipeline/         docs/jp_miipro_dashboard.html         jp_pipeline/config_jp.yaml         jp_pipeline/fillers_ja.txt

# 既存の変更がある場合は併せてコミット（必要に応じて -p で選択）
git commit -m "JP pipeline: 9-min window (lemma+fillers), age parsing, pragmatics tab, dashboard; add README and config"

# push
git push origin main
```

> 既存の変更（例: `dyads.*` 系）を含めたくない場合は、`git add -p` で個別に選択してください。

---

## 9. 参考（内部構成）

- `jp_pipeline/jp_pipeline/compute_metrics.py`  
  - 9分窓抽出、トークン化、MLU/NDW計算、年齢パース（@Age/@ID）、語用論集計、CSV出力、ダッシュボード生成
- `jp_pipeline/jp_pipeline/pragmatics_ja.py`  
  - 質問率検出、談話標識・心的状態語の辞書＆カウント
- `jp_pipeline/run_jp_pipeline.sh`  
  - どこからでも実行できるよう `PYTHONPATH` を設定し、ダッシュボードのパスを表示
- `jp_pipeline/config_jp.yaml`  
  - すべての設定（しきい値、年齢バケット、出力先など）

---

**Happy analyzing!**  
（ダッシュボード: `docs/jp_miipro_dashboard.html` をブラウザで開けばOK）
