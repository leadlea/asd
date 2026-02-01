#!/usr/bin/env python3
import argparse
import io
from urllib.parse import urlparse

import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def parse_s3(uri: str):
    u = urlparse(uri)
    assert u.scheme == "s3"
    return u.netloc, u.path.lstrip("/")


def s3_read_parquet(s3, uri: str) -> pd.DataFrame:
    b, k = parse_s3(uri)
    obj = s3.get_object(Bucket=b, Key=k)
    buf = io.BytesIO(obj["Body"].read())
    return pq.read_table(buf).to_pandas()


def s3_write_parquet(s3, df: pd.DataFrame, uri: str, kms_key_arn: str | None):
    b, k = parse_s3(uri)
    table = pa.Table.from_pandas(df, preserve_index=False)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    extra = {}
    if kms_key_arn:
        extra["ServerSideEncryption"] = "aws:kms"
        extra["SSEKMSKeyId"] = kms_key_arn
    s3.put_object(Bucket=b, Key=k, Body=buf.getvalue(), **extra)


def s3_write_csv(s3, df: pd.DataFrame, uri: str, kms_key_arn: str | None):
    b, k = parse_s3(uri)
    body = df.to_csv(index=False)
    extra = {"ContentType": "text/csv"}
    if kms_key_arn:
        extra["ServerSideEncryption"] = "aws:kms"
        extra["SSEKMSKeyId"] = kms_key_arn
    s3.put_object(Bucket=b, Key=k, Body=body.encode("utf-8"), **extra)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold-s3-prefix", required=True)
    ap.add_argument("--analysis-s3-prefix", required=True)
    ap.add_argument("--gold-version", type=int, required=True)
    ap.add_argument("--kms-key-arn", default=None)
    ap.add_argument("--dataset", default="cejc_dyad", choices=["cejc_all","cejc_dyad","csj_all","csj_dialog"])
    ap.add_argument("--min-ne-events", type=int, default=20)
    ap.add_argument("--k-per-speaker", type=int, default=3, help="examples per (conversation_id, speaker_id)")
    args = ap.parse_args()

    s3 = boto3.client("s3")
    gold = args.gold_s3_prefix.rstrip("/")
    ana  = args.analysis_s3_prefix.rstrip("/")
    gv   = args.gold_version

    corpus = "cejc" if args.dataset.startswith("cejc") else "csj"

    # Load gold tables
    m = s3_read_parquet(s3, f"{gold}/v{gv}/corpus={corpus}/table=metrics_resp/part-00000.parquet")
    p = s3_read_parquet(s3, f"{gold}/v{gv}/corpus={corpus}/table=pairs/part-00000.parquet")
    s = s3_read_parquet(s3, f"{gold}/v{gv}/corpus={corpus}/table=segments/part-00000.parquet")

    # speaker count per conversation (subset split)
    nspk = s.groupby("conversation_id")["speaker_id"].nunique().rename("n_speakers")
    m = m.merge(nspk.reset_index(), on="conversation_id", how="left")

    if args.dataset.endswith("dyad"):
        m = m[m["n_speakers"] == 2].copy()
    if args.dataset.endswith("dialog"):
        m = m[m["n_speakers"] >= 2].copy()

    # Reliability by metrics_resp
    m["n_pairs_after_NE"] = pd.to_numeric(m["n_pairs_after_NE"], errors="coerce").fillna(0).astype(int)
    reliable_keys = set(
        tuple(x) for x in m.loc[m["n_pairs_after_NE"] >= args.min_ne_events, ["conversation_id","speaker_id"]].itertuples(index=False, name=None)
    )

    # Build lookup for speaker metrics
    m_key = m.set_index(["conversation_id","speaker_id"])[["RESP_NE_AIZUCHI_RATE","n_pairs_after_NE"]].copy()

    # Filter candidate pairs: prev_sfp_group in {NE, NE_Q}
    sfpcol = "prev_sfp_group"
    p2 = p[p[sfpcol].astype(str).str.upper().isin(["NE","NE_Q"])].copy()

    # helper: collect examples for a key
    def collect_examples(keys, prefer_aizuchi: bool | None):
        rows = []
        for conv_id, spk in keys:
            df = p2[(p2["conversation_id"] == conv_id) & (p2["resp_speaker_id"] == spk)].copy()
            if len(df) == 0:
                continue
            if prefer_aizuchi is True:
                dfp = df[df["resp_is_aizuchi"] == True]
                df = dfp if len(dfp) else df
            if prefer_aizuchi is False:
                dfn = df[df["resp_is_aizuchi"] == False]
                df = dfn if len(dfn) else df
            df = df.sort_values(by=["resp_utt_index","prev_utt_index"]).head(args.k_per_speaker)
            for _, r in df.iterrows():
                met = m_key.loc[(conv_id, spk)] if (conv_id, spk) in m_key.index else None
                rows.append({
                    "dataset": args.dataset,
                    "conversation_id": conv_id,
                    "speaker_id": spk,
                    "RESP_NE_AIZUCHI_RATE": float(met["RESP_NE_AIZUCHI_RATE"]) if met is not None else None,
                    "n_pairs_after_NE": int(met["n_pairs_after_NE"]) if met is not None else None,
                    "prev_utt_index": int(r["prev_utt_index"]),
                    "prev_text": r["prev_text"],
                    "prev_sfp_group": r["prev_sfp_group"],
                    "resp_utt_index": int(r["resp_utt_index"]),
                    "resp_speaker_id": r["resp_speaker_id"],
                    "resp_text": r["resp_text"],
                    "resp_first_token": r["resp_first_token"],
                    "resp_is_aizuchi": bool(r["resp_is_aizuchi"]),
                    "resp_is_question": bool(r["resp_is_question"]),
                })
        return pd.DataFrame(rows)

    # TOP/BOTTOM keys from rank files (analysis output)
    top_uri = f"{ana}/gold=v{gv}/rank_ne_aizuchi/{args.dataset}/top50.parquet"
    bot_uri = f"{ana}/gold=v{gv}/rank_ne_aizuchi/{args.dataset}/bottom50.parquet"
    top = s3_read_parquet(s3, top_uri)
    bot = s3_read_parquet(s3, bot_uri)

    top_keys = [tuple(x) for x in top[["conversation_id","speaker_id"]].itertuples(index=False, name=None)]
    bot_keys = [tuple(x) for x in bot[["conversation_id","speaker_id"]].itertuples(index=False, name=None)]

    # examples_all: one row per reliable key (pick earliest pair)
    all_rows = []
    for conv_id, spk in sorted(reliable_keys):
        df = p2[(p2["conversation_id"] == conv_id) & (p2["resp_speaker_id"] == spk)].copy()
        if len(df) == 0:
            continue
        df = df.sort_values(by=["resp_utt_index","prev_utt_index"]).head(1)
        r = df.iloc[0]
        met = m_key.loc[(conv_id, spk)] if (conv_id, spk) in m_key.index else None
        all_rows.append({
            "dataset": args.dataset,
            "conversation_id": conv_id,
            "speaker_id": spk,
            "RESP_NE_AIZUCHI_RATE": float(met["RESP_NE_AIZUCHI_RATE"]) if met is not None else None,
            "n_pairs_after_NE": int(met["n_pairs_after_NE"]) if met is not None else None,
            "prev_utt_index": int(r["prev_utt_index"]),
            "prev_text": r["prev_text"],
            "prev_sfp_group": r["prev_sfp_group"],
            "resp_utt_index": int(r["resp_utt_index"]),
            "resp_speaker_id": r["resp_speaker_id"],
            "resp_text": r["resp_text"],
            "resp_first_token": r["resp_first_token"],
            "resp_is_aizuchi": bool(r["resp_is_aizuchi"]),
            "resp_is_question": bool(r["resp_is_question"]),
        })
    df_all = pd.DataFrame(all_rows)

    # examples_top/bottom: prefer aizuchi/non-aizuchi
    df_top = collect_examples(top_keys, prefer_aizuchi=True)
    df_bot = collect_examples(bot_keys, prefer_aizuchi=False)

    # Write (v8互換パス)
    base = f"{ana}/gold=v{gv}/examples/ne_aizuchi/{args.dataset}"
    s3_write_csv(s3, df_all, f"{base}/examples_all.csv", args.kms_key_arn)
    s3_write_parquet(s3, df_all, f"{base}/examples_all.parquet", args.kms_key_arn)

    s3_write_csv(s3, df_top, f"{base}/examples_top.csv", args.kms_key_arn)
    s3_write_parquet(s3, df_top, f"{base}/examples_top.parquet", args.kms_key_arn)

    s3_write_csv(s3, df_bot, f"{base}/examples_bottom.csv", args.kms_key_arn)
    s3_write_parquet(s3, df_bot, f"{base}/examples_bottom.parquet", args.kms_key_arn)

    # 引き継ぎ書の “examples_all/top/bottom” も同時に作る（代表として dataset の top/bottom をコピー）
    base2 = f"{ana}/gold=v{gv}/examples_all"
    s3_write_csv(s3, df_top, f"{base2}/top.csv", args.kms_key_arn)
    s3_write_parquet(s3, df_top, f"{base2}/top.parquet", args.kms_key_arn)
    s3_write_csv(s3, df_bot, f"{base2}/bottom.csv", args.kms_key_arn)
    s3_write_parquet(s3, df_bot, f"{base2}/bottom.parquet", args.kms_key_arn)

    print("[OK] wrote examples to:", base, "and", base2)

if __name__ == "__main__":
    main()
