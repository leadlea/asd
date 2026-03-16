# Runbook: 会話ダッシュボードに style_title を安全追加して反映する手順

Date: 2026-03-16  
Owner: 福原玄  
Repo: `leadlea/asd`  
Target UI: `docs/index.html`

---

## 目的

既存の `docs/index.html` ベースの会話ダッシュボードに、生成済みの **会話スタイル名 (`style_title`)** を補助的な見出しとして追加する。

今回の要件は以下。

- 一覧の `summary` 上に `style_title` を表示
- 詳細パネルに `style_title` / `style_title_reason` / `style_title_confidence` を表示
- 既存の `summary / labels / primary_label / atypicality_v0 / prompt_features_used_json` を壊さない
- 旧データでも落ちないよう、列がない場合は非表示フォールバック
- 最小差分で実装する

---

## 結論

今回の `docs/index.html` は **外部 parquet/json を fetch していない**。  
UI データは `index.html` 内の

```html
<script id="DATA" type="application/json">...</script>
````

に **inline 埋め込み**されている。

そのため、安全な最小実装は次の2点。

1. `docs/index.html` の描画ロジックに `style_title*` 表示を追加
2. `style_title*` を含む merge 済み parquet から inline DATA を再埋め込み

---

## 使用データ

### merge済み parquet

```text
artifacts/phase56_full_20260104_024221/_llm500_opus45/labels_tb500_UIFINAL_opus45_WITHCL_WITHNEYO_WITHIX__FIXED_WITH_STYLETITLE.parquet
```

### join key

* `dataset`
* `speaker_id`
* `conversation_id`

---

## 事前確認

### 1. 対象ファイル確認

```bash
ls -lt docs
```

### 2. `style_title` 列の存在確認

```bash
python - <<'PY'
import pandas as pd

p = "artifacts/phase56_full_20260104_024221/_llm500_opus45/labels_tb500_UIFINAL_opus45_WITHCL_WITHNEYO_WITHIX__FIXED_WITH_STYLETITLE.parquet"
df = pd.read_parquet(p)

print("rows:", len(df))
print("has style_title col:", "style_title" in df.columns)
print("has style_title_reason col:", "style_title_reason" in df.columns)
print("has style_title_confidence col:", "style_title_confidence" in df.columns)

if "style_title" in df.columns:
    print("style_title non-null:", int(df["style_title"].notna().sum()))

cols = [c for c in [
    "dataset","conversation_id","speaker_id",
    "style_title","style_title_reason","style_title_confidence"
] if c in df.columns]

target = df[df["speaker_id"] == "K010_003a:IC01"][cols]
print(target.head(3).to_string(index=False))
PY
```

期待結果の例:

* `rows: 500`
* `has style_title col: True`
* `style_title non-null: 500`

---

## Step 1. `docs/index.html` に描画ロジックを追加

以下のパッチで、既存 UI を壊さずに `style_title` 表示だけを追加する。

```bash
python - <<'PY'
from pathlib import Path
from datetime import datetime
import shutil

p = Path("docs/index.html")
src = p.read_text(encoding="utf-8")

bak = p.with_name(f"index.html.bak_styletitle_render_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(p, bak)

old = src

# 1) CSS 追加
anchor_css = '.summaryHint{ font-size: 11px; color: var(--muted); margin-top: 4px; }'
insert_css = '''.summaryHint{ font-size: 11px; color: var(--muted); margin-top: 4px; }

    .styleTitleClamp{
      font-size: 14px;
      font-weight: 800;
      line-height: 1.35;
      margin-bottom: 6px;
      color: var(--text);
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
      word-break: break-word;
    }
    .styleTitleMeta{
      font-size: 12px;
      color: var(--muted);
      margin-top: 6px;
      line-height: 1.5;
    }'''
if anchor_css not in src:
    raise SystemExit("CSS anchor not found")
src = src.replace(anchor_css, insert_css, 1)

# 2) helper 追加
anchor_helper = '''function _summaryText(rec){
      if (rec && rec.labels && typeof rec.labels.summary === "string") return rec.labels.summary;
      if (rec && typeof rec.summary === "string") return rec.summary;
      return "";
    }'''
insert_helper = '''function _summaryText(rec){
      if (rec && rec.labels && typeof rec.labels.summary === "string") return rec.labels.summary;
      if (rec && typeof rec.summary === "string") return rec.summary;
      return "";
    }

    function _styleTitle(rec){
      if (rec && typeof rec.style_title === "string" && rec.style_title.trim()) return rec.style_title.trim();
      return "";
    }

    function _styleTitleReason(rec){
      if (rec && typeof rec.style_title_reason === "string" && rec.style_title_reason.trim()) return rec.style_title_reason.trim();
      return "";
    }

    function _styleTitleConf(rec){
      const v = rec ? rec.style_title_confidence : null;
      if (v === null || v === undefined || v === "") return null;
      const n = Number(v);
      return Number.isFinite(n) ? n : null;
    }'''
if anchor_helper not in src:
    raise SystemExit("helper anchor not found")
src = src.replace(anchor_helper, insert_helper, 1)

# 3) renderTable で style_title を summary 上に表示
anchor_render1 = 'const summary = _summaryText(r);'
replace_render1 = '''const summary = _summaryText(r);
        const styleTitle = _styleTitle(r);'''
if anchor_render1 not in src:
    raise SystemExit("render anchor1 not found")
src = src.replace(anchor_render1, replace_render1, 1)

anchor_render2 = 'const summaryTitle = summary.replace(/\\s+/g, " ").trim();'
replace_render2 = 'const summaryTitle = [styleTitle, summary].filter(Boolean).join(" / ").replace(/\\s+/g, " ").trim();'
if anchor_render2 not in src:
    raise SystemExit("render anchor2 not found")
src = src.replace(anchor_render2, replace_render2, 1)

anchor_render3 = '''<td class="summaryCell" title="${esc(summaryTitle)}">
              <div class="summaryClamp">${esc(summary)}</div>
              <div class="summaryHint">click for details →</div>
            </td>'''
replace_render3 = '''<td class="summaryCell" title="${esc(summaryTitle)}">
              ${styleTitle ? `<div class="styleTitleClamp">${esc(styleTitle)}</div>` : ``}
              <div class="summaryClamp">${esc(summary)}</div>
              <div class="summaryHint">click for details →</div>
            </td>'''
if anchor_render3 not in src:
    raise SystemExit("render anchor3 not found")
src = src.replace(anchor_render3, replace_render3, 1)

# 4) showDetails で style_title / reason / confidence 追加
anchor_detail1 = 'const summary = _summaryText(rec);'
replace_detail1 = '''const summary = _summaryText(rec);
      const styleTitle = _styleTitle(rec);
      const styleTitleReason = _styleTitleReason(rec);
      const styleTitleConf = _styleTitleConf(rec);'''
if anchor_detail1 not in src:
    raise SystemExit("detail anchor1 not found")
src = src.replace(anchor_detail1, replace_detail1, 1)

anchor_detail2 = '''<div class="small">
          <b>summary</b>: ${esc(summary)}
        </div>'''
replace_detail2 = '''${styleTitle ? `
        <div class="panel" style="margin-bottom:10px;">
          <div class="sectionTitle" style="margin-top:0;">Conversation style</div>
          <div style="font-size:18px;font-weight:800;line-height:1.4;">${esc(styleTitle)}</div>
          ${styleTitleReason ? `<div class="styleTitleMeta">${esc(styleTitleReason)}</div>` : ``}
          ${styleTitleConf !== null ? `<div class="styleTitleMeta">confidence: ${esc(styleTitleConf.toFixed(2))}</div>` : ``}
        </div>
        ` : ``}

        <div class="small">
          <b>summary</b>: ${esc(summary)}
        </div>'''
if anchor_detail2 not in src:
    raise SystemExit("detail anchor2 not found")
src = src.replace(anchor_detail2, replace_detail2, 1)

if src == old:
    raise SystemExit("no changes made")

p.write_text(src, encoding="utf-8")
print(f"patched: {p}")
print(f"backup : {bak}")
PY
```

---

## Step 2. merge済み parquet を inline DATA として再埋め込み

`ndarray` を含むネスト列があるため、NumPy 型も吸収できる serializer を使う。

```bash
python - <<'PY'
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import json, math, re, shutil

html_path = Path("docs/index.html")
parquet_path = Path("artifacts/phase56_full_20260104_024221/_llm500_opus45/labels_tb500_UIFINAL_opus45_WITHCL_WITHNEYO_WITHIX__FIXED_WITH_STYLETITLE.parquet")

def clean(x):
    if x is None:
        return None

    if isinstance(x, np.ndarray):
        return [clean(v) for v in x.tolist()]
    if isinstance(x, pd.Series):
        return [clean(v) for v in x.tolist()]

    if isinstance(x, np.generic):
        return clean(x.item())

    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [clean(v) for v in x]

    if isinstance(x, (bytes, bytearray)):
        return x.decode("utf-8", errors="replace")

    if hasattr(x, "isoformat") and not isinstance(x, str):
        try:
            return x.isoformat()
        except Exception:
            pass

    if isinstance(x, float):
        if math.isnan(x) or math.isinf(x):
            return None
        return x

    try:
        if pd.isna(x):
            return None
    except Exception:
        pass

    return x

df = pd.read_parquet(parquet_path)
records = [clean(r) for r in df.to_dict(orient="records")]

def fallback(o):
    if isinstance(o, np.ndarray):
        return [clean(v) for v in o.tolist()]
    if isinstance(o, np.generic):
        return clean(o.item())
    if hasattr(o, "tolist"):
        try:
            return o.tolist()
        except Exception:
            pass
    if hasattr(o, "isoformat"):
        try:
            return o.isoformat()
        except Exception:
            pass
    return str(o)

payload = json.dumps(
    records,
    ensure_ascii=False,
    separators=(",", ":"),
    default=fallback
)

text = html_path.read_text(encoding="utf-8")
bak = html_path.with_name(f"index.html.bak_embed_styletitle_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(html_path, bak)

pat = re.compile(r'(<script id="DATA" type="application/json">)(.*?)(</script>)', re.S)
if not pat.search(text):
    raise SystemExit("DATA script tag not found")

text2 = pat.sub(lambda m: m.group(1) + payload + m.group(3), text, count=1)
html_path.write_text(text2, encoding="utf-8")

print(f"embedded {len(records)} rows into {html_path}")
print(f"backup: {bak}")
print("style_title non-null rows:", int(df["style_title"].notna().sum()) if "style_title" in df.columns else 0)

target = df[df["speaker_id"] == "K010_003a:IC01"][["speaker_id","style_title","style_title_reason","style_title_confidence"]]
print("\nTARGET ROW:")
print(target.to_string(index=False))
PY
```

---

## Step 3. 埋め込み確認

```bash
grep -n "_styleTitle\|styleTitleClamp\|Conversation style" docs/index.html
grep -o 'style_title' docs/index.html | wc -l
grep -o 'うなずき待機中の観客席' docs/index.html | wc -l
grep -o 'K010_003a:IC01' docs/index.html | wc -l
```

期待値:

* `style_title` が 0 ではない
* 該当タイトル文字列が 1 以上
* 該当 speaker_id が 1 以上

---

## Step 4. ローカル確認

```bash
python -m http.server 8000
```

ブラウザで以下を開く。

```text
http://localhost:8000/docs/index.html
```

表示確認時は **ハードリロード** を推奨。

* Mac Chrome: `Cmd + Shift + R`

---

## 表示確認ポイント

### 一覧

* `summary` の上に `style_title` が表示される
* 例: `ためらいがちな主人公ボイス`
* 例: `静かに見守る観客席`

### 詳細パネル

* `Conversation style` セクションが追加される
* `style_title_reason` が表示される
* `confidence: 0.xx` が表示される

### 非破壊性

* `summary` が引き続き表示される
* `labels` / `primary_label` / `score` / 既存ソート・絞り込みが壊れない
* `style_title` 列が無い場合は非表示で落ちない

---

## 実際に確認できた例

対象話者:

```text
K010_003a:IC01
```

style_title:

```text
うなずき待機中の観客席
```

style_title_reason:

```text
発話数・ペア数が平均以下で会話参加が控えめな点と、RESP_NE_AIZUCHI_RATEが高く相槌系の反応が多いことから、積極的に話すより聞いて頷く役回りが浮かぶ。質問率も低めで、じっと見守る観客席のような存在感を連想した。
```

style_title_confidence:

```text
0.68
```

---

## Git 反映

今回の成功状態を再現するために push すべきファイルは **`docs/index.html` のみ**。

理由:

* 描画ロジック追加
* CSS追加
* inline DATA 更新

が全部 `docs/index.html` に含まれているため。

### commit / push

```bash
git status --short
git add docs/index.html
git commit -m "Add style_title to conversation dashboard and embed updated data"
git push
```

---

## push対象外

以下は push 不要。

```text
docs/index.html.bak_*
artifacts/.../*.parquet
ローカル確認用の一時ファイル
```

---

## S3 / CloudFront 反映する場合

必要に応じて以下。

```bash
aws s3 cp docs/index.html s3://YOUR_BUCKET/index.html \
  --content-type "text/html; charset=utf-8" \
  --cache-control "no-cache, no-store, must-revalidate"

aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/index.html"
```

---

## トラブルシュート

### 症状

`style_title` が表示されない

### 原因1

`docs/index.html` の描画コードだけ更新され、inline DATA が古い

### 確認

```bash
grep -o 'style_title' docs/index.html | wc -l
```

### 原因2

parquet には列があるが、JSON 化時に `ndarray` が含まれて `json.dumps()` で失敗

### エラー例

```text
TypeError: Object of type ndarray is not JSON serializable
```

### 対応

NumPy 型を吸収する serializer を使う

---

## 今回の実装要約

* `docs/index.html` は inline DATA 方式
* 外部 parquet を直接読む実装には変更していない
* `style_title` は **補助的見出し**
* 一覧では `summary` 上、詳細では `Conversation style` セクションとして追加
* 既存の説明系 UI は維持
* 旧データにも配慮して存在時のみ表示

---

## 完了条件

* 一覧に `style_title` が見える
* 詳細に `style_title_reason` / `style_title_confidence` が見える
* 既存 UI が壊れていない
* `docs/index.html` のみで成功状態を再現できる
