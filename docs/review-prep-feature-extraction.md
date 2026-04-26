# 査読対応準備: 特徴量抽出ルールの妥当性

更新日: 2026-04-27
目的: 「特徴量の定義根拠は？」「なぜこのルールなのか？」という査読質問に即座に回答できる資料

---

## 1. 19 特徴量の構成

スクリプト: `scripts/analysis/extract_interaction_features_min.py`
定義ファイル: `scripts/paper_figs/feature_definitions.py`

### Classical（10 特徴量: PG 8 + FILL 2）

| # | 特徴量 | カテゴリ | 概要 | アルゴリズム |
|---|--------|---------|------|-------------|
| 1 | PG_speech_ratio | PG | 発話率 | 話者の総発話時間 / 会話全体時間 |
| 2 | PG_pause_mean | PG | 平均沈黙長 | 同一話者の連続発話間ギャップ（≥0.05秒）の平均 |
| 3 | PG_pause_p50 | PG | 沈黙中央値 | 同上の50パーセンタイル |
| 4 | PG_pause_p90 | PG | 沈黙90パーセンタイル | 同上の90パーセンタイル |
| 5 | PG_resp_gap_mean | PG | 平均応答遅れ | 話者交替時のギャップ（prev_end → resp_start）の平均 |
| 6 | PG_resp_gap_p50 | PG | 応答遅れ中央値 | 同上の50パーセンタイル |
| 7 | PG_resp_gap_p90 | PG | 応答遅れ90パーセンタイル | 同上の90パーセンタイル |
| 8 | PG_overlap_rate | PG | オーバーラップ率 | ギャップ < -0.05秒（重なり）の割合 |
| 9 | FILL_has_any | FILL | フィラー発話率 | フィラー（えっと/えー/あの）を含む発話の割合 |
| 10 | FILL_rate_per_100chars | FILL | 100文字あたりフィラー率 | フィラー総数 / (文字数 / 100) |

### Novel（9 特徴量: IX 5 + RESP 3 + PG 1）

| # | 特徴量 | カテゴリ | 概要 | アルゴリズム |
|---|--------|---------|------|-------------|
| 11 | IX_oirmarker_rate | IX | OIR率 | OIRマーカー（え？/なに？等）で始まる応答の割合 |
| 12 | IX_oirmarker_after_question_rate | IX | 質問直後OIR率 | 質問の直後にOIRマーカーが出る割合 |
| 13 | IX_yesno_rate | IX | YES/NO応答率 | はい/うん/いいえ等で始まる応答の割合 |
| 14 | IX_yesno_after_question_rate | IX | 質問直後YES/NO率 | 質問の直後にYES/NOが出る割合 |
| 15 | IX_lex_overlap_mean | IX | 語彙つながり | 前発話と応答の文字バイグラムJaccard係数の平均 |
| 16 | RESP_NE_AIZUCHI_RATE | RESP | ね直後相槌率 | 「ね」で終わる発話の直後に相槌が出る割合 |
| 17 | RESP_NE_ENTROPY | RESP | ね直後応答多様性 | 「ね」直後の応答初頭トークンのShannon entropy |
| 18 | RESP_YO_ENTROPY | RESP | よ直後応答多様性 | 「よ」直後の応答初頭トークンのShannon entropy |
| 19 | PG_pause_variability | PG | 沈黙変動係数 | 沈黙長のCV（std / mean）。2件以上かつmean>0で算出 |

---

## 2. 判定ルールの詳細と根拠

### 2.1 フィラー判定

```python
RE_ETO = re.compile(r"(えっと|えと)")
RE_E   = re.compile(r"(えー+|えぇ+|え〜+)")
RE_ANO = re.compile(r"(あの)")
```

- 3種類のフィラー（えっと系 / えー系 / あの）を正規表現で検出
- 「えっと」を先に除去してから「えー」を検出（二重カウント防止）
- 根拠: 日本語会話のフィラー研究（定延・田窪 1995 等）で確立された3大フィラー

### 2.2 相槌判定

```python
AIZUCHI_PREFIXES = [
    "はい", "うん", "ええ", "そう", "そうそう", "そっか",
    "なるほど", "へえ", "了解", "わかった", "わかりました",
    "OK", "オーケー", "あー", "ああ", "うーん"
]
```

- 応答の先頭トークンがプレフィックスリストに一致するかで判定
- v12 で長音（ー）を含む相槌を追加、v13 で同意系（ですよね/だよね等）を追加
- 具体例は `reports/goldv13_cejcdyad_vs_csjdialog_a4_full.html` に掲載済み
- 根拠: 堀口（1997）の相槌分類、CEJC の相槌タグ体系を参考

### 2.3 OIR（Other-Initiated Repair）マーカー判定

```python
OIR_PREFIXES = [
    "え？", "えっ", "えっ？", "ん？", "は？", "なに？", "何？",
    "もう一回", "もう一度", "どういうこと", "どういう意味",
    "聞こえ", "聞き取", "わから", "分から"
]
```

- 会話分析（CA）における「他者開始修復」の日本語版マーカー
- 根拠: Schegloff et al. (1977) の修復組織、串田・平本・林（2017）の日本語会話分析

### 2.4 終助詞（SFP）判定

```python
_SFP_NE_RE = re.compile(r"(よね|だよね|ですよね|だよな|ね)$")
_SFP_YO_RE = re.compile(r"(だよ|ですよ|よ)$")
```

- 発話末の終助詞を正規表現で分類（NE系 / YO系 / OTHER）
- 「よね」は NE 系に分類（「ね」が主機能）
- 疑問マーカー付きの「ね」は NE_Q として区別可能
- 根拠: B-1_168 論文（応答の多様性・よ/ね文の比較）、金水・田窪（1998）

### 2.5 疑問判定

```python
_QMARK_RE = re.compile(r"[?？]")
_Q_END_RE = re.compile(r"(か|かな|かね|でしょう|でしょ|だろう|だろ|の)$")
```

- 疑問符の有無 + 疑問形末尾パターンの2段階判定
- 根拠: 日本語の疑問文は疑問符なしでも成立するため、末尾パターンも併用

### 2.6 語彙つながり（Lexical Overlap）

```python
def char_bigrams(s: str):
    t = re.sub(r"\s+", "", norm_text(s))
    return set() if len(t) < 2 else {t[i:i+2] for i in range(len(t)-1)}

def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b)
```

- 前発話と応答の文字バイグラム集合のJaccard係数
- 形態素解析不要で日本語に適用可能（分かち書き不要）
- topic_drift = 1 - lex_overlap（共線性のため topic_drift は EXCL3 として除外）

---

## 3. 除外変数（EXCL3: 13 control variables）

以下は特徴量抽出時に算出されるが、回帰モデルの説明変数からは除外：

| 変数 | 除外理由 |
|------|---------|
| IX_topic_drift_mean | IX_lex_overlap_mean と完全共線（1 - overlap） |
| n_pairs_total, IX_n_pairs | サンプルサイズ指標（予測変数ではない） |
| n_pairs_after_NE, n_pairs_after_YO | 分母情報（rate の信頼性指標） |
| IX_n_pairs_after_question | 同上 |
| PG_total_time | 会話長（交絡変数） |
| PG_resp_overlap_rate | PG_overlap_rate と同一実装 |
| FILL_text_len | テキスト長（交絡変数） |
| FILL_cnt_total, cnt_eto, cnt_e, cnt_ano | 絶対数（rate で正規化済み） |

---

## 4. 想定される査読質問と回答案

### Q1: 「フィラーの定義は恣意的では？」

**回答**: 日本語会話のフィラー研究で確立された3大フィラー（えっと/えー/あの）を採用した。これらは定延・田窪（1995）等で体系的に分類されており、CEJC のタグ体系とも整合する。「なんか」「まあ」等の談話標識は、フィラーとの境界が曖昧なため今回は除外した。将来的には拡張可能。

### Q2: 「相槌のプレフィックスリストは網羅的か？」

**回答**: 完全な網羅性は主張しない。ルールベースの限界として、文脈依存的な相槌（例: 相手の発話を繰り返す「エコー型」）は捕捉できない。ただし、v8→v13 の段階的改善で主要な相槌パターンをカバーしており、B-1_168 論文との sanity check で方向一致を確認済み。

### Q3: 「文字バイグラムの Jaccard は粗すぎないか？」

**回答**: 形態素解析を介さない設計は意図的。日本語の形態素解析は口語・フィラー・不完全文に弱く、解析器依存のノイズが入る。文字バイグラムは解析器非依存で再現性が高い。粗い指標であることは認めるが、topic drift の方向性を捉えるには十分であり、bootstrap でも安定した寄与を示している。

### Q4: 「OIR マーカーの判定は先頭一致だけで十分か？」

**回答**: 先頭一致は CA（会話分析）の知見に基づく。OIR は典型的にターンの冒頭に出現する（Schegloff et al. 1977）。ただし、「え」が感嘆詞として使われるケースとの区別は不完全であり、これは Limitation として記載する。
