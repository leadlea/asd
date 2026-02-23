# Runbook: CEJC home2 HQ1 → Interaction features → LLM teacher (IPIP-NEO C24) → Ridge + Permutation + Bootstrap
Owner: 福原玄  
Last updated: 2026-02-xx  
Repo: leadlea/asd  
Workdir: ~/cpsy  
Python: 3.12 (venv)

---

## 0) 前提
- CEJC utterances: `artifacts/_tmp_utt/cejc_utterances/part-00000.parquet`
- CEJC convlist: `artifacts/tmp_meta/cejc_convlist.parquet`
- IPIP-NEO-120 items: `artifacts/big5/items_ipipneo120_ja.csv`
- Bedrock Region: `ap-northeast-1`
- LLM (teacher): `global.anthropic.claude-sonnet-4-20250514-v1:0`
- HQ1 definition (home2):
  - `n_pairs_total >= 80`
  - `FILL_text_len >= 2000`
  - `IX_n_pairs_after_question >= 10`
- Main claim excludes drift due to audit findings (optional section at end).

Activate venv:
```bash
cd ~/cpsy
source .venv/bin/activate
python -V
aws sts get-caller-identity
````

---

## 1) Target pairs 作成（CEJC 自宅・2名 → HQ1 pairs）

**Output**

* `artifacts/analysis/target_pairs/cejc_home2_hq1_pairs.parquet`
* `artifacts/analysis/target_pairs/cejc_home2_hq1_pairs_preview.tsv`

```bash
cd ~/cpsy
source .venv/bin/activate
mkdir -p artifacts/analysis/target_pairs

python - <<'PY'
import pandas as pd, re
from pathlib import Path

conv="artifacts/tmp_meta/cejc_convlist.parquet"
utt ="artifacts/_tmp_utt/cejc_utterances/part-00000.parquet"
out_pairs="artifacts/analysis/target_pairs/cejc_home2_hq1_pairs.parquet"
out_preview="artifacts/analysis/target_pairs/cejc_home2_hq1_pairs_preview.tsv"

meta=pd.read_parquet(conv)
id_col = "会話ID" if "会話ID" in meta.columns else ("conversation_id" if "conversation_id" in meta.columns else None)
place_col = "場所" if "場所" in meta.columns else None
assert id_col and place_col

meta[id_col]=meta[id_col].astype(str)
if "speaker_n" not in meta.columns:
    src="話者数" if "話者数" in meta.columns else None
    assert src
    def to_int(x):
        s=str(x).strip()
        s=re.sub(r'^[^0-9]*','',s)
        s=re.sub(r'[^0-9].*$','',s)
        return int(s) if s.isdigit() else None
    meta["speaker_n"]=meta[src].map(to_int)

home2_ids=set(meta[(meta[place_col].astype(str).str.contains("自宅",na=False)) & (meta["speaker_n"]==2)][id_col].dropna().unique().tolist())
print("home2 conversations:", len(home2_ids))

u=pd.read_parquet(utt).copy()
u["conversation_id"]=u["conversation_id"].astype(str)
u["speaker_id"]=u["speaker_id"].astype(str)
u=u[u["conversation_id"].isin(home2_ids)].copy()
u["text"]=u["text"].fillna("").astype(str)

# text_len per (conv,spk)
g_text=(u.groupby(["conversation_id","speaker_id"],as_index=False)
          .agg(FILL_text_len=("text", lambda s: int(sum(len(t.replace(" ","").replace("　","")) for t in s.tolist())))))

# pairs on speaker change + prev_is_question
u=u.sort_values(["conversation_id","start_time","end_time"], kind="mergesort")
prev=u.groupby("conversation_id").shift(1)

QMARK=re.compile(r"[?？]")
QEND=re.compile(r"(か|かな|かね|でしょう|でしょ|だろう|だろ|の)$")
def is_q(t:str)->bool:
    t=(t or "").strip()
    if not t: return False
    if QMARK.search(t): return True
    tail=re.sub(r"[。．\.！!、,「」\"\'\s]+$","",t)
    return bool(QEND.search(tail))

prev_text = prev["text"].fillna("").astype(str)
prev_is_q = prev_text.map(is_q)

mask=(u["speaker_id"]!=prev["speaker_id"]) & prev["speaker_id"].notna()
pairs=u.loc[mask, ["conversation_id","speaker_id"]].rename(columns={"speaker_id":"resp_speaker_id"})
pairs["prev_is_question"]=prev_is_q.loc[mask].values

g_pairs=(pairs.groupby(["conversation_id","resp_speaker_id"],as_index=False)
           .agg(n_pairs_total=("prev_is_question","size"),
                IX_n_pairs_after_question=("prev_is_question","sum"))
           .rename(columns={"resp_speaker_id":"speaker_id"}))

cand=g_text.merge(g_pairs,on=["conversation_id","speaker_id"],how="left").fillna({"n_pairs_total":0,"IX_n_pairs_after_question":0})
cand["n_pairs_total"]=cand["n_pairs_total"].astype(int)
cand["IX_n_pairs_after_question"]=cand["IX_n_pairs_after_question"].astype(int)

hq1=cand[(cand["n_pairs_total"]>=80) & (cand["FILL_text_len"]>=2000) & (cand["IX_n_pairs_after_question"]>=10)].copy()
print("HQ1 pairs (home2):", len(hq1))

Path(out_pairs).parent.mkdir(parents=True, exist_ok=True)
hq1[["conversation_id","speaker_id"]].drop_duplicates().to_parquet(out_pairs, index=False)

hq1.sort_values(["n_pairs_total","FILL_text_len"], ascending=False).head(200).to_csv(out_preview, sep="\t", index=False)
print("OK:", out_pairs)
print("OK:", out_preview)
PY
```

---

## 2) Monologues 生成（HQ1 pairs → 話者発話連結）＋ v1固定（sha256）

**Output**

* `artifacts/cejc/monologues_cejc_home2_hq1_v1.parquet`
* `artifacts/cejc/monologues_cejc_home2_hq1_v1.sha256.txt`
* `artifacts/cejc/monologues_cejc_home2_hq1_preview.tsv`

```bash
cd ~/cpsy
source .venv/bin/activate
mkdir -p artifacts/cejc

python - <<'PY'
import pandas as pd
from pathlib import Path
import hashlib

utt="artifacts/_tmp_utt/cejc_utterances/part-00000.parquet"
tp ="artifacts/analysis/target_pairs/cejc_home2_hq1_pairs.parquet"

out0="artifacts/cejc/monologues_cejc_home2_hq1.parquet"
outv="artifacts/cejc/monologues_cejc_home2_hq1_v1.parquet"
sha ="artifacts/cejc/monologues_cejc_home2_hq1_v1.sha256.txt"
prev="artifacts/cejc/monologues_cejc_home2_hq1_preview.tsv"

u=pd.read_parquet(utt).copy()
u["conversation_id"]=u["conversation_id"].astype(str)
u["speaker_id"]=u["speaker_id"].astype(str)
u["text"]=u["text"].fillna("").astype(str)

pairs=pd.read_parquet(tp)[["conversation_id","speaker_id"]].drop_duplicates()
pairs["conversation_id"]=pairs["conversation_id"].astype(str)
pairs["speaker_id"]=pairs["speaker_id"].astype(str)

uu=u.merge(pairs, on=["conversation_id","speaker_id"], how="inner").copy()
uu=uu.sort_values(["conversation_id","speaker_id","start_time","end_time"], kind="mergesort")

g=(uu.groupby(["conversation_id","speaker_id"], as_index=False)
     .agg(n_utt=("text","count"),
          n_chars=("text", lambda s: int(sum(len(t.replace(" ","").replace("　","")) for t in s.tolist()))),
          text=("text", lambda s: "\n".join(s.tolist()).strip())))

Path(out0).parent.mkdir(parents=True, exist_ok=True)
g.to_parquet(out0, index=False)

# v1固定
Path(outv).write_bytes(Path(out0).read_bytes())
h=hashlib.sha256(Path(outv).read_bytes()).hexdigest()
Path(sha).write_text("sha256 "+h+"\n", encoding="utf-8")

tmp=g.copy()
tmp["head200"]=tmp["text"].str.replace("\n"," ",regex=False).str.slice(0,200)
tmp.sort_values(["n_chars"], ascending=False).head(200)[["conversation_id","speaker_id","n_chars","n_utt","head200"]].to_csv(prev, sep="\t", index=False)

print("OK:", outv, "rows=", len(g))
print("OK:", sha, "=>", h[:12])
print("OK:", prev)
PY
```

---

## 3) Items を C24 に絞る（IPIP-NEO-120 → Cのみ24項目）

**Output**

* `artifacts/big5/items_ipipneo120_ja_C24.csv`

```bash
cd ~/cpsy
source .venv/bin/activate

python - <<'PY'
import pandas as pd
items=pd.read_csv("artifacts/big5/items_ipipneo120_ja.csv")
trait_col = "trait" if "trait" in items.columns else ("Trait" if "Trait" in items.columns else None)
assert trait_col is not None
items[items[trait_col].astype(str).str.strip()=="C"].to_csv(
    "artifacts/big5/items_ipipneo120_ja_C24.csv", index=False
)
print("OK: artifacts/big5/items_ipipneo120_ja_C24.csv")
PY
```

---

## 4) Monologues をシャード分割（再開可能運用）

**Output**

* `artifacts/cejc/shards_home2_hq1/monologues_..._shard000.parquet` など

```bash
cd ~/cpsy
source .venv/bin/activate
mkdir -p artifacts/cejc/shards_home2_hq1

python - <<'PY'
import pandas as pd, math
from pathlib import Path
mono="artifacts/cejc/monologues_cejc_home2_hq1_v1.parquet"
df=pd.read_parquet(mono)
outdir=Path("artifacts/cejc/shards_home2_hq1"); outdir.mkdir(parents=True, exist_ok=True)
shard_size=10
k=math.ceil(len(df)/shard_size)
for i in range(k):
    df.iloc[i*shard_size:(i+1)*shard_size].to_parquet(outdir/f"monologues_cejc_home2_hq1_v1_shard{i:03d}.parquet", index=False)
print("rows:", len(df), "shards:", k, "shard_size:", shard_size)
PY
```

---

## 5) Bedrock で C24 を採点（shardごと・再開可能）

**Script**

* `scripts/big5/score_big5_bedrock.py`

**Output**

* `artifacts/big5/llm_scores/dataset=cejc_home2_hq1_v1__items=C24__teacher=sonnet4/shard=.../model=.../trait_scores.parquet`

```bash
cd ~/cpsy
source .venv/bin/activate

export AWS_RETRY_MODE=adaptive
export AWS_MAX_ATTEMPTS=10

MODEL="global.anthropic.claude-sonnet-4-20250514-v1:0"
SAFE="$(echo "$MODEL" | tr ':/' '__')"
ITEMS="artifacts/big5/items_ipipneo120_ja_C24.csv"
OUTROOT="artifacts/big5/llm_scores/dataset=cejc_home2_hq1_v1__items=C24__teacher=sonnet4"

mkdir -p "$OUTROOT"

for SHARD in artifacts/cejc/shards_home2_hq1/monologues_cejc_home2_hq1_v1_shard*.parquet; do
  SID="$(basename "$SHARD" .parquet | sed 's/.*shard//')"
  OUTDIR="$OUTROOT/shard=$SID/model=$SAFE"
  if [ -f "$OUTDIR/trait_scores.parquet" ]; then
    echo "[SKIP] shard=$SID already done"
    continue
  fi
  echo "== RUN shard=$SID =="
  python scripts/big5/score_big5_bedrock.py \
    --monologues_parquet "$SHARD" \
    --items_csv "$ITEMS" \
    --model_id "$MODEL" \
    --region "ap-northeast-1" \
    --out_dir "$OUTDIR" || exit 1
done
```

Progress check:

```bash
ls -d artifacts/big5/llm_scores/dataset=cejc_home2_hq1_v1__items=C24__teacher=sonnet4/shard=*/model=* 2>/dev/null | wc -l
```

---

## 6) 教師（trait_scores）結合（Cのみ）

**Output**

* `.../teacher_merged/trait_scores_C_merged.parquet`

```bash
cd ~/cpsy
source .venv/bin/activate

python - <<'PY'
import pandas as pd
from pathlib import Path
root=Path("artifacts/big5/llm_scores/dataset=cejc_home2_hq1_v1__items=C24__teacher=sonnet4")
ps=sorted(root.glob("shard=*/model=*/trait_scores.parquet"))
df=pd.concat([pd.read_parquet(p) for p in ps], ignore_index=True)
outdir=root/"teacher_merged"; outdir.mkdir(parents=True, exist_ok=True)
out=outdir/"trait_scores_C_merged.parquet"
df.to_parquet(out, index=False)
print("traits:", df["trait"].unique().tolist())
print("unique_pairs:", df[["conversation_id","speaker_id"]].drop_duplicates().shape[0], "rows:", len(df))
print("OK:", out.as_posix())
PY
```

---

## 7) X（相互行為特徴）抽出

**Script**

* `scripts/analysis/extract_interaction_features_min.py`

**Output**

* `artifacts/analysis/features_min/features_cejc_home2_hq1.parquet`

```bash
cd ~/cpsy
source .venv/bin/activate
mkdir -p artifacts/analysis/features_min

python scripts/analysis/extract_interaction_features_min.py \
  --utterances_parquet artifacts/_tmp_utt/cejc_utterances/part-00000.parquet \
  --target_pairs_parquet artifacts/analysis/target_pairs/cejc_home2_hq1_pairs.parquet \
  --out_parquet artifacts/analysis/features_min/features_cejc_home2_hq1.parquet
```

---

## 8) XY 作成（X + Y_C）

**Output**

* `artifacts/analysis/datasets/cejc_home2_hq1_XY_Conly_sonnet.parquet`

```bash
cd ~/cpsy
source .venv/bin/activate
mkdir -p artifacts/analysis/datasets

python - <<'PY'
import pandas as pd
X="artifacts/analysis/features_min/features_cejc_home2_hq1.parquet"
Y="artifacts/big5/llm_scores/dataset=cejc_home2_hq1_v1__items=C24__teacher=sonnet4/teacher_merged/trait_scores_C_merged.parquet"
x=pd.read_parquet(X)
y=pd.read_parquet(Y)[["conversation_id","speaker_id","trait_score"]].rename(columns={"trait_score":"Y_C"})
df=x.merge(y,on=["conversation_id","speaker_id"],how="inner")
out="artifacts/analysis/datasets/cejc_home2_hq1_XY_Conly_sonnet.parquet"
df.to_parquet(out, index=False)
print("OK:", out, "shape=", df.shape)
print(df[["n_pairs_total","IX_n_pairs_after_question","FILL_text_len","Y_C"]].describe().to_string())
PY
```

---

## 9) 学習（Ridge / 5-fold CV）

**Script**

* `scripts/analysis/train_cejc_big5_from_features_v2.py`

**Output**

* `artifacts/analysis/results/cejc_home2_hq1_Conly_sonnet_controls_excluded/summary.tsv`
* `.../top15_features_all_traits.tsv`

```bash
cd ~/cpsy
source .venv/bin/activate

EXCL3="IX_n_pairs,n_pairs_total,FILL_text_len,FILL_cnt_total,FILL_cnt_ano,FILL_cnt_e,FILL_cnt_eto,PG_total_time,PG_overlap_rate,PG_resp_overlap_rate,n_pairs_after_NE,n_pairs_after_YO,IX_n_pairs_after_question"

python scripts/analysis/train_cejc_big5_from_features_v2.py \
  --xy_parquet artifacts/analysis/datasets/cejc_home2_hq1_XY_Conly_sonnet.parquet \
  --out_dir artifacts/analysis/results/cejc_home2_hq1_Conly_sonnet_controls_excluded \
  --min_pairs_total 0 --min_text_len 0 --cv_folds 5 \
  --exclude_cols "$EXCL3"
```

---

## 10) 置換検定（Permutation test, 5000）

**Output**

* stdout: `Y_C: r_obs=... p(|r|)=... n=... Xdim=...`

```bash
cd ~/cpsy
source .venv/bin/activate

python - <<'PY'
import numpy as np, pandas as pd
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import RidgeCV

XY="artifacts/analysis/datasets/cejc_home2_hq1_XY_Conly_sonnet.parquet"
EXCL=set("IX_n_pairs,n_pairs_total,FILL_text_len,FILL_cnt_total,FILL_cnt_ano,FILL_cnt_e,FILL_cnt_eto,PG_total_time,PG_overlap_rate,PG_resp_overlap_rate,n_pairs_after_NE,n_pairs_after_YO,IX_n_pairs_after_question".split(","))
N_PERM=5000

def pearson(a,b):
    a=a-np.mean(a); b=b-np.mean(b)
    den=np.sqrt((a*a).sum())*np.sqrt((b*b).sum())
    return float((a*b).sum()/den) if den>0 else float("nan")

df=pd.read_parquet(XY).reset_index(drop=True)
drop=set(["conversation_id","speaker_id","Y_C"])
Xcols=[c for c in df.columns if (c not in drop) and (c not in EXCL)]
X=df[Xcols].apply(pd.to_numeric, errors="coerce")

cv=KFold(n_splits=5, shuffle=True, random_state=42)
model=Pipeline([
    ("imp", SimpleImputer(strategy="median")),
    ("sc", StandardScaler()),
    ("ridge", RidgeCV(alphas=np.logspace(-3,3,25), cv=5)),
])
rng=np.random.default_rng(0)

y=df["Y_C"].astype(float).values
yhat=cross_val_predict(model, X, y, cv=cv)
r_obs=pearson(y,yhat)

rs=[]
for _ in range(N_PERM):
    yp=rng.permutation(y)
    yhatp=cross_val_predict(model, X, yp, cv=cv)
    rs.append(pearson(yp,yhatp))
rs=np.array(rs)
p=(np.sum(np.abs(rs)>=abs(r_obs))+1)/(len(rs)+1)
print(f"Y_C: r_obs={r_obs:.3f}  perm_mean={rs.mean():.3f}  p(|r|)={p:.4f}  n={len(df)}  Xdim={X.shape[1]}")
PY
```

---

## 11) 係数安定性（Bootstrap 500）

**Script**

* `scripts/analysis/bootstrap_coef_stability.py`

**Output**

* `artifacts/analysis/results/bootstrap/cejc_home2_hq1_Conly_sonnet_controls_excluded/bootstrap_summary.tsv`
* `.../alpha_describe.tsv`

```bash
cd ~/cpsy
source .venv/bin/activate
mkdir -p artifacts/analysis/results/bootstrap/cejc_home2_hq1_Conly_sonnet_controls_excluded

python scripts/analysis/bootstrap_coef_stability.py \
  --xy_parquet artifacts/analysis/datasets/cejc_home2_hq1_XY_Conly_sonnet.parquet \
  --y_col Y_C \
  --out_dir artifacts/analysis/results/bootstrap/cejc_home2_hq1_Conly_sonnet_controls_excluded \
  --n_boot 500 --topk 10 --seed 0 \
  --exclude_cols "$EXCL3"
```

---

## Appendix (Optional, not used in main claim): drift audit + driftv2

* Create `features_cejc_home2_hq1_driftfix.parquet` and evaluate driftv2 model (expected: performance drops; drift excluded).

---

## Linked docs (paper assets)

* `docs/homework/cejc_conscientiousness_results.md`
* `docs/homework/cejc_conscientiousness_slide.md`
* `docs/homework/cejc_conscientiousness_table1.md`
