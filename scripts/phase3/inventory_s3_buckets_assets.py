# scripts/phase3/inventory_s3_buckets_assets.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import boto3


MEDIA_EXTS = {"wav", "mp3", "m4a", "flac", "ogg", "mp4", "mov", "mkv", "webm", "avi"}
TEXT_EXTS = {"txt", "csv", "tsv", "json", "jsonl", "xml", "html", "md", "yaml", "yml"}
ANNOT_EXTS = {"eaf", "trs", "textgrid", "lab", "ctm", "srt", "vtt"}


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def human_bytes(n: int) -> str:
    if n is None:
        return "-"
    units = ["B", "KB", "MB", "GB", "TB"]
    x = float(n)
    for u in units:
        if x < 1024 or u == units[-1]:
            return f"{x:.2f}{u}" if u != "B" else f"{int(x)}B"
        x /= 1024.0
    return f"{n}B"


def ext_of(key: str) -> str:
    key_l = key.lower()
    if key_l.endswith(".tar.gz"):
        return "tar.gz"
    if key_l.endswith(".jsonl.gz"):
        return "jsonl.gz"
    if key_l.endswith(".csv.gz"):
        return "csv.gz"
    if "." not in key_l:
        return ""
    return key_l.rsplit(".", 1)[-1]


def top_dirs(key: str, depth: int = 2) -> str:
    parts = [p for p in key.split("/") if p]
    return "/".join(parts[:depth]) if parts else ""


def looks_like_metadata(key: str) -> bool:
    k = key.lower()
    name = k.rsplit("/", 1)[-1]
    pats = [
        "meta", "metadata", "demograph", "speaker", "participant", "profile",
        "age", "gender", "sex", "attributes", "info", "master", "manifest",
        "readme", "license", "annotation", "label", "schema", "index",
        "conversation", "session", "utt", "turn",
    ]
    return any(p in name for p in pats)


@dataclass
class BucketScan:
    bucket: str
    prefix: str
    total_objects: int
    total_bytes: int
    ext_counts: Dict[str, int]
    ext_bytes: Dict[str, int]
    dir_counts: Dict[str, int]
    media_counts: Dict[str, int]
    text_counts: Dict[str, int]
    annot_counts: Dict[str, int]
    metadata_candidates: List[str]
    sample_keys_by_ext: Dict[str, List[str]]
    errors: List[str]
    tree: Dict[str, Any]


def list_tree(s3, bucket: str, prefix: str, depth: int = 3, max_items: int = 200) -> Dict[str, Any]:
    """
    delimiter='/' で浅いツリーだけを見る（巨大バケットでも安全）
    """
    out: Dict[str, Any] = {"bucket": bucket, "prefix": prefix, "depth": depth, "nodes": {}}

    def step(pfx: str, d: int) -> Dict[str, Any]:
        if d <= 0:
            return {}
        resp = s3.list_objects_v2(Bucket=bucket, Prefix=pfx, Delimiter="/", MaxKeys=max_items)
        cps = [x["Prefix"] for x in resp.get("CommonPrefixes", [])]
        node = {"common_prefixes": cps[:max_items]}
        children = {}
        for cp in cps[:max_items]:
            children[cp] = step(cp, d - 1)
        node["children"] = children
        return node

    out["nodes"] = step(prefix, depth)
    return out


def scan_bucket(
    s3,
    bucket: str,
    prefix: str,
    max_keys: int,
    max_samples_per_ext: int,
    tree_depth: int,
) -> BucketScan:
    paginator = s3.get_paginator("list_objects_v2")

    ext_counts: Dict[str, int] = defaultdict(int)
    ext_bytes: Dict[str, int] = defaultdict(int)
    dir_counts: Dict[str, int] = defaultdict(int)

    media_counts: Dict[str, int] = defaultdict(int)
    text_counts: Dict[str, int] = defaultdict(int)
    annot_counts: Dict[str, int] = defaultdict(int)

    sample_keys_by_ext: Dict[str, List[str]] = defaultdict(list)
    metadata_candidates: List[str] = []
    errors: List[str] = []

    total_objects = 0
    total_bytes = 0

    tree = {}
    try:
        tree = list_tree(s3, bucket, prefix, depth=tree_depth)
    except Exception as e:
        errors.append(f"tree_error: {type(e).__name__}: {e}")

    try:
        page_iter = paginator.paginate(
            Bucket=bucket,
            Prefix=prefix,
            PaginationConfig={"PageSize": 1000},
        )
        for page in page_iter:
            for obj in page.get("Contents", []):
                key = obj.get("Key", "")
                size = int(obj.get("Size") or 0)

                total_objects += 1
                total_bytes += size

                e = ext_of(key)
                ext_counts[e] += 1
                ext_bytes[e] += size

                dkey = top_dirs(key[len(prefix):] if key.startswith(prefix) else key, depth=2)
                if dkey:
                    dir_counts[dkey] += 1

                if e in MEDIA_EXTS:
                    media_counts[e] += 1
                if e in TEXT_EXTS:
                    text_counts[e] += 1
                if e in ANNOT_EXTS:
                    annot_counts[e] += 1

                if looks_like_metadata(key):
                    if len(metadata_candidates) < 250:
                        metadata_candidates.append(key)

                if len(sample_keys_by_ext[e]) < max_samples_per_ext:
                    sample_keys_by_ext[e].append(key)

                if total_objects >= max_keys:
                    raise StopIteration()

    except StopIteration:
        pass
    except Exception as e:
        errors.append(f"scan_error: {type(e).__name__}: {e}")

    metadata_candidates = sorted(metadata_candidates)[:250]

    return BucketScan(
        bucket=bucket,
        prefix=prefix,
        total_objects=total_objects,
        total_bytes=total_bytes,
        ext_counts=dict(sorted(ext_counts.items(), key=lambda kv: kv[1], reverse=True)),
        ext_bytes=dict(sorted(ext_bytes.items(), key=lambda kv: kv[1], reverse=True)),
        dir_counts=dict(sorted(dir_counts.items(), key=lambda kv: kv[1], reverse=True)),
        media_counts=dict(sorted(media_counts.items(), key=lambda kv: kv[1], reverse=True)),
        text_counts=dict(sorted(text_counts.items(), key=lambda kv: kv[1], reverse=True)),
        annot_counts=dict(sorted(annot_counts.items(), key=lambda kv: kv[1], reverse=True)),
        metadata_candidates=metadata_candidates,
        sample_keys_by_ext={k: v for k, v in sample_keys_by_ext.items()},
        errors=errors,
        tree=tree,
    )


def to_dict(s: BucketScan) -> Dict[str, Any]:
    return {
        "bucket": s.bucket,
        "prefix": s.prefix,
        "total_objects_scanned": s.total_objects,
        "total_size_scanned_bytes": s.total_bytes,
        "total_size_scanned_human": human_bytes(s.total_bytes),
        "ext_counts_top": dict(list(s.ext_counts.items())[:30]),
        "ext_bytes_human_top": {k: human_bytes(v) for k, v in list(s.ext_bytes.items())[:30]},
        "media_counts": s.media_counts,
        "text_counts": s.text_counts,
        "annotation_counts": s.annot_counts,
        "top_dirs": dict(list(s.dir_counts.items())[:60]),
        "metadata_candidates_head": s.metadata_candidates[:80],
        "samples_by_ext": {k: v[:8] for k, v in s.sample_keys_by_ext.items()},
        "errors": s.errors,
        "tree": s.tree,
    }


def write_md(out_path: Path, meta: Dict[str, Any], scans: List[Dict[str, Any]]) -> None:
    lines = []
    lines.append("# RAW corpus inventory (CSJ/CEJC)")
    lines.append("")
    lines.append(f"- created_at: `{meta['created_at']}`")
    lines.append(f"- region: `{meta['region']}`")
    lines.append(f"- max_keys_per_bucket: `{meta['max_keys']}`")
    lines.append("")
    lines.append("> NOTE: partial scan（最大 max_keys 件まで）。必要なら MAX_KEYS を上げて再実行。")
    lines.append("")

    for d in scans:
        lines.append(f"## {d['bucket']}")
        lines.append("")
        lines.append(f"- prefix: `{d['prefix']}`")
        lines.append(f"- objects_scanned: **{d['total_objects_scanned']}**")
        lines.append(f"- size_scanned: **{d['total_size_scanned_human']}**")
        lines.append("")
        lines.append("### Media counts")
        mc = d.get("media_counts", {})
        lines.append("- " + (", ".join([f"{k}:{v}" for k, v in mc.items()]) if mc else "(none found in scan)"))
        lines.append("")
        lines.append("### Annotation counts")
        ac = d.get("annotation_counts", {})
        lines.append("- " + (", ".join([f"{k}:{v}" for k, v in ac.items()]) if ac else "(none found in scan)"))
        lines.append("")
        lines.append("### Metadata candidates (head)")
        for k in d.get("metadata_candidates_head", [])[:20]:
            lines.append(f"- `{k}`")
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_html(out_path: Path, meta: Dict[str, Any], scans: List[Dict[str, Any]]) -> None:
    def esc(s: Any) -> str:
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#039;")
        )

    def chips(kv: Dict[str, Any], limit: int = 24) -> str:
        items = list(kv.items())[:limit]
        if not items:
            return '<span class="muted">(none)</span>'
        return "".join([f'<span class="chip"><b>{esc(k or "noext")}</b> {esc(v)}</span>' for k, v in items])

    def list_keys(keys: List[str], limit: int = 30) -> str:
        if not keys:
            return '<div class="muted">(none)</div>'
        return "<ul>" + "".join([f"<li><code>{esc(k)}</code></li>" for k in keys[:limit]]) + "</ul>"

    cards = []
    for d in scans:
        cards.append(f"""
<div class="card">
  <div class="head">
    <h2>{esc(d["bucket"])}</h2>
    <div class="muted">prefix: <code>{esc(d["prefix"])}</code></div>
    <div class="kpi">
      <span class="pill">objects <b>{esc(d["total_objects_scanned"])}</b></span>
      <span class="pill">size <b>{esc(d["total_size_scanned_human"])}</b></span>
    </div>
  </div>

  <h3>File types (top)</h3>
  <div>{chips(d.get("ext_counts_top", {}), 28)}</div>

  <h3>Media</h3>
  <div>{chips(d.get("media_counts", {}), 24)}</div>

  <h3>Annotations</h3>
  <div>{chips(d.get("annotation_counts", {}), 24)}</div>

  <h3>Metadata candidates (head)</h3>
  {list_keys(d.get("metadata_candidates_head", []), 25)}

  <details style="margin-top:10px;">
    <summary>Tree (shallow)</summary>
    <pre class="pre">{esc(json.dumps(d.get("tree",{}), ensure_ascii=False, indent=2)[:6000])}</pre>
  </details>

  <details style="margin-top:10px;">
    <summary>Errors</summary>
    <pre class="pre">{esc(json.dumps(d.get("errors",[]), ensure_ascii=False, indent=2))}</pre>
  </details>
</div>
""")

    html = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>RAW corpus inventory</title>
<style>
  :root{{ --bg:#fff; --text:#111; --muted:#666; --line:#ddd; --card:#fafafa; --radius:16px; }}
  body{{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans JP","Yu Gothic",Meiryo,Segoe UI,Roboto,Helvetica,Arial,sans-serif; background:var(--bg); color:var(--text); }}
  .wrap{{ max-width:1100px; margin:0 auto; padding:18px 14px 80px; }}
  .hero{{ border:1px solid var(--line); border-radius:var(--radius); background:linear-gradient(180deg,#fff,#fbfbfb); padding:16px; }}
  h1{{ margin:0 0 6px; font-size:20px; }}
  .muted{{ color:var(--muted); font-size:13px; line-height:1.4; }}
  .grid{{ display:grid; grid-template-columns:1fr; gap:12px; margin-top:12px; }}
  .card{{ border:1px solid var(--line); border-radius:var(--radius); background:var(--card); padding:14px; }}
  .kpi{{ display:flex; gap:8px; flex-wrap:wrap; margin-top:8px; }}
  .pill{{ border:1px solid var(--line); background:#fff; border-radius:999px; padding:6px 10px; font-size:12px; }}
  .chip{{ display:inline-flex; gap:8px; align-items:baseline; border:1px solid var(--line); background:#fff; border-radius:999px; padding:4px 10px; font-size:12px; margin:4px 6px 0 0; }}
  code{{ background:#fff; border:1px solid var(--line); border-radius:10px; padding:2px 6px; }}
  h2{{ margin:0 0 4px; font-size:16px; }}
  h3{{ margin:14px 0 6px; font-size:13px; }}
  .pre{{ white-space:pre-wrap; background:#fff; border:1px solid var(--line); border-radius:12px; padding:10px; font-size:12px; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <h1>RAW corpus inventory (CSJ/CEJC)</h1>
    <div class="muted">created_at: <code>{esc(meta["created_at"])}</code></div>
    <div class="muted">region: <code>{esc(meta["region"])}</code></div>
    <div class="kpi">
      <span class="pill">max_keys_per_bucket <b>{esc(meta["max_keys"])}</b></span>
      <span class="pill">partial scan</span>
    </div>
  </div>

  <div class="grid">
    {''.join(cards)}
  </div>
</div>
</body>
</html>
"""
    out_path.write_text(html, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--buckets", nargs="+", required=True)
    ap.add_argument("--prefix", default="", help="optional prefix inside bucket (default: root)")
    ap.add_argument("--region", default="ap-northeast-1")
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--max_keys", type=int, default=50000)
    ap.add_argument("--tree_depth", type=int, default=3)
    ap.add_argument("--max_samples_per_ext", type=int, default=12)
    ap.add_argument("--write_md", action="store_true")
    ap.add_argument("--write_html", action="store_true")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    prefix = args.prefix.lstrip("/")
    if prefix and not prefix.endswith("/"):
        prefix += "/"

    s3 = boto3.client("s3", region_name=args.region)

    meta = {"created_at": now_utc_iso(), "region": args.region, "max_keys": args.max_keys, "prefix": prefix}
    scans: List[Dict[str, Any]] = []

    for b in args.buckets:
        res = scan_bucket(
            s3=s3,
            bucket=b,
            prefix=prefix,
            max_keys=args.max_keys,
            max_samples_per_ext=args.max_samples_per_ext,
            tree_depth=args.tree_depth,
        )
        scans.append(to_dict(res))

    out_json = {"meta": meta, "buckets": scans}
    (out_dir / "inventory.json").write_text(json.dumps(out_json, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.write_md:
        write_md(out_dir / "inventory_summary.md", meta, scans)
    if args.write_html:
        write_html(out_dir / "inventory_summary.html", meta, scans)

    print(json.dumps(
        {
            "ok": True,
            "out_dir": str(out_dir),
            "buckets": [d["bucket"] for d in scans],
            "max_keys": args.max_keys,
            "note": "partial scan; raise MAX_KEYS for deeper coverage",
        },
        ensure_ascii=False, indent=2
    ))


if __name__ == "__main__":
    main()

