#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse, re
from pathlib import Path
from typing import List, Tuple, Dict
import yaml, csv
from collections import defaultdict, Counter

# ---------- regex helpers ----------
WHITES   = re.compile(r"\s+")
WORD_RX  = re.compile(r"^[A-Za-z]+(?:'[A-Za-z]+)?$")     # don't 等の省略形を許可
PUNCT_RX = re.compile(r"[.,;:!?()\[\]{}\-\_/\"“”‘’]+")   # アポストロフィは残す
TIME_RX  = re.compile(r"\[(\d+)_\s*(\d+)\]")             # [start_end] in ms
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
    """@Bg: 0 / @Eg: 540000 のような形式（ミリ秒）。無ければ (None,None)"""
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
    """
    優先順位:
      1) @ID の CHI 行に ASD/TYP/TD があれば採用
      2) 1)が無ければ他の @ID 行もスキャン
      3) それでも無ければ @Types に ASD/TYP/TD があれば採用
      4) 見つからなければ空文字（""）
    """
    def pick_from(s: str) -> str:
        s_low = s.lower()
        if re.search(r"\basd\b|\baut(?:ism)?\b", s_low):
            return "ASD"
        if re.search(r"\btyp\b|\btd\b|\btypical\b|\bcontrol(?:s)?\b|\bcon\b", s_low):
            return "TYP"
        return ""

    id_lines = [ln for ln in lines[:800] if ln.startswith("@ID:")]
    chi_lines = [ln for ln in id_lines if "|CHI|" in ln or "|CHI" in ln]
    for ln in chi_lines:
        g = pick_from(ln)
        if g: return g
    for ln in id_lines:
        g = pick_from(ln)
        if g: return g
    for ln in lines[:400]:
        if ln.startswith("@Types:"):
            g = pick_from(ln)
            if g: return g
    return ""

def get_mother_uid(lines: List[str], path: Path) -> str:
    """
    Nadig系：CHI の @ID[9] に個体コード（例: 115）が入る前提で、
    母親UIDを '<study>::<code>' に正規化。フォールバックあり。
    """
    # 1) CHI の @ID
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

    # 2) MOT の @ID を使って簡易キーに圧縮
    for ln in lines[:400]:
        if ln.startswith("@ID:") and "|MOT|" in ln:
            raw = ln.split(":",1)[1].strip()
            parts = [p.strip() for p in raw.split("|")]
            study = parts[1] if len(parts) > 1 and parts[1] else "STUDY"
            label = parts[7] if len(parts) > 7 and parts[7] else "MOT"
            edu   = parts[8] if len(parts) > 8 and parts[8] else ""
            key   = f"{study}::{label}"
            if edu:
                key += f"::{edu}"
            return key

    # 3) Participants
    for ln in lines[:400]:
        if ln.startswith("@Participants:") and "MOT" in ln:
            return f"PARTS::{ln.strip()}"

    # 4) 最後の手段：ファイル名
    return f"MOT::{path.stem}"

def get_child_uid(lines: List[str], path: Path) -> str:
    """
    子ども集約用の安定キー。まず CHI の @ID 行全体をUIDとして使う（最も一意性が高い）。
    無ければ Participants ベース→ファイル名。
    """
    for ln in lines[:400]:
        if ln.startswith("@ID:") and "|CHI|" in ln:
            return ln.strip()
    for ln in lines[:300]:
        if ln.startswith("@Participants:") and "CHI" in ln:
            return f"PARTS_CHI::{ln.strip()}"
    return f"CHI::{path.stem}"

# ---------- main-tier iterator ----------
def iter_main_tier(lines: List[str], speakers: List[str]):
    """yield (idx, speaker, utt_text, (start_ms, end_ms or None)) for main tiers"""
    for idx, ln in enumerate(lines):
        if not ln.startswith("*"):  # main tier only
            continue
        try:
            spk, rest = ln[1:].split(":",1)
        except ValueError:
            continue
        spk = spk.strip()
        if speakers and spk not in speakers:
            continue
        utt = rest.strip()
        # 末尾の [start_end] を切り落として保持
        t = TIME_RX.search(utt)
        start = end = None
        if t:
            start = int(t.group(1)); end = int(t.group(2))
            utt = utt[:t.start()].rstrip()
        yield idx, spk, utt, (start, end)

# ---------- %mor utilities ----------
def mor_all_interjection(mor_raw: str) -> bool:
    """%mor 生文字列が intj|... のみで構成されていれば True（その発話は丸ごと除外）"""
    has_chunk = False
    for chunk in mor_raw.split():
        m = MOR_CHUNK_RX.match(chunk)
        if not m:
            return False
        has_chunk = True
        if m.group("pos").lower() != "intj":
            return False
    return has_chunk  # 1個以上の mor チャンクがあり、すべて intj

# ---------- tokenization ----------
def tokenize(text: str, lowercase=True) -> List[str]:
    if lowercase: text = text.lower()
    text = PUNCT_RX.sub(" ", text)     # 句読点・括弧等を空白化（' は残す）
    toks = [t for t in WHITES.split(text) if t]
    return toks

def is_valid_token(tok: str, cfg) -> bool:
    rx_excl = cfg["preprocess"].get("exclude_tokens_regex","")
    if rx_excl and re.match(rx_excl, tok):
        return False
    if cfg["preprocess"].get("alphabetic_only_tokens", False):
        if not WORD_RX.match(tok):
            return False
    return True

def in_gem_range(tspan, bg, eg) -> bool:
    # Gem ウィンドウ無し → 採用
    if bg is None or eg is None:
        return True
    # 時刻なし → 採用（除外しない）
    if tspan is None:
        return True
    s, e = tspan
    if s is None or e is None:
        return True
    # 少しでも重なれば採用
    return not (e < bg or s > eg)

# ---------- core ----------
def compute_mlu_for_file(path: Path, cfg) -> dict:
    lines = read_cha_lines(path)
    langs = get_languages(lines)
    incl_langs = set(cfg["dataset"]["include_language_codes"] or [])

    # 英語を含まないセッションはスキップ
    if incl_langs and not any(l in incl_langs for l in langs):
        return {"file": str(path), "skip_reason": "language_filtered"}

    # 厳密な英語のみ（必要なら）
    if cfg["dataset"].get("strict_english_only", False):
        if set(langs) != {"eng"}:
            return {"file": str(path), "skip_reason": "non_english_only"}

    group = infer_group_from_id(lines)
    mother_uid = get_mother_uid(lines, path)
    child_uid  = get_child_uid(lines, path)
    bg, eg = get_gem_window(lines) if cfg["preprocess"].get("use_gem_window", False) else (None, None)

    total_words = 0
    total_utts  = 0
    use_mor = bool(cfg["preprocess"].get("use_mor_tokens", False))
    exclude_pure_intj = bool(cfg["preprocess"].get("exclude_pure_intj", False))  # strict/robust 切替

    for idx, spk, utt, tspan in iter_main_tier(lines, cfg["dataset"]["include_speakers"]):
        if cfg["preprocess"].get("use_gem_window", False) and not in_gem_range(tspan, bg, eg):
            continue

        toks = []
        if use_mor:
            # %mor 生文字列を +15行まで探索
            mor_raw = None
            for j in range(idx+1, min(idx+16, len(lines))):
                m = MOR_LINE.match(lines[j])
                if m:
                    mor_raw = m.group(1)
                    break
            if mor_raw:
                # 間投詞のみの発話はまるごと除外（robustモードのみ）
                if exclude_pure_intj and mor_all_interjection(mor_raw):
                    continue
                for chunk in mor_raw.split():
                    if "|" in chunk:
                        _, word = chunk.split("|", 1)
                    else:
                        word = chunk
                    word = re.sub(r"[^A-Za-z']+", "", word)  # keep apostrophe
                    if word:
                        toks.append(word.lower())

        # %mor 由来で語が得られなければ表層にフォールバック
        if not toks:
            toks = tokenize(utt, lowercase=cfg["preprocess"].get("lowercase", True))
            toks = [t for t in toks if is_valid_token(t, cfg)]

        if len(toks) >= cfg["preprocess"].get("min_utterance_len_tokens", 1):
            total_utts  += 1
            total_words += len(toks)

    # ---- universal backoff: MORで全落ちしたセッションは表層語で再計算 ----
    if total_utts == 0:
        toks_total = utts_total = 0
        for idx, spk, utt, tspan in iter_main_tier(lines, cfg["dataset"]["include_speakers"]):
            if cfg["preprocess"].get("use_gem_window", False) and not in_gem_range(tspan, bg, eg):
                continue
            toks = tokenize(utt, lowercase=cfg["preprocess"].get("lowercase", True))
            toks = [t for t in toks if is_valid_token(t, cfg)]
            if len(toks) >= cfg["preprocess"].get("min_utterance_len_tokens", 1):
                utts_total += 1
                toks_total += len(toks)
        if utts_total > 0:
            total_utts, total_words = utts_total, toks_total
        else:
            print(f"[DEBUG] dropped-all-utterances: {path}")

    mlu = (total_words/total_utts) if total_utts>0 else float("nan")
    return {
        "file": str(path),
        "group": group,
        "mother_uid": mother_uid,
        "child_uid":  child_uid,
        "mlu_words": round(mlu, 6) if total_utts>0 else None,
        "utterances": total_utts,
        "words": total_words,
        "languages": ",".join(langs),
        "bg": bg, "eg": eg
    }

# ---------- aggregation ----------
def summarize_by_group(rows: List[dict], target_groups: List[str]) -> List[dict]:
    out = []
    for g in target_groups:
        vals = [r["mlu_words"] for r in rows if r.get("group","")==g and r.get("mlu_words") is not None]
        n = len(vals)
        mean = (sum(vals)/n) if n else None
        if n>1:
            mu = mean
            sd = (sum((v-mu)**2 for v in vals)/n)**0.5   # population SD
        else:
            sd = None
        out.append({"group": g, "n": n, "mean": round(mean,3) if mean is not None else None, "sd": round(sd,3) if sd is not None else None})
    return out

def summarize_by_mother_then_group(rows: List[dict], target_groups: List[str]) -> Tuple[List[dict], List[dict]]:
    """
    同一 mother_uid の複数ファイルをまず平均 → その後 ASD/TYP 群平均。
    group は「その母親で観測された非空ラベルの多数決」で決める（空は無視）。
    """
    by_uid: Dict[str, Dict[str, list]] = defaultdict(lambda: {"groups": [], "mlus": []})
    for r in rows:
        uid = r.get("mother_uid","")
        if not uid or r.get("mlu_words") is None:
            continue
        g = r.get("group","")
        if g:
            by_uid[uid]["groups"].append(g)
        by_uid[uid]["mlus"].append(r["mlu_words"])

    mother_rows = []
    for uid, info in by_uid.items():
        if not info["mlus"]:
            continue
        mean_mlu = sum(info["mlus"])/len(info["mlus"])
        # 非空ラベルの多数決（同数なら ASD を優先，次いで TYP）
        group = ""
        if info["groups"]:
            cnt = Counter(info["groups"])
            top = cnt.most_common()
            if len(top) == 1 or top[0][1] > top[1][1]:
                group = top[0][0]
            else:
                if "ASD" in cnt and "TYP" in cnt and cnt["ASD"] == cnt["TYP"]:
                    group = "ASD"
                else:
                    group = top[0][0]
        if not group:
            continue
        mother_rows.append({"mother_uid": uid, "group": group, "mlu_words": mean_mlu})

    out = []
    for g in target_groups:
        vals = [r["mlu_words"] for r in mother_rows if r.get("group","")==g and r.get("mlu_words") is not None]
        n = len(vals)
        mean = (sum(vals)/n) if n else None
        if n>1:
            mu = mean
            sd = (sum((v-mu)**2 for v in vals)/n)**0.5
        else:
            sd = None
        out.append({"group": g, "n_mothers": n, "mean": round(mean,3) if mean is not None else None, "sd": round(sd,3) if sd is not None else None})
    return out, mother_rows

def summarize_by_child_then_group(rows: List[dict], target_groups: List[str]) -> Tuple[List[dict], List[dict]]:
    """
    同一 child_uid の複数ファイルをまず平均 → その後 ASD/TYP 群平均。
    group は「その子で観測された非空ラベルの多数決」で決める（空は無視）。
    """
    by_uid: Dict[str, Dict[str, list]] = defaultdict(lambda: {"groups": [], "mlus": []})
    for r in rows:
        uid = r.get("child_uid","")
        if not uid or r.get("mlu_words") is None:
            continue
        g = r.get("group","")
        if g:
            by_uid[uid]["groups"].append(g)
        by_uid[uid]["mlus"].append(r["mlu_words"])

    child_rows = []
    for uid, info in by_uid.items():
        if not info["mlus"]:
            continue
        mean_mlu = sum(info["mlus"])/len(info["mlus"])
        group = ""
        if info["groups"]:
            cnt = Counter(info["groups"]).most_common()
            group = cnt[0][0]
        if not group:
            continue
        child_rows.append({"child_uid": uid, "group": group, "mlu_words": mean_mlu})

    out = []
    for g in target_groups:
        vals = [r["mlu_words"] for r in child_rows if r.get("group","")==g and r.get("mlu_words") is not None]
        n = len(vals)
        mean = (sum(vals)/n) if n else None
        if n>1:
            mu = mean
            sd = (sum((v-mu)**2 for v in vals)/n)**0.5
        else:
            sd = None
        out.append({"group": g, "n_children": n, "mean": round(mean,3) if mean is not None else None, "sd": round(sd,3) if sd is not None else None})
    return out, child_rows

# ---------- tolerance ----------
def within_tolerance(val, tgt, abs_tol, rel_tol):
    if val is None or tgt is None:
        return False
    if abs(val - tgt) <= abs_tol:
        return True
    if rel_tol is not None and tgt != 0 and abs((val - tgt)/tgt) <= rel_tol:
        return True
    return False

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config, "r", encoding="utf-8"))

    root = Path(cfg["dataset"]["transcripts_dir"]).expanduser()
    files = [p for p in root.rglob("*.cha") if p.is_file()]
    if not files:
        raise SystemExit("No .cha files found under transcripts_dir")

    results = []
    for p in files:
        r = compute_mlu_for_file(p, cfg)
        if "skip_reason" not in r:
            results.append(r)

    # デバッグ：件数とUID欠損
    grp_cnt = Counter(r.get("group","") for r in results)
    mom_uid_empty = sum(1 for r in results if not r.get("mother_uid"))
    uniq_moms = len({r.get("mother_uid","") for r in results if r.get("mother_uid")})
    uniq_kids = len({r.get("child_uid","") for r in results if r.get("child_uid")})
    print(f"[DEBUG] rows={len(results)} by_group={dict(grp_cnt)}, mother_uid_empty={mom_uid_empty}")
    print(f"[DEBUG] unique_mother_uids={uniq_moms}")
    print(f"[DEBUG] unique_child_uids={uniq_kids}")

    # per-file 出力（列に child_uid も追加）
    out_per = Path(cfg["outputs"]["per_mother_csv"])
    out_per.parent.mkdir(parents=True, exist_ok=True)
    with open(out_per, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["file","group","mother_uid","child_uid","mlu_words","utterances","words","languages","bg","eg"]
        )
        w.writeheader()
        for r in results:
            w.writerow(r)

    aggregate_mother = bool(cfg["dataset"].get("aggregate_by_mother", False))
    aggregate_child  = bool(cfg["dataset"].get("aggregate_by_child", False))
    groups = cfg["dataset"]["group_labels"]

    if aggregate_child:
        summary, child_rows = summarize_by_child_then_group(results, groups)
        out_sum = Path(cfg["outputs"]["group_summary_csv"])
        out_sum.parent.mkdir(parents=True, exist_ok=True)
        with open(out_sum, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["group","n_children","mean","sd"])
            w.writeheader()
            for row in summary:
                w.writerow(row)
        print("[DEBUG] children_by_group = " + str({g: sum(1 for r in child_rows if r['group']==g) for g in groups}))
        agg_label = "child"
    elif aggregate_mother:
        summary, mother_rows = summarize_by_mother_then_group(results, groups)
        out_sum = Path(cfg["outputs"]["group_summary_csv"])
        out_sum.parent.mkdir(parents=True, exist_ok=True)
        with open(out_sum, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["group","n_mothers","mean","sd"])
            w.writeheader()
            for row in summary:
                w.writerow(row)
        print("[DEBUG] mothers_by_group = " + str({g: sum(1 for r in mother_rows if r['group']==g) for g in groups}))
        agg_label = "mother"
    else:
        summary = summarize_by_group(results, groups)
        out_sum = Path(cfg["outputs"]["group_summary_csv"])
        out_sum.parent.mkdir(parents=True, exist_ok=True)
        with open(out_sum, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["group","n","mean","sd"])
            w.writeheader()
            for row in summary:
                w.writerow(row)
        agg_label = "file"

    # レポート
    tgt = cfg.get("targets", {})
    abs_tol = cfg.get("tolerance", {}).get("absolute_mean")
    rel_tol = cfg.get("tolerance", {}).get("relative_mean")
    speakers = ",".join(cfg["dataset"].get("include_speakers", [])) or "(unspecified)"

    lines = []
    lines.append(f"# Reproduction — {cfg.get('paper_title','(paper)')}\n")
    lines.append(f"**Metric**: {speakers} MLU (words/utterance)\n")
    lines.append(f"**Aggregation**: {'per '+agg_label+' -> group'}\n")
    lines.append(f"**Token source**: {'%mor' if cfg['preprocess'].get('use_mor_tokens', False) else 'surface words'}\n")
    lines.append("## Results (ours vs paper)\n")
    for row in summary:
        g = row["group"]; ours_mean = row["mean"]; ours_sd = row["sd"]
        tgt_mean = tgt.get(g,{}).get("mean") if tgt else None
        tgt_sd   = tgt.get(g,{}).get("sd") if tgt else None
        ok = within_tolerance(ours_mean, tgt_mean, abs_tol, rel_tol) if (ours_mean is not None and tgt_mean is not None and abs_tol is not None) else False
        lines.append(f"- {g}: ours mean={ours_mean}, sd={ours_sd}; paper mean={tgt_mean}, sd={tgt_sd} → {'OK' if ok else '—'}")

    # Gemの可視化：設定ON/実データのウィンドウ有無
    have_win = sum(1 for r in results if r.get("bg") is not None and r.get("eg") is not None)
    total    = len(results)
    gem_cfg  = bool(cfg["preprocess"].get("use_gem_window"))

    lines.append("\n## Notes")
    lines.append(f"- Gem: setting={'ON' if gem_cfg else 'OFF'}, windows present={have_win}/{total}; timestamps-missing -> included.")
    lines.append("- Language: sessions that include English are kept (strict_english_only may be off).")
    lines.append("- Tokens: punctuation stripped; alphabetic+contractions; fillers/codes dropped. If use_mor_tokens=true, %mor-based counting with surface fallback.")
    lines.append(f"- Aggregation: {agg_label}-level means when enabled; population SD for descriptives.")
    Path(cfg["outputs"]["report_md"]).write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {out_per}")
    print(f"Wrote {out_sum}")
    print(f"Wrote {cfg['outputs']['report_md']}")
    print(
        f"Processed {len(results)} files "
        f"(Gem setting: {'ON' if gem_cfg else 'OFF'}, windows present: {have_win}/{total}); "
        f"aggregation={agg_label}."
    )

if __name__ == "__main__":
    main()
