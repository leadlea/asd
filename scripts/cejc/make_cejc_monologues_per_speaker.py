import argparse, os, re
import pandas as pd

def clean_text(t: str) -> str:
    t = "" if t is None else str(t)
    # 必要最低限の整形（後で強化OK）
    t = re.sub(r"\s+", " ", t).strip()
    return t

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids_txt", required=True)
    ap.add_argument("--utterances_parquet", required=True)
    ap.add_argument("--out_parquet", required=True)
    ap.add_argument("--min_total_sec", type=float, default=20.0)  # まずは緩め推奨
    args = ap.parse_args()

    ids = [l.strip() for l in open(args.ids_txt, encoding="utf-8") if l.strip()]
    ids = set(ids)

    utt = pd.read_parquet(args.utterances_parquet)
    sub = utt[utt["conversation_id"].isin(ids)].copy()

    sub["dur"] = (sub["end_time"].astype(float) - sub["start_time"].astype(float)).clip(lower=0.0)
    sub["text_clean"] = sub["text"].map(clean_text)
    sub = sub[sub["text_clean"] != ""].copy()
    sub = sub.sort_values(["conversation_id","speaker_id","start_time"])

    # speakerごとの総発話時間
    sp = (sub.groupby(["conversation_id","speaker_id"])["dur"].sum()
            .reset_index().rename(columns={"dur":"total_dur"}))
    sp = sp[sp["total_dur"] >= args.min_total_sec].copy()

    keep = set(zip(sp["conversation_id"], sp["speaker_id"]))
    sub = sub[sub.apply(lambda r: (r["conversation_id"], r["speaker_id"]) in keep, axis=1)].copy()

    mono = (sub.groupby(["conversation_id","speaker_id"])["text_clean"]
              .apply(lambda s: "\n".join(s.tolist()))
              .reset_index().rename(columns={"text_clean":"text"}))

    mono = mono.merge(sp, on=["conversation_id","speaker_id"], how="left")
    os.makedirs(os.path.dirname(args.out_parquet), exist_ok=True)
    mono.to_parquet(args.out_parquet, index=False)

    print("OK:", args.out_parquet)
    print("rows (conv×speaker):", len(mono), "unique conv:", mono["conversation_id"].nunique())
    print("total_dur sec summary:")
    print(mono["total_dur"].describe().to_string())
    print("\nhead:")
    print(mono.head(10).to_string(index=False))

if __name__ == "__main__":
    main()
