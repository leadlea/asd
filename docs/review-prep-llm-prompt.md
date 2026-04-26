# 査読対応準備: LLM 疑似教師の採点プロトコル

更新日: 2026-04-27
目的: 「LLM が採点した Big Five を教師にしていいのか？」という査読質問に即座に回答できる資料

---

## 1. 採点プロトコルの概要

### 使用した尺度

IPIP-NEO-120（International Personality Item Pool, NEO 版 120 項目）

- 5 trait × 24 項目 = 120 項目
- 各項目は 5 件法（0〜4）: Very Inaccurate / Moderately Inaccurate / Neither Accurate Nor Inaccurate / Moderately Accurate / Very Accurate
- 55 項目が逆転項目（reverse=1）→ スコアを 4 - score で反転
- 項目ファイル: `artifacts/big5/items_ipipneo120_ja.csv`（日本語版）、`artifacts/big5/items_ipipneo120_en.csv`（英語版）

### 使用した LLM（4 モデル）

| モデル | Bedrock Model ID | リージョン |
|--------|-----------------|-----------|
| Sonnet 4 | anthropic.claude-sonnet-4-* | ap-northeast-1 |
| Qwen3-235B | qwen.qwen3-235b-* | ap-northeast-1 |
| DeepSeek-V3 | deepseek.v3-* | ap-northeast-1 |
| GPT-OSS-120B | openai.gpt-oss-120b-* | ap-northeast-1 |

### 推論パラメータ（全モデル共通）

```
temperature: 0.0
top_p: 1.0
max_tokens: 128
seed: 0（モデルが対応する場合）
```

temperature=0.0 により決定的な出力を得ている。同一入力に対して同一出力が期待される。

---

## 2. プロンプト全文（再現性の根拠）

スクリプト: `scripts/big5/score_big5_bedrock.py`

### 英語版プロンプト（デフォルト: --prompt_lang en）

```
Your task is to respond to the following IPIP-NEO-120 question based on the
participant's daily diaries of the most significant event that occurred during
the day, provided below. Respond as though you are the individual who generated
these thoughts, reflecting their personality traits.

Base your answer on inferred personality traits. Think carefully about what the
thoughts imply about tendencies and behaviors.

For each question, select the most appropriate option:
– Very Inaccurate: The statement is definitely false or the participant would
  strongly disagree with it.
– Moderately Inaccurate: The statement is mostly false or the participant would
  generally disagree with it.
– Neither Accurate Nor Inaccurate: The participant would be neutral on the
  statement, cannot decide, or find the statement equally true and false.
– Moderately Accurate: The statement is mostly true or the participant would
  generally agree with it.
– Very Accurate: The statement is definitely true or the participant would
  strongly agree with it.

IPIP-NEO-120 question to answer:
{statement}

Participant's daily diaries:
{transcript}

Your response must be exactly one of:
Very Inaccurate
Moderately Inaccurate
Neither Accurate Nor Inaccurate
Moderately Accurate
Very Accurate

Do not include any explanation, punctuation, or additional text.
Return only the exact phrase from the list above.
```

### 日本語版プロンプト（--prompt_lang ja）

```
あなたのタスクは、以下に示す参加者の「その日もっとも重要だった出来事」に関する
日記（テキスト）を根拠として、IPIP-NEO-120 の質問項目に回答することです。
あなた自身がこの日記を書いた本人になりきって、その人の性格特性が反映されるように
答えてください。
推論される性格特性に基づいて判断し、日記内容が示す傾向や行動をよく考えてください。

質問ごとに、最も適切な選択肢を次から1つだけ選んでください
（必ず下の英語の文言をそのまま返してください）:

IPIP-NEO-120 question to answer:
{statement}

Participant's daily diaries:
{transcript}

Your response must be exactly one of:
Very Inaccurate
Moderately Inaccurate
Neither Accurate Nor Inaccurate
Moderately Accurate
Very Accurate

Do not include any explanation, punctuation, or additional text.
Return only the exact phrase from the list above.
```

### プロンプト設計のポイント

- `{transcript}` にはモノローグ化した会話テキストが入る（1話者分の発話を連結）
- `{statement}` には IPIP-NEO-120 の 1 項目が入る（例: 「心配性だ」）
- 選択肢は英語で固定（日本語版でも回答は英語）→ 正規化の揺れを最小化
- 無効回答時は最大 5 回リトライ（`--paper_strict` モード）
- リトライ時は `REMINDER: Return only ONE exact phrase from the list.` を追記
- 全試行を `attempts.jsonl` に記録（監査可能）

---

## 3. 品質保証メカニズム

### 回答の正規化

```python
normalize_choice(text) → 5択のいずれか or None
```

- 完全一致を優先
- 部分一致（大文字小文字無視）でフォールバック
- どちらにも該当しない場合は None → リトライ or NaN

### リトライと失敗処理

- `--paper_strict` モード: 正規化後も無効な回答は破棄してリトライ（最大 5 回）
- `--on_fail nan`: 全リトライ失敗時は NaN（デフォルト）
- `--on_fail neutral`: 全リトライ失敗時は中央値（Neither Accurate Nor Inaccurate）

### 逆転項目の処理

```python
if rev == 1:
    score = 4.0 - score  # 0..4 の反転
```

### Cronbach's α（内的整合性）

各 trait × 各モデルで Cronbach's α を算出し、項目間の整合性を検証。
結果は `cronbach_alpha.csv` に保存。

---

## 4. Teacher 間一致度（4 モデル間の相関）

データソース: `docs/homework/teacher_agreement_big5.md`

| Trait | N | Mean off-diagonal r | 解釈 |
|-------|---|--------------------:|------|
| C | 120 | **0.699** | 最高。疑似教師として最も安定 |
| E | 120 | 0.640 | 高い |
| N | 120 | 0.603 | 中程度 |
| O | 120 | 0.559 | 中程度 |
| A | 120 | 0.435 | 最低。teacher 依存性が大きい |

### 査読対応の要点

- C の mean r=0.699 は「4つの独立した LLM が同じ話者に対して類似した C スコアを付けた」ことを意味する
- A の mean r=0.435 は teacher 依存性が大きく、A の結果は探索的として位置づける根拠になる
- 一致度が高い ≠ 正しい（LLM 間で共通のバイアスがある可能性）→ Limitation に明記

---

## 5. Ensemble の構築

- 4 モデルの item-level スコア（120 項目 × 4 モデル）を平均して ensemble を構築
- Ensemble の Cronbach's α:
  - CEJC: 全 trait α ≥ 0.78
  - CSJ: C/E/N/O 高 α、A のみ弱い（発話量依存）

---

## 6. 想定される査読質問と回答案

### Q1: 「LLM の採点は信頼できるのか？」

**回答**: 単一 LLM の採点は信頼性が不十分な可能性がある。そのため 4 つの独立した LLM を疑似教師として使用し、teacher 間一致度で安定性を検証した。C（誠実性）は mean r=0.699 と最も高い一致度を示し、3/4 教師で permutation test が有意（p<0.005）であった。本研究では LLM スコアを「真の性格」ではなく「テキストから推定可能な性格的傾向の代理指標」として位置づけている。

### Q2: 「プロンプトの設計根拠は？」

**回答**: IPIP-NEO-120 の原著論文に準拠した 5 件法を採用し、LLM に「本人になりきって回答する」よう指示した。選択肢は英語で固定し、正規化の揺れを最小化した。temperature=0.0 で決定的な出力を得ており、同一入力に対する再現性を担保している。

### Q3: 「日本語の会話テキストに英語のプロンプトを使うのはなぜか？」

**回答**: 選択肢の正規化精度を優先した。日本語の自由記述回答は表記揺れが大きく、5 択への正規化が困難になる。質問項目自体は日本語版（`items_ipipneo120_ja.csv`）を使用しており、LLM は日本語テキストを読んで英語の選択肢で回答する形式。日本語版プロンプト（`--prompt_lang ja`）も用意しており、指示文は日本語だが回答は英語で統一している。

### Q4: 「LLM 間で共通のバイアスがあるのでは？」

**回答**: その可能性は否定できない。4 モデルはいずれも大規模言語モデルであり、訓練データの重複や類似した推論パターンを持つ可能性がある。これは本研究の主要な限界の一つであり、将来的には人間評定との比較検証が必要である。ただし、A（協調性）の teacher 間一致度が 0.435 と低いことは、モデル間で一様なバイアスがあるわけではないことを示唆している。
