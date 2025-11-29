# Nanami Pragmatics Dashboard (JP) — README

本リポジトリは、日本語母子対話コーパス **Nanami/TYP** を対象に、

- pyannote.audio による **話者分離（ダイアライゼーション）**
- ターン構造・終助詞・フィラー・質問・プロソディなどの **語用論・韻律指標の自動算出**
- それらをまとめた **HTML ダッシュボードの可視化**

を行うための実験・可視化用リポジトリです。

GitHub Pages のトップ（`https://leadlea.github.io/asd/`）は、  
本リポジトリから生成される **Nanami Pragmatics Dashboard** を指しています。

---

## 1. GitHub Pages（ダッシュボード）

- Nanami Pragmatics Dashboard（デフォルト）  
  👉 https://leadlea.github.io/asd/

主な構成は以下の 3 ブロックです。

1. **BASIC_TOKENS_PER_TURN**  
   - セッションごとに、CHI / MOT / BOTH の  
     「1ターンあたり平均トークン数（`n_tokens / n_utts`）」をバーグラフで表示。
2. **語用論・プロソディ指標サマリテーブル**  
   - CHI と MOT の値を 1 セル 2 段表示（`CHI xx.xx` / `MOT yy.yy`）で一覧化。
3. **指標 × セッション ヒートマップ**  
   - 各指標について、**セッション間の相対的な高さ**を色（ラベンダー〜パープル）で可視化。
   - CHI 用と MOT 用を別パネルで表示。

---

## 2. 対象データと前提

### 対象

- 日本語母子対話コーパス **Nanami/TYP** の 8 セッション
- pyannote.audio ベースのパイプラインを通した出力（`out/audio/Nanami/<session_id>/...`）

### セッションディレクトリ構造（例）

```text
out/audio/Nanami/
  ├── 10129/
  │   ├── turns.csv
  │   ├── segments.csv
  │   ├── prosody.csv
  │   └── ...（diagnostics.csv など）
  ├── 10225/
  ├── 10421/
  ├── 10622/
  ├── 10928/
  ├── 11025/
  ├── 20213/
  └── 20319/
````

本 README で述べるスクリプトは、上記のような Nanami 出力が
すでに揃っていることを前提としています。

---

## 3. 指標セットの概要

### 3.1 ベース指標

* **BASIC_TOKENS_PER_TURN**

  * 出典: `turns.csv`
  * 定義: `n_tokens / n_utts`
  * 単位: `tokens_per_turn`
  * 集計単位: CHI / MOT / BOTH

### 3.2 語用論・会話タイミング指標

* **TT_GAP_MEAN**

  * 出典: `pragmatics.csv`
  * 定義: ターン間のギャップ時間（秒）の平均
  * 単位: 秒
* **TT_OVERLAP_RATE**

  * 出典: `pragmatics.csv`
  * 定義: オーバーラップしたターンの割合
  * 単位: `%`
* **FILLER_RATE**

  * 出典: `pragmatics.csv`（`segments.text` ベース）
  * 定義: `['えー', 'えぇ', 'えっと', 'えと', 'あの', 'そのー', 'その…', 'うーん', 'うんと', 'まー', 'まあ']`
    にマッチするフィラー出現数 / 100トークン
  * 単位: `per_100_tokens`
* **SFP_NEGOTIATING_RATE**

  * 出典: `pragmatics.csv`（`segments.text` ベース）
  * 定義: 交渉的終助詞（例: 「〜よね」「〜でしょ」「〜かな」「〜かも」など）を含むターン数 / 100ターン
  * 単位: `per_100_turns`
* **QUESTION_RATE**

  * 出典: `segments.csv`
  * 定義: 「?」「？」や「〜か」「〜の？」など簡易ルールで質問とみなされたターン数 / 100ターン
  * 単位: `per_100_turns`

### 3.3 プロソディ指標

* **SPEECH_RATE**

  * 出典: `prosody.csv`
  * 定義: 発話速度（`tokens/sec` など）
  * 単位: `per_sec`
* **PAUSE_RATIO**

  * 出典: `prosody.csv` の `pause_p95`
  * 定義: 発話中のポーズ長を代表する 95 パーセンタイル値
  * 単位: 任意スケール（秒相当・無次元のいずれか）
* **F0_SD**

  * 出典: `prosody.csv` の `f0_sd`
  * 定義: F0（基本周波数）の標準偏差
  * 単位: Hz

---

## 4. スクリプト構成

今回の Nanami ダッシュボードに関連する主なファイルは以下です。

### 4.1 指標カタログ

* `config/pragmatics_index_catalog.csv`

  * Nanami で扱う指標のカタログ
  * `metric_id`, `speaker_role`, `source_tables`, `required_columns`, `status` などを列挙
  * カバレッジ確認や将来の指標拡張の土台として利用

### 4.2 カバレッジ行列の生成

* `scripts/build_nanami_metric_coverage.py`

  * Nanami 各セッションについて、

    * 必要なテーブル・列が揃っているか（available / needs_annotation など）
    * 実際に値が算出されているか
      を `nanami_metric_session_coverage.csv` に出力

出力例（ヘッダ）:

```text
metric_id,session_id,speaker_role,availability_status,missing_tables,missing_columns,implemented,computed,n_tokens_covered,n_turns_covered,notes
BASIC_TOKENS_PER_TURN,10129,CHI,ready,,,1,0,0,0,
...
```

### 4.3 指標値の集計

* `scripts/calc_nanami_pragmatics_metrics.py`

  * `turns.csv`, `segments.csv`, `prosody.csv` などから
    各指標の値をまとめて `nanami_metric_results.csv` に整形

出力例（冒頭）:

```text
metric_id,session_id,speaker_role,value,unit,notes
BASIC_TOKENS_PER_TURN,10129,BOTH,13.1349,tokens_per_turn,(CHI + MOT) n_tokens / n_utts from turns.csv
BASIC_TOKENS_PER_TURN,10129,CHI,12.0896,tokens_per_turn,n_tokens / n_utts from turns.csv
...
FILLER_RATE,10129,CHI,0.2731,per_100_tokens,"count of filler patterns per 100 tokens; ..."
...
QUESTION_RATE,10129,MOT,xx.x,per_100_turns,...
SPEECH_RATE,10129,CHI,10.75,per_sec,...
PAUSE_RATIO,10129,MOT,15.5,unitless,...
F0_SD,10129,CHI,108.86,Hz,...
```

### 4.4 ダッシュボード HTML 生成

* `scripts/build_nanami_pragmatics_dashboard.py`

  * 入力: `out/audio/Nanami/nanami_metric_results.csv`
  * 出力: `docs/index.html`（＝ GitHub Pages のトップ）

主な可視化内容：

1. セッション別の BASIC_TOKENS_PER_TURN（CHI / MOT / BOTH）
2. 語用論・プロソディ指標のサマリテーブル（1セル2段表示）
3. 指標 × セッションのヒートマップ（CHI 用 / MOT 用）

---

## 5. 再現手順（Quickstart）

### 5.1 環境準備

```bash
cd ~/gen/cpsy   # 本リポジトリ

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### 5.2 Nanami 出力の準備

* 別途用意したパイプライン（例: `jp_pipeline/` や `run_nanami.sh`）を通して、
  `out/audio/Nanami/<session_id>/turns.csv`, `segments.csv`, `prosody.csv` 等を生成しておきます。
* 詳細はプロジェクト内のスクリプト・メモを参照。

### 5.3 指標計算・ダッシュボード生成

```bash
# 1) 指標計算（nanami_metric_results.csv）
python scripts/calc_nanami_pragmatics_metrics.py \
  --nanami-root out/audio/Nanami \
  --out out/audio/Nanami/nanami_metric_results.csv

# 2) カバレッジ行列（任意・開発用）
python scripts/build_nanami_metric_coverage.py \
  --nanami-root out/audio/Nanami \
  --catalog config/pragmatics_index_catalog.csv \
  --out out/audio/Nanami/nanami_metric_session_coverage.csv

# 3) ダッシュボード HTML 生成（docs/index.html）
python scripts/build_nanami_pragmatics_dashboard.py \
  --results out/audio/Nanami/nanami_metric_results.csv \
  --out docs/index.html
```

GitHub に push すると、`https://leadlea.github.io/asd/` が更新されます。

---

## 6. 共同研究・今後の拡張のためのメモ

* 本ダッシュボードはあくまで **exploratory なプロトタイプ** です。
* CSJ / CEJC を用いたスケールアウト時には、

  * 指標定義の精緻化（終助詞・談話標識のラベリング精度向上）
  * prosody 指標の妥当性検証（録音条件・話者属性差を踏まえた正規化）
  * ASD / TD / その他臨床群との比較設計（年齢・課題条件のマッチング）
    などが必要になります。
* 研究メンバーとの議論（例: NCNP 山下先生ら）を通じて、

  * **臨床的に有意義な指標セットの絞り込み**
  * 「本命指標」「補助指標」「参考指標」の層別
    を行うことを想定しています。

---

## 7. 過去の英語 ASD Pragmatics MVP について

以前の README で説明していた **英語 ASD/TD 語用論 MVP（ASDBank + CHILDES）** に関するレポートは、
以下の HTML にアーカイブされています。

* ASD Pragmatics MVP Report (EN)
  👉 [https://leadlea.github.io/asd/ASD_TD_MVP_Report.html](https://leadlea.github.io/asd/ASD_TD_MVP_Report.html)

現在のリポジトリの主眼は **Nanami/TYP を使った日本語母子対話の語用論・プロソディ解析** ですが、
英語MVPのコード・レポートも必要に応じて参照可能です。

````