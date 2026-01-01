#!/usr/bin/env python3
import argparse, io, math, re
from urllib.parse import urlparse

import boto3
import pandas as pd
import pyarrow.parquet as pq

PAPER_ANCHOR = {
    "dyad_conversations": 280,
    "hours_approx": 93.0,
    "yo_utt": 7162,
    "ne_utt": 19885,
    # following token counts from paper (reference)
    "yo_follow_un": 1236,
    "yo_follow_sou": 221,
    "yo_follow_hai": 144,
    "ne_follow_un": 4797,
    "ne_follow_sou": 1480,
    "ne_follow_hai": 781,
}

TOK_TARGET = {"うん", "そう", "はい"}

def parse_s3(uri: str):
    u = urlparse(uri)
    assert u.scheme == "s3"
    return u.netloc, u.path.lstrip("/")

def s3_read_parquet(s3, uri: str) -> pd.DataFrame:
    b, k = parse_s3(uri)
    obj = s3.get_object(Bucket=b, Key=k)
    buf = io.BytesIO(obj["Body"].read())
    return pq.read_table(buf).to_pandas()

def norm_tail(text: str) -> str:
    s = "" if text is None else str(text)
    # remove simple bracket tags like (F ...), (L ...), etc.
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"\s+", "", s)
    # strip trailing punctuation
    s = re.sub(r"[。．\.\!\?！？？、,]+$", "", s)
    s = s.strip()
    return s

def is_yone(text: str) -> bool:
    s = norm_tail(text)
    # tolerate trailing elongations
    s = re.sub(r"[ー〜…]+$", "", s)
    return bool(re.search(r"よね$", s))

def norm_token(tok) -> str | None:
    if tok is None:
        return None
    s = str(tok).strip()
    if s == "" or s.lower() == "nan":
        return None
    s = re.sub(r"[。．\.\!\?！？？、,]+$", "", s)
    s = re.sub(r"[ー〜…]+$", "", s)
    s = s.strip()
    return s if s else None

def entropy_log2(tokens: pd.Series) -> float | None:
    toks = tokens.dropna().astype(str)
    if len(toks) == 0:
        return None
    vc = toks.value_counts()
    n = float(vc.sum())
    ent = 0.0
    for c in vc.values:
        p = float(c) / n
        ent -= p * math.log2(p)
    return float(ent)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold-s3-prefix", required=True)
    ap.add_argument("--gold-version", type=int, required=True)
    ap.add_argument("--include-ne-q", action="store_true",
                    help="NE_Q を NE に含めて数える（論文に合わせるなら通常OFF）")
    args = ap.parse_args()

    s3 = boto3.client("s3")
    gold = args.gold_s3_prefix.rstrip("/")
    gv = args.gold_version

    def load(table):
        return s3_read_parquet(s3, f"{gold}/v{gv}/corpus=cejc/table={table}/part-00000.parquet")

    seg = load("segments")
    pairs = load("pairs")

    # ---- dyad conversations ----
    nspk = seg.groupby("conversation_id")["speaker_id"].nunique()
    dyad_convs = set(nspk[nspk == 2].index.tolist())

    seg_dyad = seg[seg["conversation_id"].isin(dyad_convs)].copy()

    # approx hours by conversation span
    # (rough; overlap etc. ignored)
    conv_span = seg_dyad.groupby("conversation_id").agg(
        t0=("start_time", "min"),
        t1=("end_time", "max"),
    )
    conv_span["dur_sec"] = (pd.to_numeric(conv_span["t1"], errors="coerce") - pd.to_numeric(conv_span["t0"], errors="coerce")).clip(lower=0)
    hours_approx = float(conv_span["dur_sec"].sum() / 3600.0)

    # ---- utterance counts (YO / NE excluding YONE) ----
    seg_dyad["sfp_group_u"] = seg_dyad["sfp_group"].astype(str).str.upper()

    yo_seg = seg_dyad[seg_dyad["sfp_group_u"] == "YO"].copy()
    yo_seg = yo_seg[~yo_seg["text"].map(is_yone)]

    ne_groups = ["NE"] + (["NE_Q"] if args.include_ne_q else [])
    ne_seg = seg_dyad[seg_dyad["sfp_group_u"].isin(ne_groups)].copy()
    ne_seg = ne_seg[~ne_seg["text"].map(is_yone)]

    # ---- pairs: speaker different, YO/NE, exclude YONE ----
    pairs_dyad = pairs[pairs["conversation_id"].isin(dyad_convs)].copy()
    pairs_dyad["prev_sfp_group_u"] = pairs_dyad["prev_sfp_group"].astype(str).str.upper()

    pairs_dyad = pairs_dyad[pairs_dyad["prev_speaker_id"] != pairs_dyad["resp_speaker_id"]]

    yo_pairs = pairs_dyad[pairs_dyad["prev_sfp_group_u"] == "YO"].copy()
    yo_pairs = yo_pairs[~yo_pairs["prev_text"].map(is_yone)]

    ne_pairs = pairs_dyad[pairs_dyad["prev_sfp_group_u"].isin(ne_groups)].copy()
    ne_pairs = ne_pairs[~ne_pairs["prev_text"].map(is_yone)]

    # normalize response first token
    yo_pairs["resp_tok"] = yo_pairs["resp_first_token"].map(norm_token)
    ne_pairs["resp_tok"] = ne_pairs["resp_first_token"].map(norm_token)

    def tok_stats(df: pd.DataFrame):
        n = int(len(df))
        vc = df["resp_tok"].value_counts(dropna=True)
        top10 = vc.head(10)
        ent = entropy_log2(df["resp_tok"])
        # rates for うん/そう/はい
        counts = {t: int((df["resp_tok"] == t).sum()) for t in TOK_TARGET}
        rates = {t: (counts[t] / n if n else None) for t in TOK_TARGET}
        return n, ent, counts, rates, top10

    yo_n, yo_ent, yo_counts, yo_rates, yo_top10 = tok_stats(yo_pairs)
    ne_n, ne_ent, ne_counts, ne_rates, ne_top10 = tok_stats(ne_pairs)

    # ---- print summary ----
    print("\n=== B-1_168 approximate replication from v13 gold (CEJC) ===")
    print(f"[dyad] conversations: {len(dyad_convs)} (paper≈{PAPER_ANCHOR['dyad_conversations']})")
    print(f"[dyad] approx hours:  {hours_approx:.2f} (paper≈{PAPER_ANCHOR['hours_approx']})")

    print("\n[utterances in dyad, excluding YONE]")
    print(f"YO utt: {len(yo_seg)} (paper {PAPER_ANCHOR['yo_utt']})")
    print(f"NE utt: {len(ne_seg)} (paper {PAPER_ANCHOR['ne_utt']})  include_ne_q={args.include_ne_q}")

    print("\n[pairs in dyad, speaker!=speaker, excluding YONE]")
    print(f"YO pairs: {yo_n}")
    print(f"NE pairs: {ne_n}  include_ne_q={args.include_ne_q}")

    def show_rates(tag, counts, rates, paper_prefix):
        print(f"\n[{tag}] follow-token rates (using resp_first_token; paper uses short-units)")
        for t in ["うん","そう","はい"]:
            c = counts.get(t, 0)
            r = rates.get(t, None)
            paper_c = PAPER_ANCHOR.get(f"{paper_prefix}_follow_{'un' if t=='うん' else 'sou' if t=='そう' else 'hai'}", None)
            if r is None:
                print(f"  {t}: {c} (rate -)  paper_count={paper_c}")
            else:
                print(f"  {t}: {c} (rate {r*100:.2f}%)  paper_count={paper_c}")

    show_rates("YO", yo_counts, yo_rates, "yo")
    show_rates("NE", ne_counts, ne_rates, "ne")

    print("\n[entropy] (log2) of resp_first_token distribution")
    print(f"YO entropy: {yo_ent}")
    print(f"NE entropy: {ne_ent}")
    print("  ※論文は『後続する短単位(語彙素レベル)』のエントロピーなので、絶対値は一致しない可能性が高い。相対傾向を見る。")

    print("\n[top10 resp_first_token]")
    print("\nYO top10:")
    print(yo_top10.to_string())
    print("\nNE top10:")
    print(ne_top10.to_string())

if __name__ == "__main__":
    main()
