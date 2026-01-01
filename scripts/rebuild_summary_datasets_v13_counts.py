#!/usr/bin/env python3
import argparse, io
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


def s3_write_parquet(s3, df: pd.DataFrame, uri: str, kms: str | None):
    b, k = parse_s3(uri)
    table = pa.Table.from_pandas(df, preserve_index=False)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    extra = {}
    if kms:
        extra["ServerSideEncryption"] = "aws:kms"
        extra["SSEKMSKeyId"] = kms
    s3.put_object(Bucket=b, Key=k, Body=buf.getvalue(), **extra)


def s3_write_csv(s3, df: pd.DataFrame, uri: str, kms: str | None):
    b, k = parse_s3(uri)
    extra = {"ContentType": "text/csv"}
    if kms:
        extra["ServerSideEncryption"] = "aws:kms"
        extra["SSEKMSKeyId"] = kms
    s3.put_object(Bucket=b, Key=k, Body=df.to_csv(index=False).encode("utf-8"), **extra)


SFP_GROUPS = ["OTHER","NONLEX","NONE","NE","NE_Q","YO","NO","NA","MON"]

def safe_mean(series):
    if series is None or len(series) == 0:
        return None
    s = pd.to_numeric(series, errors="coerce").dropna()
    return float(s.mean()) if len(s) else None


def build_one_dataset(name: str, segments: pd.DataFrame, pairs: pd.DataFrame, msfp: pd.DataFrame, mresp: pd.DataFrame, conv_ids: set):
    seg = segments[segments["conversation_id"].isin(conv_ids)].copy()
    pr  = pairs[pairs["conversation_id"].isin(conv_ids)].copy()
    sfp = msfp[msfp["conversation_id"].isin(conv_ids)].copy()
    mr  = mresp[mresp["conversation_id"].isin(conv_ids)].copy()

    out = {
        "dataset": name,
        "n_conversations": int(len(conv_ids)),
        "segments_rows": int(len(seg)),
        "pairs_rows": int(len(pr)),
        "metrics_sfp_rows": int(len(sfp)),
        "metrics_resp_rows": int(len(mr)),
        "question_rate": None,
        "aizuchi_rate_in_pairs": None,
    }

    if "is_question" in seg.columns and len(seg):
        out["question_rate"] = float(pd.to_numeric(seg["is_question"], errors="coerce").fillna(False).astype(int).mean())

    if "resp_is_aizuchi" in pr.columns and len(pr):
        out["aizuchi_rate_in_pairs"] = float(pd.to_numeric(pr["resp_is_aizuchi"], errors="coerce").fillna(False).astype(int).mean())

    # sfp ratio from segments.sfp_group
    if "sfp_group" in seg.columns and len(seg):
        vc = seg["sfp_group"].astype(str).str.upper().value_counts(dropna=False)
        denom = float(vc.sum()) if vc.sum() else 1.0
        for g in SFP_GROUPS:
            out[f"sfp_ratio_{g}"] = float(vc.get(g, 0) / denom)
    else:
        for g in SFP_GROUPS:
            out[f"sfp_ratio_{g}"] = None

    # 追加：論文/先生説明で使える NE後あいづち系（平均）
    # metrics_resp から取れる列があれば入れる（A4で使えるように）
    for c in ["RESP_NE_AIZUCHI_RATE","RESP_NE_ENTROPY","RESP_YO_ENTROPY","n_pairs_after_NE","n_pairs_total"]:
        out[c] = safe_mean(mr[c]) if c in mr.columns else None

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold-s3-prefix", required=True)
    ap.add_argument("--gold-version", type=int, required=True)
    ap.add_argument("--analysis-s3-prefix", required=True)
    ap.add_argument("--kms-key-arn", default=None)
    args = ap.parse_args()

    s3 = boto3.client("s3")
    gold = args.gold_s3_prefix.rstrip("/")
    ana  = args.analysis_s3_prefix.rstrip("/")
    gv   = args.gold_version

    def load(corpus, table):
        return s3_read_parquet(s3, f"{gold}/v{gv}/corpus={corpus}/table={table}/part-00000.parquet")

    # load gold tables
    seg_cejc = load("cejc","segments")
    pr_cejc  = load("cejc","pairs")
    msfp_cejc = load("cejc","metrics_sfp")
    mr_cejc   = load("cejc","metrics_resp")

    seg_csj = load("csj","segments")
    pr_csj  = load("csj","pairs")
    msfp_csj = load("csj","metrics_sfp")
    mr_csj   = load("csj","metrics_resp")

    # conversation -> n_speakers
    nspk_cejc = seg_cejc.groupby("conversation_id")["speaker_id"].nunique()
    nspk_csj  = seg_csj.groupby("conversation_id")["speaker_id"].nunique()

    cejc_all_conv   = set(nspk_cejc.index.tolist())
    cejc_dyad_conv  = set(nspk_cejc[nspk_cejc == 2].index.tolist())
    csj_all_conv    = set(nspk_csj.index.tolist())
    csj_dialog_conv = set(nspk_csj[nspk_csj >= 2].index.tolist())

    rows = []
    rows.append(build_one_dataset("cejc_all",   seg_cejc, pr_cejc, msfp_cejc, mr_cejc, cejc_all_conv))
    rows.append(build_one_dataset("cejc_dyad",  seg_cejc, pr_cejc, msfp_cejc, mr_cejc, cejc_dyad_conv))
    rows.append(build_one_dataset("csj_all",    seg_csj,  pr_csj,  msfp_csj,  mr_csj,  csj_all_conv))
    rows.append(build_one_dataset("csj_dialog", seg_csj,  pr_csj,  msfp_csj,  mr_csj,  csj_dialog_conv))

    df = pd.DataFrame(rows)

    # 既存スキーマ（あなたのCSVヘッダ）に寄せつつ、追加列は後ろに残す
    base_cols = [
        "dataset","n_conversations","segments_rows","pairs_rows","metrics_sfp_rows","metrics_resp_rows",
        "question_rate","aizuchi_rate_in_pairs",
    ] + [f"sfp_ratio_{g}" for g in SFP_GROUPS]
    extra_cols = [c for c in df.columns if c not in base_cols]
    df = df[base_cols + extra_cols]

    out_base = f"{ana}/gold=v{gv}/summary"
    s3_write_csv(s3, df, f"{out_base}/summary_datasets.csv", args.kms_key_arn)
    s3_write_parquet(s3, df, f"{out_base}/summary_datasets.parquet", args.kms_key_arn)

    print("[OK] rebuilt:", f"{out_base}/summary_datasets.(csv|parquet)")

if __name__ == "__main__":
    main()
