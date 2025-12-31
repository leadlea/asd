# scripts/phase3/build_speaker_features.py
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

import duckdb
import pandas as pd


def is_s3(path: str) -> bool:
    return path.startswith("s3://")


def aws_s3_cp(local_path: str, s3_path: str, kms_key_arn: Optional[str]) -> None:
    cmd = ["aws", "s3", "cp", local_path, s3_path]
    if kms_key_arn:
        cmd += ["--sse", "aws:kms", "--sse-kms-key-id", kms_key_arn]
    subprocess.run(cmd, check=True)


def escape_sql_str(s: str) -> str:
    return s.replace("'", "''")


def qident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def list_local_parquet_files(root_dir: str) -> List[str]:
    root = Path(root_dir)
    files = sorted([str(p) for p in root.rglob("*.parquet") if p.is_file()])
    if not files:
        raise RuntimeError(f"No parquet files found under: {root_dir}")
    return files


def build_source_sql(metrics_path: str) -> str:
    p = metrics_path.rstrip("/")

    if p.endswith(".parquet"):
        return f"read_parquet('{escape_sql_str(p)}', union_by_name=true, hive_partitioning=true)"

    if is_s3(p):
        return f"read_parquet('{escape_sql_str(p)}/**/*.parquet', union_by_name=true, hive_partitioning=true)"

    files = list_local_parquet_files(p)
    items = ",".join([f"'{escape_sql_str(f)}'" for f in files])
    return f"read_parquet([{items}], union_by_name=true, hive_partitioning=true)"


def pick_weight_col(cols: List[str], candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in cols:
            return c
    return None


def build_agg_sql(
    table_value: str,
    prefix: str,
    cols: List[str],
    weight_col: Optional[str],
) -> str:
    # ★ speaker_session で集約するため conversation_id を group key に追加
    group_cols = ["corpus", "conversation_id", "speaker_id"]

    # weight: NULL安全
    w = "1"
    if weight_col:
        w = f"COALESCE({qident(weight_col)}, 0)"

    selects = [
        "corpus",
        "conversation_id",
        "speaker_id",
        f"'{escape_sql_str(table_value)}' AS {prefix}table_name",
    ]

    # 合計分母（後でフィルタに使う）
    if weight_col:
        selects.append(f"SUM({w}) AS {prefix}{weight_col}__sum")
    else:
        selects.append(f"COUNT(*) AS {prefix}rows__count")

    exclude = set(group_cols + ["utt_id", "turn_id"])
    for c in cols:
        if c in exclude:
            continue
        if c in ["corpus", "conversation_id", "speaker_id", "table"]:
            continue

        qc = qident(c)

        if c.startswith("rate_") or c == "coverage":
            selects.append(f"SUM({qc} * {w}) / NULLIF(SUM({w}), 0) AS {prefix}{c}__wmean")
        elif c.startswith("n_"):
            selects.append(f"SUM({qc}) AS {prefix}{c}__sum")
        else:
            # v1と同様：控えめに平均
            selects.append(f"AVG({qc}) AS {prefix}{c}__avg")

    select_sql = ",\n  ".join(selects)
    group_sql = ", ".join(group_cols)

    return f"""
    SELECT
      {select_sql}
    FROM source
    WHERE {qident('table')} = '{escape_sql_str(table_value)}'
    GROUP BY {group_sql}
    """


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", required=True, help="metrics parquet dir/file (local preferred)")
    ap.add_argument("--out", required=True, help="output parquet (s3:// or local)")
    ap.add_argument("--min_n_utt", type=int, default=0, help="min SUM(n_utt) for metrics_sfp (0 disables)")
    ap.add_argument("--min_n_pairs_total", type=int, default=0, help="min SUM(n_pairs_total) for metrics_resp (0 disables)")
    args = ap.parse_args()

    con = duckdb.connect(database=":memory:")

    if is_s3(args.metrics):
        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute("SET s3_region='ap-northeast-1';")

    source_sql = build_source_sql(args.metrics)
    con.execute(f"CREATE TEMP VIEW source AS SELECT * FROM {source_sql}")

    # 必須列チェック（hive_partitioningで corpus/table が入る前提）
    cols_all = con.execute("SELECT * FROM source LIMIT 1").df().columns.tolist()
    for need in ["corpus", "table", "conversation_id", "speaker_id"]:
        if need not in cols_all:
            raise RuntimeError(f"Missing required col: {need}. got={cols_all[:80]}")

    # ---- table=metrics_sfp ----
    sfp_sample = con.execute(
        f"SELECT * FROM source WHERE {qident('table')}='metrics_sfp' LIMIT 1"
    ).df()
    if len(sfp_sample) == 0:
        raise RuntimeError("No rows for table=metrics_sfp")
    sfp_cols = list(sfp_sample.columns)
    sfp_weight = pick_weight_col(sfp_cols, ["n_utt", "n_valid"])
    sfp_agg = build_agg_sql("metrics_sfp", "sfp__", sfp_cols, sfp_weight)

    # ---- table=metrics_resp ----
    resp_sample = con.execute(
        f"SELECT * FROM source WHERE {qident('table')}='metrics_resp' LIMIT 1"
    ).df()
    if len(resp_sample) == 0:
        raise RuntimeError("No rows for table=metrics_resp")
    resp_cols = list(resp_sample.columns)
    resp_weight = pick_weight_col(resp_cols, ["n_pairs_total", "n_valid"])
    resp_agg = build_agg_sql("metrics_resp", "resp__", resp_cols, resp_weight)

    con.execute(f"CREATE TEMP VIEW sfp AS {sfp_agg}")
    con.execute(f"CREATE TEMP VIEW resp AS {resp_agg}")

    # ---- join (speaker_session key: corpus + conversation_id + speaker_id) ----
    join_sql = f"""
    WITH joined AS (
      SELECT
        COALESCE(sfp.corpus, resp.corpus) AS dataset,
        COALESCE(sfp.conversation_id, resp.conversation_id) AS conversation_id,
        COALESCE(sfp.speaker_id, resp.speaker_id) AS speaker_side,

        -- downstream互換：speaker_id をユニークIDにする（conversation_id:speaker_side）
        CASE
          WHEN COALESCE(sfp.conversation_id, resp.conversation_id) IS NULL THEN COALESCE(sfp.speaker_id, resp.speaker_id)
          ELSE COALESCE(sfp.conversation_id, resp.conversation_id) || ':' || COALESCE(sfp.speaker_id, resp.speaker_id)
        END AS speaker_id,

        -- totals (フィルタ用)
        COALESCE(sfp.sfp__n_utt__sum, 0) AS n_utt_total,
        COALESCE(resp.resp__n_pairs_total__sum, 0) AS n_pairs_total,

        sfp.* EXCLUDE (corpus, conversation_id, speaker_id),
        resp.* EXCLUDE (corpus, conversation_id, speaker_id)
      FROM sfp
      FULL OUTER JOIN resp
        ON sfp.corpus = resp.corpus
       AND sfp.conversation_id = resp.conversation_id
       AND sfp.speaker_id = resp.speaker_id
    )
    SELECT * FROM joined
    """

    df = con.execute(join_sql).df()

    # ---- filter by denominators ----
    if args.min_n_utt > 0:
        df = df[df["n_utt_total"] >= args.min_n_utt]
    if args.min_n_pairs_total > 0:
        df = df[df["n_pairs_total"] >= args.min_n_pairs_total]

    out_path = args.out
    kms = os.environ.get("S3_KMS_KEY_ARN")

    if is_s3(out_path):
        with tempfile.TemporaryDirectory() as td:
            local_out = str(Path(td) / "speaker_features.parquet")
            df.to_parquet(local_out, index=False)
            aws_s3_cp(local_out, out_path, kms)
    else:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out_path, index=False)

    print(json.dumps({
        "rows": int(len(df)),
        "out": out_path,
        "sfp_weight": sfp_weight,
        "resp_weight": resp_weight,
        "min_n_utt": args.min_n_utt,
        "min_n_pairs_total": args.min_n_pairs_total,
        "note": "speaker_session = (dataset, conversation_id, speaker_side); speaker_id is made unique as conversation_id:speaker_side"
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

