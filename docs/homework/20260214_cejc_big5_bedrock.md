# CEJC（自宅・少人数）抽出 → Big5 を Bedrock 複数モデルで採点 → LLM平均を作成（再現ログ）
Date: 2026-02-14  
Owner: 福原玄

## 目的
- 元論文「Assessing personality using zero-shot generative AI scoring ...」の **daily diary / idiographic narrative** に寄せて、  
  日本語会話コーパスから **日常（自宅・少人数）** 条件を作り、Big5 を LLM zero-shot で採点する。
- 論文では「**複数LLMの平均が最も強い**」「LLMを複数 rater とみなすのが妥当」とされるため、  
  **複数モデルの trait score を揃え、モデル平均（mean/sd）を作る**。  
  Evidence: Abstract と本文の該当箇所。  
  - “average LLM score across models provided the strongest agreement …”:contentReference[oaicite:2]{index=2}
  - “use multiple LLM ‘raters’ … recommendation …”:contentReference[oaicite:3]{index=3}

## なぜ CSJ ではなく CEJC を選んだか
- 本タスクは「日記的 / 自然な独り語り（diary-like）」に近い条件が必要。  
- **CEJC は会話一覧のメタデータに “場所（例：自宅）/ 活動（例：食事）/ 話者数” などがあり**、  
  “自宅・少人数” の抽出が **メタデータ駆動で再現可能**。  
- 一方 CSJ は（少なくとも本タスクの狙いに対して）スピーチ寄りの条件になりやすく、  
  diary-like 条件の構成が難しい（メタの粒度・条件設計の観点）。

## 論文に近いモデル選定（ただし Tokyo リージョン制約あり）
- 論文は複数の商用LLMを比較し、モデル平均を推奨。モデル例に **Qwen3-235B** 等が含まれる。:contentReference[oaicite:4]{index=4}
- 本実験は **Bedrock ap-northeast-1（Tokyo）縛り**の中で利用可能な高性能モデルを優先し、
  - `qwen.qwen3-235b-a22b-2507-v1:0`
  - `global.anthropic.claude-sonnet-4-20250514-v1:0`（on-demand 制約で global prefix 使用）
  - `deepseek.v3-v1:0`
  - `openai.gpt-oss-120b-1:0`
  を採用した。

---

## 成果物（最終出力）
### 4モデルの trait_scores（各 n_subjects=50）
最終ログ（要点）：
- picked models = 4
- 各モデル n_subjects = 50
- LLM平均 parquet も n_subjects=50 / n_models=4 が揃う

出力例：
- `artifacts/big5/llm_scores/model=<...>/trait_scores.parquet`
- `artifacts/big5/llm_scores/model=<...>/item_scores.parquet`
- `artifacts/big5/llm_scores/model=<...>/cronbach_alpha.csv`
- `artifacts/big5/llm_scores/llm_avg_manifest_best.csv`
- `artifacts/big5/llm_scores/trait_scores_llm_average_all.parquet`
- `artifacts/big5/llm_scores/trait_scores_llm_average_full50_3models.parquet`（※ファイル名は歴史的経緯。実際は n_models=4）
- `artifacts/big5/llm_scores/trait_scores_llm_average_strict_allmodels.parquet`

---

## 再現手順（コマンド）
前提：
- Python 3.12 / venv
- AWS 認証情報（`AWS_PROFILE` 等）
- Bedrock region: `ap-northeast-1`

### 0) 入力・前提確認
```bash
python -V
aws sts get-caller-identity
ls -la artifacts/big5/items.csv
````

### 1) CEJC メタデータ確認（convlist.parquet の存在・中身）

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

（convlist.parquet が無い場合は、手元で成功した scrape スクリプトを 1 本に固定して実行し、ログを保存する）

```bash
# 例：リポジトリ内の実在スクリプト名に合わせて1本に固定すること
python scripts/cejc/scrape_cejc_convlist_no_lxml.py \
  --out_parquet artifacts/tmp_meta/cejc_convlist.parquet \
  --out_top_tsv artifacts/tmp_meta/cejc_diary_candidates_top200.tsv \
  --topk 200 \
| tee artifacts/tmp_meta/cejc_meta_profile.txt
```

### 2) diary-like（自宅・少人数）IDリスト作成（メタデータ駆動）

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

### 3) utterances から「会話ごとのトップ話者」を抽出し、擬似モノローグ化（Top1）

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

### 4) Bedrock で Big5 採点（複数モデル）

models.txt

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
* `trait_scores.parquet` の列が long format（`trait` / `trait_score`）なので、平均集計では pivot が必要。

---

## 5) trait_scores の subject mean & LLM平均（mean/sd/n_models）を作成（最終形）

（※すでに生成済みの成果物と同等のものを、再現可能な形で生成する “確定版” スクリプト）

```bash
python - <<'PY'
import glob, os, pandas as pd

ROOT="artifacts/big5/llm_scores"
paths=glob.glob(f"{ROOT}/model=*/trait_scores.parquet")

rows=[]
for p in paths:
    df=pd.read_parquet(p)
    # 必須列
    need={"conversation_id","speaker_id","trait"}
    if not need.issubset(df.columns):
        continue
    subj=df[["conversation_id","speaker_id"]].drop_duplicates()
    rows.append({
        "path": p,
        "model_id": df["model_id"].iloc[0] if "model_id" in df.columns and len(df) else os.path.basename(os.path.dirname(p)),
        "n_subjects": len(subj),
    })

manifest=pd.DataFrame(rows).sort_values(["model_id","n_subjects","path"], ascending=[True,False,True])
# model_id ごとに最大 n_subjects のパスを採用（重複runの整理）
picked=(manifest.groupby("model_id", as_index=False).head(1)).reset_index(drop=True)

print("[INFO] picked models =", len(picked))
print(picked[["model_id","n_subjects","path"]].to_string(index=False))

picked.to_csv(f"{ROOT}/llm_avg_manifest_best.csv", index=False)

def make_subject_mean(path: str) -> pd.DataFrame:
    df=pd.read_parquet(path)
    score_col="trait_score" if "trait_score" in df.columns else "score"
    wide=(df.pivot_table(index=["conversation_id","speaker_id"],
                         columns="trait", values=score_col, aggfunc="mean")
            .reset_index())
    # trait order
    for t in ["A","C","E","N","O"]:
        if t not in wide.columns:
            wide[t]=pd.NA
    wide=wide[["conversation_id","speaker_id","A","C","E","N","O"]]
    wide["subject_key"]=wide["conversation_id"].astype(str)+"|"+wide["speaker_id"].astype(str)
    return wide

# 各モデルの subject mean を保存
subj_means=[]
for _,r in picked.iterrows():
    path=r["path"]
    model=r["model_id"]
    outdir=os.path.dirname(path)
    outpath=os.path.join(outdir, "trait_scores_subject_mean.parquet")
    sm=make_subject_mean(path)
    sm["model_id"]=model
    sm.to_parquet(outpath, index=False)
    print("[OK] wrote:", outpath, "n_subjects=", sm["subject_key"].nunique())
    subj_means.append(sm)

all_sm=pd.concat(subj_means, ignore_index=True)

# LLM平均（mean / sd / n_models）
g=all_sm.groupby(["conversation_id","speaker_id","subject_key"], as_index=False).agg(
    A=("A","mean"), C=("C","mean"), E=("E","mean"), N=("N","mean"), O=("O","mean"),
    sd_A=("A","std"), sd_C=("C","std"), sd_E=("E","std"), sd_N=("N","std"), sd_O=("O","std"),
    n_models=("model_id","nunique"),
)
g["sd_A"]=g["sd_A"].fillna(0.0)
g["sd_C"]=g["sd_C"].fillna(0.0)
g["sd_E"]=g["sd_E"].fillna(0.0)
g["sd_N"]=g["sd_N"].fillna(0.0)
g["sd_O"]=g["sd_O"].fillna(0.0)

out=f"{ROOT}/trait_scores_llm_average_strict_allmodels.parquet"
g.to_parquet(out, index=False)

print("[OK] wrote:", out, "n_subjects=", g["subject_key"].nunique(),
      "min_n_models=", int(g["n_models"].min()), "max_n_models=", int(g["n_models"].max()))
print("[HEAD]")
print(g.head(5).to_string(index=False))
PY
```

### 6) 出力確認（エビデンス）

trait_scores の探索（重複runの存在も含めて確認）

```bash
find artifacts/big5/llm_scores -maxdepth 2 -type f -name trait_scores.parquet -print
```

---

## 注意（データ取り扱い）

* corpora の本文（発話テキスト）や parquet 本体は、ライセンス・容量の観点で **git 管理対象にしない**。
* git に残すのは **再現コマンド / スクリプト / ログ**（本 md）を中心にする。

