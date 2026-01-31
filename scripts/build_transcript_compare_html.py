#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build side-by-side transcript comparison HTML for CEJC/CSJ style data.

Left : CPsy transcript (from parquet, filtered by speaker_id)
Right: Nanami transcript (from segments.csv; roles ALL/CHI/MOT)

Windowing: fixed time window (e.g. 30 sec) shared by both sources.
Fallback: if CPsy has no start/end, falls back to char-window.

Usage example:
python scripts/build_transcript_compare_html.py \
  --speaker_id "T007_007:IC06" \
  --cpsy_parquet "artifacts/.../labels_....parquet" \
  --nanami_dir "tmp/nanami_audio/T007_007_IC06" \
  --out "tmp/compare_T007_007_IC06/transcript_compare.html" \
  --window_sec 30
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

try:
    import jaconv
except Exception:
    jaconv = None

try:
    from jiwer import cer as jiwer_cer
except Exception:
    jiwer_cer = None


TEXT_COL_CANDIDATES = [
    # common guesses
    "text", "utt", "utterance", "transcript", "surface", "content",
    "ja_text", "utt_text", "utt_surface", "raw_text", "raw_utt",
    # sometimes normalized variants exist
    "norm_text", "normalized_text",
]
START_COL_CANDIDATES = ["start", "t_start", "utt_start", "begin", "onset", "start_sec", "start_time"]
END_COL_CANDIDATES = ["end", "t_end", "utt_end", "finish", "offset", "end_sec", "end_time"]


def norm_text(s: str) -> str:
    s = (s or "").strip()
    if jaconv is not None:
        # zenkaku->hankaku for digits/ascii, keep kana as is
        s = jaconv.z2h(s, kana=False, digit=True, ascii=True)
    # remove spaces
    s = re.sub(r"\s+", "", s)
    # unify punctuation a bit
    s = s.replace("，", "、").replace(",", "、").replace("．", "。").replace(".", "。")
    return s


def pick_first_existing(cols: List[str], candidates: List[str]) -> Optional[str]:
    s = set(cols)
    for c in candidates:
        if c in s:
            return c
    # try case-insensitive match
    lower = {c.lower(): c for c in cols}
    for c in candidates:
        if c.lower() in lower:
            return lower[c.lower()]
    return None


def read_cpsy_parquet(path: Path, speaker_id: str) -> pd.DataFrame:
    # Prefer pyarrow dataset filter if available; fallback to pandas
    try:
        import pyarrow.dataset as ds  # type: ignore

        dataset = ds.dataset(str(path))
        # speaker_id column name could be different; try to find it
        schema_names = [f.name for f in dataset.schema]
        spk_col = None
        for cand in ["speaker_id", "speaker", "spkid", "spk_id"]:
            if cand in schema_names:
                spk_col = cand
                break
        if spk_col is None:
            # fallback: read all
            return pd.read_parquet(path)

        table = dataset.to_table(filter=(ds.field(spk_col) == speaker_id))
        return table.to_pandas()
    except Exception:
        df = pd.read_parquet(path)
        # try to find speaker column
        spk_col = pick_first_existing(list(df.columns), ["speaker_id", "speaker", "spkid", "spk_id"])
        if spk_col is None:
            raise RuntimeError(f"Could not find speaker_id column in parquet. columns={list(df.columns)[:50]}")
        return df[df[spk_col] == speaker_id].copy()


def make_time_windows(t0: float, t1: float, w: float) -> List[Tuple[float, float]]:
    n = int((t1 - t0) // w) + 1
    out = []
    for i in range(n):
        a = t0 + i * w
        b = min(t1, a + w)
        out.append((a, b))
    return out


def collect_text_in_window(
    df: pd.DataFrame,
    start_col: str,
    end_col: str,
    text_col: str,
    a: float,
    b: float,
    extra_filter: Optional[pd.Series] = None,
) -> str:
    sub = df
    if extra_filter is not None:
        sub = sub[extra_filter]
    # overlap condition: (start < b) & (end > a)
    s = pd.to_numeric(sub[start_col], errors="coerce")
    e = pd.to_numeric(sub[end_col], errors="coerce")
    m = (s < b) & (e > a)
    sub2 = sub[m]
    if sub2.empty:
        return ""
    texts = [str(x) for x in sub2[text_col].fillna("").tolist() if str(x).strip()]
    return "\n".join(texts)


def sim_metrics(a: str, b: str) -> Dict[str, float]:
    na = norm_text(a)
    nb = norm_text(b)
    if len(na) == 0 and len(nb) == 0:
        return {"cer": 0.0, "len_a": 0, "len_b": 0}
    if jiwer_cer is not None:
        try:
            c = float(jiwer_cer(na, nb))
        except Exception:
            c = 1.0
    else:
        # rough fallback: 1 if different, 0 if same
        c = 0.0 if na == nb else 1.0
    return {"cer": c, "len_a": len(na), "len_b": len(nb)}


def render_html(
    rows_all: List[Dict],
    rows_chi: List[Dict],
    rows_mot: List[Dict],
    title: str,
    out: Path,
) -> None:
    def rows_to_html(rows: List[Dict]) -> str:
        buf = []
        for r in rows:
            ta = html.escape(r.get("left", ""))
            tb = html.escape(r.get("right", ""))
            cer = r.get("cer", 1.0)
            a, b = r["t0"], r["t1"]
            badge = "ok" if cer <= 0.5 else ("mid" if cer <= 1.0 else "bad")
            buf.append(f"""
            <div class="row">
              <div class="meta">
                <div class="time">{a:8.1f}–{b:8.1f} sec</div>
                <div class="cer {badge}">CER(norm): {cer:.3f}</div>
              </div>
              <div class="pane">
                <pre class="cell left">{ta}</pre>
                <pre class="cell right">{tb}</pre>
              </div>
            </div>
            """)
        return "\n".join(buf)

    html_text = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{html.escape(title)}</title>
<style>
  body {{ font-family: ui-sans-serif, system-ui, -apple-system; margin:0; background:#fff; color:#111; }}
  header {{ position: sticky; top:0; background:#fff; border-bottom:1px solid #eee; padding:12px 16px; z-index:10; }}
  .title {{ font-size:16px; font-weight:700; }}
  .controls {{ margin-top:8px; display:flex; gap:10px; align-items:center; flex-wrap:wrap; }}
  button {{ padding:6px 10px; border:1px solid #ddd; background:#fafafa; border-radius:8px; cursor:pointer; }}
  button.active {{ border-color:#999; background:#f0f0f0; }}
  input[type="text"] {{ padding:6px 10px; border:1px solid #ddd; border-radius:8px; min-width:240px; }}
  .wrap {{ padding: 8px 12px 24px; }}
  .row {{ border:1px solid #eee; border-radius:12px; margin:10px 4px; overflow:hidden; }}
  .meta {{ display:flex; justify-content:space-between; gap:12px; padding:8px 10px; background:#fafafa; border-bottom:1px solid #eee; }}
  .time {{ font-family: ui-monospace, Menlo, monospace; font-size:12px; color:#333; }}
  .cer {{ font-family: ui-monospace, Menlo, monospace; font-size:12px; }}
  .cer.ok {{ color:#0a7; }}
  .cer.mid {{ color:#b80; }}
  .cer.bad {{ color:#c22; }}
  .pane {{ display:grid; grid-template-columns: 1fr 1fr; gap:0; }}
  .cell {{ margin:0; padding:10px; white-space:pre-wrap; overflow-wrap:anywhere; font-size:13px; line-height:1.5; min-height:56px; }}
  .left {{ border-right:1px solid #eee; background:#fff; }}
  .right {{ background:#fff; }}
  .hidden {{ display:none; }}
  mark {{ background: #ffec99; }}
</style>
</head>
<body>
<header>
  <div class="title">{html.escape(title)}</div>
  <div class="controls">
    <button id="tab_all" class="active" onclick="setTab('all')">Nanami: ALL</button>
    <button id="tab_chi" onclick="setTab('chi')">Nanami: CHI</button>
    <button id="tab_mot" onclick="setTab('mot')">Nanami: MOT</button>
    <span style="margin-left:8px;">検索:</span>
    <input id="q" type="text" placeholder="文字列（両側ハイライト）" oninput="applySearch()"/>
    <button onclick="clearSearch()">クリア</button>
    <label style="margin-left:8px;">
      <input id="hideEmpty" type="checkbox" onchange="toggleEmpty()"/> 空行を隠す
    </label>
  </div>
</header>

<div class="wrap">
  <div id="view_all">{rows_to_html(rows_all)}</div>
  <div id="view_chi" class="hidden">{rows_to_html(rows_chi)}</div>
  <div id="view_mot" class="hidden">{rows_to_html(rows_mot)}</div>
</div>

<script>
let currentTab = 'all';

function setTab(t) {{
  currentTab = t;
  document.getElementById('view_all').classList.toggle('hidden', t !== 'all');
  document.getElementById('view_chi').classList.toggle('hidden', t !== 'chi');
  document.getElementById('view_mot').classList.toggle('hidden', t !== 'mot');
  document.getElementById('tab_all').classList.toggle('active', t === 'all');
  document.getElementById('tab_chi').classList.toggle('active', t === 'chi');
  document.getElementById('tab_mot').classList.toggle('active', t === 'mot');
  applySearch();
  toggleEmpty();
}}

function escRegExp(s) {{
  return s.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&');
}}

function applySearch() {{
  const q = document.getElementById('q').value.trim();
  const view = document.getElementById('view_' + currentTab);
  view.querySelectorAll('pre.cell').forEach(pre => {{
    const raw = pre.textContent;
    if (!q) {{
      pre.innerHTML = raw.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
      return;
    }}
    const re = new RegExp(escRegExp(q), 'g');
    const safe = raw.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
    pre.innerHTML = safe.replace(re, m => `<mark>${{m}}</mark>`);
  }});
}}

function clearSearch() {{
  document.getElementById('q').value = '';
  applySearch();
}}

function toggleEmpty() {{
  const hide = document.getElementById('hideEmpty').checked;
  const view = document.getElementById('view_' + currentTab);
  view.querySelectorAll('.row').forEach(row => {{
    const left = row.querySelector('pre.left').textContent.trim();
    const right = row.querySelector('pre.right').textContent.trim();
    const empty = (!left && !right);
    row.style.display = (hide && empty) ? 'none' : '';
  }});
}}
</script>
</body>
</html>
"""
    out.write_text(html_text, encoding="utf-8")
    print(f"wrote: {out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--speaker_id", required=True)
    ap.add_argument("--cpsy_parquet", required=True)
    ap.add_argument("--nanami_dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--window_sec", type=float, default=30.0)
    args = ap.parse_args()

    speaker_id = args.speaker_id
    cpsy_parquet = Path(args.cpsy_parquet)
    nan_dir = Path(args.nanami_dir)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    # --- load nanami segments ---
    seg_path = nan_dir / "segments.csv"
    if not seg_path.exists():
        raise FileNotFoundError(f"nanami segments.csv not found: {seg_path}")
    nan = pd.read_csv(seg_path)
    # expected: start,end,speaker,text
    n_start = pick_first_existing(list(nan.columns), ["start"])
    n_end = pick_first_existing(list(nan.columns), ["end"])
    n_spk = pick_first_existing(list(nan.columns), ["speaker"])
    n_txt = pick_first_existing(list(nan.columns), ["text"])
    if not all([n_start, n_end, n_txt]):
        raise RuntimeError(f"nanami segments.csv must have start/end/text. cols={list(nan.columns)}")

    # --- load cpsy filtered rows ---
    cpsy = read_cpsy_parquet(cpsy_parquet, speaker_id=speaker_id)
    if cpsy.empty:
        raise RuntimeError(f"No rows found in cpsy parquet for speaker_id={speaker_id}")

    c_txt = pick_first_existing(list(cpsy.columns), TEXT_COL_CANDIDATES)
    if c_txt is None:
        raise RuntimeError(
            "Could not auto-detect CPsy text column.\n"
            f"Columns sample: {list(cpsy.columns)[:80]}\n"
            "Please add your column name to TEXT_COL_CANDIDATES in this script."
        )

    c_start = pick_first_existing(list(cpsy.columns), START_COL_CANDIDATES)
    c_end = pick_first_existing(list(cpsy.columns), END_COL_CANDIDATES)

    # If no time columns, fallback to char windowing (rare)
    use_time = (c_start is not None and c_end is not None)
    if not use_time:
        print("[warn] CPsy has no start/end columns; falling back to char-window compare.")
        left_text = "\n".join([str(x) for x in cpsy[c_txt].fillna("").tolist() if str(x).strip()])
        right_all = "\n".join([str(x) for x in nan[n_txt].fillna("").tolist() if str(x).strip()])
        right_chi = "\n".join([str(x) for x in nan[nan[n_spk] == "CHI"][n_txt].fillna("").tolist()]) if n_spk else right_all
        right_mot = "\n".join([str(x) for x in nan[nan[n_spk] == "MOT"][n_txt].fillna("").tolist()]) if n_spk else right_all

        def chunk(s: str, w: int = 240) -> List[str]:
            s = s.strip()
            return [s[i:i+w] for i in range(0, len(s), w)] or [""]

        L = chunk(left_text)
        A = chunk(right_all)
        C = chunk(right_chi)
        M = chunk(right_mot)
        nmax = max(len(L), len(A), len(C), len(M))
        def pad(x): return x + [""] * (nmax - len(x))
        L, A, C, M = pad(L), pad(A), pad(C), pad(M)

        rows_all, rows_chi, rows_mot = [], [], []
        for i in range(nmax):
            met = sim_metrics(L[i], A[i])
            rows_all.append({"t0": i, "t1": i+1, "left": L[i], "right": A[i], "cer": met["cer"]})
            met = sim_metrics(L[i], C[i])
            rows_chi.append({"t0": i, "t1": i+1, "left": L[i], "right": C[i], "cer": met["cer"]})
            met = sim_metrics(L[i], M[i])
            rows_mot.append({"t0": i, "t1": i+1, "left": L[i], "right": M[i], "cer": met["cer"]})

        title = f"Transcript Compare (char-window) | {speaker_id}"
        render_html(rows_all, rows_chi, rows_mot, title=title, out=out)
        return

    # --- time-window compare ---
    cpsy[c_start] = pd.to_numeric(cpsy[c_start], errors="coerce")
    cpsy[c_end] = pd.to_numeric(cpsy[c_end], errors="coerce")
    nan[n_start] = pd.to_numeric(nan[n_start], errors="coerce")
    nan[n_end] = pd.to_numeric(nan[n_end], errors="coerce")

    t1 = float(
        max(
            cpsy[c_end].dropna().max(),
            nan[n_end].dropna().max(),
        )
    )
    windows = make_time_windows(0.0, t1, float(args.window_sec))

    rows_all, rows_chi, rows_mot = [], [], []

    for (a, b) in windows:
        left = collect_text_in_window(cpsy, c_start, c_end, c_txt, a, b)
        right_all = collect_text_in_window(nan, n_start, n_end, n_txt, a, b)

        if n_spk:
            right_chi = collect_text_in_window(nan, n_start, n_end, n_txt, a, b, extra_filter=(nan[n_spk] == "CHI"))
            right_mot = collect_text_in_window(nan, n_start, n_end, n_txt, a, b, extra_filter=(nan[n_spk] == "MOT"))
        else:
            right_chi, right_mot = right_all, right_all

        rows_all.append({"t0": a, "t1": b, "left": left, "right": right_all, "cer": sim_metrics(left, right_all)["cer"]})
        rows_chi.append({"t0": a, "t1": b, "left": left, "right": right_chi, "cer": sim_metrics(left, right_chi)["cer"]})
        rows_mot.append({"t0": a, "t1": b, "left": left, "right": right_mot, "cer": sim_metrics(left, right_mot)["cer"]})

    title = f"Transcript Compare (time-window {args.window_sec:.0f}s) | {speaker_id}"
    render_html(rows_all, rows_chi, rows_mot, title=title, out=out)


if __name__ == "__main__":
    main()

