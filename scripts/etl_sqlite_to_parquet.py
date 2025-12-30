# scripts/etl_sqlite_to_parquet.py
# -*- coding: utf-8 -*-
"""
SQLite(.db) -> Parquet(zstd) ETL for CEJC/CSJ (S3 <-> local tmp <-> S3)

- Downloads SQLite .db from S3 to a temp directory
- Dumps selected tables into partitioned Parquet on S3 (chunked by rowid when available)
- Builds a canonical "utterances" table for pragmatics research:
  - CEJC: segLUU -> utterances
  - CSJ : segIPU -> utterances

IMPORTANT:
- Your curated bucket policy explicitly DENIES PutObject unless SSE-KMS headers are present
  and the KMS key matches. Therefore, set env var:
    export S3_KMS_KEY_ARN="arn:aws:kms:ap-northeast-1:982534361827:key/...."
"""

import argparse
import os
import re
import sqlite3
import tempfile
import sys
from typing import List, Optional, Tuple

import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


# Global clients
s3 = boto3.client("s3")


# -----------------------------
# S3 helpers
# -----------------------------
def parse_s3_uri(uri: str) -> Tuple[str, str]:
    """
    Parse s3://bucket/key into (bucket, key)
    """
    m = re.match(r"^s3://([^/]+)/(.+)$", uri)
    if not m:
        raise ValueError(f"Invalid s3 uri: {uri}")
    return m.group(1), m.group(2)


def s3_download_to_file(s3_uri: str, local_path: str) -> None:
    """
    Download an S3 object to local file path
    """
    b, k = parse_s3_uri(s3_uri)
    s3.download_file(b, k, local_path)


def _kms_extra_args_or_die() -> dict:
    """
    Build ExtraArgs for boto3 S3 upload to satisfy bucket policy that requires SSE-KMS headers.
    """
    kms_key_arn = os.getenv("S3_KMS_KEY_ARN")
    if not kms_key_arn:
        print(
            "ERROR: S3_KMS_KEY_ARN is not set. "
            "Your curated bucket policy likely requires SSE-KMS headers.",
            file=sys.stderr,
        )
        raise RuntimeError("Missing env var: S3_KMS_KEY_ARN")

    return {
        "ServerSideEncryption": "aws:kms",
        "SSEKMSKeyId": kms_key_arn,
    }


def s3_upload_file(local_path: str, out_s3_uri: str) -> None:
    """
    Upload local file to S3 with SSE-KMS headers (required by bucket policy)
    """
    b, k = parse_s3_uri(out_s3_uri)
    extra_args = _kms_extra_args_or_die()
    s3.upload_file(local_path, b, k, ExtraArgs=extra_args)


# -----------------------------
# SQLite helpers
# -----------------------------
def list_tables(con: sqlite3.Connection) -> List[str]:
    cur = con.cursor()
    rows = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def get_columns(con: sqlite3.Connection, table: str) -> List[str]:
    rows = con.execute(f"PRAGMA table_info('{table}')").fetchall()
    return [r[1] for r in rows]


def has_rowid(con: sqlite3.Connection, table: str) -> bool:
    try:
        con.execute(f"SELECT rowid FROM '{table}' LIMIT 1").fetchall()
        return True
    except Exception:
        return False


def chunk_query_by_rowid(table: str, cols: List[str], start: int, end: int) -> str:
    col_sql = ", ".join([f'"{c}"' for c in cols])
    return (
        f'SELECT rowid AS __rowid, {col_sql} FROM "{table}" '
        f"WHERE rowid > {start} AND rowid <= {end} ORDER BY rowid"
    )


# -----------------------------
# Pandas/Arrow compatibility helpers
# -----------------------------
_BYTES_TYPES = (bytes, bytearray, memoryview)


def _to_text(x):
    """
    Normalize values into text for Arrow when a column contains mixed object types.
    - bytes -> utf-8 decode (replace errors)
    - others -> str(x)
    - None/NaN -> <NA>
    """
    if x is None:
        return pd.NA
    # pandas may pass nan as float
    try:
        if pd.isna(x):
            return pd.NA
    except Exception:
        pass

    if isinstance(x, _BYTES_TYPES):
        try:
            return bytes(x).decode("utf-8")
        except Exception:
            return bytes(x).decode("utf-8", errors="replace")
    return str(x)


def _coerce_column_to_string(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """
    Force a column to pandas StringDtype with safe conversion:
    - bytes decoded
    - mixed types stringified
    """
    s = df[col]
    # Only coerce if it's object or already problematic
    # (ArrowTypeError often happens on object)
    if s.dtype == "object" or str(s.dtype).startswith("string"):
        df[col] = s.map(_to_text).astype("string")
    else:
        # still coerce just in case (rare)
        df[col] = s.astype("string")
    return df


def _table_from_pandas_with_fixes(df: pd.DataFrame, max_rounds: int = 8) -> pa.Table:
    """
    Try pa.Table.from_pandas. If ArrowTypeError occurs for a specific column,
    coerce that column to string and retry (few rounds).
    This avoids converting all object columns preemptively.
    """
    work = df
    last_err = None

    for _ in range(max_rounds):
        try:
            return pa.Table.from_pandas(work, preserve_index=False)
        except pa.ArrowTypeError as e:
            last_err = e
            msg = str(e)

            # Typical message:
            # ("Expected bytes, got a 'int' object", 'Conversion failed for column housemate with type object')
            m = re.search(r"Conversion failed for column ([^ ]+) with type", msg)
            if m:
                col = m.group(1)
                if col in work.columns:
                    work = work.copy()
                    work = _coerce_column_to_string(work, col)
                    continue

            # Fallback: coerce ALL object columns to string once
            work = work.copy()
            for c in work.columns:
                if work[c].dtype == "object":
                    work = _coerce_column_to_string(work, c)
            try:
                return pa.Table.from_pandas(work, preserve_index=False)
            except Exception as e2:
                last_err = e2
                break

    raise last_err if last_err else RuntimeError("Unknown Arrow conversion failure")


# -----------------------------
# Parquet helpers
# -----------------------------
def write_parquet_chunk(df: pd.DataFrame, out_path: str) -> None:
    """
    Write dataframe to Parquet (zstd). Index is dropped.
    Auto-fixes ArrowTypeError due to mixed object types (bytes/int etc.).
    """
    table = _table_from_pandas_with_fixes(df)
    pq.write_table(table, out_path, compression="zstd")


# -----------------------------
# Dump table -> partitioned parquet on S3
# -----------------------------
def dump_table_to_parquet(
    con: sqlite3.Connection,
    table: str,
    out_prefix_s3: str,
    corpus: str,
    chunk_rows: int = 500_000,
    max_parts: Optional[int] = None,
) -> List[str]:
    """
    Dump a SQLite table to S3 as multiple parquet parts.
    Output:
      {out_prefix_s3}/corpus={corpus}/table={table}/part-00000.parquet ...
    Returns list of out uris.
    """
    cols = get_columns(con, table)
    out_uris: List[str] = []

    out_prefix = out_prefix_s3.rstrip("/")

    # Prefer rowid range chunking (stable and fast) if available
    if has_rowid(con, table):
        max_rowid = con.execute(f'SELECT MAX(rowid) FROM "{table}"').fetchone()[0] or 0
        part = 0
        start = 0

        while start < max_rowid:
            end = min(start + chunk_rows, max_rowid)
            q = chunk_query_by_rowid(table, cols, start, end)
            df = pd.read_sql_query(q, con)

            if df.empty:
                start = end
                continue

            # Remove internal rowid helper column if present
            df = df.drop(columns=["__rowid"], errors="ignore")

            with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tf:
                tmp_path = tf.name

            write_parquet_chunk(df, tmp_path)

            out_uri = f"{out_prefix}/corpus={corpus}/table={table}/part-{part:05d}.parquet"
            s3_upload_file(tmp_path, out_uri)
            os.remove(tmp_path)

            out_uris.append(out_uri)

            part += 1
            start = end

            if max_parts is not None and part >= max_parts:
                break

    else:
        # Fallback: one-shot dump (ok for small tables)
        df = pd.read_sql_query(f'SELECT * FROM "{table}"', con)

        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tf:
            tmp_path = tf.name

        write_parquet_chunk(df, tmp_path)

        out_uri = f"{out_prefix}/corpus={corpus}/table={table}/part-00000.parquet"
        s3_upload_file(tmp_path, out_uri)
        os.remove(tmp_path)

        out_uris.append(out_uri)

    return out_uris


# -----------------------------
# Canonical utterances builders
# -----------------------------
def build_utterances_cejc(con: sqlite3.Connection) -> pd.DataFrame:
    """
    CEJC: segLUU -> utterances
    """
    df = pd.read_sql_query(
        """
        SELECT
          conversationID AS conversation_id,
          luuID         AS utterance_id,
          speakerID     AS speaker_id,
          startTime     AS start_time,
          endTime       AS end_time,
          text          AS text
        FROM segLUU
        """,
        con,
    )
    df["corpus"] = "cejc"
    df["unit_type"] = "LUU"
    return df


def build_utterances_csj(con: sqlite3.Connection) -> pd.DataFrame:
    """
    CSJ: segIPU -> utterances
    Speaker is not explicit; use Channel as speaker_id for now.
    """
    df = pd.read_sql_query(
        """
        SELECT
          TalkID     AS conversation_id,
          IPUID      AS utterance_id,
          Channel    AS speaker_id,
          StartTime  AS start_time,
          EndTime    AS end_time,
          Text       AS text
        FROM segIPU
        """,
        con,
    )
    df["corpus"] = "csj"
    df["unit_type"] = "IPU"
    return df


def write_df_to_s3_parquet(df: pd.DataFrame, out_uri: str) -> None:
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tf:
        tmp_path = tf.name
    write_parquet_chunk(df, tmp_path)
    s3_upload_file(tmp_path, out_uri)
    os.remove(tmp_path)


# -----------------------------
# CLI
# -----------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-db-s3", required=True, help="s3://bucket/key to sqlite .db")
    ap.add_argument("--corpus", required=True, choices=["cejc", "csj"], help="corpus id")
    ap.add_argument("--out-s3-prefix", required=True, help="s3://bucket/prefix")
    ap.add_argument(
        "--dump-tables",
        default="",
        help="comma-separated table names to dump (optional). Example: infoSession,infoParticipant",
    )
    ap.add_argument("--chunk-rows", type=int, default=500_000)
    ap.add_argument("--max-parts", type=int, default=0, help="0 means no limit; for debugging")
    ap.add_argument("--build-utterances", action="store_true")
    args = ap.parse_args()

    # Fail fast if KMS env var missing (because bucket policy has explicit deny)
    _ = _kms_extra_args_or_die()

    out_prefix = args.out_s3_prefix.rstrip("/")
    max_parts = None if args.max_parts == 0 else args.max_parts

    with tempfile.TemporaryDirectory() as d:
        local_db = os.path.join(d, f"{args.corpus}.db")
        s3_download_to_file(args.in_db_s3, local_db)

        con = sqlite3.connect(local_db)

        # Validate tables
        available = set(list_tables(con))
        tables: List[str] = []
        if args.dump_tables.strip():
            tables = [t.strip() for t in args.dump_tables.split(",") if t.strip()]

        for t in tables:
            if t not in available:
                raise ValueError(f"Table not found: {t}")

        # Dump requested tables
        for t in tables:
            dump_table_to_parquet(
                con=con,
                table=t,
                out_prefix_s3=out_prefix,
                corpus=args.corpus,
                chunk_rows=args.chunk_rows,
                max_parts=max_parts,
            )

        # Build canonical utterances
        if args.build_utterances:
            if args.corpus == "cejc":
                u = build_utterances_cejc(con)
            else:
                u = build_utterances_csj(con)

            out_uri = f"{out_prefix}/corpus={args.corpus}/table=utterances/part-00000.parquet"
            write_df_to_s3_parquet(u, out_uri)

        con.close()


if __name__ == "__main__":
    main()

