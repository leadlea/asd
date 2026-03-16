#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

PREFERRED_KEY_COLS = [
    "dataset",
    "speaker_id",
    "conversation_id",
    "conv_id",
    "example_id",
    "row_id",
    "id",
]

IMPORTANT_COLS = [
    "summary",
    "labels_json",
    "primary_label",
    "atypicality_v0",
    "prompt_features_used_json",
    "pg",
    "ix",
    "fill",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_parquet", type=Path)
    ap.add_argument("--head", type=int, default=3)
    args = ap.parse_args()

    df = pd.read_parquet(args.input_parquet)
    print(f"path={args.input_parquet}")
    print(f"rows={len(df)} cols={len(df.columns)}")
    print("\n== columns ==")
    for c in df.columns:
        print(c)

    key_cols = [c for c in PREFERRED_KEY_COLS if c in df.columns]
    important_cols = [c for c in IMPORTANT_COLS if c in df.columns]
    print("\n== preferred key columns found ==")
    print(json.dumps(key_cols, ensure_ascii=False, indent=2))
    print("\n== important feature columns found ==")
    print(json.dumps(important_cols, ensure_ascii=False, indent=2))

    if key_cols:
        print("\n== key uniqueness checks ==")
        for i in range(1, len(key_cols) + 1):
            cols = key_cols[:i]
            nunique = len(df[cols].drop_duplicates())
            print(f"{cols}: unique_rows={nunique} / total={len(df)}")

    sample_cols = key_cols + important_cols
    sample_cols = list(dict.fromkeys([c for c in sample_cols if c in df.columns]))
    if not sample_cols:
        sample_cols = list(df.columns[: min(10, len(df.columns))])

    print("\n== sample rows ==")
    print(df[sample_cols].head(args.head).to_json(orient="records", force_ascii=False, indent=2))


if __name__ == "__main__":
    main()
