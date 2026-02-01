#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path
import pandas as pd

try:
    import pyarrow.parquet as pq
except ImportError:
    raise SystemExit("pyarrow が必要です: pip install pyarrow")

# ====== TODO: あなたの実ファイルに合わせて修正 ======
PATH_CURATED_UTT = Path("curated/v1/utterances.parquet")
PATH_GOLD_SEG    = Path("gold/v13/segments.parquet")
PATH_GOLD_PAIR   = Path("gold/v13/pairs.parquet")
PATH_GOLD_MSFP   = Path("gold/v13/metrics_sfp.parquet")
PATH_GOLD_MRESP  = Path("gold/v13/metrics_resp.parquet")
PATH_LABELS      = Path("artifacts/phase7/labels/labels_tb500_UIFINAL_FIXED.parquet")
# ===============================================

def schema_cols(p: Path):
    t = pq.read_table(p)
    return t.num_rows, t.column_names, t.schema

def nonnull_rate(series: pd.Series) -> float:
    return float(series.notna().mean())

def main():
    targets = [
        ("curated_utterances", PATH_CURATED_UTT),
        ("gold_segments", PATH_GOLD_SEG),
        ("gold_pairs", PATH_GOLD_PAIR),
        ("gold_metrics_sfp", PATH_GOLD_MSFP),
        ("gold_metrics_resp", PATH_GOLD_MRESP),
    ]

    print("=== (1) Row counts & columns ===")
    for name, p in targets:
        rows, cols, _ = schema_cols(p)
        print(f"[{name}] rows={rows} cols={len(cols)}")
        print("  columns:", cols)

    print("\n=== (2) metrics_resp column check (exact) ===")
    _, cols, _ = schema_cols(PATH_GOLD_MRESP)
    expected = [
        "conversation_id","speaker_id",
        "n_pairs_total","n_pairs_after_NE","n_pairs_after_YO",
        "RESP_NE_AIZUCHI_RATE","RESP_NE_ENTROPY","RESP_YO_ENTROPY"
    ]
    print("expected:", expected)
    print("actual  :", cols)
    print("match   :", cols == expected)

    print("\n=== (3) reliable rows (min_ne_events=20) ===")
    mresp = pq.read_table(PATH_GOLD_MRESP).to_pandas()
    reliable = mresp[mresp["n_pairs_after_NE"] >= 20]
    print("reliable_rows =", len(reliable))

    print("\n=== (5) labels provenance non-null (if exists) ===")
    if PATH_LABELS.exists():
        lab = pq.read_table(PATH_LABELS).to_pandas()
        if "prompt_features_used_json" in lab.columns:
            r = nonnull_rate(lab["prompt_features_used_json"])
            print("prompt_features_used_json nonnull rate =", r, f"({lab['prompt_features_used_json'].notna().sum()}/{len(lab)})")
        else:
            print("labels exists but prompt_features_used_json not found.")
    else:
        print("labels file not found:", PATH_LABELS)

if __name__ == "__main__":
    main()
