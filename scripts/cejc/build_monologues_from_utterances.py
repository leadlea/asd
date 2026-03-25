import argparse, re
import pandas as pd

TAG_RE = re.compile(r"\((?:L|D|U|F|B|S|R|X)(?:\s[^)]*)?\)")  # (L ...), (D ...), (U ...), (L) など
WS_RE  = re.compile(r"[ \t]+")

def clean_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = TAG_RE.sub("", s)
    s = WS_RE.sub(" ", s)
    s = s.strip()
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--utterances_parquet", required=True)
    ap.add_argument("--ids_txt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min_utts", type=int, default=40)
    ap.add_argument("--min_chars", type=int, default=800)
    args = ap.parse_args()

    ids = []
    with open(args.ids_txt, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # 先頭カラムに会話IDが来てる想定（tsv/csvでも1列目だけ拾えるように）
            ids.append(line.split()[0])
    ids = sorted(set(ids))
    if not ids:
        raise SystemExit("no ids loaded")

    utt = pd.read_parquet(args.utterances_parquet)
    need_cols = ["conversation_id","speaker_id","start_time","text"]
    for c in need_cols:
        if c not in utt.columns:
            raise SystemExit(f"utterances missing {c}")

    utt = utt[utt["conversation_id"].isin(ids)].copy()
    if len(utt) == 0:
        raise SystemExit("no utterances matched ids")

    utt["text_clean"] = utt["text"].map(clean_text)
    utt = utt[utt["text_clean"].str.len() > 0].copy()

    # speaker別に時系列で連結
    utt = utt.sort_values(["conversation_id","speaker_id","start_time"])
    g = utt.groupby(["conversation_id","speaker_id"], as_index=False)["text_clean"].apply(lambda x: "\n".join(x.tolist()))
    g = g.rename(columns={"text_clean":"text"})

    # 付帯情報
    cnt = utt.groupby(["conversation_id","speaker_id"]).size().reset_index(name="n_utts")
    g = g.merge(cnt, on=["conversation_id","speaker_id"], how="left")
    g["n_chars"] = g["text"].str.len()

    # 閾値でフィルタ
    before = len(g)
    g = g[(g["n_utts"] >= args.min_utts) & (g["n_chars"] >= args.min_chars)].copy()
    after = len(g)

    g["corpus"] = "cejc"
    g.to_parquet(args.out, index=False)

    print(f"OK wrote: {args.out}")
    print(f"conversation_ids in list = {len(ids)}")
    print(f"subjects(before filter) = {before}  subjects(after filter) = {after}")
    print(g.head(5).to_string(index=False))

if __name__ == "__main__":
    main()
