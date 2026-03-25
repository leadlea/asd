import json
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

def promote_metrics(rec: dict):
    # parquetに pg/ix/fill のdict列がある場合、PG_/IX_/FILL_ をトップレベルに昇格
    for k in ["pg", "ix", "fill"]:
        obj = rec.get(k)
        if isinstance(obj, dict):
            for kk, vv in obj.items():
                if isinstance(kk, str) and kk.startswith(("PG_", "IX_", "FILL_")):
                    rec[kk] = vv
    return rec

def to_jsonable(x):
    """Convert numpy/pandas objects into JSON-serializable Python types."""
    if x is None:
        return None

    # pandas missing
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass

    # numpy scalars
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)

    # numpy arrays
    if isinstance(x, np.ndarray):
        return [to_jsonable(v) for v in x.tolist()]

    # pandas Timestamp / Timedelta
    if isinstance(x, (pd.Timestamp,)):
        # keep ISO string
        return x.isoformat()
    if isinstance(x, (pd.Timedelta,)):
        return str(x)

    # dict / list / tuple
    if isinstance(x, dict):
        return {str(k): to_jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [to_jsonable(v) for v in x]

    # bytes
    if isinstance(x, (bytes, bytearray)):
        try:
            return x.decode("utf-8")
        except Exception:
            return x.hex()

    # fallback: plain Python primitives are fine
    return x

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="outp", required=True)
    args = ap.parse_args()

    df = pd.read_parquet(args.inp)
    outp = Path(args.outp)
    outp.parent.mkdir(parents=True, exist_ok=True)

    with outp.open("w", encoding="utf-8") as f:
        for rec in df.to_dict(orient="records"):
            rec = promote_metrics(rec)
            rec = to_jsonable(rec)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print("wrote:", outp, "rows:", len(df))

if __name__ == "__main__":
    main()
