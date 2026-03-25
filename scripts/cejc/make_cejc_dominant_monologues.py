import argparse, os, re
import pandas as pd

def clean_text(t: str) -> str:
    t = "" if t is None else str(t)
    # 超雑な注記除去（必要なら後で強化）
    t = re.sub(r"\(L[^)]*\)", "", t)
    t = re.sub(r"\(D[^)]*\)", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids_txt", required=True)
    ap.add_argument("--utterances_parquet", required=True)
    ap.add_argument("--out_parquet", required=True)
    ap.add_argument("--min_dominance", type=float, default=0.80)  # 0.70/0.80/0.90 で感度分析可
    ap.add_argument("--min_total_sec", type=float, default=60.0)  # 短すぎ会話を落とす
    args = ap.parse_args()

    ids = [l.strip() for l in open(args.ids_txt, encoding="utf-8") if l.strip()]
    ids = set(ids)
    utt = pd.read_parquet(args.utterances_parquet)
    sub = utt[utt["conversation_id"].isin(ids)].copy()

    # duration（秒）
    sub["dur"] = (sub["end_time"].astype(float) - sub["start_time"].astype(float)).clip(lower=0.0)

    # 会話ごとの speaker dur 集計
    sp = (sub.groupby(["conversation_id","speaker_id"])["dur"].sum().reset_index())
    total = sp.groupby("conversation_id")["dur"].sum().rename("total_dur").reset_index()
    sp = sp.merge(total, on="conversation_id", how="left")
    sp["ratio"] = sp["dur"] / sp["total_dur"].replace({0: pd.NA})

    # 主話者（ratio最大）
    idx = sp.groupby("conversation_id")["ratio"].idxmax()
    main_sp = sp.loc[idx].copy()
    main_sp = main_sp[main_sp["total_dur"] >= args.min_total_sec].copy()
    main_sp = main_sp[main_sp["ratio"] >= args.min_dominance].copy()

    keep = set(zip(main_sp["conversation_id"], main_sp["speaker_id"]))

    # 主話者の発話だけ抽出→結合
    sub = sub[sub.apply(lambda r: (r["conversation_id"], r["speaker_id"]) in keep, axis=1)].copy()
    sub["text_clean"] = sub["text"].map(clean_text)
    sub = sub[sub["text_clean"] != ""].copy()
    sub = sub.sort_values(["conversation_id","speaker_id","start_time"])

    mono = (sub.groupby(["conversation_id","speaker_id"])["text_clean"]
              .apply(lambda s: "\n".join(s.tolist()))
              .reset_index().rename(columns={"text_clean":"text"}))

    # dominance情報を付加（論文の条件差を後で書ける）
    mono = mono.merge(main_sp[["conversation_id","speaker_id","ratio","total_dur","dur"]],
                      on=["conversation_id","speaker_id"], how="left")\
               .rename(columns={"ratio":"dominance","dur":"main_dur"})

    os.makedirs(os.path.dirname(args.out_parquet), exist_ok=True)
    mono.to_parquet(args.out_parquet, index=False)

    print("OK:", args.out_parquet)
    print("kept conversations:", mono["conversation_id"].nunique(),
          "rows (conv×speaker):", len(mono))
    print("dominance summary:")
    print(mono["dominance"].describe().to_string())
    print("\nhead:")
    print(mono.head(10).to_string(index=False))

if __name__ == "__main__":
    main()
