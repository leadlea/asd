import json, argparse, math
from pathlib import Path

KEYS = ["PG_overlap_rate", "PG_resp_overlap_rate"]

def is_num(x):
    if x is None:
        return False
    try:
        return not (isinstance(x, float) and math.isnan(x))
    except Exception:
        return True

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--in_jsonl", required=True)
    ap.add_argument("--out_jsonl", required=True)
    ap.add_argument("--min_n", type=int, default=10)
    args=ap.parse_args()

    rows=[json.loads(x) for x in Path(args.in_jsonl).read_text(encoding="utf-8").splitlines() if x.strip()]

    # datasetごとに「全0」か判定
    flag = {}  # (dataset,key)->bool
    datasets=sorted({r.get("dataset") for r in rows})
    for ds in datasets:
        for k in KEYS:
            vals=[]
            for r in rows:
                if r.get("dataset")!=ds:
                    continue
                v=r.get(k)
                if is_num(v):
                    vals.append(float(v))
            if len(vals) >= args.min_n and min(vals)==0.0 and max(vals)==0.0:
                flag[(ds,k)] = True

    outp=Path(args.out_jsonl)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with outp.open("w", encoding="utf-8") as f:
        for r in rows:
            ds=r.get("dataset")
            for k in KEYS:
                if flag.get((ds,k), False) and r.get(k)==0:
                    r[k]=None
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("flags:", {f"{k[0]}::{k[1]}": v for k,v in flag.items()})
    print("wrote:", outp, "rows:", len(rows))

if __name__=="__main__":
    main()
