#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, csv, yaml
from pathlib import Path
from collections import defaultdict, Counter

WHITES   = re.compile(r"\s+")
WORD_RX  = re.compile(r"^[A-Za-z]+(?:'[A-Za-z]+)?$")
PUNCT_RX = re.compile(r"[.,;:!?()\[\]{}\-\_/\"“”‘’]+")
MOR_LINE = re.compile(r"^%mor:\s*(.+)$")
MOR_CHUNK_RX = re.compile(r"^(?P<pos>[A-Za-z0-9]+)\|(?P<form>[^ ]+)$")

def read(path): return open(path,"r",encoding="utf-8",errors="ignore").read().splitlines()

def langs(lines):
    for ln in lines[:200]:
        if ln.startswith("@Languages:"):
            return [s.strip() for s in re.split(r"[,\s]+", ln.split(":",1)[1].strip()) if s.strip()]
    return []

def infer_group(lines):
    def pick(s):
        s=s.lower()
        if re.search(r"\basd\b|aut(?:ism)?",s): return "ASD"
        if re.search(r"\btyp\b|\btd\b|typical|controls?\b|\bcon\b",s): return "TYP"
        return ""
    ids=[ln for ln in lines[:800] if ln.startswith("@ID:")]
    for ln in ids:
        if "|CHI|" in ln or "|CHI" in ln:
            g=pick(ln); 
            if g: return g
    for ln in ids:
        g=pick(ln); 
        if g: return g
    for ln in lines[:400]:
        if ln.startswith("@Types:"):
            g=pick(ln)
            if g: return g
    return ""

def child_uid(lines, path):
    for ln in lines[:400]:
        if ln.startswith("@ID:") and "|CHI|" in ln:
            return ln.strip()
    for ln in lines[:300]:
        if ln.startswith("@Participants:") and "CHI" in ln:
            return "PARTS_CHI::"+ln.strip()
    return "CHI::"+path.stem

def iter_main(lines, speakers):
    for i,ln in enumerate(lines):
        if not ln.startswith("*"): continue
        try: spk, rest = ln[1:].split(":",1)
        except ValueError: continue
        if speakers and spk.strip() not in speakers: continue
        yield i, rest.strip()

def tokenize(text, lowercase=True):
    if lowercase: text=text.lower()
    text=PUNCT_RX.sub(" ", text)
    return [t for t in WHITES.split(text) if t]

def valid(tok, rx_excl, alpha_only):
    if rx_excl and re.match(rx_excl, tok): return False
    if alpha_only and not WORD_RX.match(tok): return False
    return True

def main():
    cfg = yaml.safe_load(open("reproduce/bang_nadig_2015/reproduce_bang_nadig_2015.yaml","r",encoding="utf-8"))
    root = Path(cfg["dataset"]["transcripts_dir"]).expanduser()
    files = [p for p in root.rglob("*.cha") if p.is_file()]
    use_mor = bool(cfg["preprocess"].get("use_mor_tokens", True))
    min_len = int(cfg["preprocess"].get("min_utterance_len_tokens",1))
    excl_rx = cfg["preprocess"].get("exclude_tokens_regex","")
    alpha_only = bool(cfg["preprocess"].get("alphabetic_only_tokens", True))
    lowercase = bool(cfg["preprocess"].get("lowercase", True))

    per_child = defaultdict(lambda: {"tokens":0,"types":set(),"groups":[],"n_utts":0})

    for p in files:
        lines = read(p)
        if cfg["dataset"]["include_language_codes"]:
            if not any(l in set(cfg["dataset"]["include_language_codes"]) for l in langs(lines)): 
                continue
        g = infer_group(lines)
        uid = child_uid(lines, p)

        for i, utt in iter_main(lines, cfg["dataset"]["include_speakers"]):
            toks=[]
            if use_mor:
                mor_raw=None
                for j in range(i+1, min(i+16,len(lines))):
                    m=MOR_LINE.match(lines[j])
                    if m: mor_raw=m.group(1); break
                if mor_raw:
                    for chunk in mor_raw.split():
                        if "|" in chunk: _, w = chunk.split("|",1)
                        else: w = chunk
                        w = re.sub(r"[^A-Za-z']+","", w)
                        if w: toks.append(w.lower())
            if not toks:
                toks=[t for t in tokenize(utt, lowercase) if valid(t, excl_rx, alpha_only)]
            if len(toks) >= min_len:
                per_child[uid]["tokens"] += len(toks)
                per_child[uid]["types"].update(toks)
                per_child[uid]["n_utts"] += 1
        if g:
            per_child[uid]["groups"].append(g)

    rows=[]
    for uid,info in per_child.items():
        if info["tokens"]==0: continue
        group = Counter(info["groups"]).most_common(1)[0][0] if info["groups"] else ""
        rows.append({
            "child_uid": uid,
            "group": group,
            "tokens": info["tokens"],
            "ndw": len(info["types"]),
            "ttr": round(len(info["types"])/info["tokens"], 6),
            "utterances": info["n_utts"]
        })

    out = Path("reports/reproduction/bang_nadig_2015/per_child_ttr_ndw.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=["child_uid","group","tokens","ndw","ttr","utterances"])
        w.writeheader(); w.writerows(rows)
    print("Wrote", out)

    # group summary + Cohen's d（TTR/NDW）
    def summarize(metric):
        from math import sqrt
        import statistics as st
        a=[r[metric] for r in rows if r["group"]=="ASD"]
        t=[r[metric] for r in rows if r["group"]=="TYP"]
        if not a or not t: 
            print(metric, "insufficient data"); return
        m1,m2=st.mean(a), st.mean(t)
        s1=st.pstdev(a); s2=st.pstdev(t)
        n1,n2=len(a),len(t)
        sp=sqrt(((n1*s1*s1)+(n2*s2*s2))/(n1+n2)) if (n1+n2)>0 else float("nan")
        d=(m1-m2)/sp if sp>0 else float("nan")
        print(f"{metric}: ASD={m1:.4f}(n={n1}), TYP={m2:.4f}(n={n2}), d={d:.3f}")
    summarize("ttr")
    summarize("ndw")

if __name__=="__main__":
    main()
