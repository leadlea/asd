#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse, os, pandas as pd, re
import spacy
from collections import Counter

DMARKERS = ["well","you know","i mean","like","so","anyway","okay","ok","right","actually"]
MENTAL_STATE = {"think","know","believe","want","guess","feel","hope","remember","forget","understand"}

def load_nlp():
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        raise SystemExit("spaCy model 'en_core_web_sm' is not installed. Run: python -m spacy download en_core_web_sm")

def per_utt(nlp, text):
    doc = nlp(text)
    toks = [t for t in doc if not t.is_space]
    n = max(1, len(toks))
    pos = Counter(t.pos_ for t in toks)
    tl = text.lower()
    dmark = sum(tl.count(dm) for dm in DMARKERS)
    repair = len(re.findall(r"\b(um+|uh+)\b", tl))
    mental = sum(1 for t in toks if t.lemma_.lower() in MENTAL_STATE and t.pos_ in ("VERB","AUX"))
    return {
        "len_tokens": len(toks),
        "pronoun_ratio": pos.get("PRON",0)/n,
        "propernoun_ratio": pos.get("PROPN",0)/n,
        "noun_ratio": pos.get("NOUN",0)/n,
        "verb_ratio": (pos.get("VERB",0)+pos.get("AUX",0))/n,
        "discourse_marker_rate": dmark/n,
        "repair_rate_umuh": repair/n,
        "mental_state_rate": mental/n,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_csv", required=True)
    ap.add_argument("--out_csv", required=True)
    args = ap.parse_args()
    nlp = load_nlp()
    df = pd.read_csv(args.in_csv)
    feats = []
    for _, r in df.iterrows():
        f = per_utt(nlp, str(r["utt"]))
        f["file_id"] = r["file_id"]
        feats.append(f)
    out = pd.DataFrame(feats).groupby("file_id").mean(numeric_only=True).reset_index()
    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)
    out.to_csv(args.out_csv, index=False)
    print(f"wrote pragmatics features -> {args.out_csv}")

if __name__ == "__main__":
    main()
