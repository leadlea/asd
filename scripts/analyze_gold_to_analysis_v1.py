# scripts/analyze_gold_to_analysis_v1.py
from __future__ import annotations

import argparse
import io
import sys
from typing import Dict, List, Optional, Tuple

import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from botocore.exceptions import ClientError


# ---------------------------
# S3 helpers
# ---------------------------

def _parse_s3_uri(uri: str) -> Tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"not s3 uri: {uri}")
    path = uri[len("s3://") :]
    bucket, _, key = path.partition("/")
    if not bucket or not key:
        raise ValueError(f"invalid s3 uri: {uri}")
    return bucket, key


def s3_exists(s3_client, uri: str) -> bool:
    bucket, key = _parse_s3_uri(uri)
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def s3_read_parquet(s3_client, uri: str) -> pd.DataFrame:
    bucket, key = _parse_s3_uri(uri)
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    body = obj["Body"].read()
    table = pq.read_table(io.BytesIO(body))
    return table.to_pandas()


def s3_write_parquet(s3_client, df: pd.DataFrame, uri: str, kms_key_arn: str | None = None) -> None:
    bucket, key = _parse_s3_uri(uri)
    table = pa.Table.from_pandas(df, preserve_index=False)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="zstd")
    put_kwargs = {
        "Bucket": bucket,
        "Key": key,
        "Body": buf.getvalue(),
        "ContentType": "application/octet-stream",
    }
    if kms_key_arn:
        put_kwargs["ServerSideEncryption"] = "aws:kms"
        put_kwargs["SSEKMSKeyId"] = kms_key_arn
    s3_client.put_object(**put_kwargs)


def s3_write_text(
    s3_client,
    text: str,
    uri: str,
    kms_key_arn: str | None = None,
    content_type: str = "text/plain",
) -> None:
    bucket, key = _parse_s3_uri(uri)
    put_kwargs = {"Bucket": bucket, "Key": key, "Body": text.encode("utf-8"), "ContentType": content_type}
    if kms_key_arn:
        put_kwargs["ServerSideEncryption"] = "aws:kms"
        put_kwargs["SSEKMSKeyId"] = kms_key_arn
    s3_client.put_object(**put_kwargs)


def s3_write_csv(s3_client, df: pd.DataFrame, uri: str, kms_key_arn: str | None = None) -> None:
    s3_write_text(s3_client, df.to_csv(index=False), uri, kms_key_arn, content_type="text/csv")


# ---------------------------
# Phase4: safe merge (fix CSJ speaker_id mismatch)
# ---------------------------

def merge_on_keys(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
    """
    Merge `right` into `left` with a robust key:
      - always uses conversation_id
      - normalizes speaker_id by taking the suffix after ':' if present
        e.g. 'A01F0055:L' -> 'L', 'IC01' -> 'IC01'

    This fixes CSJ mismatch:
      - metrics_pausegap has speaker_id like 'A01F0055:L'
      - rank datasets use speaker_id like 'L'

    Also:
      - avoids duplicate columns by temporarily renaming colliding columns from right,
        then combine_first into the left canonical name.
      - cleans legacy suffix columns (*_pausegap, *_pg) if present.
    """
    if right is None or len(right) == 0:
        return left

    l = left.copy()
    r = right.copy()

    # Normalize speaker key
    def _norm_spk(x):
        if x is None:
            return None
        s = str(x)
        return s.split(":", 1)[1] if ":" in s else s

    if "conversation_id" not in l.columns or "speaker_id" not in l.columns:
        raise ValueError("left must have conversation_id and speaker_id")
    if "conversation_id" not in r.columns or "speaker_id" not in r.columns:
        raise ValueError("right must have conversation_id and speaker_id")

    l["_spk_norm"] = l["speaker_id"].map(_norm_spk)
    r["_spk_norm"] = r["speaker_id"].map(_norm_spk)

    # We never want right.dataset / right.speaker_id to overwrite left's identity columns
    drop_cols = [c for c in ("dataset", "speaker_id") if c in r.columns]
    if drop_cols:
        r = r.drop(columns=drop_cols)

    # If right has columns already in left, merge without suffix by renaming right columns,
    # then combine_first into canonical names.
    key_cols = {"conversation_id", "_spk_norm"}
    r_cols = [c for c in r.columns if c not in key_cols]
    collisions = [c for c in r_cols if c in l.columns]

    rename_map = {c: f"{c}__pgsrc" for c in collisions}
    if rename_map:
        r = r.rename(columns=rename_map)

    out = l.merge(r, on=["conversation_id", "_spk_norm"], how="left")

    # combine_first for collisions (prefer left if already present, otherwise take pausegap)
    for c in collisions:
        src = f"{c}__pgsrc"
        if src in out.columns:
            out[c] = out[c].combine_first(out[src])
            out = out.drop(columns=[src])

    # cleanup
    out = out.drop(columns=["_spk_norm"])

    # legacy suffix cleanup (if you previously produced *_pausegap or *_pg columns)
    for suf in ("_pausegap", "_pg"):
        suffixed = [c for c in out.columns if c.endswith(suf)]
        for sc in suffixed:
            base = sc[: -len(suf)]
            if base in out.columns:
                # keep canonical base
                out = out.drop(columns=[sc])

    return out


# ---------------------------
# Summary / Rank builders
# ---------------------------

def _numeric_cols(df: pd.DataFrame, exclude: Optional[set] = None) -> List[str]:
    exclude = exclude or set()
    cols = []
    for c in df.columns:
        if c in exclude:
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            cols.append(c)
    return cols


def build_summary_row(df: pd.DataFrame, dataset_name: str, cols_template: Optional[List[str]]) -> pd.DataFrame:
    """
    Build 1-row summary for a dataset:
      - dataset
      - for each numeric column: <col>_mean
    If cols_template is provided, keep only those columns (if present) and order accordingly.
    """
    if df is None or len(df) == 0:
        # still return a row so downstream doesn't break
        row = {"dataset": dataset_name}
        out = pd.DataFrame([row])
        if cols_template:
            # make sure all template cols exist
            for c in cols_template:
                if c not in out.columns:
                    out[c] = pd.NA
            out = out[cols_template]
        return out

    exclude = {"dataset"}  # keep conversation_id/speaker_id-based metrics in means unless you want exclude them
    nums = _numeric_cols(df, exclude=exclude.union({"conversation_id", "speaker_id"}))
    row = {"dataset": dataset_name}
    for c in nums:
        row[f"{c}_mean"] = float(df[c].mean(skipna=True)) if len(df[c]) else pd.NA

    out = pd.DataFrame([row])

    if cols_template:
        for c in cols_template:
            if c not in out.columns:
                out[c] = pd.NA
        out = out[[c for c in cols_template if c in out.columns]]
        # Ensure dataset is present (template might start with dataset)
        if "dataset" in cols_template:
            out = out[cols_template]
        else:
            out = out[["dataset"] + [c for c in cols_template if c != "dataset"]]

    return out


def _default_rank_cols(df: pd.DataFrame) -> List[str]:
    # baseline important cols (keep if exist)
    base = [
        "conversation_id",
        "speaker_id",
        "n_pairs_total",
        "n_pairs_after_NE",
        "n_pairs_after_YO",
        "RESP_NE_AIZUCHI_RATE",
        "RESP_NE_ENTROPY",
        "RESP_YO_ENTROPY",
        "n_speakers",
    ]
    # pause/gap canonical cols (keep if exist)
    pg = [
        "speech_extract_mode",
        "total_time",
        "speech_time",
        "speech_ratio",
        "n_segments",
        "pause_mean",
        "pause_p50",
        "pause_p90",
        "overlap_rate",
        "resp_gap_mean",
        "resp_gap_p50",
        "resp_gap_p90",
        "resp_overlap_rate",
        "n_resp_events",
    ]
    cols = [c for c in base + pg if c in df.columns]
    # Always ensure keys
    for c in ("conversation_id", "speaker_id"):
        if c not in cols and c in df.columns:
            cols.insert(0, c)
    return cols


def build_rank_tables(
    df: pd.DataFrame,
    dataset_name: str,
    out_base: str,
    s3_client,
    kms_key_arn: str | None,
    rank_cols_template: Optional[List[str]],
    min_ne_events: int,
) -> None:
    """
    Write:
      - all_reliable.parquet
      - top50.parquet
      - bottom50.parquet
    under: {out_base}/{dataset_name}/
    """
    if df is None:
        df = pd.DataFrame()

    # reliability filter
    if "n_pairs_after_NE" in df.columns:
        reliable = df[df["n_pairs_after_NE"].fillna(0) >= min_ne_events].copy()
    else:
        reliable = df.copy()

    # choose columns
    if rank_cols_template:
        # keep only columns present
        cols = [c for c in rank_cols_template if c in reliable.columns]
        # ensure keys
        for c in ("conversation_id", "speaker_id"):
            if c in reliable.columns and c not in cols:
                cols.insert(0, c)
    else:
        cols = _default_rank_cols(reliable)

    reliable_out = reliable[cols] if len(reliable) else reliable.reindex(columns=cols)

    # top/bottom
    score_col = "RESP_NE_AIZUCHI_RATE"
    if score_col in reliable_out.columns and len(reliable_out):
        top50 = reliable_out.sort_values(score_col, ascending=False).head(50)
        bottom50 = reliable_out.sort_values(score_col, ascending=True).head(50)
    else:
        top50 = reliable_out.head(0)
        bottom50 = reliable_out.head(0)

    # write
    s3_write_parquet(s3_client, reliable_out, f"{out_base}/{dataset_name}/all_reliable.parquet", kms_key_arn)
    s3_write_parquet(s3_client, top50, f"{out_base}/{dataset_name}/top50.parquet", kms_key_arn)
    s3_write_parquet(s3_client, bottom50, f"{out_base}/{dataset_name}/bottom50.parquet", kms_key_arn)


# ---------------------------
# main
# ---------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold-s3-prefix", required=True, help="s3://.../gold (NOT including /v13)")
    ap.add_argument("--gold-version", required=True, type=int, help="e.g. 13")
    ap.add_argument("--out-s3-prefix", required=True, help="s3://.../analysis/v1_tmp_xxx (output root)")
    ap.add_argument("--kms-key-arn", default="", help="optional KMS key ARN for SSE-KMS")
    ap.add_argument("--template-gold-version", type=int, default=13, help="attempt to use existing out/gold=vX schema as template")
    ap.add_argument("--min-ne-events", type=int, default=10, help="minimum n_pairs_after_NE for reliable rank")
    args = ap.parse_args()

    gold = args.gold_s3_prefix.rstrip("/")
    gv = int(args.gold_version)
    out = args.out_s3_prefix.rstrip("/")
    kms = args.kms_key_arn.strip() or None
    template_v = int(args.template_gold_version) if args.template_gold_version is not None else None

    s3 = boto3.client("s3")

    def load(corpus: str, table: str) -> pd.DataFrame:
        uri = f"{gold}/v{gv}/corpus={corpus}/table={table}/part-00000.parquet"
        return s3_read_parquet(s3, uri)

    # load source metrics (resp)
    m_cejc = load("cejc", "metrics_resp")
    m_csj = load("csj", "metrics_resp")

    # template cols (best-effort)
    templ: Dict[str, Optional[List[str]]] = {"summary_cols": None, "rank_cols": None}
    if template_v is not None and template_v > 0:
        try:
            # try read from the same out prefix (works when out points to stable analysis/v1)
            t_sum_uri = f"{out}/gold=v{template_v}/summary/summary_datasets.parquet"
            if s3_exists(s3, t_sum_uri):
                templ["summary_cols"] = list(s3_read_parquet(s3, t_sum_uri).columns)
        except Exception:
            templ["summary_cols"] = None

        try:
            t_rank_uri = f"{out}/gold=v{template_v}/rank_ne_aizuchi/cejc_all/top50.parquet"
            if s3_exists(s3, t_rank_uri):
                templ["rank_cols"] = list(s3_read_parquet(s3, t_rank_uri).columns)
        except Exception:
            templ["rank_cols"] = None

    # split datasets (expects dataset column)
    datasets: Dict[str, pd.DataFrame] = {}

    for df in (m_cejc, m_csj):
        if "dataset" not in df.columns:
            # fallback: treat whole corpus as one dataset
            # (should not happen in your v13, but keep script robust)
            continue
        for name in sorted(df["dataset"].dropna().unique().tolist()):
            datasets[name] = df[df["dataset"] == name].copy()

    # If dataset col missing, fallback to known names with full corpus
    if not datasets:
        datasets = {
            "cejc_all": m_cejc.copy(),
            "cejc_dyad": m_cejc.copy(),
            "csj_all": m_csj.copy(),
            "csj_dialog": m_csj.copy(),
        }

    # --- Phase4: attach metrics_pausegap to each dataset (so summary/rank can see it)
    # load pausegap tables once per corpus
    try:
        m_cejc_pg = load("cejc", "metrics_pausegap")
    except Exception:
        m_cejc_pg = pd.DataFrame()

    try:
        m_csj_pg = load("csj", "metrics_pausegap")
    except Exception:
        m_csj_pg = pd.DataFrame()

    # helper to get pausegap by corpus
    def _pg_for_dataset(name: str) -> pd.DataFrame:
        if name.startswith("cejc"):
            return m_cejc_pg
        if name.startswith("csj"):
            return m_csj_pg
        return pd.DataFrame()

    # merge + create PG_* columns for summary
    pg_map = {
        "total_time": "PG_total_time",
        "speech_time": "PG_speech_time",
        "speech_ratio": "PG_speech_ratio",
        "n_segments": "PG_n_segments",
        "pause_mean": "PG_pause_mean",
        "pause_p50": "PG_pause_p50",
        "pause_p90": "PG_pause_p90",
        "overlap_rate": "PG_overlap_rate",
        "resp_gap_mean": "PG_resp_gap_mean",
        "resp_gap_p50": "PG_resp_gap_p50",
        "resp_gap_p90": "PG_resp_gap_p90",
        "resp_overlap_rate": "PG_resp_overlap_rate",
        "n_resp_events": "PG_n_resp_events",
    }

    for name in list(datasets.keys()):
        df_in = datasets[name]
        _pg = _pg_for_dataset(name)
        if _pg is not None and len(_pg):
            df_in = merge_on_keys(df_in, _pg)

        # create PG_* copies (for summary aggregation clarity)
        for src, dst in pg_map.items():
            if src in df_in.columns:
                df_in[dst] = df_in[src]

        datasets[name] = df_in

    # --- summary
    summary_cols = templ.get("summary_cols")
    df_summary = pd.concat([build_summary_row(datasets[name], name, summary_cols) for name in sorted(datasets.keys())], ignore_index=True)

    s3_write_parquet(s3, df_summary, f"{out}/gold=v{gv}/summary/summary_datasets.parquet", kms)
    s3_write_csv(s3, df_summary, f"{out}/gold=v{gv}/summary/summary_datasets.csv", kms)

    # --- rank
    rank_cols = templ.get("rank_cols")
    base_rank = f"{out}/gold=v{gv}/rank_ne_aizuchi"

    for name in sorted(datasets.keys()):
        build_rank_tables(
            datasets[name],
            dataset_name=name,
            out_base=base_rank,
            s3_client=s3,
            kms_key_arn=kms,
            rank_cols_template=rank_cols,
            min_ne_events=int(args.min_ne_events),
        )

    print(
        f"[OK] Rebuilt v{gv} summary + rank using metrics_resp.n_pairs_after_NE for reliability:",
        f"{out}/gold=v{gv}/",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()

