#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import html
import re
from pathlib import Path

def norm_text(t: str) -> str:
    t = (t or "").strip()
    # 見やすさのため空白を1つに
    t = re.sub(r"\s+", " ", t)
    return t

def load_nanami_segments(path: Path, with_speaker: bool):
    rows=[]
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        r = csv.DictReader(f)
        for i, row in enumerate(r, start=1):
            start = float(row.get("start") or 0.0)
            end   = float(row.get("end") or 0.0)
            spk   = (row.get("speaker") or "").strip()
            txt   = norm_text(row.get("text") or "")
            if not txt:
                continue
            rows.append({
                "idx": i,
                "start": start,
                "end": end,
                "speaker": spk,
                "text": txt,
                "text_disp": f"[{spk}] {txt}" if (with_speaker and spk) else txt
            })
    return rows

def detect_text_col(cols):
    # よくある候補
    cand = ["text", "transcription", "utterance", "orth", "kana", "surface", "content"]
    for c in cand:
        if c in cols:
            return c
    # “文字列っぽい列”を自動推定（時間列/ID列は除外）
    bad = set(["start","end","xmin","xmax","tmin","tmax","begin","finish","duration","tier","speaker","spk","id","index","conv_id","conversation_id"])
    best=None
    best_score=-1
    for c in cols:
        if c in bad:
            continue
        lc=c.lower()
        if any(k in lc for k in ["time","sec","dur","start","end","xmin","xmax","tmin","tmax","idx","id"]):
            continue
        # “txt” “trans” “orth” が入ってたら加点
        score = 0
        if any(k in lc for k in ["text","trans","orth","utt","sentence","content"]):
            score += 3
        best = c if score > best_score else best
        best_score = max(best_score, score)
    return best

def load_ref_csv(path: Path):
    import pandas as pd
    # CEJC csv is often not UTF-8 (cp932/shift_jis). Try fallbacks.
    last_err = None
    for enc in ("utf-8", "utf-8-sig", "cp932", "shift_jis", "latin-1"):
        try:
            df = pd.read_csv(path, encoding=enc)
            # success
            break
        except Exception as e:
            last_err = e
            df = None
    if df is None:
        raise RuntimeError(f"Failed to read ref_csv with fallback encodings: {last_err}")
    cols = list(df.columns)
    # 時間列候補
    start_col = next((c for c in cols if c.lower() in ["start","xmin","tmin","begin"]), None)
    end_col   = next((c for c in cols if c.lower() in ["end","xmax","tmax","finish"]), None)

    if start_col is None or end_col is None:
        # “start/endっぽい”を緩く探索
        for c in cols:
            lc=c.lower()
            if start_col is None and "start" in lc:
                start_col=c
            if end_col is None and ("end" in lc or "stop" in lc or "finish" in lc):
                end_col=c

    text_col = detect_text_col(cols)
    if text_col is None:
        raise RuntimeError(f"Could not detect ref text column. cols={cols}")

    # speaker列（任意）
    spk_col = next((c for c in cols if c.lower() in ["speaker","spk","role","who"]), None)

    rows=[]
    for i, r in df.iterrows():
        try:
            st=float(r[start_col]) if start_col else 0.0
            en=float(r[end_col]) if end_col else 0.0
        except Exception:
            continue
        txt=norm_text(str(r.get(text_col,"") if r.get(text_col,"") is not None else ""))
        if not txt or txt.lower()=="nan":
            continue
        spk = norm_text(str(r.get(spk_col,""))) if spk_col else ""
        rows.append({
            "idx": int(i)+1,
            "start": st,
            "end": en,
            "speaker": spk,
            "text": txt,
            "text_disp": f"[{spk}] {txt}" if spk else txt
        })
    return rows, {"start_col":start_col, "end_col":end_col, "text_col":text_col, "speaker_col":spk_col}

def fmt_time(x: float) -> str:
    m = int(x//60)
    s = x - 60*m
    return f"{m:02d}:{s:06.3f}"

def slice_windows(rows, win_sec: float):
    # rowsを時間順に、win_sec幅で切る（最小公倍数というより “等幅窓”）
    if not rows:
        return []
    rows = sorted(rows, key=lambda r: (r["start"], r["end"]))
    t0 = min(r["start"] for r in rows)
    t1 = max(r["end"] for r in rows)
    n = int(((t1 - t0) / win_sec) + 1)
    windows=[]
    for k in range(n):
        a = t0 + k*win_sec
        b = a + win_sec
        items = [r for r in rows if not (r["end"] <= a or r["start"] >= b)]
        if items:
            windows.append({"widx":k+1,"a":a,"b":b,"items":items})
    return windows

def build_html(ref_windows, hyp_windows, title: str, ref_meta: dict, out: Path):
    # window indexで合わせる（長さが違う場合も表示は揃える）
    n = max(len(ref_windows), len(hyp_windows))
    def getw(ws, i):
        return ws[i] if 0 <= i < len(ws) else None

    css = """
    body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:0}
    header{position:sticky;top:0;background:#fff;border-bottom:1px solid #ddd;padding:10px 14px;z-index:10}
    .meta{color:#555;font-size:12px}
    .wrap{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:10px}
    .col{border:1px solid #ddd;border-radius:10px;overflow:hidden}
    .col h2{margin:0;font-size:14px;padding:10px;background:#f7f7f7;border-bottom:1px solid #ddd}
    .win{border-top:1px solid #eee;padding:10px}
    .whead{font-weight:600;font-size:12px;color:#333;margin-bottom:6px}
    .item{font-size:13px;line-height:1.45;margin:3px 0}
    .time{color:#666;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;font-size:12px}
    .empty{color:#aaa;font-style:italic}
    .toolbar{display:flex;gap:8px;align-items:center;margin-top:6px}
    input[type="number"]{width:90px}
    """
    js = """
    function filterText(){
      const q = (document.getElementById('q').value||'').trim();
      const items = document.querySelectorAll('.item');
      if(!q){ items.forEach(el=>el.style.display=''); return; }
      const re = new RegExp(q,'i');
      items.forEach(el=>{
        el.style.display = re.test(el.textContent) ? '' : 'none';
      });
    }
    function jumpWin(){
      const n = parseInt(document.getElementById('jump').value||'1',10);
      const el = document.getElementById('w_'+n);
      if(el) el.scrollIntoView({behavior:'smooth', block:'start'});
    }
    """

    def render_win(w):
        if w is None:
            return '<div class="win"><div class="empty">（no window）</div></div>'
        lines = []
        lines.append(f'<div class="whead"><span class="time">{html.escape(fmt_time(w["a"]))} – {html.escape(fmt_time(w["b"]))}</span></div>')
        if not w["items"]:
            lines.append('<div class="empty">（no items）</div>')
        else:
            for r in w["items"]:
                lines.append(
                    f'<div class="item"><span class="time">{html.escape(fmt_time(r["start"]))}-{html.escape(fmt_time(r["end"]))}</span> '
                    f'{html.escape(r["text_disp"])}</div>'
                )
        return '<div class="win">' + "\n".join(lines) + "</div>"

    parts=[]
    parts.append("<!doctype html><html><head><meta charset='utf-8'>")
    parts.append(f"<title>{html.escape(title)}</title>")
    parts.append(f"<style>{css}</style></head><body>")
    parts.append("<header>")
    parts.append(f"<div><b>{html.escape(title)}</b></div>")
    parts.append(f"<div class='meta'>ref cols: start={ref_meta.get('start_col')} end={ref_meta.get('end_col')} text={ref_meta.get('text_col')} speaker={ref_meta.get('speaker_col')}</div>")
    parts.append("<div class='toolbar'>")
    parts.append("Filter: <input id='q' oninput='filterText()' placeholder='regex / keyword' />")
    parts.append("Jump window#: <input id='jump' type='number' min='1' /> <button onclick='jumpWin()'>Go</button>")
    parts.append("</div>")
    parts.append("</header>")

    parts.append("<div class='wrap'>")
    parts.append("<div class='col'><h2>LEFT: CEJC transUnit (ref)</h2>")
    for i in range(n):
        w=getw(ref_windows,i)
        parts.append(f"<div id='w_{i+1}'>"+render_win(w)+"</div>")
    parts.append("</div>")
    parts.append("<div class='col'><h2>RIGHT: Nanami segments (hyp)</h2>")
    for i in range(n):
        w=getw(hyp_windows,i)
        parts.append(render_win(w))
    parts.append("</div>")
    parts.append("</div>")

    parts.append(f"<script>{js}</script></body></html>")
    out.write_text("\n".join(parts), encoding="utf-8")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--ref_csv", required=True)
    ap.add_argument("--nanami_segments", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="Transcript Compare")
    ap.add_argument("--min_window_sec", type=float, default=0.8)
    ap.add_argument("--with_nanami_speaker", action="store_true")
    args=ap.parse_args()

    ref_csv=Path(args.ref_csv)
    hyp_csv=Path(args.nanami_segments)
    out=Path(args.out)

    if not ref_csv.exists():
        raise SystemExit(f"ref_csv not found: {ref_csv}")
    if not hyp_csv.exists():
        raise SystemExit(f"nanami_segments not found: {hyp_csv}")

    ref_rows, ref_meta = load_ref_csv(ref_csv)
    hyp_rows = load_nanami_segments(hyp_csv, with_speaker=args.with_nanami_speaker)

    ref_w = slice_windows(ref_rows, args.min_window_sec)
    hyp_w = slice_windows(hyp_rows, args.min_window_sec)

    out.parent.mkdir(parents=True, exist_ok=True)
    build_html(ref_w, hyp_w, args.title, ref_meta, out)
    print("wrote:", out)
    print("ref_rows:", len(ref_rows), "ref_windows:", len(ref_w))
    print("hyp_rows:", len(hyp_rows), "hyp_windows:", len(hyp_w))

if __name__=="__main__":
    main()
