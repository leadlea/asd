#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse, pandas as pd, re

DMAP = {
    r"\bwell\b": "えっと、",
    r"\byou know\b": "ほら、",
    r"\bi mean\b": "というか、",
    r"\bokay\b": "はい、",
    r"\bright\b": "ですよね、",
    r"\banyway\b": "ともかく、",
}

def add_final_particle(s):
    s = s.strip()
    if not s: return s
    if re.search(r"[?？]$", s):
        if not s.endswith("か？") and not s.endswith("？"):
            s = re.sub(r"[?？]$", "かな？", s)
        return s
    if re.search(r"(でしょう|よね)$", s):
        return s
    if re.search(r"(です|ます|だ)$", s):
        return s + "よ"
    return s + "ね"

def apply_rules(text):
    t = text
    tl = t.lower()
    for pat, rep in DMAP.items():
        tl_new = re.sub(pat, "", tl)
        if tl != tl_new:
            t = rep + t
            tl = tl_new
    t = add_final_particle(t)
    return t

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_csv", required=True)
    ap.add_argument("--out_csv", required=True)
    args = ap.parse_args()
    df = pd.read_csv(args.in_csv)
    if "utt_ja" not in df.columns:
        df["utt_ja"] = df["utt"]
    df["utt_ja_post"] = df["utt_ja"].fillna("").map(apply_rules)
    df.to_csv(args.out_csv, index=False)
    print(f"wrote -> {args.out_csv}")

if __name__ == "__main__":
    main()
