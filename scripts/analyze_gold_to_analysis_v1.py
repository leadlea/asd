#!/usr/bin/env python3
import argparse
import io
import sys
from urllib.parse import urlparse

import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def parse_s3_uri(uri: str):
    u = urlparse(uri)
    if u.scheme != "s3":
        raise ValueError(f"Not an s3 uri: {uri}")
    return u.netloc, u.path.lstrip("/")




def merge_on_keys(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
    """Left-join right into left using best keys, bringing only non-overlapping columns."""
    keys = [k for k in ["dataset", "conversation_id", "speaker_id"] if k in left.columns and k in right.columns]
    if not keys:
        keys = [k for k in ["conversation_id", "speaker_id"] if k in left.columns and k in right.columns]
    if not keys:
        raise ValueError(f"no join keys. left={list(left.columns)[:30]} right={list(right.columns)[:30]}")

    # bring only columns that don't already exist in left
    add_cols = [c for c in right.columns if c not in keys and c not in left.columns]
    right2 = right[keys + add_cols] if add_cols else right[keys].copy()

    out = left.merge(right2, on=keys, how="left")

    # cleanup legacy suffix columns if any remain
    for suf in ("_pausegap", "_pg"):
        drop = [c for c in out.columns if c.endswith(suf) and c[:-len(suf)] in out.columns]
        if drop:
            out = out.drop(columns=drop)

    return out

def s3_read_parquet(s3_client, uri: str) -> pd.DataFrame:
    bucket, key = parse_s3_uri(uri)
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    body = obj["Body"].read()
    table = pq.read_table(io.BytesIO(body))
    return table.to_pandas()


def s3_write_parquet(s3_client, df: pd.DataFrame, uri: str, kms_key_arn: str | None):
    bucket, key = parse_s3_uri(uri)
    table = pa.Table.from_pandas(df, preserve_index=False)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    extra = {}
    if kms_key_arn:
        extra["ServerSideEncryption"] = "aws:kms"
        extra["SSEKMSKeyId"] = kms_key_arn
    s3_client.put_object(Bucket=bucket, Key=key, Body=buf.getvalue(), **extra)


def s3_write_text(s3_client, text: str, uri: str, kms_key_arn: str | None, content_type="text/plain"):
    bucket, key = parse_s3_uri(uri)
    extra = {"ContentType": content_type}
    if kms_key_arn:
        extra["ServerSideEncryption"] = "aws:kms"
        extra["SSEKMSKeyId"] = kms_key_arn
    s3_client.put_object(Bucket=bucket, Key=key, Body=text.encode("utf-8"), **extra)


def load_templates(s3, out_prefix: str, template_v: int):
    out = out_prefix.rstrip("/")
    templ = {}
    try:
        templ["summary_cols"] = s3_read_parquet(
            s3, f"{out}/gold=v{template_v}/summary/summary_datasets.parquet"
        ).columns.tolist()
    except Exception:
        templ["summary_cols"] = None
    try:
        templ["rank_cols"] = s3_read_parquet(
            s3, f"{out}/gold=v{template_v}/rank_ne_aizuchi/cejc_all/top50.parquet"
        ).columns.tolist()
    except Exception:
        templ["rank_cols"] = None
    return templ


def build_summary_row(df: pd.DataFrame, dataset_name: str, cols_template):
    default_metrics = [
        "rate_NE_valid", "rate_YO_valid", "rate_question",
        "RESP_NE_AIZUCHI_RATE", "RESP_NE_ENTROPY", "RESP_YO_ENTROPY",
    ]
    row = {}

    # Phase4: pause/gap summary cols (dataset-level mean over speaker rows)
    _pg_cols = [
        "total_time","speech_time","speech_ratio","n_segments",
        "pause_mean","pause_p50","pause_p90",
        "overlap_rate",
        "resp_gap_mean","resp_gap_p50","resp_gap_p90",
        "resp_overlap_rate","n_resp_events",
    ]
    for c in _pg_cols:
        if c in df.columns:
            v = df[c].dropna()
            row[f"PG_{c}_mean"] = float(v.mean()) if len(v) else None
    if cols_template:
        label_col = None
        for c in ["dataset", "dataset_id", "dataset_name", "dataset_key", "corpus_subset"]:
            if c in cols_template:
                label_col = c
                break
        row[label_col or "dataset"] = dataset_name

        for c in cols_template:
            if c in row:
                continue
            if c in ["n_rows", "N", "n"]:
                row[c] = int(len(df))
            elif c in df.columns and pd.api.types.is_numeric_dtype(df[c]):
                if c.startswith("n_"):
                    row[c] = float(pd.to_numeric(df[c], errors="coerce").fillna(0.0).sum())
                else:
                    row[c] = float(pd.to_numeric(df[c], errors="coerce").dropna().mean())
            elif c in default_metrics and c in df.columns:
                row[c] = float(pd.to_numeric(df[c], errors="coerce").dropna().mean())
            else:
                row[c] = None
        return pd.DataFrame([row], columns=cols_template)

    # minimal
    row["dataset"] = dataset_name
    row["n_rows"] = int(len(df))
    for m in default_metrics:
        if m in df.columns:
            row[m] = float(pd.to_numeric(df[m], errors="coerce").dropna().mean())
    return pd.DataFrame([row])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold-s3-prefix", required=True)
    ap.add_argument("--gold-version", required=True, type=int)
    ap.add_argument("--out-s3-prefix", required=True)
    ap.add_argument("--kms-key-arn", default=None)
    ap.add_argument("--template-gold-version", type=int, default=8)
    ap.add_argument("--min-ne-events", type=int, default=20, help="reliable threshold by n_pairs_after_NE")
    args = ap.parse_args()

    s3 = boto3.client("s3")
    gold = args.gold_s3_prefix.rstrip("/")
    out = args.out_s3_prefix.rstrip("/")
    gv = args.gold_version

    templ = load_templates(s3, out, args.template_gold_version)
    summary_cols = templ.get("summary_cols")
    rank_cols = templ.get("rank_cols")

    def load(corpus, table):
        return s3_read_parquet(s3, f"{gold}/v{gv}/corpus={corpus}/table={table}/part-00000.parquet")

    # load gold
    m_cejc = load("cejc", "metrics_resp")
    m_cejc_pg = load("cejc", "metrics_pausegap")
    m_cejc = merge_on_keys(m_cejc, m_cejc_pg)
    m_csj = load("csj", "metrics_resp")
    m_csj_pg = load("csj", "metrics_pausegap")
    m_csj = merge_on_keys(m_csj, m_csj_pg)
    s_cejc = load("cejc", "segments")
    s_csj  = load("csj",  "segments")

    # sanity
    for corpus, m in [("cejc", m_cejc), ("csj", m_csj)]:
        need = {"conversation_id", "speaker_id", "RESP_NE_AIZUCHI_RATE", "n_pairs_after_NE"}
        miss = need - set(m.columns)
        if miss:
            print(f"[FATAL] {corpus} metrics_resp missing: {sorted(miss)}", file=sys.stderr)
            sys.exit(2)

    # speaker count per conversation for subset split
    def n_speakers(segments: pd.DataFrame) -> pd.Series:
        if "conversation_id" not in segments.columns or "speaker_id" not in segments.columns:
            return pd.Series(dtype=float)
        return segments.groupby("conversation_id")["speaker_id"].nunique().rename("n_speakers")

    ns_cejc = n_speakers(s_cejc)
    ns_csj  = n_speakers(s_csj)

    def enrich(metrics: pd.DataFrame, ns: pd.Series) -> pd.DataFrame:
        df = metrics.copy()
        df["n_pairs_after_NE"] = pd.to_numeric(df["n_pairs_after_NE"], errors="coerce").fillna(0).astype(int)
        if len(ns) > 0:
            df = df.merge(ns.reset_index(), on="conversation_id", how="left")
        else:
            df["n_speakers"] = None
        return df

    cejc = enrich(m_cejc, ns_cejc)
    csj  = enrich(m_csj,  ns_csj)

    # subsets (conversation-level)
    cejc_all = cejc
    csj_all = csj
    cejc_dyad   = cejc[cejc["n_speakers"] == 2].copy() if "n_speakers" in cejc.columns else cejc.copy()
    csj_dialog  = csj[csj["n_speakers"] >= 2].copy() if "n_speakers" in csj.columns else csj.copy()

    datasets = {
        "cejc_all": cejc_all,
        "cejc_dyad": cejc_dyad,
        "csj_all": csj_all,
        "csj_dialog": csj_dialog,
    }

    # Phase4: attach metrics_pausegap to each dataset (so summary/rank can see it)

    for _name, _df in list(datasets.items()):

        _corpus = "cejc" if _name.startswith("cejc") else "csj"

        _pg = load(_corpus, "metrics_pausegap")

        datasets[_name] = merge_on_keys(_df, _pg)


    # summary
    df_summary = pd.concat(
        [build_summary_row(dfx, name, summary_cols) for name, dfx in datasets.items()],
        ignore_index=True,
    )
    s3_write_parquet(s3, df_summary, f"{out}/gold=v{gv}/summary/summary_datasets.parquet", args.kms_key_arn)
    s3_write_text(s3, df_summary.to_csv(index=False), f"{out}/gold=v{gv}/summary/summary_datasets.csv", args.kms_key_arn, content_type="text/csv")

    # rank
    metric = "RESP_NE_AIZUCHI_RATE"

    must_keep = ["conversation_id", "speaker_id", "n_pairs_after_NE", "RESP_NE_AIZUCHI_RATE"]
    for name, dfx in datasets.items():
        if len(dfx) == 0:
            print(f"[WARN] dataset={name} empty; skipping", file=sys.stderr)
            continue

        reliable = dfx[dfx["n_pairs_after_NE"] >= args.min_ne_events].copy()
        if len(reliable) == 0:
            print(f"[WARN] dataset={name} no reliable rows with min_ne={args.min_ne_events}. Using ALL rows.", file=sys.stderr)
            reliable = dfx.copy()

        reliable_desc = reliable.sort_values(by=metric, ascending=False)
        top50 = reliable_desc.head(50)
        bottom50 = reliable.sort_values(by=metric, ascending=True).head(50)
        all_rel = reliable_desc

        # fit to template cols but always keep core cols if present
        if rank_cols:
            def fit(df_in: pd.DataFrame) -> pd.DataFrame:
                cols = [c for c in rank_cols if c in df_in.columns]
                for c in must_keep:
                    if c in df_in.columns and c not in cols:
                        cols.append(c)
                return df_in[cols] if cols else df_in
            top50, bottom50, all_rel = fit(top50), fit(bottom50), fit(all_rel)

        base = f"{out}/gold=v{gv}/rank_ne_aizuchi/{name}"
        # Phase4: extend rank cols with pausegap (AUTO_SAFE)
        _df_for_cols = top50
        _extra_cols = [
            c for c in _df_for_cols.columns
            if c.startswith(("pause_","resp_gap","resp_overlap","speech_"))
            or c in ("total_time","speech_time","speech_ratio","n_segments","overlap_rate","n_resp_events")
        ]
        try:
            cols = cols + [c for c in _extra_cols if c not in cols]
        except NameError:
            cols = list(_df_for_cols.columns)

        s3_write_parquet(s3, top50,    f"{base}/top50.parquet", args.kms_key_arn)
        s3_write_parquet(s3, bottom50, f"{base}/bottom50.parquet", args.kms_key_arn)
        s3_write_parquet(s3, all_rel,  f"{base}/all_reliable.parquet", args.kms_key_arn)

    print("[OK] Rebuilt v13 summary + rank using metrics_resp.n_pairs_after_NE for reliability:", f"{out}/gold=v{gv}/", file=sys.stderr)


if __name__ == "__main__":
    main()
