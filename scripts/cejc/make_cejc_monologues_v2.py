import argparse, glob, os, re
import pandas as pd

def strip_balanced(text: str, open_ch: str, close_ch: str) -> str:
    """Remove balanced segments including nested ones, e.g., ( ... ( ... ) ... )."""
    if not text:
        return ""
    out = []
    depth = 0
    for ch in text:
        if ch == open_ch:
            depth += 1
            continue
        if ch == close_ch and depth > 0:
            depth -= 1
            continue
        if depth == 0:
            out.append(ch)
    return "".join(out)

def clean_cejc_text(s: str) -> str:
    if s is None:
        return ""
    t = str(s)

    # 1) remove CEJC annotation chunks in () and （） with nesting support
    t = strip_balanced(t, "(", ")")
    t = strip_balanced(t, "（", "）")

    # 2) normalize whitespace
    t = re.sub(r"\s+", " ", t).strip()

    # 3) drop common leftovers
    # (sometimes single symbols remain)
    t = t.replace("　", " ").strip()
    return t

def is_valid_utt(t: str) -> bool:
    if not t:
        return False
    # keep if contains at least one of these
    return bool(re.search(r"[ぁ-んァ-ン一-龥A-Za-z0-9]", t))

def read_ids(path: str):
    if not path:
        return None
    ids = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            x = line.strip()
            if not x:
                continue
            ids.append(x)
    return ids

def load_utterances(paths, ids=None):
    # Prefer pyarrow.dataset filtering if available (fast when ids list is small)
    try:
        import pyarrow.dataset as ds
        if ids:
            dataset = ds.dataset(paths, format="parquet")
            filt = ds.field("conversation_id").isin(ids)
            table = dataset.to_table(filter=filt)
            return table.to_pandas()
    except Exception:
        pass

    # Fallback: read all then filter
    if len(paths) == 1 and os.path.isfile(paths[0]):
        df = pd.read_parquet(paths[0])
    else:
        dfs = [pd.read_parquet(p) for p in paths]
        df = pd.concat(dfs, ignore_index=True)
    if ids:
        df = df[df["conversation_id"].isin(ids)].copy()
    return df

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--utterances_glob", required=True, help="e.g. artifacts/_tmp_utt/cejc_utterances/part-*.parquet")
    ap.add_argument("--id_list", default="", help="txt: one conversation_id per line")
    ap.add_argument("--out", required=True, help="output parquet (conversation_id, speaker_id, text, ...)")
    ap.add_argument("--min_main_share", type=float, default=0.75, help="main speaker share by chars")
    ap.add_argument("--min_main_utts", type=int, default=80)
    ap.add_argument("--min_chars", type=int, default=800)
    ap.add_argument("--unit_type", default="", help="optional filter, e.g. LUU")
    ap.add_argument("--top_preview", type=int, default=30)
    ap.add_argument("--out_preview_tsv", default="", help="optional tsv preview")
    args = ap.parse_args()

    paths = sorted(glob.glob(args.utterances_glob)) if any(x in args.utterances_glob for x in ["*", "?", "["]) else [args.utterances_glob]
    if not paths:
        raise SystemExit(f"no parquet matched: {args.utterances_glob}")

    ids = read_ids(args.id_list) if args.id_list else None

    df = load_utterances(paths, ids=ids)
    need = ["conversation_id", "speaker_id", "start_time", "end_time", "text"]
    for c in need:
        if c not in df.columns:
            raise SystemExit(f"missing column: {c} (have: {list(df.columns)})")

    if args.unit_type:
        if "unit_type" not in df.columns:
            raise SystemExit("unit_type filter requested, but column unit_type not found")
        df = df[df["unit_type"] == args.unit_type].copy()

    # clean + validity
    df["text_clean"] = df["text"].map(clean_cejc_text)
    df["is_valid"] = df["text_clean"].map(is_valid_utt)
    df = df[df["is_valid"]].copy()

    # stats per (conversation, speaker)
    df["n_char"] = df["text_clean"].map(len)
    g = df.groupby(["conversation_id", "speaker_id"], as_index=False).agg(
        n_utt=("utterance_id", "count"),
        n_char=("n_char", "sum"),
        t0=("start_time", "min"),
        t1=("end_time", "max"),
    )

    # total per conversation
    tot = g.groupby("conversation_id", as_index=False).agg(
        total_utt=("n_utt", "sum"),
        total_char=("n_char", "sum"),
        conv_t0=("t0", "min"),
        conv_t1=("t1", "max"),
        speaker_n=("speaker_id", "nunique"),
    )

    # choose main speaker by n_char then n_utt
    g2 = g.merge(tot, on="conversation_id", how="left")
    g2 = g2.sort_values(["conversation_id", "n_char", "n_utt"], ascending=[True, False, False])
    main = g2.groupby("conversation_id", as_index=False).head(1).copy()
    main["main_share"] = (main["n_char"] / main["total_char"]).fillna(0.0)
    main["duration_sec"] = (main["conv_t1"] - main["conv_t0"]).fillna(0.0)

    # filter for diary-like monologues
    keep = main[
        (main["main_share"] >= args.min_main_share) &
        (main["n_utt"] >= args.min_main_utts) &
        (main["n_char"] >= args.min_chars)
    ].copy()

    if len(keep) == 0:
        print("WARNING: no conversation passed filters. Try relaxing thresholds.")
        print("main_share range:", main["main_share"].min(), main["main_share"].max())
        print("n_utt range:", main["n_utt"].min(), main["n_utt"].max())
        print("n_char range:", main["n_char"].min(), main["n_char"].max())

    # build monologue text for main speaker
    keep_ids = set(keep["conversation_id"].tolist())
    dfk = df[df["conversation_id"].isin(keep_ids)].copy()
    dfk = dfk.merge(keep[["conversation_id", "speaker_id"]], on=["conversation_id", "speaker_id"], how="inner")
    dfk = dfk.sort_values(["conversation_id", "speaker_id", "start_time", "utterance_id"])

    # join with newline (transcript-like)
    mono = dfk.groupby(["conversation_id", "speaker_id"], as_index=False).agg(
        text=("text_clean", lambda xs: "\n".join([x for x in xs if x]))
    )

    out = keep.rename(columns={"n_utt": "n_main_utt"}).merge(mono, on=["conversation_id", "speaker_id"], how="left")
    out = out.rename(columns={"total_utt": "n_total_utt"})
    out = out[[
        "conversation_id", "speaker_id", "text",
        "main_share", "n_main_utt", "n_total_utt", "n_char",
        "speaker_n", "duration_sec"
    ]].sort_values(["main_share", "n_char", "n_main_utt"], ascending=False)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    out.to_parquet(args.out, index=False)
    print("OK wrote:", args.out, "rows=", len(out), "cols=", len(out.columns))

    # preview
    prev = out.head(args.top_preview)[["conversation_id","speaker_id","main_share","n_main_utt","n_total_utt","n_char","speaker_n","duration_sec"]]
    print(prev.to_string(index=False))

    if args.out_preview_tsv:
        os.makedirs(os.path.dirname(args.out_preview_tsv) or ".", exist_ok=True)
        prev.to_csv(args.out_preview_tsv, sep="\t", index=False)
        print("OK wrote:", args.out_preview_tsv)

if __name__ == "__main__":
    main()
