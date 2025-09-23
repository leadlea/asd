#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, yaml, argparse, math, csv
from pathlib import Path
from collections import defaultdict, Counter
from statistics import mean, pstdev
try:
    from scipy import stats
    SCIPY=True
except Exception:
    SCIPY=False

# ---- regex helpers ----
WHITES   = re.compile(r"\s+")
WORD_RX  = re.compile(r"^[A-Za-z]+(?:'[A-Za-z]+)?$")
PUNCT_RX = re.compile(r"[.,;:!?()\[\]{}\-\_/\"“”‘’]+")
MOR_LINE = re.compile(r"^%mor:\s*(.+)$")

def read_lines(p: Path):
    return p.read_text(encoding="utf-8", errors="ignore").splitlines()

def get_languages(lines):
    for ln in lines[:200]:
        if ln.startswith("@Languages:"):
            part = ln.split(":",1)[1].strip()
            return [s.strip() for s in re.split(r"[,\s]+", part) if s.strip()]
    return []

def infer_group(lines):
    def pick(s):
        s=s.lower()
        if re.search(r"\basd\b|aut(?:ism)?", s): return "ASD"
        if re.search(r"\btyp\b|\btd\b|typical|controls?\b|\bcon\b", s): return "TYP"
        return ""
    ids=[ln for ln in lines[:800] if ln.startswith("@ID:")]
    # CHI優先
    for ln in ids:
        if "|CHI|" in ln or "|CHI" in ln:
            g=pick(ln); 
            if g: return g
    for ln in ids:
        g=pick(ln)
        if g: return g
    for ln in lines[:400]:
        if ln.startswith("@Types:"):
            g=pick(ln)
            if g: return g
    return ""

def child_uid(lines, path: Path):
    # CHI の @ID 行全体をUIDにして重複回避（Nadig系は9番目に個体コードが入ることが多い）
    for ln in lines[:400]:
        if ln.startswith("@ID:") and "|CHI|" in ln:
            return ln.strip()
    for ln in lines[:300]:
        if ln.startswith("@Participants:") and "CHI" in ln:
            return "PARTS_CHI::"+ln.strip()
    return "CHI::"+path.stem

def iter_chi_main(lines):
    for i,ln in enumerate(lines):
        if ln.startswith("*CHI:"):
            yield i, ln.split(":",1)[1].strip()

def mor_tokens(lines, i):
    # 直後〜15行以内の %mor を語列に展開
    for j in range(i+1, min(i+16, len(lines))):
        ln = lines[j]
        if ln.startswith("%mor:"):
            mor_raw = ln.split(":",1)[1].strip()
            out=[]
            for chunk in mor_raw.split():
                w = chunk.split("|",1)[-1] if "|" in chunk else chunk
                w = re.sub(r"[^A-Za-z']+","", w).lower()
                if w: out.append(w)
            return out
    return None

def surface_tokens(utt, lowercase=True, exclude_rx=None, alpha_only=True):
    if lowercase: utt = utt.lower()
    utt = PUNCT_RX.sub(" ", utt)
    toks = [t for t in WHITES.split(utt) if t]
    out=[]
    for t in toks:
        if exclude_rx and re.match(exclude_rx, t): 
            continue
        if alpha_only and not WORD_RX.match(t):
            continue
        out.append(t)
    return out

def cohens_d(a, b):
    if not a or not b: 
        return float("nan")
    n1,n2 = len(a), len(b)
    s1,s2 = pstdev(a), pstdev(b)
    sp = math.sqrt(((n1*s1*s1)+(n2*s2*s2))/(n1+n2)) if (n1+n2)>0 else float("nan")
    return (mean(a)-mean(b))/sp if sp>0 else float("nan")

def welch_t_ci(a, b, alpha=0.05):
    if not SCIPY or not a or not b:
        return (float("nan"), float("nan"), (float("nan"), float("nan")))
    t,p = stats.ttest_ind(a,b,equal_var=False)
    m1,m2 = mean(a), mean(b)
    s1,s2 = pstdev(a), pstdev(b); n1,n2 = len(a), len(b)
    se = math.sqrt(s1*s1/n1 + s2*s2/n2)
    df = ((s1*s1/n1 + s2*s2/n2)**2)/(((s1*s1/n1)**2)/(n1-1) + ((s2*s2/n2)**2)/(n2-1))
    h = stats.t.ppf(1-alpha/2, df)*se
    return (t, p, (m1-m2-h, m1-m2+h))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=100, help="use first N tokens per child (NDW@N)")
    ap.add_argument("--dump_csv", action="store_true", help="save per-child NDW@N csv")
    args = ap.parse_args()

    cfg = yaml.safe_load(open("reproduce/bang_nadig_2015/reproduce_bang_nadig_2015.yaml","r",encoding="utf-8"))
    root = Path(cfg["dataset"]["transcripts_dir"]).expanduser()
    files = [p for p in root.rglob("*.cha") if p.is_file()]

    include_langs   = set(cfg["dataset"].get("include_language_codes", []) or [])
    strict_english  = bool(cfg["dataset"].get("strict_english_only", False))
    min_len         = int(cfg["preprocess"].get("min_utterance_len_tokens", 1))
    use_mor         = bool(cfg["preprocess"].get("use_mor_tokens", True))
    exclude_rx      = cfg["preprocess"].get("exclude_tokens_regex", "")
    alpha_only      = bool(cfg["preprocess"].get("alphabetic_only_tokens", True))
    lowercase       = bool(cfg["preprocess"].get("lowercase", True))

    per_child = defaultdict(lambda: {"tok": [], "grp_votes": [], "debug": {"dropped_short":0, "no_tokens":0}})
    file_kept = 0; file_lang_drop = 0; file_strict_drop = 0

    for p in files:
        L = read_lines(p)
        Lcodes = set(get_languages(L))
        # 言語フィルタ
        if include_langs and not (Lcodes & include_langs):
            file_lang_drop += 1
            continue
        if strict_english and Lcodes != {"eng"}:
            file_strict_drop += 1
            continue
        file_kept += 1

        uid = child_uid(L, p)
        g   = infer_group(L)
        if g: per_child[uid]["grp_votes"].append(g)

        for i, utt in iter_chi_main(L):
            toks = mor_tokens(L, i) if use_mor else None
            if not toks:
                toks = surface_tokens(utt, lowercase, exclude_rx, alpha_only)
            if len(toks) >= min_len:
                per_child[uid]["tok"].extend(toks)
            else:
                per_child[uid]["debug"]["dropped_short"] += 1
            if not toks:
                per_child[uid]["debug"]["no_tokens"] += 1

    # 集計
    rows=[]
    grp_counts_before = Counter()
    grp_counts_after  = Counter()
    for uid,info in per_child.items():
        # グループ決定（多数決）。空は除外。
        grp = Counter(info["grp_votes"]).most_common(1)[0][0] if info["grp_votes"] else ""
        if grp: grp_counts_before[grp]+=1
        toksN = info["tok"][:args.N]
        if not grp or not toksN:
            continue
        ndw = len(set(toksN))
        rows.append({"child_uid": uid, "group": grp, "ndw_atN": ndw, "n_tokens_used": len(toksN)})
        grp_counts_after[grp]+=1

    A=[r["ndw_atN"] for r in rows if r["group"]=="ASD"]
    T=[r["ndw_atN"] for r in rows if r["group"]=="TYP"]

    print(f"[DEBUG] files kept={file_kept}, dropped_by_language={file_lang_drop}, dropped_by_strict={file_strict_drop}")
    print(f"[DEBUG] children with group(label) before token filter: {dict(grp_counts_before)}")
    print(f"[DEBUG] children kept after NDW@{args.N} token filter: {dict(grp_counts_after)}")

    if args.dump_csv:
        out = Path(f"reports/reproduction/bang_nadig_2015/per_child_ndw_at{args.N}.csv")
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", newline="", encoding="utf-8") as f:
            w=csv.DictWriter(f, fieldnames=["child_uid","group","ndw_atN","n_tokens_used"])
            w.writeheader(); w.writerows(rows)
        print("Wrote", out)

    if not A or not T:
        print("[WARN] ASD or TYP has zero samples after filtering. Check YAML filters and token counts.")
        return

    d = cohens_d(A,T)
    if SCIPY:
        t,p,ci = welch_t_ci(A,T)
        print(f"NDW@{args.N}: ASD={mean(A):.1f}(n={len(A)}), TYP={mean(T):.1f}(n={len(T)}), d={d:.3f}, Welch t={t:.3f}, p={p:.3f}, 95%CI={ci}")
    else:
        print(f"NDW@{args.N}: ASD={mean(A):.1f}(n={len(A)}), TYP={mean(T):.1f}(n={len(T)}), d={d:.3f}  (scipy未導入のため t/CI は省略)")

if __name__ == "__main__":
    main()
