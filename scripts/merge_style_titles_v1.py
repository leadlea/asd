#!/usr/bin/env python3
from __future__ import annotations

import argparse
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

STYLE_COLS = [
    "style_title",
    "style_title_reason",
    "style_title_confidence",
    "style_title_prompt_features_used_json",
    "style_title_model_id",
    "style_title_created_at",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, type=Path)
    ap.add_argument("--sidecar", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()

    base = pd.read_parquet(args.base)
    side = pd.read_parquet(args.sidecar)

    key_cols = [c for c in PREFERRED_KEY_COLS if c in base.columns and c in side.columns]
    if not key_cols:
        raise SystemExit("No common key columns found between base and sidecar")

    dup_count = len(side) - len(side[key_cols].drop_duplicates())
    if dup_count:
        raise SystemExit(f"Sidecar has duplicate keys: {dup_count}")

    keep_cols = key_cols + [c for c in STYLE_COLS if c in side.columns]
    merged = base.merge(side[keep_cols], on=key_cols, how="left", validate="one_to_one")

    if len(merged) != len(base):
        raise SystemExit("Row count changed after merge; aborting")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(args.output, index=False)
    print(f"DONE: wrote {len(merged)} rows -> {args.output}")
    print(f"key_cols={key_cols}")
    for c in STYLE_COLS:
        if c in merged.columns:
            print(f"{c}: non_null={merged[c].notna().sum()}")


if __name__ == "__main__":
    main()
