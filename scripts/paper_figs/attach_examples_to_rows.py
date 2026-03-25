import json
import argparse
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

def norm_dataset(ds: str):
    s = (ds or "").lower()
    if "cejc" in s: return "cejc"
    if "csj" in s: return "csj"
    return s

def mk_key(conv, spk):
    if conv is None or spk is None: 
        return None
    return f"{str(conv)}:{str(spk)}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows_parquet", required=True)
    ap.add_argument("--examples", nargs="+", required=True)
    ap.add_argument("--out_jsonl", required=True)
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()

    # rows
    rows = pd.read_parquet(args.rows_parquet)
    if "dataset" not in rows.columns or "speaker_id" not in rows.columns:
        raise RuntimeError("rows_parquet must contain dataset and speaker_id")
    rows["dataset_norm"] = rows["dataset"].astype(str).map(norm_dataset)
    # rows speaker_id はすでに conv:role 形式のはず
    rows["speaker_key"] = rows["speaker_id"].astype(str)

    # build example map: (dataset_norm, speaker_key) -> list[examples]
    mp = {}
    for p in args.examples:
        pf = pq.ParquetFile(p)
        cols = pf.schema.names

        # 必須列（あなたの出力から確定）
        need = ["dataset","conversation_id","speaker_id","resp_speaker_id","prev_text","resp_text","prev_utt_index","resp_utt_index"]
        use = [c for c in need if c in cols]
        df = pf.read(columns=use).to_pandas()

        df["dataset_norm"] = df["dataset"].astype(str).map(norm_dataset)

        # prev側 / resp側どちらのspeakerにも紐付ける（とりあえず確実に付ける）
        df["prev_key"] = [mk_key(c,s) for c,s in zip(df["conversation_id"], df["speaker_id"])]
        df["resp_key"] = [mk_key(c,s) for c,s in zip(df["conversation_id"], df["resp_speaker_id"])]

        # evidence object
        def mk_ex(r, side):
            eid = f'{r["conversation_id"]}:{int(r["prev_utt_index"])}->{int(r["resp_utt_index"])}'
            return {
                "example_id": eid,
                "side": side,  # "prev" or "resp"
                "prev_text": str(r.get("prev_text",""))[:300],
                "resp_text": str(r.get("resp_text",""))[:300],
            }

        # group add
        for _, r in df.iterrows():
            ds = r["dataset_norm"]
            pk = r["prev_key"]
            rk = r["resp_key"]
            ex_prev = mk_ex(r, "prev")
            ex_resp = mk_ex(r, "resp")
            if pk:
                mp.setdefault((ds, pk), []).append(ex_prev)
            if rk:
                mp.setdefault((ds, rk), []).append(ex_resp)

    # cap to k per key（先頭kでOK。後で “選び方” は改善できる）
    for kkey in list(mp.keys()):
        mp[kkey] = mp[kkey][:args.k]

    outp = Path(args.out_jsonl)
    outp.parent.mkdir(parents=True, exist_ok=True)

    attached = 0
    with outp.open("w", encoding="utf-8") as f:
        for rec in rows.to_dict(orient="records"):
            key = (rec["dataset_norm"], rec["speaker_key"])
            ex = mp.get(key, [])
            rec["examples"] = ex
            if len(ex) > 0:
                attached += 1
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")

    print("wrote:", outp)
    print("rows:", len(rows))
    print("rows_with_examples:", attached)

if __name__ == "__main__":
    main()
