# CEJC（自宅・少人数）抽出 → 擬似日記（Top1話者） → IPIP-NEO-120(日本語) で Big5 採点 → 複数LLM平均（再現ログ）＋ CSJ（対話D）検証ログ
Date: 2026-02-16  
Owner: 福原玄  
Last updated: 2026-02-17

---

## 0) これを一言で（何も知らない人向け）
**「日常会話の文字起こし」から、性格テスト（Big5）120問をLLMに回答させて点数化し、4つのLLMの平均を“最終スコア”として作る**実験です。  
論文が主張する「**複数モデルの平均が強い（安定する）**」を、今回の日本語会話データでも **Cronbach’s α（内部一貫性）**で確かめました。

---

## 1) 今回“完了”と判断した論文検証の範囲（何が言えて、何がまだか）
本mdで完了したのは、論文の主張のうち次の部分です：

- ✅ **論文のプロトコル（participantとして回答／固定5択／余計な文字禁止／invalidは破棄）**に寄せて、  
  itemレベル（120問×被験者）を機械的に採点できる“再現パイプライン”を構築した。
- ✅ **複数モデル平均（ensemble）が単体モデルより内部一貫性（α）が高い**ことを確認した  
  → 今回の主結果（§8）＋ CSJでも同様の傾向を追試（§14）。

一方、論文のもう一つの大きな主張である
- ⏳ **自己報告（self-report）との相関が高い**
は、外部基準（自己評定／人手評定）を付与していないため、**本mdでは未検証**（将来ステップ）。

---

## 2) 全体フロー（図）
```mermaid
flowchart TD
  A[CEJC convlist（会話メタ）取得] --> B[条件抽出: 自宅 & 話者数2-3]
  B --> C[utterances から Top1話者を抽出]
  C --> D[Top1話者の発話を連結して擬似モノローグ化]
  D --> E[擬似モノローグを v1 として固定（sha256付与）]
  E --> F[IPIP-NEO-120 日本語 120問]
  F --> G[Bedrockで4モデル採点（0-4, reverse対応）]
  G --> H[QC: fallback=0, rows一致, n_models=4]
  H --> I[4モデル平均ensembleを作成]
  I --> J[α（単体 vs ensemble）で“平均が強い”を検証]
````

---

## 3) なぜ CSJ ではなく CEJC を選んだか（コーパス選定の理由）

* 目標が「**daily diary / idiographic narrative（“日記っぽい独り語り”）**」に近い条件であるため。
* **CEJC は会話メタデータに “場所（例：自宅）/ 活動 / 話者数” 等があり**、
  「自宅・少人数」を **メタデータ駆動で再現可能に抽出**できる。
* CSJ は（少なくともこの目的に対して）スピーチ寄り条件になりやすく、
  “日記っぽさ”条件の設計・再現が難しい。

> ※ただし、次ステップとして「発話量確保」「形式差（対話/講演）の影響」を見るために、CSJ（対話D）も追試対象とした（§14）。

---

## 4) 今回のデータセット定義（固定化・バージョニング）

### 4.1 50 subject（会話×話者）を作る方法

* CEJCの会話から **「自宅」かつ「話者数2〜3」**の会話IDを抽出
* utterances から **会話内で最も支配的（dominanceが最大）な Top1話者**だけ残す
* Top1話者の発話テキストを時系列に連結し、**擬似モノローグ（擬似日記）**として扱う
* 速度と筋のバランスで **上位50会話**に限定（rows=50, unique_conversations=50）

### 4.2 v1固定（sha256を付ける）

* 生成した擬似モノローグparquetを **`monologues_diary_home_top1_v1.parquet`**として固定
* **sha256** を付与して「同じ入力から同じ結果」を主張できるようにする

実測 sha256：

* `a71b14ef91c180798ba47c836621ce591b1ab06c70cf30c2a8debf20117708ba`

ファイル：

* `artifacts/cejc/monologues_diary_home_top1_v1.parquet`
* `artifacts/cejc/monologues_diary_home_top1_v1.sha256.txt`

> ※ shaファイル作成で `tee` を誤用して詰まった場合は、下の“正しい一発”を使う（§7.5）。

---

## 5) 質問紙（items）とスコアリング（論文互換性の要）

### 5.1 items は IPIP-NEO-120（日本語 120項目）

* 今回の“論文比較可能性”の中心は、**120問（各特性24問）**を使うこと。
* 実行に使用した items（例）：

  * `artifacts/big5/items_ipipneo120_ja.csv`（120問）

> 注意：過去の試行で `items.csv` が 30問の軽量版だった時期があるため、
> 本mdの「最終結果」は **必ず 120問版（ipipneo120ja120）**を指すよう、出力ディレクトリ名でも識別している（§6.2）。

### 5.2 0–4の5件法（reverse対応）

* 選択肢（固定5択）：

  * Very Inaccurate / Moderately Inaccurate / Neither Accurate nor Inaccurate / Moderately Accurate / Very Accurate
* スコア変換（0〜4）：

  * Very Inaccurate = 0, … , Very Accurate = 4
* reverse項目は **score = 4 - base** に変換

---

## 6) LLM採点プロトコル（論文に寄せた設計）

論文側の要点（本実装で必須化した点）：

* **participant として回答**（採点者ではなく“本人になりきる”）
* **選択肢は固定5択**
* **出力は選択肢の完全一致のみ（説明・句読点・余計な文字禁止）**
* invalid（許容されない出力）は **破棄して再試行**
* item は独立に投げる（new conversation運用）

本実装では、この方針を **strict** として固定し、
“下流で fallback になった”などを検出できるよう、QC（§9）も必ず残す。

---

## 7) 再現手順（コマンド）— 最初から最後まで

前提：

* Python 3.12 / venv
* AWS 認証情報（`AWS_PROFILE` 等）
* Bedrock region: `ap-northeast-1`

### 7.1 入力・前提確認

```bash
python -V
aws sts get-caller-identity
```

### 7.2 CEJC メタデータ（convlist.parquet）確認

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

（convlist.parquet が無い場合：scrape）

```bash
python scripts/cejc/scrape_cejc_convlist_no_lxml.py \
  --out_parquet artifacts/tmp_meta/cejc_convlist.parquet \
  --out_top_tsv artifacts/tmp_meta/cejc_diary_candidates_top200.tsv \
  --topk 200 \
| tee artifacts/tmp_meta/cejc_meta_profile.txt
```

### 7.3 diary-like（自宅・少人数）IDリスト作成（メタデータ駆動）

```bash
python - <<'PY'
import pandas as pd, re, os
inp="artifacts/tmp_meta/cejc_convlist.parquet"
out_ids="artifacts/tmp_meta/cejc_diary_home_small_ids.txt"
out_preview="artifacts/tmp_meta/cejc_diary_home_small_preview.tsv"
df=pd.read_parquet(inp)

# 話者数の数値化（列名は環境差があり得るため存在列で処理）
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

### 7.4 utterances から Top1 話者を抽出し擬似モノローグ化（Top1）

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

# 速度・筋のバランスで上位50会話に限定
out=out.sort_values(["dominance","n_chars"], ascending=[False,False]).head(50).reset_index(drop=True)
out.to_parquet(out_parquet, index=False)
print("OK:", out_parquet, "n_conversations=", out["conversation_id"].nunique(), "rows=", len(out))
print(out.head(5).to_string(index=False))
PY
```

### 7.5 v1固定（コピー＋sha256付与）— 正しい一発

```bash
cd ~/cpsy
cp -a artifacts/cejc/monologues_diary_home_top1.parquet \
      artifacts/cejc/monologues_diary_home_top1_v1.parquet

python - <<'PY' | tee artifacts/cejc/monologues_diary_home_top1_v1.sha256.txt
import hashlib, pathlib
p=pathlib.Path("artifacts/cejc/monologues_diary_home_top1_v1.parquet")
h=hashlib.sha256(p.read_bytes()).hexdigest()
print("sha256", h)
PY
```

### 7.6 Bedrock で Big5 採点（4モデル × 120 items）

#### モデル

```bash
cat > artifacts/big5/models.txt <<'TXT'
qwen.qwen3-235b-a22b-2507-v1:0
global.anthropic.claude-sonnet-4-20250514-v1:0
deepseek.v3-v1:0
openai.gpt-oss-120b-1:0
TXT
nl -ba artifacts/big5/models.txt
```

#### 実行（dataset名に sha と items を埋め込む）

```bash
MONO="artifacts/cejc/monologues_diary_home_top1_v1.parquet"
ITEMS="artifacts/big5/items_ipipneo120_ja.csv"   # 120 items はこちら
ROOT="artifacts/big5/llm_scores"
SHA="a71b14ef"  # sha256先頭8桁（見やすさ用）

DATASET="dataset=cejc_diary_home_top1_v1__sha=${SHA}__items=ipipneo120ja120"
OUTROOT="$ROOT/$DATASET"

while IFS= read -r MODEL; do
  [ -z "$MODEL" ] && continue
  SAFE="$(echo "$MODEL" | tr ':/' '__')"
  OUTDIR="$OUTROOT/model=$SAFE"
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

  * → `global.` prefix 付きの model id を使う（Claude Sonnet 4 は `global.anthropic...`）

---

## 8) 主結果（論文主張「複数モデル平均が強い」を “内部一貫性(α)” でも検証）

### 8.0 原著（Sample2: daily diaries）で報告されている α（比較用ベンチマーク）

原著は item-level 応答を使って、各trait×各LLMの Cronbach’s α を算出している。要点は以下：

* **Sample2（daily diaries）**：LLM生成traitの内部一貫性は **平均α=0.88**、かつ **全モデル×全尺度で最小α=0.70**。self-report の平均αも **0.88**。
  【論文根拠：Sample2 平均α=0.88、self-report平均α=0.88、最小α=0.70】
* **Sample1（spontaneous thoughts）**：平均α=0.76（self-report平均α=0.78）。ただし **Openness のαがLLM間で低下（0.26–0.79）**。
  【論文根拠：Sample1 平均α=0.76 / self-report0.78 / Oのレンジ0.26–0.79】

> 注：原著の「平均α=0.88」は **“全trait×全LLMをまとめた平均”**。本mdの ensemble は **“4モデル平均で1つのスコア系列を作ってから trait別α”**なので、厳密に同一集計ではないが、目安として比較可能。

---

### 8.1 単体モデルの Cronbach’s α（120 items = 各trait24問）

凡例：🟩>=0.70 / 🟨0.50–0.70 / 🟥<0.50

| Model (Bedrock) |          A |          C |          E |          N |          O |
| --------------- | ---------: | ---------: | ---------: | ---------: | ---------: |
| Qwen3-235B      | 🟥0.470250 | 🟩0.739250 | 🟩0.816709 | 🟩0.704363 | 🟨0.641231 |
| Claude Sonnet 4 | 🟩0.760230 | 🟩0.818102 | 🟩0.779544 | 🟩0.835077 | 🟩0.859147 |
| DeepSeek V3     | 🟥0.293894 | 🟩0.704180 | 🟩0.736994 | 🟩0.794459 | 🟨0.689223 |
| GPT-OSS 120B    | 🟩0.824672 | 🟩0.899156 | 🟩0.796702 | 🟩0.842254 | 🟩0.780861 |

観察：

* 単体モデルだと、特に **A（協調性）**がモデルによって不安定（🟥が出る）
* ただし次の **ensemble（4モデル平均）**で一段安定する（次節）

---

### 8.2 4モデル平均（ensemble）の Cronbach’s α（今回の核心）

**ensemble=item_mean_4models**（itemごとに4モデル平均→trait集計）

| Ensemble          |          A |          C |          E |          N |          O |
| ----------------- | ---------: | ---------: | ---------: | ---------: | ---------: |
| item_mean_4models | 🟩0.781606 | 🟩0.904440 | 🟩0.874387 | 🟩0.875451 | 🟩0.862863 |

結論（このmd内での論文検証として言えること）：

* **単体モデルで崩れる特性（例：A）も含め、4モデル平均では全特性で α>=0.70 を満たした**
* よって「**複数モデル平均が強い**」は、少なくとも **内部一貫性（α）の観点でも**、日本語会話（CEJC擬似日記）で再現できた

> 参考：原著が主に評価している “self-report との相関（収束妥当性）” は本mdでは未検証（外部基準未付与）。

---

### 8.3 論文（Sample2）との “α” 定量比較（先生向けワンメッセージ）

ここでは、比較しやすいように「平均」と「最小」を並べる。

* 本実験（ensemble）の **trait平均α = 0.860**（= (A,C,E,N,O)/5）、**最小α = 0.782**（A）
* 原著 Sample2 は **平均α=0.88**、**最小α=0.70**（全モデル×全尺度の最小）
  【論文根拠：Sample2 平均α=0.88 / 最小α=0.70】

| Setting    | 対象                                                                      | αの集計                                     |   平均α |   最小α |
| ---------- | ----------------------------------------------------------------------- | ---------------------------------------- | ----: | ----: |
| 原著 Sample2 | nightly daily diaries（N=108, IPIP-NEO-120）                              | 全trait×全LLM平均                            |  0.88 |  0.70 |
| 本実験        | CEJC「自宅・少人数」Top1擬似モノローグ（N=50, IPIP-NEO-120 日本語版120項目, 4models ensemble） | trait別α（IPIP-NEO-120 120項目の ensemble 系列） | 0.860 | 0.782 |

解釈（控えめな主張）：

* **“daily diaryそのもの” ではない（会話Top1抽出）**にもかかわらず、ensemble後の α は **原著 Sample2 の水準にかなり近い**。
* ただし原著は “self-report 相関” が主評価のため、次はそこを揃えると議論が一気に強くなる。

---

### 8.4 （参考）原著の「複数モデル平均が強い」は “相関 r” でも確認されている

原著 Sample2 では、self-report との収束相関について：

* 個別LLMの “相関平均” は **0.37〜0.45** 程度
* **LLM average の平均相関は 0.44**
* さらに “全LLM×全trait の相関平均” は **r=0.415**（Sample1/2で同一）
  【論文根拠：Sample2 の相関平均レンジ / LLM average=0.44 / r=0.415】

> 本mdは相関（外部基準）未検証だが、今回 **αがensembleで改善**しているのは、原著が述べる “wisdom of the crowds（複数rater平均）” と整合的。

---

## 9) QC（再現性・監査のためのチェック）

### 9.1 行数・fallback の検証（4モデルすべてOK）

* n_subjects = 50
* n_items = 120 → 期待行数は 50×120 = 6000 / モデル

以下のような検証を必ず残す：

```bash
python - <<'PY'
import pandas as pd
from pathlib import Path

root = Path("artifacts/big5/llm_scores/dataset=cejc_diary_home_top1_v1__sha=a71b14ef__items=ipipneo120ja120")
items = pd.read_csv("artifacts/big5/items_ipipneo120_ja.csv")
n_items = len(items)

print("root =", root)
print("n_items =", n_items)
print()

for d in sorted(root.glob("model=*")):
    item_pq = d/"item_scores.parquet"
    if not item_pq.exists():
        continue

    df = pd.read_parquet(item_pq)
    n_subj = df[["conversation_id","speaker_id"]].drop_duplicates().shape[0]
    expected = n_subj * n_items
    n_rows = len(df)

    fb = 0
    for col in ["choice_raw","choice_norm"]:
        if col in df.columns:
            fb += int((df[col].astype(str)=="NEUTRAL_FALLBACK").sum())

    ok = (n_rows==expected and fb==0)
    print(d.name)
    print(f"  subjects={n_subj}  expected_rows={expected}  item_rows={n_rows}  fallback={fb}  OK={ok}")
PY
```

### 9.2 ensembleの “n_models が常に4” を確認（穴なし）

```bash
python - <<'PY'
import pandas as pd
from pathlib import Path

root = Path("artifacts/big5/llm_scores/dataset=cejc_diary_home_top1_v1__sha=a71b14ef__items=ipipneo120ja120")
ens = root/"ensemble=item_mean_4models"/"item_scores_ensemble_mean.parquet"
df = pd.read_parquet(ens)

print(df[["n_models"]].describe())
print("n_models_min =", df["n_models"].min())
PY
```

---

## 10) 生成物（ファイル一覧）

### 10.1 単体モデル

`artifacts/big5/llm_scores/dataset=cejc_diary_home_top1_v1__sha=a71b14ef__items=ipipneo120ja120/model=<MODEL_SAFE>/`

* `item_scores.parquet`
* `trait_scores.parquet`
* `cronbach_alpha.csv`

### 10.2 ensemble

`.../ensemble=item_mean_4models/`

* `item_scores_ensemble_mean.parquet`
* `trait_scores_ensemble_mean.parquet`
* `cronbach_alpha_ensemble_mean.csv`

---

## 11) Appendix A（2026-02-15）Smoke strict_v2：NEUTRAL_FALLBACK 多発の修正ログ（証跡）

> 本番の 120items×50subjects とは別に、初期の smoke 実行で発生した不具合の“原因→対処→復旧”を残す。
> 結論として、本番系（§8〜§10）は fallback=0 を達成している。

### A.1 事象（症状）

smoke（120 items, 1 subject）で `NEUTRAL_FALLBACK` が大量発生。

* before（バックアップ `item_scores.jsonl.bak`）：`NEUTRAL_FALLBACK` **83/120**
* after（修正版 `item_scores.jsonl`）：`NEUTRAL_FALLBACK` **0/120**

### A.2 原因（root cause）

`attempts.jsonl` に保存される `choice_raw / choice_norm` が **途中で切り捨て（truncate）**され、
固定選択肢と完全一致せず `valid:false` 扱い → downstream で fallback になっていた。

例：

* 本来 `Neither Accurate nor Inaccurate` なのに `Neither Accurate nor In` で切れる、等。

### A.3 対処（復旧）

* `attempts.jsonl` 側の `choice_*` を **prefix一致で正規化**し、
* `item_scores_fixed.* / trait_scores_fixed.* / cronbach_alpha_fixed.csv` を再生成
* 結果として fallback を 0 に復旧

（詳細スクリプトは、当該 OUTDIR 内に残しているものを参照）

---

## 12) Appendix B（2026-02-16）本番系：NaN 1件（GPT-OSS / item21）の修復ログ（bak付き）

### B.1 事象

* `ipipneo120ja120` 本番系で、GPT-OSS の N trait に **NaN が1件**混入
* 該当：

  * `conversation_id=S001_011, speaker_id=IC02, item_id=21（N）, reverse=0`

症状：

* 1行だけ `choice_norm / score` が NaN（choice_raw に長いログが混入してパース不能になった）

### B.2 対処方針（論文プロトコルに合わせた扱い）

* その1問だけを **単発で再実行**して、正しい1行を得る
* 元 `item_scores.parquet` は **bak を残した上で**、該当1行だけ差し替える
* その後、`trait_scores.parquet` と `cronbach_alpha.csv` を再計算

### B.3 証跡（バックアップと最終出力）

バックアップが残っていること：

* `item_scores.parquet.bak_nanfix`（存在確認OK）

ensemble 出力：

* `cronbach_alpha_ensemble_mean.csv`
* `item_scores_ensemble_mean.parquet`
* `trait_scores_ensemble_mean.parquet`

### B.4 修復手順（コピペ用：1回で完結する安全版）

> ここは“先生に見せる”というより「再現性・監査」のための作業ログ。
> 必要ならそのまま再実行できる形にしてある。

```bash
cd ~/cpsy

python - <<'PY'
import pandas as pd
from pathlib import Path
import shutil

ROOT = Path("artifacts/big5/llm_scores/dataset=cejc_diary_home_top1_v1__sha=a71b14ef__items=ipipneo120ja120")
MODEL_DIR = ROOT/"model=openai.gpt-oss-120b-1_0"

orig_p = MODEL_DIR/"item_scores.parquet"
bak_p  = MODEL_DIR/"item_scores.parquet.bak_nanfix"

# 単発再実行で得た “正しい1行だけ” のparquet（ユーザー側で生成済みのものを指定）
fix_p  = Path("artifacts/tmp_fix/out_item21_gptoss/item_scores.parquet")

# 1) fixが1行であることを確認
fix = pd.read_parquet(fix_p)
assert len(fix)==1, f"fix rows={len(fix)}"
r = fix.iloc[0]
assert r["conversation_id"]=="S001_011" and r["speaker_id"]=="IC02" and int(r["item_id"])==21, "fix row key mismatch"

# 2) バックアップ（未作成なら作る）
if not bak_p.exists():
    shutil.copy2(orig_p, bak_p)

# 3) 置換（該当1行を落としてfixを追加）
df = pd.read_parquet(orig_p)
key = (df["conversation_id"]=="S001_011") & (df["speaker_id"]=="IC02") & (df["item_id"]==21)
print("target_rows_in_orig =", int(key.sum()))
assert int(key.sum())==1, "target row not found or duplicated"

df2 = pd.concat([df[~key], fix], ignore_index=True)

# NaNが残ってないことを確認（score）
na = int(df2["score"].isna().sum())
print("score_na_after_patch =", na)
assert na==0, "score NaN still exists after patch"

# 4) item_scores を書き戻し
df2.to_parquet(orig_p, index=False)

# 5) trait_scores 再生成
trait = (df2.groupby(["conversation_id","speaker_id","trait"], as_index=False)
           .agg(trait_score=("score","mean")))
trait.to_parquet(MODEL_DIR/"trait_scores.parquet", index=False)

# 6) cronbach_alpha 再生成（complete-case）
def cronbach_alpha(wide: pd.DataFrame) -> float:
    wide = wide.dropna(axis=1, how="all").dropna(axis=0, how="any")
    k = wide.shape[1]
    if k < 2:
        return float("nan")
    item_vars = wide.var(axis=0, ddof=1)
    total_var = wide.sum(axis=1).var(ddof=1)
    if total_var == 0 or pd.isna(total_var):
        return float("nan")
    return (k/(k-1)) * (1 - item_vars.sum()/total_var)

rows=[]
for t in sorted(df2["trait"].unique()):
    sub = df2[df2["trait"]==t]
    wide = sub.pivot_table(index=["conversation_id","speaker_id"], columns="item_id", values="score")
    rows.append({
        "trait": t,
        "alpha": cronbach_alpha(wide),
        "n_subjects": wide.dropna(axis=0, how="any").shape[0],
        "k_items": wide.shape[1]
    })

alpha_df = pd.DataFrame(rows).sort_values("trait")
alpha_df.to_csv(MODEL_DIR/"cronbach_alpha.csv", index=False)

print("\n== updated cronbach_alpha ==")
print(alpha_df.to_string(index=False))
print("\nbackup =", bak_p)
PY
```

修復後の該当行（例）：

* `conversation_id=S001_011, speaker_id=IC02, item_id=21, trait=N`
* `choice_norm=Moderately Inaccurate, score=1.0`

---

## 13) データ取り扱い（重要）

* corpora の本文（発話テキスト）や大きな parquet 本体は、ライセンス・容量の観点で **git 管理対象にしない**
* git に残すのは **再現コマンド／スクリプト／QCログ／このmd** を中心にする
* 本mdでは **dataset sha** により、入力固定を明示している

---

## 14) CSJチャレンジ（対話D）: 自然寄り side 抽出 → Big5 採点 → 安定性/感度分析（N=6 → N=36）

### 14.0 目的（CEJCの次ステップ）

* CSJの **対話（D）** から、（可能な範囲で）自然寄りの発話を抽出し、
  IPIP-NEO-120（日本語120項目）を **Bedrock複数LLM** で採点して Big5 を推定する。
* まずは **CSJでも「複数モデル平均（ensemble）が強い」**が出るかを、Cronbach’s α（内部一貫性）で確認する。
* 追加で、

  * **モデル感度（leave-one-out）**：特定モデルがαを壊していないか
  * **発話量（長さ）感度（top-k by n_chars）**：短い発話を混ぜるとどの特性が崩れるか
    を定量化する。

---

### 14.1 データセット定義

#### 14.1.1 Pilot（N=6）

* 目的：CSJでもパイプラインが問題なく回り、ensembleの改善が見えるかを **低コストで確認**
* 生成済み出力（Big5）root：

  * `artifacts/big5/llm_scores/dataset=csjD_side_v4_pass6_v1__sha=767447f2__items=ipipneo120ja120/`

#### 14.1.2 ix36 all sides（N=36）

* 目的：CSJ側で **母数を増やし**、結果の安定性を確認
* 対象：`metrics_interaction_csj_v1.parquet` に載っている **18会話×L/R = 36 side**
* 入力：

  * `artifacts/phase7/metrics_interaction_csj_v1.parquet`
  * `artifacts/_tmp_utt/csj_utterances/part-00000.parquet`
* monologues v1：

  * `artifacts/csj/monologues_csj_ix36_all_sides_v1.parquet`
  * sha256: `de3fd2e3734054a280fe3d4a01c6a0860f81855665a2a393e833757dcecf129d`
* 発話量（参考）：

  * n_chars（36件）: mean=3510 / median=2877 / max=7672（CEJCより短め）
* 出力（Big5）root：

  * `artifacts/big5/llm_scores/dataset=csj_ix36_all_sides_v1__sha=de3fd2e3__items=ipipneo120ja120/`

---

### 14.2 再現手順（ix36：monologues作成→v1固定）

#### 14.2.1 monologues生成（36 sideを全文連結）

```bash
cd ~/cpsy
python - <<'PY'
import pandas as pd
from pathlib import Path

utt_path="artifacts/_tmp_utt/csj_utterances/part-00000.parquet"
ix_path ="artifacts/phase7/metrics_interaction_csj_v1.parquet"
out_parquet="artifacts/csj/monologues_csj_ix36_all_sides.parquet"

utt=pd.read_parquet(utt_path).copy()
utt["conversation_id"]=utt["conversation_id"].astype(str)
utt["speaker_id"]=utt["speaker_id"].astype(str)
utt["text"]=utt["text"].fillna("").astype(str)

ix=pd.read_parquet(ix_path).copy()
ix["conversation_id"]=ix["conversation_id"].astype(str)
ix["speaker_id"]=ix["speaker_id"].astype(str)

ids = ix[["conversation_id","speaker_id"]].drop_duplicates()

u=utt.merge(ids, on=["conversation_id","speaker_id"], how="inner").copy()
u=u.sort_values(["conversation_id","speaker_id","start_time","end_time"], kind="mergesort")

g=(u.groupby(["conversation_id","speaker_id"], as_index=False)
     .agg(n_utt=("text","count"),
          n_chars=("text", lambda s: int(sum(map(len, s.tolist())))),
          text=("text", lambda s: "\n".join(s.tolist()).strip())))

Path("artifacts/csj").mkdir(parents=True, exist_ok=True)
g.to_parquet(out_parquet, index=False)

prev=g.copy()
prev["head200"]=prev["text"].str.replace("\n"," ", regex=False).str.slice(0,200)
prev[["conversation_id","speaker_id","n_chars","n_utt","head200"]].to_csv(
    "artifacts/csj/monologues_csj_ix36_all_sides_preview.tsv", sep="\t", index=False
)

print("OK:", out_parquet, "rows=", len(g))
print("OK: artifacts/csj/monologues_csj_ix36_all_sides_preview.tsv")
print(g[["n_chars"]].describe().to_string())
PY
```

#### 14.2.2 v1固定（コピー＋sha256付与）

```bash
cd ~/cpsy
cp -a artifacts/csj/monologues_csj_ix36_all_sides.parquet \
      artifacts/csj/monologues_csj_ix36_all_sides_v1.parquet

python - <<'PY' | tee artifacts/csj/monologues_csj_ix36_all_sides_v1.sha256.txt
import hashlib, pathlib
p=pathlib.Path("artifacts/csj/monologues_csj_ix36_all_sides_v1.parquet")
print("sha256", hashlib.sha256(p.read_bytes()).hexdigest())
PY
```

---

### 14.3 Big5採点（ix36：4モデル×120items）

```bash
cd ~/cpsy

MONO="artifacts/csj/monologues_csj_ix36_all_sides_v1.parquet"
ITEMS="artifacts/big5/items_ipipneo120_ja.csv"
ROOT="artifacts/big5/llm_scores"
SHA="de3fd2e3"

DATASET="dataset=csj_ix36_all_sides_v1__sha=${SHA}__items=ipipneo120ja120"
OUTROOT="$ROOT/$DATASET"

while IFS= read -r MODEL; do
  [ -z "$MODEL" ] && continue
  SAFE="$(echo "$MODEL" | tr ':/' '__')"
  OUTDIR="$OUTROOT/model=$SAFE"
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

---

### 14.4 結果（Pilot N=6）

#### 14.4.1 4モデル平均（ensemble） Cronbach’s α（N=6）

| Ensemble(all4)    |        A |        C |        E |        N |        O |
| ----------------- | -------: | -------: | -------: | -------: | -------: |
| item_mean_4models | 0.541556 | 0.961744 | 0.843843 | 0.854445 | 0.720214 |

観察（N=6でも見える）：

* CSJでも **ensembleにより全体に安定化**（特に C/E/N/O）。
* Aはなお弱いが、単体で出た負αは回避できた（モデル平均の効果）。

---

### 14.5 結果（ix36 all sides N=36）

#### 14.5.1 単体モデル Cronbach’s α（N=36, k_items=24）

| Model           |         A |        C |        E |        N |        O |
| --------------- | --------: | -------: | -------: | -------: | -------: |
| Qwen3-235B      | -0.178830 | 0.732876 | 0.805688 | 0.757652 | 0.747209 |
| Claude Sonnet 4 |  0.603728 | 0.906816 | 0.764628 | 0.839628 | 0.831913 |
| DeepSeek V3     |  0.326002 | 0.866219 | 0.756029 | 0.798751 | 0.799292 |
| GPT-OSS 120B    |  0.687978 | 0.923408 | 0.770580 | 0.893105 | 0.778073 |

観察：

* C/E/N/O は概ね高い一方、**Aはモデル依存が強い**（Qwenで負α、DeepSeekでも低め）。
* ix36 は n_chars が短め（median=2877）で、Aの手がかり不足が出やすい可能性。

#### 14.5.2 ensemble(all4) Cronbach’s α（N=36）

| Ensemble(all4)    |        A |        C |        E |        N |        O |
| ----------------- | -------: | -------: | -------: | -------: | -------: |
| item_mean_4models | 0.590261 | 0.947658 | 0.869241 | 0.915664 | 0.883791 |

結論：

* CSJ ix36 でも **ensembleで高い内部一貫性**（C/E/N/Oは特に頑健）。
* Aは0.59まで回復するが、相対的には弱い。

---

### 14.6 感度分析（leave-one-out：どのモデルが効いているか）

出力：`ensemble_leave1out_alpha.tsv`

| variant       |            A |        C |        E |        N |        O |
| ------------- | -----------: | -------: | -------: | -------: | -------: |
| all4          |     0.590261 | 0.947658 | 0.869241 | 0.915664 | 0.883791 |
| drop DeepSeek |     0.624589 | 0.946937 | 0.841302 | 0.914533 | 0.874604 |
| drop Claude   |     0.581409 | 0.933294 | 0.859361 | 0.897980 | 0.865850 |
| drop GPT-OSS  | **0.372993** | 0.925835 | 0.860233 | 0.886028 | 0.869685 |
| drop Qwen     | **0.630030** | 0.945168 | 0.852622 | 0.911565 | 0.869690 |

要点（特にA）：

* **GPT-OSSを抜くとAが大きく悪化（0.373）** → Aの安定化に GPT-OSS が強く寄与
* **Qwenを抜くとAが改善（0.630）** → QwenはAを壊し気味
* C/E/N/O は drop しても大きくは動かず、**モデル混合に頑健**

---

### 14.7 発話量（長さ）感度（top-k by n_chars：25/50/75/100%）

出力：`ensemble_alpha_by_topk_chars.tsv`
定義：ix36を n_chars 降順に並べ、top9/top18/top27/top36（=25/50/75/100%）で ensemble α を算出。

| topk |        A |        C |        E |        N |        O |
| ---: | -------: | -------: | -------: | -------: | -------: |
|    9 | 0.754656 | 0.945333 | 0.805720 | 0.888911 | 0.844351 |
|   18 | 0.678777 | 0.932697 | 0.851317 | 0.930902 | 0.839405 |
|   27 | 0.635316 | 0.937458 | 0.855933 | 0.914748 | 0.843385 |
|   36 | 0.590261 | 0.947658 | 0.869241 | 0.915664 | 0.883791 |

観察（重要）：

* C/E/N/O は topk を増やしても概ね安定。
* **Aだけが topk増加で単調に低下（0.755→0.590）**。

  * 今回の“増やす”は「短い発話を追加している」ため、
    **短いサンプルを混ぜるほど A の手がかり不足で項目間整合が崩れ、αが下がる**可能性が示唆される。

---

### 14.8 CSJのQC（再現性・監査）

（CEJCと同型。期待行数は N_subjects×120）

```bash
python - <<'PY'
import pandas as pd
from pathlib import Path

root = Path("artifacts/big5/llm_scores/dataset=csj_ix36_all_sides_v1__sha=de3fd2e3__items=ipipneo120ja120")
items = pd.read_csv("artifacts/big5/items_ipipneo120_ja.csv")
n_items = len(items)

print("root =", root)
print("n_items =", n_items)
print()

for d in sorted(root.glob("model=*")):
    item_pq = d/"item_scores.parquet"
    if not item_pq.exists():
        continue

    df = pd.read_parquet(item_pq)
    n_subj = df[["conversation_id","speaker_id"]].drop_duplicates().shape[0]
    expected = n_subj * n_items
    n_rows = len(df)

    fb = 0
    for col in ["choice_raw","choice_norm"]:
        if col in df.columns:
            fb += int((df[col].astype(str)=="NEUTRAL_FALLBACK").sum())

    ok = (n_rows==expected and fb==0)
    print(d.name)
    print(f"  subjects={n_subj}  expected_rows={expected}  item_rows={n_rows}  fallback={fb}  OK={ok}")
PY
```

---

### 14.9 ここまでの暫定結論（先生向けワンメッセージ）

* CSJ（対話D, side擬似モノローグ）でも、
  **4モデル平均（ensemble）で内部一貫性が上がり、C/E/N/Oは高αで頑健**。
* 一方 **A（協調性）はモデル依存・発話量依存が強い**：

  * leave-one-outで **GPT-OSSを抜くとAが大幅悪化**、**Qwenを抜くと改善**
  * topk（長い→短いを追加）で **Aのみ単調低下**
* 次ステップは、CSJ側で

  * **n_chars下限（例：>=5000 or >=6000）で再定義**してAが持ち上がるか確認
  * CSJ全体から **N=50〜100** を構築し、CEJCと同程度の発話量で比較
  * Aについては **モデル混合の方針（例：Qwen除外3モデル平均も併記）**を検討
    が優先。

---

### 14.10 CSJ生成物（ファイル一覧）

#### 14.10.1 monologues

* `artifacts/csj/monologues_csj_ix36_all_sides.parquet`
* `artifacts/csj/monologues_csj_ix36_all_sides_preview.tsv`
* `artifacts/csj/monologues_csj_ix36_all_sides_v1.parquet`
* `artifacts/csj/monologues_csj_ix36_all_sides_v1.sha256.txt`

#### 14.10.2 Big5（単体モデル）

`artifacts/big5/llm_scores/dataset=csj_ix36_all_sides_v1__sha=de3fd2e3__items=ipipneo120ja120/model=<MODEL_SAFE>/`

* `item_scores.parquet`
* `trait_scores.parquet`
* `cronbach_alpha.csv`

#### 14.10.3 Big5（ensemble＋分析）

`.../ensemble=item_mean_4models/`

* `item_scores_ensemble_mean.parquet`
* `trait_scores_ensemble_mean.parquet`
* `cronbach_alpha_ensemble_mean.csv`
* `ensemble_leave1out_alpha.tsv`
* `ensemble_alpha_by_topk_chars.tsv`

