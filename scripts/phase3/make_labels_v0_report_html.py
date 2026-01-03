# scripts/phase3/make_labels_v0_report_html.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import html as htmlmod
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd


# -------------------------
# JSON utils
# -------------------------
def _safe_json_obj(s: Any) -> Dict[str, Any]:
    if not isinstance(s, str) or not s.strip():
        return {}
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _safe_json_list(s: Any) -> List[Any]:
    if not isinstance(s, str) or not s.strip():
        return []
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, list) else []
    except Exception:
        return []


def _safe_float(v: Any) -> float | None:
    """Convert to float; return None for None/NaN/Inf."""
    try:
        if v is None:
            return None
        x = float(v)
        if math.isnan(x) or math.isinf(x):
            return None
        return x
    except Exception:
        return None



def _collect_parquet_paths(path_str: str) -> List[Path]:
    """
    Accepts:
      - empty
      - single file
      - directory (rglob *.parquet)
      - comma-separated list of files/dirs
    """
    if not path_str:
        return []
    parts = [x.strip() for x in path_str.split(",") if x.strip()]
    out: List[Path] = []
    for s in parts:
        p = Path(s)
        if p.is_dir():
            out.extend(sorted([q for q in p.rglob("*.parquet") if q.is_file()]))
        else:
            out.append(p)

    # unique (keep order)
    seen = set()
    uniq: List[Path] = []
    for p in out:
        sp = str(p)
        if sp not in seen:
            seen.add(sp)
            uniq.append(p)
    return uniq


def build_pg_index(pg_paths: List[Path]) -> Tuple[Dict[str, Dict[str, Any]], int]:
    """
    Build index: speaker_key -> PG metrics dict
    speaker_key = f"{conversation_id}:{speaker_id}"

    Expected columns (either prefixed or not):
      conversation_id, speaker_id, dataset?, speech_extract_mode?
      total_time, pause_mean, resp_gap_mean, resp_gap_p50, resp_gap_p90,
      resp_overlap_rate, n_resp_events
    """
    idx: Dict[str, Dict[str, Any]] = {}
    total = 0

    for fp in pg_paths:
        if not fp.exists():
            continue
        df = pd.read_parquet(fp)
        total += len(df)
        if not {"conversation_id", "speaker_id"}.issubset(df.columns):
            continue

        def pick(row, a, b=None):
            if a in row and row[a] is not None:
                return row[a]
            if b and b in row and row[b] is not None:
                return row[b]
            return None

        for _, r in df.iterrows():
            conv = str(r.get("conversation_id") or "").strip()
            spk = str(r.get("speaker_id") or "").strip()
            conv = conv.split("/")[-1]
            spk = spk.split("/")[-1]
            if not conv or not spk:
                continue
            key = f"{conv}:{spk}"

            m = {
                "dataset_full": str(r.get("dataset") or ""),
                "speech_extract_mode": str(r.get("speech_extract_mode") or ""),
                "PG_total_time": _safe_float(pick(r, "PG_total_time", "total_time")),
                "PG_pause_mean": _safe_float(pick(r, "PG_pause_mean", "pause_mean")),
                "PG_resp_gap_mean": _safe_float(pick(r, "PG_resp_gap_mean", "resp_gap_mean")),
                "PG_resp_gap_p50": _safe_float(pick(r, "PG_resp_gap_p50", "resp_gap_p50")),
                "PG_resp_gap_p90": _safe_float(pick(r, "PG_resp_gap_p90", "resp_gap_p90")),
                "PG_resp_overlap_rate": _safe_float(pick(r, "PG_resp_overlap_rate", "resp_overlap_rate")),
                "PG_n_resp_events": _safe_float(pick(r, "PG_n_resp_events", "n_resp_events")),
                "source_file": str(fp),
            }
            keys = {key}

            if ":" in spk:

                keys.add(spk)

            if ":" in conv:

                keys.add(conv)

            for k in keys:

                idx[k] = m
    return idx, total




def build_pg_index_v2(pg_metrics_parquet_or_dir: str) -> Tuple[Dict[str, Dict[str, Any]], int]:
    """
    Robust PG index builder.
    Inputs: parquet file/dir or list of them (or comma-separated).

    Supports BOTH schemas:
      A) speaker-level (Phase5 PG parquet): columns ['dataset','speaker_id','PG_*...']
         - speaker_id is already "conv:role" (e.g., D01M0047:R, T007_007:IC06)
      B) legacy: columns ['conversation_id','speaker_id', ...] (+ optional PG_* without prefix)

    Key strategy (matches this script's speaker_key = labels.speaker_id):
      - If speaker_id already contains ":" => use it directly as key.
      - Else if conversation_id exists => key = f"{conversation_id}:{speaker_id}".
      - Else => key = speaker_id.
    """
    def norm(x):
        return ("" if x is None else str(x)).strip().split("/")[-1]

    def safe_num(x):
        return _safe_float(x)

    # inputs: list[Path]/list[str] OR comma-separated string
    files = []
    if isinstance(pg_metrics_parquet_or_dir, (list, tuple)):
        for x in pg_metrics_parquet_or_dir:
            xp = Path(str(x))
            if xp.is_dir():
                files += [q for q in xp.rglob("*.parquet") if q.is_file()]
            elif xp.is_file() and xp.suffix.lower() == ".parquet":
                files.append(xp)
    else:
        roots = [x.strip() for x in (pg_metrics_parquet_or_dir or "").split(",") if x.strip()]
        for r in roots:
            rp = Path(r)
            if rp.is_dir():
                files += [q for q in rp.rglob("*.parquet") if q.is_file()]
            elif rp.is_file() and rp.suffix.lower() == ".parquet":
                files.append(rp)

    files = sorted(set(files))
    if not files:
        return {}, 0

    idx: Dict[str, Dict[str, Any]] = {}
    total = 0

    for fp in files:
        df = pd.read_parquet(fp)
        if "speaker_id" not in df.columns:
            continue

        total += len(df)
        has_conv = "conversation_id" in df.columns
        has_ds = "dataset" in df.columns

        # collect PG columns (future-proof)
        pg_cols = [c for c in df.columns if str(c).startswith("PG_")]

        for _, r in df.iterrows():
            conv = norm(r.get("conversation_id")) if has_conv else ""
            spk = norm(r.get("speaker_id"))
            if not spk:
                continue

            # metrics dict
            m: Dict[str, Any] = {"source_file": str(fp)}
            if has_ds:
                m["dataset_full"] = str(r.get("dataset") or "")

            # PG_* direct
            for c in pg_cols:
                m[c] = safe_num(r.get(c))

            # legacy fallback (when PG_* columns are not present)
            if not pg_cols:
                m.update({
                    "PG_total_time":        safe_num(r.get("total_time")),
                    "PG_pause_mean":        safe_num(r.get("pause_mean")),
                    "PG_pause_p50":         safe_num(r.get("pause_p50")),
                    "PG_pause_p90":         safe_num(r.get("pause_p90")),
                    "PG_resp_gap_mean":     safe_num(r.get("resp_gap_mean")),
                    "PG_resp_gap_p50":      safe_num(r.get("resp_gap_p50")),
                    "PG_resp_gap_p90":      safe_num(r.get("resp_gap_p90")),
                    "PG_overlap_rate":      safe_num(r.get("overlap_rate")),
                    "PG_resp_overlap_rate": safe_num(r.get("resp_overlap_rate")),
                    "PG_n_resp_events":     safe_num(r.get("n_resp_events")),
                })

            keys = set()
            if ":" in spk:
                keys.add(spk)  # already "conv:role"
                # also add conv:role if conv differs / safety
                if conv:
                    parts = spk.split(":", 1)
                    if len(parts) == 2 and parts[1]:
                        keys.add(f"{conv}:{parts[1]}")
            else:
                if conv:
                    keys.add(f"{conv}:{spk}")
                else:
                    keys.add(spk)

            for k in keys:
                idx[k] = m

    return idx, total


def load_pg_summary(pg_summary_parquet: str) -> Dict[str, Dict[str, Any]]:
    """
    dataset -> summary stats dict (json-friendly)
    expects column 'dataset' + PG_* columns
    """
    if not pg_summary_parquet:
        return {}
    p = Path(pg_summary_parquet)
    if not p.exists():
        return {}
    df = pd.read_parquet(p)
    if "dataset" not in df.columns:
        return {}

    out: Dict[str, Dict[str, Any]] = {}
    for _, r in df.iterrows():
        ds = str(r.get("dataset") or "").strip()
        if not ds:
            continue
        d: Dict[str, Any] = {}
        for c in df.columns:
            if c == "dataset":
                continue
            v = r.get(c)
            d[c] = _safe_float(v)
        out[ds] = d
    return out


def _script_json(s: str) -> str:
    # scriptタグ内で </script> が出ても壊れない保険
    return s.replace("</", "<\\/")


def _dataset_norm(x: str) -> str:
    x = (x or "").lower()
    if x.startswith("cejc"):
        return "cejc"
    if x.startswith("csj"):
        return "csj"
    return "unknown"


# -------------------------
# Examples index
# -------------------------
def build_examples_index(examples_dir: str, max_per_speaker: int = 12) -> Tuple[Dict[str, List[Dict[str, Any]]], int]:
    """
    speaker_key = f"{conversation_id}:{speaker_id}"
      - rec.speaker_id が "T007_007:IC06" の形式なら一致する想定
    例: examples parquet schema (your current):
      dataset, conversation_id, speaker_id,
      prev_text, prev_sfp_group,
      resp_speaker_id, resp_text, resp_is_aizuchi, resp_is_question,
      RESP_NE_AIZUCHI_RATE, n_pairs_after_NE, ...
    """
    root = Path(examples_dir)
    files = sorted([p for p in root.rglob("*.parquet") if p.is_file()])
    if not files:
        return {}, 0

    idx: Dict[str, List[Dict[str, Any]]] = {}
    total = 0

    for fp in files:
        df = pd.read_parquet(fp)
        total += len(df)

        needed = ["dataset", "conversation_id", "speaker_id", "prev_text", "resp_text"]
        if not all(c in df.columns for c in needed):
            continue

        has_prev_group = "prev_sfp_group" in df.columns
        has_resp_speaker = "resp_speaker_id" in df.columns
        has_aizuchi = "resp_is_aizuchi" in df.columns
        has_q = "resp_is_question" in df.columns
        has_rate = "RESP_NE_AIZUCHI_RATE" in df.columns
        has_npairs = "n_pairs_after_NE" in df.columns

        # metric name from path (optional)
        metric = "NE_AIZUCHI_EXAMPLE"
        pstr = str(fp).lower()
        if "ne_aizuchi" in pstr:
            metric = "NE_AIZUCHI_EXAMPLE"

        for _, r in df.iterrows():
            ds = _dataset_norm(str(r.get("dataset") or ""))
            conv = str(r.get("conversation_id") or "")
            spk = str(r.get("speaker_id") or "")
            if not conv or not spk:
                continue

            key = f"{conv}:{spk}"

            prev_text = str(r.get("prev_text") or "").strip()
            resp_text = str(r.get("resp_text") or "").strip()
            prev_group = str(r.get("prev_sfp_group") or "") if has_prev_group else ""
            resp_spk = str(r.get("resp_speaker_id") or "") if has_resp_speaker else ""
            is_aiz = bool(r.get("resp_is_aizuchi")) if has_aizuchi and r.get("resp_is_aizuchi") is not None else None
            is_qv = bool(r.get("resp_is_question")) if has_q and r.get("resp_is_question") is not None else None
            rate = float(r.get("RESP_NE_AIZUCHI_RATE")) if has_rate and r.get("RESP_NE_AIZUCHI_RATE") is not None else None
            npairs = int(r.get("n_pairs_after_NE")) if has_npairs and r.get("n_pairs_after_NE") is not None else None

            ex = {
                "metric": metric,
                "dataset": ds,
                "conversation_id": conv,
                "speaker_id": spk,
                "prev_text": prev_text,
                "prev_sfp_group": prev_group,
                "resp_text": resp_text,
                "resp_speaker_id": resp_spk,
                "resp_is_aizuchi": is_aiz,
                "resp_is_question": is_qv,
                "RESP_NE_AIZUCHI_RATE": rate,
                "n_pairs_after_NE": npairs,
                "source_file": str(fp),
            }

            lst = idx.get(key)
            if lst is None:
                idx[key] = [ex]
            else:
                if len(lst) < max_per_speaker:
                    lst.append(ex)

    return idx, total


# -------------------------
# HTML template (NO f-string)
# -------------------------
HTML_TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>__TITLE_ESC__</title>
  <style>
    :root {
      --bg: #ffffff;
      --text: #111111;
      --muted: #666666;
      --line: #d9d9d9;
      --head: #f6f6f6;
      --card: #fafafa;
      --shadow: 0 2px 14px rgba(0,0,0,0.06);
      --radius: 16px;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      --sans: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Hiragino Kaku Gothic ProN",
              "Noto Sans JP", "Yu Gothic", "Meiryo", Segoe UI, Roboto, Helvetica, Arial, sans-serif;

      --accent: #4a76ff;
      --accent2: #60a5fa;
      --ok: #16a34a;
      --warn: #d97706;
    }

    html, body { background: var(--bg); color: var(--text); font-family: var(--sans); margin:0; padding:0; }
    .wrap { max-width: 1280px; margin: 0 auto; padding: 18px 16px 84px; }

    /* header */
    .hero {
      border:1px solid var(--line);
      border-radius:var(--radius);
      box-shadow:var(--shadow);
      background: linear-gradient(180deg, #fff, #fbfbfb);
      padding:18px;
      display:grid;
      gap:10px;
    }
    .heroTop{ display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }
    .hero h1 { font-size:22px; margin:0; letter-spacing:0.2px; }
    .hero .sub { color: var(--muted); font-size:13px; line-height:1.4; }

    .kpiStrip{
      display:flex; flex-wrap:wrap; gap:8px;
      align-items:center;
    }
    .pill{
      display:inline-flex; align-items:center; gap:8px;
      padding:6px 10px;
      border-radius:999px;
      border:1px solid var(--line);
      background:#fff;
      font-size:12px;
      color:#111;
    }
    .pill b{ font-weight:800; font-variant-numeric: tabular-nums; }
    .pill.blue{ border-color:#bfdbfe; background:#eff6ff; }
    .pill.orange{ border-color:#fed7aa; background:#fff7ed; }
    .pill.green{ border-color:#bbf7d0; background:#f0fdf4; }
    .pill.gray{ border-color:#e5e7eb; background:#fafafa; }
    .pill .dot{ width:8px; height:8px; border-radius:999px; background:var(--accent); }
    .pill.orange .dot{ background:#fb923c; }
    .pill.green .dot{ background:#22c55e; }
    .pill.gray .dot{ background:#9ca3af; }

    /* cards */
    .grid { display:grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap:12px; margin-top:12px; }
    @media (max-width: 960px) { .grid { grid-template-columns: 1fr; } }
    .card {
      border:1px solid var(--line);
      border-radius:var(--radius);
      box-shadow:var(--shadow);
      background:var(--card);
      padding:14px;
    }
    .card h3 { margin:0 0 8px; font-size:14px; }
    .kv { font-size:13px; color:var(--muted); line-height:1.65; }
    .kv code { font-family:var(--mono); font-size:12px; background:#fff; border:1px solid var(--line); padding:2px 6px; border-radius:10px; color:var(--text); }
    .kv .num{ font-weight:900; color:#111; font-variant-numeric: tabular-nums;   font-size: 15px;
    }

    .kv .hl{ color: var(--accent); font-weight:800; }

    /* controls */
    .controls {
      display:grid;
      grid-template-columns: 1.2fr 0.8fr 0.8fr 0.6fr;
      gap:10px;
      margin-top:14px;
      align-items:end;
    }
    @media (max-width: 960px) { .controls { grid-template-columns: 1fr; } }
    .controls input, .controls select { border:1px solid var(--line); border-radius:12px; padding:10px 12px; font-size:14px; outline:none; background:#fff; }
    .controls label { font-size:12px; color:var(--muted); display:block; margin-bottom:6px; }
    .toggle { display:flex; gap:10px; align-items:center; user-select:none; }
    .toggle input { transform: scale(1.1); }

    /* layout ratio: make details readable */
    .layout { display:grid; grid-template-columns: 1.15fr 0.85fr; gap:12px; margin-top:14px; align-items:start; }
    @media (max-width: 960px) { .layout { grid-template-columns: 1fr; } }

    .tableWrap {
      border:1px solid var(--line);
      border-radius:var(--radius);
      box-shadow:var(--shadow);
      overflow:hidden;
      background:#fff;
      max-height: calc(100vh - 320px);
      overflow:auto;
    }
    table { width:100%; border-collapse:collapse; font-size:13px; table-layout: fixed; }
    thead th { position:sticky; top:0; background:var(--head); border-bottom:1px solid var(--line); padding:10px; text-align:left; font-size:12px; color:#333; z-index:2; }
    tbody td { border-bottom:1px solid var(--line); padding:10px; vertical-align:top; }
    tbody tr:hover { background:#fbfbfb; cursor:pointer; }
    tbody tr.selected { background:#f7faff; }
    tbody tr.selected td:first-child { box-shadow: inset 3px 0 0 var(--accent); }

    /* column sizing */
    td:nth-child(1), td:nth-child(2), td:nth-child(4) { white-space: nowrap; }
    td:nth-child(3) { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .mono { font-family:var(--mono); font-size:12px; }
    .muted { color:var(--muted); }

    /* summary clamp */
    .summaryCell { padding-right: 14px; }
    .summaryClamp{
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
      line-height: 1.35;
      word-break: break-word;
    }
    .summaryHint{ font-size: 11px; color: var(--muted); margin-top: 4px; }

    /* chips */
    .dsChip, .labelChip{
      display:inline-flex;
      align-items:center;
      gap:6px;
      padding: 2px 9px;
      border-radius: 999px;
      border: 1px solid var(--line);
      font-size: 11px;
      background: #fff;
    }
    .dsChip[data-ds="cejc"]{ background:#fff7ed; border-color:#fed7aa; }
    .dsChip[data-ds="csj"]{  background:#eff6ff; border-color:#bfdbfe; }

    .labelChip[data-label="QUESTION"]{ background:#eef6ff; border-color:#cde3ff; }
    .labelChip[data-label="BACKCHANNEL"]{ background:#f0fdf4; border-color:#bbf7d0; }
    .labelChip[data-label="REPAIR"]{ background:#fff7ed; border-color:#fed7aa; }
    .labelChip[data-label="TOPIC_SHIFT"]{ background:#faf5ff; border-color:#e9d5ff; }
    .labelChip[data-label="DISCOURSE_MARKER"]{ background:#ecfeff; border-color:#a5f3fc; }
    .labelChip[data-label="HESITATION"]{ background:#f8fafc; border-color:#e2e8f0; }
    .labelChip[data-label="NEGATION_OPPOSITION"]{ background:#fef2f2; border-color:#fecaca; }
    .labelChip[data-label="OTHER"]{ background:#f8fafc; border-color:#e2e8f0; }

    /* score mini bar */
    .scoreBox{ display:flex; flex-direction:column; gap:6px; }
    .scoreRow{ display:flex; align-items:baseline; gap:8px; }
    .scoreVal{ font-variant-numeric: tabular-nums; font-weight: 900; }
    .scorePct{ font-size:11px; color:var(--muted); }
    .scoreBarWrap{ height:6px; border-radius:999px; background:#f1f5f9; border:1px solid #e2e8f0; overflow:hidden; }
    .scoreBar{ height:100%; width: calc(var(--p) * 100%); background: linear-gradient(90deg, #a5b4fc, #60a5fa); }

    /* details */
    .details {
      border:1px solid var(--line);
      border-radius:var(--radius);
      box-shadow:var(--shadow);
      background:#fff;
      padding:14px;
      position: sticky;
      top: 12px;
      max-height: calc(100vh - 40px);
      overflow:auto;
    }
    .details h2 { font-size:15px; margin:0 0 10px; }
    .details .small { font-size:12px; color:var(--muted); margin-bottom:10px; line-height:1.4; }
    .banner {
      display:flex; flex-wrap:wrap; gap:8px; align-items:center;
      border:1px solid var(--line);
      border-radius:14px;
      padding:10px;
      background: linear-gradient(180deg, #fff, #fbfbfb);
      margin-bottom:10px;
    }
    .badgeBig{
      display:inline-flex; align-items:baseline; gap:8px;
      padding:6px 10px;
      border-radius:14px;
      border:1px solid #c7d2fe;
      background:#eef2ff;
      font-weight:900;
      font-variant-numeric: tabular-nums;
    }
    .badgeBig small{ font-weight:700; color:var(--muted); }
    .warn {
      display:inline-flex; align-items:center; gap:8px;
      padding:6px 10px;
      border-radius:999px;
      border:1px solid #fed7aa;
      background:#fff7ed;
      color:#7c2d12;
      font-size:12px;
      font-weight:800;
    }
    .ok {
      display:inline-flex; align-items:center; gap:8px;
      padding:6px 10px;
      border-radius:999px;
      border:1px solid #bbf7d0;
      background:#f0fdf4;
      color:#14532d;
      font-size:12px;
      font-weight:800;
    }

    .sectionTitle{ font-size:13px; font-weight:900; margin:8px 0 6px; }
    .panel { border:1px solid var(--line); background:#fbfbfb; border-radius:14px; padding:10px; }
    pre { white-space: pre-wrap; word-break: break-word; font-family: var(--mono); font-size:12px; background:#fff; border:1px solid var(--line); padding:10px; border-radius:12px; margin:8px 0; }

    .exItem{
      border:1px solid var(--line);
      background:#fff;
      border-radius:14px;
      padding:10px;
      margin:8px 0;
    }
    .exHead{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-bottom:8px; }
    .tag{
      display:inline-flex; align-items:center; gap:6px;
      padding:2px 8px;
      border-radius:999px;
      border:1px solid var(--line);
      background:#fafafa;
      font-size:11px;
      color:#111;
    }
    .tag.blue{ background:#eff6ff; border-color:#bfdbfe; }
    .tag.orange{ background:#fff7ed; border-color:#fed7aa; }
    .tag.green{ background:#f0fdf4; border-color:#bbf7d0; }
    .tag.gray{ background:#f8fafc; border-color:#e2e8f0; color:#334155; }
    .exText{ line-height:1.45; }
    .exPrev{ color:#111; }
    .exResp{ color:#111; font-weight:800; }
    .exArrow{ color:var(--muted); font-weight:700; padding:0 6px; }

    .btn { border:1px solid var(--line); background:#fff; border-radius:12px; padding:8px 10px; font-size:12px; cursor:pointer; }
    .btn:hover { background:#f7f7f7; }
  
.pgLine{ margin: 6px 0; line-height: 1.55; }
.num{ font-weight: 900; }
td:last-child{ padding-right:16px; }

</style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <div class="heroTop">
        <div>
          <h1>__TITLE_ESC__</h1>
          <div class="sub">__SUBTITLE_ESC__</div>
          <div class="sub muted">This page is a research artifact. Labels are functional hypotheses grounded in examples, not diagnosis.</div>
        </div>
        <div class="kpiStrip" id="kpiStrip"></div>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <h3>Summary</h3>
        <div class="kv" id="summaryBox"></div>
      </div>
      <div class="card">
        <h3>Dataset counts</h3>
        <div class="kv" id="datasetBox"></div>
      </div>
      <div class="card">
        <h3>Primary label counts</h3>
        <div class="kv" id="labelBox"></div>
      </div>
      <div class="card">
        <h3>Pause/Gap summary</h3>
        <div class="kv" id="pgBox"></div>
      </div>
    </div>

    <div class="controls">
      <div>
        <label>Search (speaker_id / summary)</label>
        <input id="q" placeholder="例: D01M0047:R / cejc / REPAIR ..." />
      </div>
      <div>
        <label>Dataset</label>
        <select id="datasetSel"></select>
      </div>
      <div>
        <label>Primary label</label>
        <select id="labelSel"></select>
      </div>
      <div class="toggle">
        <div>
          <label>Needs more context</label>
          <div>
            <input type="checkbox" id="needsOnly" />
            <span class="muted">only</span>
          </div>
        </div>
      </div>
    </div>

    <div class="layout">
      <div class="tableWrap">
        <table class="mainTable">
          <colgroup>
          <col style="width:70px;" />
          <col style="width:110px;" />
          <col style="width:190px;" />
          <col style="width:170px;" />
          <col />
        </colgroup>
          <thead>
            <tr>
              <th>dataset</th>
              <th>score</th>
              <th>speaker_id</th>
              <th>primary label</th>
              <th>summary</th>
            </tr>
          </thead>
          <tbody id="tbody"></tbody>
        </table>
      </div>

      <div class="details" id="details">
        <h2>Details</h2>
        <div class="small">左の表から行をクリックすると、labels / examples（根拠）を表示します。</div>
      </div>
    </div>
  </div>

  <script id="DATA" type="application/json">__DATA_JSON__</script>
  <script id="STATS" type="application/json">__STATS_JSON__</script>
  <script id="ALLOWED" type="application/json">__ALLOWED_JSON__</script>

  <script>
    const rows = JSON.parse(document.getElementById("DATA").textContent);
    const stats = JSON.parse(document.getElementById("STATS").textContent);
    const allowed = JSON.parse(document.getElementById("ALLOWED").textContent);

    const els = {
      q: document.getElementById("q"),
      datasetSel: document.getElementById("datasetSel"),
      labelSel: document.getElementById("labelSel"),
      needsOnly: document.getElementById("needsOnly"),
      tbody: document.getElementById("tbody"),
      details: document.getElementById("details"),
      summaryBox: document.getElementById("summaryBox"),
      datasetBox: document.getElementById("datasetBox"),
      labelBox: document.getElementById("labelBox"),
      kpiStrip: document.getElementById("kpiStrip"),
      pgBox: document.getElementById("pgBox"),
    };

    function esc(s) {
      return (s ?? "").toString()
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function fmt(n, d=3) {
      if (n === null || n === undefined || Number.isNaN(Number(n))) return "-";
      return Number(n).toFixed(d);
    }

    function primaryLabel(rec) {
      const lj = rec.labels || {};
      const arr = lj.labels || [];
      if (Array.isArray(arr) && arr.length>0) return arr[0].label || "OTHER";
      return "OTHER";
    }

    function primaryConf(rec) {
      const lj = rec.labels || {};
      const arr = lj.labels || [];
      if (Array.isArray(arr) && arr.length>0) {
        const c = arr[0].confidence;
        return (c===null||c===undefined) ? 0 : Number(c);
      }
      return 0;
    }

    function matchText(rec, q) {
      if (!q) return true;
      q = q.toLowerCase();
      const s1 = (rec.speaker_id || "").toLowerCase();
      const s2 = ((rec.labels && rec.labels.summary) ? rec.labels.summary : "").toLowerCase();
      const s3 = (primaryLabel(rec) || "").toLowerCase();
      const s4 = (rec.dataset || "").toLowerCase();
      return (s1.includes(q) || s2.includes(q) || s3.includes(q) || s4.includes(q));
    }

    function filterRows() {
      const q = els.q.value.trim();
      const ds = els.datasetSel.value;
      const lb = els.labelSel.value;
      const needsOnly = els.needsOnly.checked;

      return rows
        .filter(r => ds==="ALL" ? true : (r.dataset===ds))
        .filter(r => lb==="ALL" ? true : (primaryLabel(r)===lb))
        .filter(r => needsOnly ? Boolean(r.labels && r.labels.needs_more_context) : true)
        .filter(r => matchText(r, q))
        .sort((a,b) => Number(b.atypicality_v0||0) - Number(a.atypicality_v0||0));
    }

    function fillStats() {
      // KPI strip
      const total = stats.total_rows || 0;
      const cejc = (stats.dataset_counts && (stats.dataset_counts.cejc||0)) || 0;
      const csj  = (stats.dataset_counts && (stats.dataset_counts.csj||0)) || 0;

      const topLabel = Object.entries(stats.primary_label_counts || {})
        .sort((a,b)=>b[1]-a[1])[0] || ["-", 0];

      els.kpiStrip.innerHTML = `
        <span class="pill blue"><span class="dot"></span>rows <b>${esc(total)}</b></span>
        <span class="pill orange"><span class="dot"></span>cejc <b>${esc(cejc)}</b></span>
        <span class="pill blue"><span class="dot"></span>csj <b>${esc(csj)}</b></span>
        <span class="pill green"><span class="dot"></span>top label <b>${esc(topLabel[0])}</b></span>
        <span class="pill gray"><span class="dot"></span>examples loaded <b>${esc(stats.examples_rows_loaded||0)}</b></span>
      `;

      els.summaryBox.innerHTML = `
        <div>rows: <span class="num">${esc(stats.total_rows)}</span></div>
        <div>model_id: <code>${esc(stats.model_id)}</code></div>
        <div>region: <code>${esc(stats.region)}</code></div>
        <div>created_at (min/max): <code>${esc(stats.created_at_min)}</code> … <code>${esc(stats.created_at_max)}</code></div>
        <div>examples_attached_in_report: <code>${esc(stats.examples_attached)}</code></div>
        <div>examples_rows_loaded: <span class="num">${esc(stats.examples_rows_loaded)}</span></div>
        <div class="muted">score = atypicality_v0（基準分布からの逸脱度）。高いほど「要レビュー優先」</div>
      `;

      const ds = Object.entries(stats.dataset_counts || {})
        .sort((a,b)=>b[1]-a[1])
        .map(([k,v]) => `<div>${esc(k)}: <span class="num">${esc(v)}</span></div>`)
        .join("");
      els.datasetBox.innerHTML = ds || `<div class="muted">-</div>`;

      const lb = Object.entries(stats.primary_label_counts || {})
        .sort((a,b)=>b[1]-a[1])
        .map(([k,v], i) => {
          const cls = i===0 ? "hl" : "";
          return `<div class="${cls}">${esc(k)}: <span class="num">${esc(v)}</span></div>`;
        })
        .join("");
      els.labelBox.innerHTML = lb || `<div class="muted">-</div>`;
    
      // Phase4 Pause/Gap summary (dataset-level)
      const pgSummary = stats.pg_summary || {};
      const dsKeys = Object.keys(pgSummary).sort();
      if (!dsKeys.length) {
        els.pgBox.innerHTML = `<div class="muted">-</div>`;
      } else {
        // show a few key cols if present (fmt() returns "-" when missing)
        els.pgBox.innerHTML = dsKeys.map((ds) => {
          const r = pgSummary[ds] || {};
          const pm = fmt(r.PG_pause_mean_mean, 3);
          const rg = fmt(r.PG_resp_gap_mean_mean, 3);
          const ov = fmt(r.PG_overlap_rate_mean, 3);
          const ro = fmt(r.PG_resp_overlap_rate_mean, 3);
          return `<div><span class="mono">${esc(ds)}</span> <span class="muted">pause</span>=<span class="num">${esc(pm)}</span> <span class="muted">gap</span>=<span class="num">${esc(rg)}</span> <span class="muted">ov</span>=<span class="num">${esc(ov)}</span> <span class="muted">respOv</span>=<span class="num">${esc(ro)}</span></div>`;
        }).join("");
      }
}

    function fillSelectors() {
      const datasets = ["ALL", ...Object.keys(stats.dataset_counts || {}).sort()];
      els.datasetSel.innerHTML = datasets.map(x => `<option value="${esc(x)}">${esc(x)}</option>`).join("");

      const labels = ["ALL", ...allowed];
      els.labelSel.innerHTML = labels.map(x => `<option value="${esc(x)}">${esc(x)}</option>`).join("");
    }

    function renderTable() {
      const rs = filterRows();

      // score normalize for mini bar
      const scores = rs.map(r => Number(r.atypicality_v0||0));
      const sMin = scores.length ? Math.min(...scores) : 0;
      const sMax = scores.length ? Math.max(...scores) : 1;
      const denom = (sMax - sMin) || 1;

      const htmlRows = rs.map((r) => {
        const pl = primaryLabel(r);
        const pc = primaryConf(r);
        const summary = (r.labels && r.labels.summary) ? r.labels.summary : "";
        const score = Number(r.atypicality_v0||0);
        const p = Math.max(0, Math.min(1, (score - sMin) / denom)); // 0..1
        const summaryTitle = summary.replace(/\\s+/g, " ").trim();

        return `
          <tr>
            <td><span class="dsChip" data-ds="${esc(r.dataset)}">${esc(r.dataset)}</span></td>
            <td>
              <div class="scoreBox">
                <div class="scoreRow">
                  <span class="scoreVal">${esc(fmt(score, 3))}</span>
                  <span class="scorePct">${esc((p*100).toFixed(0))}p</span>
                </div>
                <div class="scoreBarWrap"><div class="scoreBar" style="--p:${p};"></div></div>
              </div>
            </td>
            <td class="mono" title="${esc(r.speaker_id || "")}">${esc(r.speaker_id || "")}</td>
            <td>
              <span class="labelChip" data-label="${esc(pl)}">${esc(pl)}</span>
              <span class="muted">(${esc(pc.toFixed(2))})</span>
            </td>
            <td class="summaryCell" title="${esc(summaryTitle)}">
              <div class="summaryClamp">${esc(summary)}</div>
              <div class="summaryHint">click for details →</div>
            </td>
          </tr>
        `;
      }).join("");

      els.tbody.innerHTML = htmlRows || `<tr><td colspan="5" class="muted">No rows</td></tr>`;

      const visible = rs;
      [...els.tbody.querySelectorAll("tr")].forEach((tr, i) => {
        tr.addEventListener("click", () => {
          [...els.tbody.querySelectorAll("tr")].forEach(x => x.classList.remove("selected"));
          tr.classList.add("selected");
          showDetails(visible[i]);
        });
      });
    }

    function tagHtml(text, cls="gray") {
      return `<span class="tag ${cls}">${esc(text)}</span>`;
    }

    function showDetails(rec) {
      const lj = rec.labels || {};
      const labels = lj.labels || [];
      const miss = lj.missing || [];
      const needs = Boolean(lj.needs_more_context);
      const summary = lj.summary || "";
      const ex = rec.examples || [];


      const pg = rec.pg || {};

      const pgPairs = [
        ["total_time", pg.PG_total_time],
        ["pause_mean", pg.PG_pause_mean],
        ["resp_gap_mean", pg.PG_resp_gap_mean],
        ["resp_gap_p50", pg.PG_resp_gap_p50],
        ["resp_gap_p90", pg.PG_resp_gap_p90],
        ["resp_overlap_rate", pg.PG_resp_overlap_rate],
        ["n_resp_events", pg.PG_n_resp_events],
      ];
      const pgHtml = pgPairs
        .map(([k,v]) => `<div><span class="mono">${esc(k)}</span>: <span class="num">${esc(fmt(v, 3))}</span></div>`)
        .join("");

      const pl = primaryLabel(rec);
      const pc = primaryConf(rec);

      // used_features highlight (top)
      const uf = (labels && labels[0] && labels[0].used_features) ? labels[0].used_features : [];
      const ufChips = (Array.isArray(uf) ? uf.slice(0, 10) : []).map(z => tagHtml(z, "blue")).join("");

      // banners
      const needsBadge = needs
        ? `<span class="warn">⚠ needs more context</span>`
        : `<span class="ok">✓ context enough (heuristic)</span>`;

      // labels list
      const labelList = (Array.isArray(labels) ? labels : []).map((x) => {
        const usedF = Array.isArray(x.used_features) ? x.used_features : [];
        const usedE = Array.isArray(x.used_examples) ? x.used_examples : [];
        const feats = usedF.slice(0, 12).map(z => tagHtml(z, "blue")).join("");
        return `
          <div class="panel" style="margin-bottom:10px;">
            <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
              <span class="labelChip" data-label="${esc(x.label||"OTHER")}">${esc(x.label||"OTHER")}</span>
              <span class="muted">conf=${esc((x.confidence??0).toFixed(2))}</span>
            </div>
            <div class="muted" style="margin-top:8px; white-space:pre-wrap;">${esc(x.why||"")}</div>
            <div style="margin-top:8px; display:flex; gap:6px; flex-wrap:wrap;">${feats || `<span class="muted">used_features: (none)</span>`}</div>
            <div class="muted" style="margin-top:8px;">used_examples: <code>${esc(JSON.stringify(usedE))}</code></div>
          </div>
        `;
      }).join("") || `<div class="muted">No labels</div>`;

      // examples (card style)
      let examplesHtml = "";
      if (Array.isArray(ex) && ex.length) {
        examplesHtml = ex.slice(0, 12).map((e, i) => {
          const tags = [];
          tags.push(tagHtml(`#${i}`, "gray"));
          if (e.metric) tags.push(tagHtml(e.metric, "orange"));
          if (e.prev_sfp_group) tags.push(tagHtml(`prev=${e.prev_sfp_group}`, "orange"));
          if (e.resp_is_aizuchi === true) tags.push(tagHtml("aizuchi", "green"));
          if (e.resp_is_question === true) tags.push(tagHtml("question", "blue"));
          if (e.n_pairs_after_NE !== null && e.n_pairs_after_NE !== undefined) tags.push(tagHtml(`n_pairs=${e.n_pairs_after_NE}`, "gray"));

          const prev = e.prev_text || "";
          const resp = e.resp_text || "";

          return `
            <div class="exItem">
              <div class="exHead">${tags.join("")}</div>
              <div class="exText">
                <span class="exPrev">${esc(prev)}</span>
                <span class="exArrow">→</span>
                <span class="exResp">${esc(resp)}</span>
              </div>
              <div class="muted" style="margin-top:6px;">source: <span class="mono">${esc(e.source_file || "")}</span></div>
            </div>
          `;
        }).join("");
      } else {
        examplesHtml = `
          <div class="panel">
            <div class="muted">
              Examples が (none) の理由は2つあり得ます：<br/>
              1) このレポートに同梱している例文セットが NE_AIZUCHI 系のみで、当該話者に該当例が無い<br/>
              2) speaker_id のキーが一致せず結合できていない（要: conversation_id:speaker_id 形式）<br/>
              <br/>
              例文は「LLMラベルの根拠提示」「特徴量→発話の説明接続」「前処理/指標の改善判断」に使います。
            </div>
          </div>
        `;
      }

      const raw = {
        dataset: rec.dataset,
        speaker_id: rec.speaker_id,
        atypicality_v0: rec.atypicality_v0,
        labels: rec.labels,
        examples: rec.examples,
        pg: rec.pg,
        meta: rec.meta
      };

      els.details.innerHTML = `
        <h2>Details</h2>

        <div class="banner">
          <span class="badgeBig">${esc(fmt(rec.atypicality_v0, 6))} <small>score</small></span>
          <span class="dsChip" data-ds="${esc(rec.dataset)}">${esc(rec.dataset)}</span>
          <span class="mono">${esc(rec.speaker_id||"")}</span>
          <span class="labelChip" data-label="${esc(pl)}">${esc(pl)}</span>
          <span class="muted">(${esc(pc.toFixed(2))})</span>
          ${needsBadge}
        </div>

        <div class="small">
          <b>summary</b>: ${esc(summary)}
        </div>

        <div class="sectionTitle">Key signals (used_features)</div>
        <div class="panel" style="display:flex;gap:6px;flex-wrap:wrap;">
          ${ufChips || `<span class="muted">(none)</span>`}
        </div>

        <div class="sectionTitle">Labels</div>
        ${labelList}
        <div class="muted">missing: <code>${esc(JSON.stringify(miss))}</code></div>

        <div class="sectionTitle">Examples (evidence)</div>
        ${examplesHtml}



        <div class="sectionTitle">Pause/Gap metrics</div>
        <div class="panel">
          ${pgHtml || `<div class="muted">No Phase4 metrics attached for this speaker.</div>`}
          <div class="muted" style="margin-top:6px;">source: <span class="mono">${esc(pg.source_file || "")}</span></div>
        </div>


        <div style="margin-top:12px;">
          <button class="btn" id="copyBtn">Copy raw JSON</button>
          <pre id="rawPre">${esc(JSON.stringify(raw, null, 2))}</pre>
        </div>
      `;

      const btn = document.getElementById("copyBtn");
      btn.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(JSON.stringify(raw, null, 2));
          btn.textContent = "Copied!";
          setTimeout(()=>btn.textContent="Copy raw JSON", 1200);
        } catch (e) {
          btn.textContent = "Copy failed";
          setTimeout(()=>btn.textContent="Copy raw JSON", 1200);
        }
      });
    }

    fillStats();
    fillSelectors();
    renderTable();

    ["input","change"].forEach(evt => {
      els.q.addEventListener(evt, renderTable);
      els.datasetSel.addEventListener(evt, renderTable);
      els.labelSel.addEventListener(evt, renderTable);
      els.needsOnly.addEventListener(evt, renderTable);
    });
  </script>

<script>
(function(){
  function esc(s){return String(s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
    .replace(/"/g,"&quot;").replace(/'/g,"&#39;");}
  function decoratePgSummary(){
    var el = document.getElementById("pgSummaryBox");
    if(!el) return;
    var txt = (el.textContent||"").trim();
    if(!txt) return;
    var lines = txt.split(/\r?\n/).filter(Boolean);
    el.innerHTML = lines.map(function(l){
      var safe = esc(l).replace(/(\d+(?:\.\d+)?)/g,'<span class="num">$1</span>');
      return '<div class="pgLine">'+safe+'</div>';
    }).join("");
  }
  try{ decoratePgSummary(); }catch(e){}
  // もし後から fillStats 等で上書きされても再適用できるように
  document.addEventListener("click", function(){ try{decoratePgSummary();}catch(e){} }, true);
})();
</script>

</body>
</html>
"""



def _json_sanitize(obj):
    """Convert NaN/Inf (and numpy scalars) to JSON-safe values."""
    try:
        import numpy as np
    except Exception:
        np = None
    if obj is None:
        return None
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, (str, int, bool)):
        return obj
    if np is not None:
        try:
            if isinstance(obj, (np.floating,)):
                v = float(obj)
                return None if (math.isnan(v) or math.isinf(v)) else v
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.bool_,)):
                return bool(obj)
        except Exception:
            pass
    if isinstance(obj, dict):
        return {str(k): _json_sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_sanitize(v) for v in obj]
    return str(obj)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels_parquet", required=True)
    ap.add_argument("--out_html", required=True)
    ap.add_argument("--examples_dir", default="", help="optional: artifacts/phase3/examples_v13 (to attach examples)")
    ap.add_argument("--max_examples_per_speaker", type=int, default=8)
    ap.add_argument("--pg_metrics_parquet", default="", help="optional: phase4 pause/gap parquet(s): file/dir or comma-separated")
    ap.add_argument("--pg_summary_parquet", default="", help="optional: phase4 summary.parquet (dataset-level means)")
    ap.add_argument("--title", default="LLM labeling v0 (Bedrock Claude Opus 4.5)")
    ap.add_argument("--subtitle", default="Phase3-2: outliers_v0_topK -> labels_v0 (GitHub Pages)")
    args = ap.parse_args()

    df = pd.read_parquet(args.labels_parquet)

    # Examples index (optional)
    ex_index: Dict[str, List[Dict[str, Any]]] = {}
    ex_rows_loaded = 0
    if args.examples_dir:
        ex_index, ex_rows_loaded = build_examples_index(args.examples_dir)

    examples_attached = bool(ex_index)


    # Phase4 Pause/Gap index (optional)
    pg_index: Dict[str, Dict[str, Any]] = {}
    pg_rows_loaded = 0
    pg_paths = _collect_parquet_paths(args.pg_metrics_parquet)
    if pg_paths:
        pg_index, pg_rows_loaded = build_pg_index_v2(pg_paths)
    pg_attached = bool(pg_index)
    pg_summary = load_pg_summary(args.pg_summary_parquet) if args.pg_summary_parquet else {}

    # Build rows for the dashboard
    rows: List[Dict[str, Any]] = []
    for _, r in df.iterrows():
        labels = _safe_json_obj(r.get("labels_json"))

        # labels側にexamples_jsonがあれば優先、無ければ index から後付け
        examples = _safe_json_list(r.get("examples_json"))
        speaker_key = str(r.get("speaker_id") or "").strip().split("/")[-1]


        # attach phase4 pg metrics by speaker_key (conversation_id:speaker_id)
        pg = pg_index.get(speaker_key, {}) if (pg_attached and speaker_key) else {}

        if (not examples) and examples_attached and speaker_key:
            examples = ex_index.get(speaker_key, [])[: args.max_examples_per_speaker]

        rec = {
            "dataset": str(r.get("dataset") or ""),
            "speaker_id": speaker_key,
            "atypicality_v0": float(r.get("atypicality_v0")) if r.get("atypicality_v0") is not None else None,
            "labels": labels,
            "examples": examples,
            "pg": pg,
            "meta": {
                "model_id": str(r.get("model_id") or ""),
                "region": str(r.get("region") or ""),
                "created_at": str(r.get("created_at") or ""),
                "fallback": bool(r.get("fallback")) if r.get("fallback") is not None else False,
                "error": str(r.get("error") or ""),
            },
        }
        rows.append(rec)

    dataset_counts = df.groupby("dataset").size().to_dict() if "dataset" in df.columns else {}

    # primary label counts
    pl_counts: Dict[str, int] = {}
    for rec in rows:
        lj = rec.get("labels") or {}
        arr = lj.get("labels") or []
        pl = "OTHER"
        if isinstance(arr, list) and arr and isinstance(arr[0], dict):
            pl = str(arr[0].get("label") or "OTHER")
        pl_counts[pl] = pl_counts.get(pl, 0) + 1

    created = []
    if "created_at" in df.columns and len(df):
        created = [str(x) for x in df["created_at"].dropna().astype(str).tolist()]

    stats = {
        "total_rows": int(len(rows)),
        "dataset_counts": dataset_counts,
        "primary_label_counts": dict(sorted(pl_counts.items(), key=lambda kv: kv[1], reverse=True)),
        "model_id": str(df["model_id"].iloc[0]) if "model_id" in df.columns and len(df) else "",
        "region": str(df["region"].iloc[0]) if "region" in df.columns and len(df) else "",
        "created_at_min": min(created) if created else "",
        "created_at_max": max(created) if created else "",
        "examples_attached": bool(examples_attached),
        "examples_rows_loaded": int(ex_rows_loaded),
        "pg_attached": bool(pg_attached),
        "pg_rows_loaded": int(pg_rows_loaded),
        "pg_summary": pg_summary,
    }

    allowed_labels = [
        "QUESTION",
        "BACKCHANNEL",
        "REPAIR",
        "TOPIC_SHIFT",
        "DISCOURSE_MARKER",
        "HESITATION",
        "NEGATION_OPPOSITION",
        "OTHER",
    ]

    data_json = _script_json(json.dumps(_json_sanitize(rows), ensure_ascii=False, allow_nan=False))
    stats_json = _script_json(json.dumps(_json_sanitize(stats), ensure_ascii=False, allow_nan=False))
    allowed_json = _script_json(json.dumps(allowed_labels, ensure_ascii=False, allow_nan=False))

    title_esc = htmlmod.escape(args.title)
    subtitle_esc = htmlmod.escape(args.subtitle)

    out_html = Path(args.out_html)
    out_html.parent.mkdir(parents=True, exist_ok=True)

    html_text = (
        HTML_TEMPLATE
        .replace("__TITLE_ESC__", title_esc)
        .replace("__SUBTITLE_ESC__", subtitle_esc)
        .replace("__DATA_JSON__", data_json)
        .replace("__STATS_JSON__", stats_json)
        .replace("__ALLOWED_JSON__", allowed_json)
    )
    out_html.write_text(html_text, encoding="utf-8")

    print(json.dumps(
        {
            "out_html": str(out_html),
            "rows": len(rows),
            "examples_attached": examples_attached,
            "examples_rows_loaded": ex_rows_loaded,
        },
        ensure_ascii=False, indent=2
    ))


if __name__ == "__main__":
    main()

