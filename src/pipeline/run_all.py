#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse, os, pandas as pd

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prag_csv", required=True)
    ap.add_argument("--pros_csv", required=False, default=None)
    ap.add_argument("--meta_csv", required=True)
    ap.add_argument("--out_csv", required=True)
    args = ap.parse_args()

    prag = pd.read_csv(args.prag_csv)
    pros = pd.read_csv(args.pros_csv) if args.pros_csv and os.path.exists(args.pros_csv) else pd.DataFrame({"file_id":[]})
    meta = pd.read_csv(args.meta_csv)
    df = prag.merge(pros, on="file_id", how="left").merge(meta, on="file_id", how="left")
    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)
    df.to_csv(args.out_csv, index=False)
    print(f"merged -> {args.out_csv}")

if __name__ == "__main__":
    main()
