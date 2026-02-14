# CEJC（自宅・少人数）抽出 → Big5 を Bedrock 複数モデルで採点 → LLM平均を作成（再現ログ）
Date: 2026-02-15  
Owner: 福原玄

---

## 0) 今回の更新点（論文比較可能性を上げる改修）
次の一手として想定していた改善（a–d）のうち、**特に「論文比較可能性」を直撃する a/b を優先**して反映し、結果も更新した。

- (a) **プロンプトを論文の “exact prompt” にさらに寄せる**
  - 「**participant として答える**（Respond as though you are the individual…）」を明示し、  
    さらに **許容される選択肢の固定**と **出力制約（余計な文字禁止）**を強めた。  
    論文側もこの方針を明確に採用している。  
    【論文根拠：prompt が participant として回答するよう指示／固定選択肢／余計な文字禁止】:contentReference[oaicite:0]{index=0}
- (b) **尺度を 0–4（IPIP-NEO-120 のスコアリング）に揃える**
  - 論文の Sample2（IPIP-NEO-120）は **0(very inaccurate)〜4(very accurate)** の 5件法。  
    【論文根拠：0〜4 の明記】:contentReference[oaicite:1]{index=1}
- (c) 日本語版 IPIP 項目（または標準尺度）へ寄せる（※要継続）
- (d) 可能なら自己報告/人手評定を付与し妥当性相関を見る（※要継続）

> 注：論文は **「各 item を別会話として投げる」「許容されない出力なら破棄して再プロンプト」**を明示している。  
> 【論文根拠：invalid response は破棄して re-issue／各 item は new conversation】:contentReference[oaicite:2]{index=2}

---

## 1) 目的
- 元論文「Assessing personality using zero-shot generative AI scoring ...」の **daily diary / idiographic narrative** に寄せて、  
  日本語会話コーパスから **日常（自宅・少人数）** 条件を作り、Big5 を LLM zero-shot で採点する。
- 論文では「**複数LLMの平均が最も強い**」「LLMを複数 rater とみなす」方向性が取られており、  
  本実験でも **複数モデルの trait score を揃え、モデル平均（mean/sd）** を作る。

（論文は Sample2 で “daily diaries” を用い、参加者が「その日の最も重要な出来事」を短く語る形式を採っている。）  
【論文根拠：most significant event の daily diary prompt】:contentReference[oaicite:3]{index=3}

---

## 2) なぜ CSJ ではなく CEJC を選んだか
- 本タスクは「日記的 / 自然な独り語り（diary-like）」に近い条件が必要。  
- **CEJC は会話一覧メタデータに “場所（例：自宅）/ 活動（例：食事）/ 話者数” 等があり**、  
  “自宅・少人数” の抽出が **メタデータ駆動で再現可能**。
- 一方 CSJ は（少なくとも本タスクの狙いに対して）スピーチ寄りの条件になりやすく、  
  diary-like 条件の構成が難しい（メタの粒度・条件設計の観点）。

---

## 3) 【重要】プロンプト比較（論文 Sample2 vs 本実装）
論文は **“participant prompt engineering” が重要な設計選択**であることも議論しているため、ここを明示的に比較・固定する。  
【論文根拠：participant prompt engineering の重要性】:contentReference[oaicite:4]{index=4}

### 3.1 論文（Sample2: IPIP-NEO-120 daily diaries）の prompt 構造（要点）
論文の Methods には Sample2 の **exact prompt** が掲載されている（全文は論文参照）。  
ここでは **比較に必要な構造要素**だけを抜き出す：

- **タスク宣言**：IPIP-NEO-120 の “質問（item）” に答える
- **コンテキスト**：participant の daily diaries（全文 transcript）
- **ロール指示**：**participant として答える**（本人になりきる）
- **選択肢固定**：Very Inaccurate / Moderately Inaccurate / Neither ... / Moderately Accurate / Very Accurate
- **出力制約**：**上の選択肢のいずれか “完全一致” の文字列のみ**。説明や句読点など一切禁止
- **invalid 時の扱い**：許容されない出力は破棄して **re-issue し直す**
- **運用**：item ごとに new conversation（独立に採点）

【論文根拠：participant 指示＋選択肢固定＋出力制約】:contentReference[oaicite:5]{index=5}  
【論文根拠：invalid は破棄して再プロンプト／item ごとに new conversation】:contentReference[oaicite:6]{index=6}

また Sample2 の IPIP-NEO-120 は **0〜4 の 5件法**（0=very inaccurate, 4=very accurate）。  
【論文根拠：0〜4 の明記】:contentReference[oaicite:7]{index=7}

### 3.2 本実装（CEJC diary-like）の prompt 方針（今回の改修点）
本実装は、上記構造に合わせて以下を **必須要件**として固定する：

- **Respond as participant** を明示（“採点者”ではなく “本人”）
- **固定選択肢**を論文 Sample2 と同等の5択に固定
- **出力制約**：許容文字列のどれか **1行のみ**
- **invalid は破棄して再試行**（最大リトライ回数を設定）
- **スコアリング**：5択を **0–4** に写像して item score 化（→ trait 集計）

> 実装確認のため、md 末尾に「プロンプト・尺度・items.csv の状態をダンプする検証コマンド」を用意（§7.3）。

---

## 4) 論文に近いモデル選定（ただし Tokyo リージョン制約あり）
本実験は **Bedrock ap-northeast-1（Tokyo）縛り**の中で利用可能な高性能モデルを優先し、
- `qwen.qwen3-235b-a22b-2507-v1:0`
- `global.anthropic.claude-sonnet-4-20250514-v1:0`（on-demand 制約で global prefix 使用）
- `deepseek.v3-v1:0`
- `openai.gpt-oss-120b-1:0`
を採用した。

---

## 5) 成果物（最終出力）
- `artifacts/big5/llm_scores/model=<...>/trait_scores.parquet`
- `artifacts/big5/llm_scores/model=<...>/item_scores.parquet`
- `artifacts/big5/llm_scores/model=<...>/cronbach_alpha.csv`
- `artifacts/big5/llm_scores/llm_avg_manifest_best.csv`
- `artifacts/big5/llm_scores/trait_scores_llm_average_strict_allmodels.parquet`

---

## 6) 再現手順（コマンド）
前提：
- Python 3.12 / venv
- AWS 認証情報（`AWS_PROFILE` 等）
- Bedrock region: `ap-northeast-1`

### 6.1 入力・前提確認
```bash
python -V
aws sts get-caller-identity
ls -la artifacts/big5/items.csv
````

### 6.2 CEJC メタデータ確認（convlist.parquet）

```bash
ls -la artifacts/tmp_meta/cejc_convlist.parquet

python - <<'PY'
import pandas as pd
p="artifacts/tmp_meta/cejc_convlist.parquet"
df=pd.read_parquet(p)
print("shape=", df.shape)
print("cols =", list(df.columns))
print(df.head(3).to_string(index=False))
PY
```

（convlist.parquet が無い場合：scrape を 1 本に固定して実行）

```bash
python scripts/cejc/scrape_cejc_convlist_no_lxml.py \
  --out_parquet artifacts/tmp_meta/cejc_convlist.parquet \
  --out_top_tsv artifacts/tmp_meta/cejc_diary_candidates_top200.tsv \
  --topk 200 \
| tee artifacts/tmp_meta/cejc_meta_profile.txt
```

### 6.3 diary-like（自宅・少人数）IDリスト作成（メタデータ駆動）

```bash
python - <<'PY'
import pandas as pd, re, os
inp="artifacts/tmp_meta/cejc_convlist.parquet"
out_ids="artifacts/tmp_meta/cejc_diary_home_small_ids.txt"
out_preview="artifacts/tmp_meta/cejc_diary_home_small_preview.tsv"
df=pd.read_parquet(inp)

# 話者数の数値化（列名は環境差があり得るので、存在する列で処理）
if "speaker_n" not in df.columns:
    src = "話者数" if "話者数" in df.columns else None
    if src:
        def to_int(x):
            s=str(x).strip()
            s=re.sub(r'^[^0-9]*','',s)
            s=re.sub(r'[^0-9].*$','',s)
            return int(s) if s.isdigit() else None
        df["speaker_n"]=df[src].map(to_int)

# 自宅 & 少人数（2-3）
place_col = "場所" if "場所" in df.columns else None
if place_col is None:
    raise SystemExit("場所 列が見つからないため抽出条件を調整してください")
sub=df.copy()
sub=sub[sub[place_col].astype(str).str.contains("自宅", na=False)]
sub=sub[sub["speaker_n"].isin([2,3])]

os.makedirs("artifacts/tmp_meta", exist_ok=True)
id_col = "会話ID" if "会話ID" in sub.columns else "conversation_id"
sub[id_col].dropna().astype(str).to_csv(out_ids, index=False, header=False)

keep=[c for c in ["会話ID","会話概要","話者数","形式","場所","活動","話者間の関係性","speaker_n"] if c in sub.columns]
sub[keep].head(100).to_csv(out_preview, sep="\t", index=False)

print("OK:", out_ids, "n_unique=", sub[id_col].nunique())
print("OK:", out_preview)
PY
```

### 6.4 utterances から「会話ごとのトップ話者」を抽出し擬似モノローグ化（Top1）

```bash
python - <<'PY'
import pandas as pd, os
utt_path="artifacts/_tmp_utt/cejc_utterances/part-00000.parquet"
ids_path="artifacts/tmp_meta/cejc_diary_home_small_ids.txt"
out_parquet="artifacts/cejc/monologues_diary_home_top1.parquet"
os.makedirs("artifacts/cejc", exist_ok=True)

utt=pd.read_parquet(utt_path)
ids=set(pd.read_csv(ids_path, header=None)[0].astype(str).tolist())
u=utt[utt["conversation_id"].astype(str).isin(ids)].copy()

u["dur"]=(u["end_time"].astype(float)-u["start_time"].astype(float)).clip(lower=0.0)

g=(u.groupby(["conversation_id","speaker_id"], as_index=False)
     .agg(speaker_dur=("dur","sum"), n_utt=("utterance_id","count"),
          n_chars=("text", lambda s: int("".join(map(str,s)).__len__()))))
tot=(u.groupby("conversation_id", as_index=False).agg(total_dur=("dur","sum")))
g=g.merge(tot,on="conversation_id",how="left")
g["dominance"]=g["speaker_dur"]/g["total_dur"].replace({0: pd.NA})

top1=(g.sort_values(["conversation_id","dominance"], ascending=[True,False])
        .groupby("conversation_id", as_index=False).head(1))

u=u.merge(top1[["conversation_id","speaker_id"]], on=["conversation_id","speaker_id"], how="inner")
u=u.sort_values(["conversation_id","start_time","end_time"])
text=(u.groupby(["conversation_id","speaker_id"], as_index=False)
        .agg(text=("text", lambda s: "\n".join(map(str,s)))))

out=top1.merge(text,on=["conversation_id","speaker_id"],how="left")
out=out.rename(columns={"speaker_dur":"main_dur"})
out=out[["conversation_id","speaker_id","text","dominance","total_dur","main_dur","n_utt","n_chars"]]

# 速度・筋のバランスで先頭50会話に限定
out=out.sort_values(["dominance","n_chars"], ascending=[False,False]).head(50).reset_index(drop=True)
out.to_parquet(out_parquet, index=False)
print("OK:", out_parquet, "n_conversations=", out["conversation_id"].nunique(), "rows=", len(out))
print(out.head(5).to_string(index=False))
PY
```

### 6.5 Bedrock で Big5 採点（複数モデル）

`artifacts/big5/models.txt`

```bash
cat > artifacts/big5/models.txt <<'TXT'
qwen.qwen3-235b-a22b-2507-v1:0
global.anthropic.claude-sonnet-4-20250514-v1:0
deepseek.v3-v1:0
openai.gpt-oss-120b-1:0
TXT

nl -ba artifacts/big5/models.txt
```

逐次実行（xargs の “command line too long” 回避）

```bash
MONO="artifacts/cejc/monologues_diary_home_top1.parquet"
ITEMS="artifacts/big5/items.csv"
ROOT="artifacts/big5/llm_scores"

while IFS= read -r MODEL; do
  [ -z "$MODEL" ] && continue
  SAFE="$(echo "$MODEL" | tr ':/' '__')"
  OUTDIR="$ROOT/model=$SAFE"
  echo "== RUN $SAFE ($MODEL) =="

  python scripts/big5/score_big5_bedrock.py \
    --monologues_parquet "$MONO" \
    --items_csv "$ITEMS" \
    --model_id "$MODEL" \
    --region "ap-northeast-1" \
    --out_dir "$OUTDIR" \
  || exit 1
done < artifacts/big5/models.txt
```

#### 詰まりポイント（再現メモ）

* `ValidationException: on-demand throughput isn’t supported`
  → `global.` prefix 付きの model id に置換して通す（例：Claude Sonnet 4）。

---

## 7) 結果サマリ（今回の最新結果）

### 7.1 Cronbach’s alpha（モデル別 / trait別）

凡例：🟩>=0.70 / 🟨0.50–0.70 / 🟥<0.50

| Model           | A       | C       | E       | N       | O       |
| --------------- | ------- | ------- | ------- | ------- | ------- |
| DeepSeek V3     | 🟨0.549 | 🟥0.451 | 🟨0.642 | 🟨0.649 | 🟨0.544 |
| Claude Sonnet 4 | 🟥0.378 | 🟨0.646 | 🟩0.760 | 🟨0.542 | 🟨0.571 |
| GPT-OSS 120B    | 🟨0.658 | 🟨0.624 | 🟩0.841 | 🟨0.693 | 🟨0.544 |
| Qwen3-235B      | 🟨0.618 | 🟨0.660 | 🟥0.395 | 🟨0.563 | 🟥0.422 |

参考：論文 Sample2 は **平均αが高く、最小でも 0.70** と報告されている（本実験はそこまで届いていない）。
【論文根拠：Sample2 の α（平均0.88、最低0.70）】

### 7.2 モデル別：平均Big5（50subjectの平均、0–4尺度）

色分け（見やすさのための区分）：🟦<1.5 / 🟩1.5–2.0 / 🟨2.0–2.5 / 🟧2.5–3.0 / 🟥>=3.0

| Model                   |          A |          C |          E |          N |          O |
| ----------------------- | ---------: | ---------: | ---------: | ---------: | ---------: |
| DeepSeek V3             |     🟧2.88 |     🟦1.23 |     🟦1.48 |     🟨2.02 |     🟨2.30 |
| Claude Sonnet 4         |     🟧2.80 |     🟩1.62 |     🟨2.38 |     🟨2.39 |     🟨2.35 |
| GPT-OSS 120B            |     🟧2.58 |     🟩1.55 |     🟨2.19 |     🟧2.70 |     🟨2.40 |
| Qwen3-235B              |     🟧2.44 |     🟩1.82 |     🟦1.34 |     🟨2.25 |     🟨2.32 |
| **LLM Mean (4 models)** | **🟧2.68** | **🟩1.56** | **🟨1.85** | **🟨2.34** | **🟨2.34** |

所見（数値の読み）：

* **C（誠実性）と E（外向性）が全体に低め**。データが “自宅・少人数会話→Top1話者の擬似モノローグ” であり、
  論文の「daily diary（最重要イベント）」と情報分布が異なる可能性がある（§8で考察）。
* α はモデル×trait でまだ不安定（🟥が残る）。特に Qwen の E/O が低い。

### 7.3 検証用：プロンプト／尺度／items の状態を md に残す（推奨）

「この結果が **どのプロンプト** と **どの尺度** と **どの item セット** から出たか」を確実に追跡するため、
以下を実行してログ化しておく（次回以降の比較が一気に楽になる）。

```bash
python - <<'PY'
import pandas as pd, textwrap, json, re

items="artifacts/big5/items.csv"
df=pd.read_csv(items)

print("== items.csv profile ==")
print("shape:", df.shape)
print("cols:", list(df.columns))
for col in ["trait","key","reverse","is_reverse","score_0","score_4"]:
    if col in df.columns:
        print("has:", col)

if "trait" in df.columns:
    print("\n-- n_items by trait --")
    print(df["trait"].value_counts().to_string())

rev_col = "reverse" if "reverse" in df.columns else ("is_reverse" if "is_reverse" in df.columns else None)
if rev_col:
    print("\n-- reverse flags by trait --")
    print(df.groupby("trait")[rev_col].sum().to_string())

# プロンプトは実装側の定数名に合わせて取り出す（例：PROMPT_TMPL / PROMPT_TEMPLATE 等）
# ここではファイルを直接読む（手元の実装に合わせてパス調整）
path="scripts/big5/score_big5_bedrock.py"
print("\n== prompt template snapshot (first 200 lines grep) ==")
with open(path, "r", encoding="utf-8") as f:
    txt=f.read()

# ありがちな定数名を探索
cands=["PROMPT_TMPL","PROMPT_TEMPLATE","SYSTEM_PROMPT","TEMPLATE"]
for k in cands:
    if k in txt:
        print(f"\n-- found token: {k} --")

# 先頭200行だけ表示（安全）
head="\n".join(txt.splitlines()[:200])
print(head)
PY | tee artifacts/big5/prompt_items_snapshot_20260215.txt
```

---

## 8) 考察（論文との比較と、本実験の結果の位置づけ）

### 8.1 いま「どこまで論文比較可能」か

* **プロンプト構造**と **0–4尺度**を論文 Sample2 に寄せたことで、
  少なくとも「LLM を複数 rater として同一プロトコルで item レベル採点 → trait 化できる」点は比較可能性が上がった。
  【論文根拠：participant として item に回答／選択肢固定／スコア変換】
* 一方で論文 Sample2 は **(i) daily diary（最重要イベント）**、**(ii) 同一人物×複数日（idiographic）**、
  **(iii) self-report（同一尺度）と相関評価** が揃っている。
  本実験は **会話×話者（擬似モノローグ）**であり、外部基準（自己評定/人手評定）が未整備のため、
  現段階の主張は「論文設計に寄せた再現可能パイプラインの構築＋内部一貫性の予備評価」まで。

### 8.2 α（内部一貫性）が論文より低い理由の候補

論文は Sample2 で α が高く（最低0.70）と報告されているが、本実験では trait/モデルにより 🟥が残る。
【論文根拠：Sample2 の α（平均0.88、最低0.70）】

原因候補（優先度順）：

1. **項目セットの差**（本実験 items.csv が IPIP-NEO-120 と同等の120項目でない／翻訳・短縮・改変がある）
2. **逆転項目（reverse-key）の扱い**（reverse の付け忘れ・適用漏れがあると平均も α も崩れる）
3. **テキスト条件の差**（daily diary “最重要イベント” ではなく、会話からの Top1 抽出で “人格を示す情報密度” が落ちる）
4. **出力分布の偏り**（モデルが安全に “低め/中立寄り” を選びやすい等）
5. **言語差・文体差**（日本語会話→擬似モノローグ化の影響）

> まずは §7.3 のスナップショットで「items と reverse の実態」を md に固定し、
> その上で **(a) item 数を増やす／(b) reverse を監査する**のが最短。

---

## 9) 次の一手（論文比較可能性を“もう一段”上げる）

（あなたの方針 a–d を、実装優先度つきで再掲）

1. **(a) プロンプトを論文 exact prompt にさらに寄せる（participant 明示＋固定選択肢＋出力制約）**

   * → 今回反映。今後は §7.3 で prompt をログ固定して比較可能にする。
2. **(b) 0–4尺度に揃える**

   * → 今回反映（IPIP-NEO-120 は 0–4）。【論文根拠】【：0–4】
3. **(c) 日本語版IPIP項目（または対応する標準尺度）へ寄せる**

   * 可能なら「翻訳の根拠（出典）」が明示できる項目群に差し替え、items.csv の出典列を持つ。
4. **(d) 自己報告/人手評定を一部に付与し妥当性相関を見る**

   * 例：50subject のうち 10–15件だけでも、人手で Big5（短縮版でも可）を付けて収束傾向を見る。
   * 論文は self-report と相関比較を主評価としているため、ここが揃うと一気に論文比較が可能になる。

---

## 10) 注意（データ取り扱い）

* corpora の本文（発話テキスト）や parquet 本体は、ライセンス・容量の観点で **git 管理対象にしない**。
* git に残すのは **再現コマンド / スクリプト / ログ（本md＋§7.3のスナップショット）** を中心にする。

---

## A/C/E/N/O（Big Five）の意味（論文のNEOドメイン）

* A = Agreeableness（協調性）
* C = Conscientiousness（誠実性）
* E = Extraversion（外向性）
* N = Neuroticism（神経症傾向）
* O = Openness（開放性）

（論文は Sample2 で IPIP-NEO-120 により 5ドメインを測定）

```

---

補足（率直な所感）  
今回の結果は、前回より **α が「それっぽいレンジ」に入ってきた trait が増えていて**、(a)(b) の効果は出てる印象です。一方で、

- **C と E の平均が全体に低い**
- **Qwen の E/O が低α（0.395/0.422）**
- **Sonnet4 の A が 0.378 と低い**

あたりは、**items.csv の内容（項目数・reverse・翻訳品質）か、テキスト条件（Top1擬似モノローグ）**がボトルネックになってる可能性が高いです。

次の最短ルートは、md内にも入れたとおり **§7.3 の「prompt/items スナップショット」を残しつつ、reverse の監査**（Traitごとの reverse 数・適用有無）を先に潰すのが良さそうです。
```
