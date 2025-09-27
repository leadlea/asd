#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bang & Nadig (2015) — English subset (Mother MLU)
Dual-run driver: strict(min=1) + robust(min=2), and writes a docs/ HTML comparing:
- paper targets
- strict results
- robust results
- optional MVP reference (from YAML)
"""

import argparse, re, csv, json
from pathlib import Path
from typing import List, Tuple, Dict
from collections import defaultdict, Counter
import copy, yaml

# ---------- regex helpers ----------
WHITES   = re.compile(r"\s+")
WORD_RX  = re.compile(r"^[A-Za-z]+(?:'[A-Za-z]+)?$")
PUNCT_RX = re.compile(r"[.,;:!?()\[\]{}\-\_/\"“”‘’]+")
TIME_RX  = re.compile(r"\[(\d+)_\s*(\d+)\]")
MOR_LINE = re.compile(r"^%mor:\s*(.+)$")
MOR_CHUNK_RX = re.compile(r"^(?P<pos>[A-Za-z0-9]+)\|(?P<form>[^ ]+)$")

# ---------- IO ----------
def read_cha_lines(path: Path) -> List[str]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().splitlines()

def get_languages(lines: List[str]) -> List[str]:
    for ln in lines[:200]:
        if ln.startswith("@Languages:"):
            part = ln.split(":",1)[1].strip()
            return [s.strip() for s in re.split(r"[,\s]+", part) if s.strip()]
    return []

def get_gem_window(lines: List[str]) -> Tuple[int,int]:
    bg = eg = None
    for ln in lines[:300]:
        if ln.startswith("@Bg:"):
            try: bg = int(ln.split(":",1)[1].strip())
            except ValueError: pass
        elif ln.startswith("@Eg:"):
            try: eg = int(ln.split(":",1)[1].strip())
            except ValueError: pass
    return bg, eg

# ---------- meta extraction ----------
def infer_group_from_id(lines: List[str]) -> str:
    def pick_from(s: str) -> str:
        s_low = s.lower()
        if re.search(r"\basd\b|\baut(?:ism)?\b", s_low): return "ASD"
        if re.search(r"\btyp\b|\btd\b|\btypical\b|\bcontrol(?:s)?\b|\bcon\b", s_low): return "TYP"
        return ""
    id_lines = [ln for ln in lines[:800] if ln.startswith("@ID:")]
    chi_lines = [ln for ln in id_lines if "|CHI|" in ln or "|CHI" in ln]
    for ln in chi_lines:
        g = pick_from(ln)
        if g: return g
    for ln in id_lines:
        g = pick_from(ln); 
        if g: return g
    for ln in lines[:400]:
        if ln.startswith("@Types:"):
            g = pick_from(ln)
            if g: return g
    return ""

def get_mother_uid(lines: List[str], path: Path) -> str:
    # Prefer CHI @ID part[1]=study, part[9]=code
    chi_parts = None
    for ln in lines[:400]:
        if ln.startswith("@ID:") and "|CHI|" in ln:
            raw = ln.split(":", 1)[1].strip()
            chi_parts = [p.strip() for p in raw.split("|")]
            break
    if chi_parts:
        study = chi_parts[1] if len(chi_parts) > 1 and chi_parts[1] else "STUDY"
        code  = chi_parts[9] if len(chi_parts) > 9 and chi_parts[9] else ""
        if code:
            return f"{study}::{code}"
    # Fallback to MOT @ID
    for ln in lines[:400]:
        if ln.startswith("@ID:") and "|MOT|" in ln:
            raw = ln.split(":",1)[1].strip()
            parts = [p.strip() for p in raw.split("|")]
            study = parts[1] if len(parts) > 1 and parts[1] else "STUDY"
            label = parts[7] if len(parts) > 7 and parts[7] else "MOT"
            edu   = parts[8] if len(parts) > 8 and parts[8] else ""
            key   = f"{study}::{label}"
            if edu: key += f"::{edu}"
            return key
    # Participants
    for ln in lines[:400]:
        if ln.startswith("@Participants:") and "MOT" in ln:
            return f"PARTS::{ln.strip()}"
    # Filename
    return f"MOT::{path.stem}"

# ---------- main-tier iterator ----------
def iter_main_tier(lines: List[str], speakers: List[str]):
    for idx, ln in enumerate(lines):
        if not ln.startswith("*"): continue
        try: spk, rest = ln[1:].split(":",1)
        except ValueError: continue
        spk = spk.strip()
        if speakers and spk not in speakers: continue
        utt = rest.strip()
        t = TIME_RX.search(utt); start = end = None
        if t:
            start = int(t.group(1)); end = int(t.group(2))
            utt = utt[:t.start()].rstrip()
        yield idx, spk, utt, (start, end)

# ---------- %mor utilities ----------
def mor_all_interjection(mor_raw: str) -> bool:
    has_chunk = False
    for chunk in mor_raw.split():
        m = MOR_CHUNK_RX.match(chunk)
        if not m: return False
        has_chunk = True
        if m.group("pos").lower() != "intj": return False
    return has_chunk

# ---------- tokenization ----------
def tokenize(text: str, lowercase=True) -> List[str]:
    if lowercase: text = text.lower()
    text = PUNCT_RX.sub(" ", text)
    toks = [t for t in WHITES.split(text) if t]
    return toks

def is_valid_token(tok: str, cfg) -> bool:
    rx_excl = cfg["preprocess"].get("exclude_tokens_regex","")
    if rx_excl and re.match(rx_excl, tok): return False
    if cfg["preprocess"].get("alphabetic_only_tokens", False):
        if not WORD_RX.match(tok): return False
    return True

def in_gem_range(tspan, bg, eg) -> bool:
    if bg is None or eg is None: return True
    if tspan is None: return True
    s, e = tspan
    if s is None or e is None: return True
    return not (e < bg or s > eg)

# ---------- core per-file ----------
def compute_mlu_for_file(path: Path, cfg) -> dict:
    lines = read_cha_lines(path)
    langs = get_languages(lines)
    incl_langs = set(cfg["dataset"]["include_language_codes"] or [])
    if incl_langs and not any(l in incl_langs for l in langs):
        return {"file": str(path), "skip_reason": "language_filtered"}
    if cfg["dataset"].get("strict_english_only", False):
        if set(langs) != {"eng"}:
            return {"file": str(path), "skip_reason": "non_english_only"}

    group = infer_group_from_id(lines)
    mother_uid = get_mother_uid(lines, path)
    bg, eg = get_gem_window(lines) if cfg["preprocess"].get("use_gem_window", False) else (None, None)

    total_words = 0; total_utts  = 0
    use_mor = bool(cfg["preprocess"].get("use_mor_tokens", False))
    exclude_pure_intj = bool(cfg["preprocess"].get("exclude_pure_intj", False))
    drop_no_ts = bool(cfg["preprocess"].get("drop_no_timestamp_when_gems", False))

    for idx, spk, utt, tspan in iter_main_tier(lines, cfg["dataset"]["include_speakers"]):
        if cfg["preprocess"].get("use_gem_window", False):
            if (tspan is None and drop_no_ts):
                continue
            if not in_gem_range(tspan, bg, eg):
                continue
        toks = []
        if use_mor:
            mor_raw = None
            for j in range(idx+1, min(idx+16, len(lines))):  # +15 lines
                m = MOR_LINE.match(lines[j])
                if m:
                    mor_raw = m.group(1)
                    break
            if mor_raw:
                if exclude_pure_intj and mor_all_interjection(mor_raw):
                    continue
                for chunk in mor_raw.split():
                    if "|" in chunk:
                        _, word = chunk.split("|", 1)
                    else:
                        word = chunk
                    word = re.sub(r"[^A-Za-z']+", "", word)
                    if word: toks.append(word.lower())
        if not toks:
            toks = tokenize(utt, lowercase=cfg["preprocess"].get("lowercase", True))
            toks = [t for t in toks if is_valid_token(t, cfg)]
        if len(toks) >= cfg["preprocess"].get("min_utterance_len_tokens", 1):
            total_utts  += 1
            total_words += len(toks)

    # universal backoff
    if total_utts == 0:
        toks_total = utts_total = 0
        for idx, spk, utt, tspan in iter_main_tier(lines, cfg["dataset"]["include_speakers"]):
            if cfg["preprocess"].get("use_gem_window", False):
                if (tspan is None and drop_no_ts):
                    continue
                if not in_gem_range(tspan, bg, eg):
                    continue
            toks = tokenize(utt, lowercase=cfg["preprocess"].get("lowercase", True))
            toks = [t for t in toks if is_valid_token(t, cfg)]
            if len(toks) >= cfg["preprocess"].get("min_utterance_len_tokens", 1):
                utts_total += 1; toks_total += len(toks)
        if utts_total > 0:
            total_utts, total_words = utts_total, toks_total
        else:
            print(f"[DEBUG] dropped-all-utterances: {path}")

    mlu = (total_words/total_utts) if total_utts>0 else float("nan")
    return {
        "file": str(path),
        "group": group,
        "mother_uid": mother_uid,
        "mlu_words": round(mlu, 6) if total_utts>0 else None,
        "utterances": total_utts,
        "words": total_words,
        "languages": ",".join(langs),
        "bg": bg, "eg": eg
    }

# ---------- aggregation ----------
def summarize_by_mother_then_group(rows: List[dict], target_groups: List[str]):
    by_uid: Dict[str, Dict[str, list]] = defaultdict(lambda: {"groups": [], "mlus": []})
    for r in rows:
        uid = r.get("mother_uid","")
        if not uid or r.get("mlu_words") is None: continue
        g = r.get("group","")
        if g: by_uid[uid]["groups"].append(g)
        by_uid[uid]["mlus"].append(r["mlu_words"])

    mother_rows = []
    for uid, info in by_uid.items():
        if not info["mlus"]: continue
        mean_mlu = sum(info["mlus"])/len(info["mlus"])
        group = ""
        if info["groups"]:
            cnt = Counter(info["groups"]); top = cnt.most_common()
            if len(top) == 1 or top[0][1] > top[1][1]:
                group = top[0][0]
            else:
                if "ASD" in cnt and "TYP" in cnt and cnt["ASD"] == cnt["TYP"]:
                    group = "ASD"
                else:
                    group = top[0][0]
        if not group: continue
        mother_rows.append({"mother_uid": uid, "group": group, "mlu_words": mean_mlu})

    out = []
    for g in target_groups:
        vals = [r["mlu_words"] for r in mother_rows if r.get("group","")==g and r.get("mlu_words") is not None]
        n = len(vals); mean = (sum(vals)/n) if n else None
        if n>1:
            mu = mean; sd = (sum((v-mu)**2 for v in vals)/(n-1))**0.5  # unbiased SD
        else:
            sd = None
        out.append({
            "group": g,
            "n_mothers": n,
            "mean": round(mean,3) if mean is not None else None,
            "sd": round(sd,3) if sd is not None else None
        })
    return out, mother_rows

# ---------- helpers ----------
def within_tolerance(val, tgt, abs_tol, rel_tol):
    if val is None or tgt is None: return False
    if abs(val - tgt) <= abs_tol: return True
    if rel_tol is not None and tgt != 0 and abs((val - tgt)/tgt) <= rel_tol: return True
    return False

def deep_merge(a, b):
    """shallow copy of a, overlay b recursively"""
    out = copy.deepcopy(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out

# ---------- run once ----------
def run_once(cfg):
    root = Path(cfg["dataset"]["transcripts_dir"]).expanduser()
    files = [p for p in root.rglob("*.cha") if p.is_file()]
    if not files:
        raise SystemExit("No .cha files found under transcripts_dir")
    results, skipped = [], Counter()
    for p in files:
        r = compute_mlu_for_file(p, cfg)
        if "skip_reason" in r:
            skipped[r["skip_reason"]] += 1
        else:
            results.append(r)

    grp_cnt = Counter(r.get("group","") for r in results)
    uid_empty = sum(1 for r in results if not r.get("mother_uid"))
    uniq_moms = len({r.get("mother_uid","") for r in results if r.get("mother_uid")})
    print(f"[DEBUG] rows={len(results)} by_group={dict(grp_cnt)}, mother_uid_empty={uid_empty}")
    print(f"[DEBUG] unique_mother_uids={uniq_moms}  skipped={dict(skipped)}")

    out_per = Path(cfg["outputs"]["per_mother_csv"]); out_per.parent.mkdir(parents=True, exist_ok=True)
    with open(out_per, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file","group","mother_uid","mlu_words","utterances","words","languages","bg","eg"])
        w.writeheader(); [w.writerow(r) for r in results]

    groups = cfg["dataset"]["group_labels"]
    summary, mother_rows = summarize_by_mother_then_group(results, groups)

    out_sum = Path(cfg["outputs"]["group_summary_csv"]); out_sum.parent.mkdir(parents=True, exist_ok=True)
    with open(out_sum, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["group","n_mothers","mean","sd"])
        w.writeheader()
        for row in summary: w.writerow(row)

    print("[DEBUG] mothers_by_group = " + str({g: sum(1 for r in mother_rows if r['group'] == g) for g in groups}))

    # report md (short)
    tgt = cfg["targets"]; abs_tol = cfg["tolerance"]["absolute_mean"]; rel_tol = cfg["tolerance"]["relative_mean"]
    lines = []
    lines.append(f"# Reproduction — {cfg['paper']['title']}\n")
    lines.append("**Metric**: Mother MLU (words/utterance)\n")
    lines.append("**Aggregation**: per mother → group\n")
    lines.append(f"**Token source**: {'%mor' if cfg['preprocess'].get('use_mor_tokens', False) else 'surface words'}\n")
    lines.append("## Results (ours vs paper)\n")
    for row in summary:
        g = row["group"]; ours_mean = row["mean"]; ours_sd = row["sd"]
        tgt_mean = tgt.get(g,{}).get("mean"); tgt_sd = tgt.get(g,{}).get("sd")
        ok = within_tolerance(ours_mean, tgt_mean, abs_tol, rel_tol) if (ours_mean is not None and tgt_mean is not None) else False
        lines.append(f"- {g}: ours mean={ours_mean}, sd={ours_sd}; paper mean={tgt_mean}, sd={tgt_sd} → {'OK' if ok else 'NG'}")
    have_win = sum(1 for r in results if r.get("bg") is not None and r.get("eg") is not None)
    total    = len(results)
    gem_cfg  = bool(cfg["preprocess"].get("use_gem_window"))
    drop_no_ts = bool(cfg["preprocess"].get("drop_no_timestamp_when_gems", False))
    lines.append("\n## Notes")
    lines.append(f"- Gem: setting={'ON' if gem_cfg else 'OFF'}, windows present={have_win}/{total}; "
                 f"no-timestamp utterances: {'dropped' if drop_no_ts else 'included'}.")
    Path(cfg["outputs"]["report_md"]).write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {out_per}")
    print(f"Wrote {out_sum}")
    print(f"Wrote {cfg['outputs']['report_md']}")
    print(f"Processed {len(results)} files (Gem setting: {'ON' if gem_cfg else 'OFF'}, windows present: {have_win}/{total}); aggregation=mother.")
    return summary

# ---------- HTML ----------
def build_html(doc_path: Path, cfg_base: dict, paper: dict, targets: dict, strict_summary: list, robust_summary: list, mvp: dict):
    def by_group(rows):
        return {r["group"]: r for r in rows}
    strict = by_group(strict_summary)
    robust = by_group(robust_summary)

    # MVP values (optional)
    mvp_vals = (mvp or {}).get("values", {}) if mvp else {}
    mvp_url  = (mvp or {}).get("url", "")
    mvp_label= (mvp or {}).get("label","MVP")

    groups = cfg_base["dataset"]["group_labels"]

    def f2(x):
        return ("" if x is None else (f"{x:.2f}" if isinstance(x,(int,float)) else x))

    trs = []
    for g in groups:
        t_mean = targets.get(g,{}).get("mean"); t_sd = targets.get(g,{}).get("sd")
        s = strict.get(g, {"n_mothers": None, "mean": None, "sd": None})
        r = robust.get(g, {"n_mothers": None, "mean": None, "sd": None})
        mv = mvp_vals.get(g, {"mean": None, "sd": None})
        tr = f"""
        <tr>
          <td>{g}</td>
          <td>{f2(t_mean)}</td>
          <td>{f2(t_sd)}</td>
          <td>{s.get('n_mothers','')}</td>
          <td>{f2(s.get('mean'))}</td>
          <td>{f2(s.get('sd'))}</td>
          <td>{r.get('n_mothers','')}</td>
          <td>{f2(r.get('mean'))}</td>
          <td>{f2(r.get('sd'))}</td>
          <td>{f2(mv.get('mean'))}</td>
          <td>{f2(mv.get('sd'))}</td>
        </tr>
        """
        trs.append(tr)

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Reproduction — {paper['title']}</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;line-height:1.6;margin:32px;}}
h1,h2{{margin:0.2em 0;}}
table{{border-collapse:collapse;width:100%;margin:16px 0;}}
th,td{{border:1px solid #ddd;padding:8px;text-align:center;}}
th{{background:#f6f7f9;}}
small, .note{{color:#555;}}
.code{{font-family:ui-monospace,Consolas,Menlo,monospace;background:#f8f8f8;padding:2px 6px;border-radius:4px;}}
a{{color:#145cc0;}}
</style>
</head>
<body>
  <h1>Reproduction — {paper['title']}</h1>
  <p>Dataset: ASDBank/CHILDES (English subset), Speaker=MOT, aggregation=per mother → group, token=%mor with surface fallback.</p>
  <p>Paper DOI: <a href="https://doi.org/{paper['doi']}" target="_blank">{paper['doi']}</a> | PDF: <a href="{paper['pdf_url']}" target="_blank">open PDF</a></p>
  <h2>Summary (Mother MLU, words/utterance)</h2>
  <table>
    <thead>
      <tr>
        <th>Group</th>
        <th>Paper mean</th>
        <th>Paper sd</th>
        <th>Strict n</th>
        <th>Strict mean</th>
        <th>Strict sd</th>
        <th>Robust n</th>
        <th>Robust mean</th>
        <th>Robust sd</th>
        <th>{mvp_label} mean</th>
        <th>{mvp_label} sd</th>
      </tr>
    </thead>
    <tbody>
      {''.join(trs)}
    </tbody>
  </table>

  <h2>Notes</h2>
  <ul>
    <li><span class="code">Strict</span>: <span class="code">min_utterance_len_tokens=1</span>, <span class="code">exclude_pure_intj=false</span>（厳密再現）。</li>
    <li><span class="code">Robust</span>: <span class="code">min_utterance_len_tokens=2</span>, <span class="code">exclude_pure_intj=true</span>（1語発話/あいづち歪みの感度分析）。</li>
    <li>Gem window: <span class="code">{'ON' if cfg_base.get('preprocess',{}).get('use_gem_window', False) else 'OFF'}</span>, 
        No-timestamp utterances: <span class="code">{'dropped' if cfg_base.get('preprocess',{}).get('drop_no_timestamp_when_gems', False) else 'included'}</span>.</li>
    <li>MVP report: <a href="{mvp_url}" target="_blank">{mvp_url}</a></li>
  </ul>
</body>
</html>
"""
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(html, encoding="utf-8")
    print(f"Wrote {doc_path}")

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="dual YAML config")
    args = ap.parse_args()
    with open(args.config, "r", encoding="utf-8") as f:
        cfg_all = yaml.safe_load(f)
    for k in ("paper","targets","base","modes"):
        if k not in cfg_all:
            raise SystemExit(f"[ERROR] Missing key in YAML: {k}")

    paper   = cfg_all["paper"]
    targets = cfg_all["targets"]
    base    = cfg_all["base"]
    modes   = cfg_all["modes"]
    mvp     = cfg_all.get("mvp", {})

    summaries = {}
    for m in modes:
        mode_name = m["name"]
        cfg_mode = deep_merge(base, {"preprocess": m.get("preprocess_overrides", {})})
        # set outputs per mode
        root = base.get("outputs_root", "reports/reproduction/bang_nadig_2015")
        suffix = m.get("outputs_suffix", mode_name)
        cfg_mode["paper"] = paper
        cfg_mode["targets"] = targets
        cfg_mode["tolerance"] = base["tolerance"]
        cfg_mode["outputs"] = {
            "per_mother_csv": f"{root}/per_mother_mlu_{suffix}.csv",
            "group_summary_csv": f"{root}/group_summary_{suffix}.csv",
            "report_md": f"{root}/bn2015_report_{suffix}.md",
        }
        print(f"\n===== Running mode: {mode_name} =====")
        summaries[mode_name] = run_once(cfg_mode)

    # build docs HTML
    docs_path = Path(cfg_all.get("docs", {}).get("html_out", "docs/bn2015_reproduction.html"))
    strict_summary = summaries.get("strict", [])
    robust_summary = summaries.get("robust", [])
    build_html(docs_path, base, paper, targets, strict_summary, robust_summary, mvp)

if __name__ == "__main__":
    main()
