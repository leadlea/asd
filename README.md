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

- Nanami Pragmatics Dashboard（ガイド資料）  
  👉 https://leadlea.github.io/asd/nanami_pragmatics_dashboard_guide.html

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

* `turns.csv`

  * 1 行 = 1 「ターン」（話者交替境界を基準としたまとまり）
  * 各ターンについて、トークン数・発話時間・平均 F0 などを記録
* `segments.csv`

  * 1 行 = 1 「セグメント」（短い発話断片）
  * 元々は ASR / diarization 出力からの派生
* `prosody.csv`

  * ターン単位での F0, エネルギー, ポーズ長などの要約指標
* `pragmatics.csv`

  * 上記を統合した、語用論・タイミング系の派生指標

---

## 3. 指標セットの概要

### 3.1 ベース指標

**`BASIC_TOKENS_PER_TURN`**

* 出典: `turns.csv`
* 定義: `n_tokens / n_utts`
  （1話者について、1ターンあたりの平均トークン数）
* 単位: `tokens_per_turn`
* 集計単位: CHI / MOT / BOTH

---

### 3.2 語用論・会話タイミング指標（総量系）

**`SFP_ALL_RATE`**

* 出典: `segments.csv`
* 定義:
  各話者について、**文末に終助詞（よ・ね・な・ぞ・じゃん など）を含む発話の割合**。
* 単位: `ratio`（0〜1）
* 解釈イメージ:

  * 「終助詞をどのくらい使う話し方か？」という**ざっくりした総量指標**。
  * より細かいプロファイルは後述の `SFP_NE_RATE` などで分解。

**`DM_DEMO_RATE`**

* 出典: `segments.csv`
* 定義:
  各話者について、「でも」で始まるターン（談話標識「でも」）の割合。
* 単位: `ratio`（0〜1）
* 解釈イメージ:

  * 「話題転換・逆接導入の多さ」の粗い指標。
  * 「でも〜」で始めるクセの有無や頻度をざっくり見る。

**`QUESTION_RATE`**（将来的な想定）

* 出典: `segments.csv`
* 定義:
  「?」「？」や「〜か」「〜の？」など簡易ルールで質問とみなされたターン数 / 100ターン。
* 単位: `per_100_turns`
* 解釈イメージ:

  * 聞き手への働きかけ（情報要求）の多さを粗く見る指標。

---

### 3.3 プロソディ指標

**`SPEECH_RATE`**

* 出典: `prosody.csv`
* 定義: 発話速度（例: `tokens/sec`）
* 単位: `per_sec`
* 解釈イメージ:

  * 「早口か／ゆっくりか」をざっくり見る。

**`PAUSE_RATIO`**（例）

* 出典: `prosody.csv` の `pause_p95`
* 定義: 発話中のポーズ長を代表する 95 パーセンタイル値
* 単位: 秒相当 or 無次元
* 解釈イメージ:

  * 長めのポーズ（沈黙）がどれくらい出るかを見る。

**`F0_SD`**

* 出典: `prosody.csv` の `f0_sd`
* 定義: F0（基本周波数）の標準偏差
* 単位: Hz
* 解釈イメージ:

  * 声の高さの「抑揚の大きさ」をざっくり把握する。

---

### 3.4 終助詞産出・応答指標（SFP_* / RESP_*）

ここは、CEJC / CEJC-Child / Nanami 関連の論文を元に、
**ASD 傾向・共感性・アレキシサイミアなどと関係が示唆されている終助詞の使い方**を
Nanami ダッシュボードに落とし込んだ指標群です。

#### 3.4.1 終助詞プロファイル（産出側）

すべて **セッション × 話者ロール（CHI / MOT / PAT / CLIN etc.）** 単位で集計します。
母子コーパスでは CHI / MOT、将来の臨床データでは PAT / CLIN などを想定。

---

**`SFP_NE_RATE` — ね系終助詞率**

* 出典: `segments.csv`
* 定義:
  各話者について、全発話のうち、文末が

  * 「ね」「だね」「よね」「だよね」などの **ね系終助詞（`NE`）**
  * ＋ 疑問的な「ね？」系（`NE_Q`）
    で終わる発話の割合。
* 単位: `ratio`（0〜1）
* 解釈イメージ:

  * 他者との **共感・同意の共有** を前提にしたスタイルの「総量」。
  * 自閉スペクトラム傾向（AQ）が高いほど、この値が下がることが報告されている（一般成人 CEJC において）。

---

**`SFP_NE_Q_RATE` — ね疑問型終助詞率**

* 出典: `segments.csv`
* 定義:
  各話者について、全発話のうち、文末が

  * 「ね？」系（確認要求的な「〜だよね？」等）で終わる発話の割合。
    （`sfp_group == NE_Q`）
* 単位: `ratio`（0〜1）
* 解釈イメージ:

  * 「〜だよね？」「〜だよねぇ？」といった、聞き手に**確認を取りに行くスタイル** の量。
  * 共感性（EQ）が高い人ほど多い、AQ の「想像力」下位得点が高いと少ない、といった関連が報告されている。

---

**`SFP_YO_RATE` — よ系終助詞率**

* 出典: `segments.csv`
* 定義:
  各話者について、全発話のうち、文末が

  * 「よ」「だよ」「だよな」など **よ系終助詞（`YO`）** で終わる発話の割合。
* 単位: `ratio`（0〜1）
* 解釈イメージ:

  * **情報提示・断定的なスタンス** の多さをざっくり捉える指標。
  * 「ね」系と対比させることで、「説明しがち／共感取りに行きがち」のバランスを見る。

---

**`SFP_NA_RATE` — な系終助詞率**

* 出典: `segments.csv`
* 定義:
  各話者について、全発話のうち、文末が

  * 「な」「かな」「よな」など **な系終助詞（`NA`）** で終わる発話の割合。
* 単位: `ratio`（0〜1）
* 解釈イメージ:

  * **独り言・自己完結的なモノローグ寄り** のスタイルを示す指標。
  * CEJC の研究では、AQ の「想像力」下位得点が高い人ほど `SFP_NA_RATE` が高い傾向が報告されており、
    「ね」系とは逆方向の動きを見せることがある。

---

**`SFP_NO_RATE` — の系終助詞率**

* 出典: `segments.csv`
* 定義:
  各話者について、全発話のうち、文末が

  * 「の」「のね」「のよ」など **の系終助詞（`NO`）** で終わる発話の割合。
* 単位: `ratio`（0〜1）
* 解釈イメージ:

  * 発話の断定を **やわらげて説明的にするスタイル**。
  * 情動共感が相対的に強い人ほど `の` 系を多用するという結果もあり、
    「やさしく説明する話し方」の一つの手がかりとして扱います。

---

**`SFP_MON_RATE` — もん系終助詞率**

* 出典: `segments.csv`
* 定義:
  各話者について、全発話のうち、文末が

  * 「もん」「もんね」など **もん系終助詞（`MON`）** で終わる発話の割合。
* 単位: `ratio`（0〜1）
* 解釈イメージ:

  * 「〜なもんで」「〜なんだもん」など、
    **理由づけ・弁明的な自己説明スタイル** の多さを表す。
  * アレキシサイミア尺度（TAS-20）との関連が指摘されており、
    「感情を言語化しづらい人ほど『〜なもんで…』と説明を付けがち」といった解釈の足がかりになる。

---

#### 3.4.2 応答パターン指標（終助詞への反応）

ここでは、同一セッション内の **連続する2発話** に注目し、

* 発話 i: 文末に終助詞（ね／よ 等）を含む発話（提示側）
* 発話 i+1: 直後の別話者による応答（応答側）

というペアから、**終助詞への応答の仕方** を定量化します。
いずれも **セッション × 応答側ロール（CHI / MOT / PAT / CLIN など）** 単位で集計。

---

**`RESP_NE_AIZUCHI_RATE` — 「ね」直後あいづち率**

* ベース: `segments.csv` から構成するペア（`segment_pairs` 相当）
* 定義:
  他者の **ね系終助詞（`NE` / `NE_Q`）** で終わる発話の直後に、
  自分が **典型的あいづち語**（例: 「うん」「はい」「そう」「ええ」など）で応答した割合。
* 単位: `ratio`（0〜1）
* 解釈イメージ:

  * 「〜ね。」に対して、**定型的な同意応答** に乗れているかを示す指標。
  * AQ の「想像力」下位得点や共感性との関連を検証するための候補。

---

**`RESP_NE_ENTROPY` — 「ね」応答エントロピー**

* ベース: `segments.csv` から構成するペア（`segment_pairs` 相当）
* 定義:
  他者の **ね系終助詞（`NE` / `NE_Q`）** で終わる発話に対する、
  自分の応答の **1語目** の分布のエントロピー（Shannon entropy, log2）。
* 単位: `float`（ビット）
* 解釈イメージ:

  * 値が **低い**:

    * 「ね」に対する返答が「うん」「そう」「はい」など、
      比較的少数の定型パターンに **まとまりやすい**。
  * 値が **高い**:

    * 応答の1語目がバラバラで、パターンのまとまりが弱い。
  * CEJC では、AQ の「想像力」下位得点が高い人ほど
    `RESP_NE_ENTROPY` が高くなる（＝「ね」を受けた後の返しが多様で散らばりやすい）ことが報告されている。

---

**`RESP_YO_ENTROPY` — 「よ」応答エントロピー**

* ベース: `segments.csv` から構成するペア（`segment_pairs` 相当）
* 定義:
  他者の **よ系終助詞（`YO`）** で終わる発話に対する、
  自分の応答の **1語目** の分布のエントロピー（Shannon entropy, log2）。
* 単位: `float`（ビット）
* 解釈イメージ:

  * 「〜よ。」に対する応答パターンの多様性を測る**ベースライン指標**。
  * `RESP_NE_ENTROPY` と対比させることで、
    「情報提示（よ）」と「同意・共感（ね）」に対する応答スタイルの違いを可視化できる。

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

* `scripts/calc_nanami_sfp_metrics.py`

  * `out/audio/Nanami/<session_id>/segments.csv` から終助詞産出指標（SFP_*）と応答パターン指標（RESP_*）を追加で計算し、
    既存の `nanami_metric_results.csv` を読み込んでこれらの指標行を追記したうえで、同じファイル名で書き戻す（後がけ処理）。

出力例（冒頭）:

```text
metric_id,session_id,speaker_role,value,unit,notes
BASIC_TOKENS_PER_TURN,10129,BOTH,13.1349,tokens_per_turn,(CHI + MOT) n_tokens / n_utts from turns.csv
BASIC_TOKENS_PER_TURN,10129,CHI,12.0896,tokens_per_turn,n_tokens / n_utts from turns.csv
...
FILLER_RATE,10129,CHI,0.2731,per_100_tokens,"count of filler patterns per 100 tokens; ..."
...
SFP_NE_RATE,10129,CHI,0.12,ratio,"computed from segments.csv (sentence-final particles)"
RESP_NE_ENTROPY,10129,MOT,1.85,float,"entropy of response first tokens after NE/NE_Q SFP (from segments.csv)"
...
```

### 4.4 ダッシュボード HTML 生成

* `scripts/build_nanami_pragmatics_dashboard.py`

  * `nanami_metric_results.csv` から、以下を含む HTML ダッシュボードを生成:

    1. セッションごとの BASIC_TOKENS_PER_TURN バーグラフ
    2. 語用論・プロソディ指標のサマリテーブル（1セル2段表示）
    3. 指標 × セッションのヒートマップ（CHI 用 / MOT 用）

### 4.5 音声解析パイプライン（`audio_mvp/` ＋ `run_nanami.sh`）

Nanami/TYP の元音声（mp3）から `turns.csv` / `segments.csv` / `prosody.csv` 等を作る部分は
`audio_mvp/` 以下のスクリプトと、ループ用シェルスクリプト `run_nanami.sh` で構成されています。

#### 単一ファイルを解析する例

```bash
python audio_mvp/audio_analyze.py \
  --audio-in audio/Nanami/10129.mp3 \
  --out-dir out/audio/Nanami/10129
```

#### mp3 をループで一括解析する例（ワンライナー）

`audio/Nanami/*.mp3` を全部処理して、
`out/audio/Nanami/<session_id>/...` に結果を書き出すシェルループは以下の通りです。

```bash
for f in audio/Nanami/*.mp3; do
  stem="$(basename "$f" .mp3)"
  echo "Processing $stem ..."
  python audio_mvp/audio_analyze.py \
    --audio-in "$f" \
    --out-dir "out/audio/Nanami/$stem"
done
```

#### `run_nanami.sh` を使う場合

同等の処理を行うラッパースクリプトとして `run_nanami.sh` を用意しています。

```bash
# 必要に応じて Hugging Face のトークンやデバイスを指定
export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx    # 自分のトークンを設定
export WHISPER_DEVICE=mps                           # CPU の場合は "cpu"
export PYANNOTE_DEVICE=cpu                          # MPS が不安定な場合は cpu 推奨

# Nanami の mp3 を一括解析
bash run_nanami.sh

# 実行後：
# out/audio/Nanami/<session_id>/report.html などが生成されます
```

---

## 5. 再現手順（Quickstart）

### 5.1 環境準備

```bash
cd ~/gen/cpsy   # 本リポジトリ

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### 5.2 Nanami 音声（mp3）から解析結果を生成する

1. Nanami/TYP の mp3 を、セッション ID をファイル名として配置します。

   ```text
   audio/Nanami/
     ├── 10129.mp3
     ├── 10225.mp3
     ├── ...
   ```

2. 上記の「音声解析パイプライン」に従って、`run_nanami.sh` またはワンライナーで解析します。

   ```bash
   export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   export WHISPER_DEVICE=mps
   export PYANNOTE_DEVICE=cpu

   bash run_nanami.sh
   ```

   実行が完了すると、`out/audio/Nanami/<session_id>/` 以下に
   `turns.csv`, `segments.csv`, `prosody.csv`, `pragmatics.csv`, `report.html` などが生成されます。

### 5.3 指標計算・ダッシュボード生成

上記 5.2 で Nanami 出力が揃った前提で、指標計算とダッシュボード生成を行います。

```bash
# 1) 指標計算（nanami_metric_results.csv）
python scripts/calc_nanami_pragmatics_metrics.py \
  --nanami-root out/audio/Nanami \
  --out out/audio/Nanami/nanami_metric_results.csv

# 2) 終助詞・応答パターン指標の追加（SFP_* / RESP_*）
python scripts/calc_nanami_sfp_metrics.py \
  --nanami-root out/audio/Nanami \
  --metrics-in out/audio/Nanami/nanami_metric_results.csv \
  --metrics-out out/audio/Nanami/nanami_metric_results.csv

# 3) カバレッジ行列（任意・開発用）
python scripts/build_nanami_metric_coverage.py \
  --nanami-root out/audio/Nanami \
  --catalog config/pragmatics_index_catalog.csv \
  --out out/audio/Nanami/nanami_metric_session_coverage.csv

# 4) ダッシュボード HTML 生成（docs/index.html）
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

* 研究メンバーとの議論を通じて、

  * **臨床的に有意義な指標セットの絞り込み**
  * 「本命指標」「補助指標」「参考指標」の層別

  を行うことを想定しています。

- 関連論文調査レポート：CEJC・CSJを活用した語用論／発達障害研究
  👉 [https://leadlea.github.io/asd/corpas_paper.html](https://leadlea.github.io/asd/corpas_paper.html)
