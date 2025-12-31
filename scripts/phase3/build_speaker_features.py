# scripts/phase3/build_speaker_features.py
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

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


def guess_cols(cols: List[str]) -> Tuple[str, str, Optional[str]]:
    """
    (dataset_col, speaker_col, role_col?)
    """
    def pick(candidates: Iterable[str]) -> Optional[str]:
        for c in candidates:
            if c in cols:
                return c
        for c in cols:
            for pat in candidates:
                if re.fullmatch(pat, c, flags=re.IGNORECASE):
                    return c
        return None

    dataset_col = pick(["dataset", "corpus", "source", "collection"])
    speaker_col = pick(["speaker_id", "speaker", "spk_id", "spk", "sid", "talker_id", "participant_id"])
    role_col = pick(["role", "speaker_role", "participant_role", "turn_role", "chi_mot", "chi_mot_both"])

    if not dataset_col or not speaker_col:
        raise RuntimeError(
            "Failed to guess dataset/speaker columns.\n"
            f"dataset_col={dataset_col}, speaker_col={speaker_col}\n"
            f"Available cols={cols[:200]}..."
        )
    return dataset_col, speaker_col, role_col


def numeric_feature_cols(sample_df: pd.DataFrame, exclude: set[str]) -> List[str]:
    num_cols = []
    for c in sample_df.columns:
        if c in exclude:
            continue
        if pd.api.types.is_numeric_dtype(sample_df[c]):
            num_cols.append(c)

    # “idっぽい”列は落とす（数値でも）
    id_like = re.compile(r"(?:^id$|_id$|^idx$|_idx$|segment|turn|utt|pair)", re.IGNORECASE)
    num_cols = [c for c in num_cols if not id_like.search(c)]
    return num_cols


def build_source_sql(metrics_path: str) -> str:
    """
    - metrics_resp と metrics_sfp のようにスキーマが違うparquetが混ざるので union_by_name=True が必須
    - corpus=.../table=... の partition を列として取り込みたいので hive_partitioning=True も必須
    - DuckDBの ** 再帰globは環境で不安定なので、ローカルはPythonでrglobしてファイルリストを渡す
    """
    p = metrics_path.rstrip("/")

    # 単一ファイル
    if p.endswith(".parquet"):
        return (
            f"read_parquet('{escape_sql_str(p)}', "
            f"union_by_name=true, hive_partitioning=true)"
        )

    # S3直読みは今回のB運用では基本使わないが、保険で残す
    if is_s3(p):
        # なるべく広く拾う
        return (
            f"read_parquet('{escape_sql_str(p)}/**/*.parquet', "
            f"union_by_name=true, hive_partitioning=true)"
        )

    # ローカルディレクトリ：再帰で全部拾ってリスト化
    root = Path(p)
    files = sorted([str(x) for x in root.rglob("*.parquet") if x.is_file()])
    if not files:
        raise RuntimeError(f"No parquet files found under local dir: {p}")

    items = ",".join([f"'{escape_sql_str(f)}'" for f in files])
    return (
        f"read_parquet([{items}], "
        f"union_by_name=true, hive_partitioning=true)"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", required=True, help="gold v13 metrics parquet dir or file (local preferred)")
    ap.add_argument("--out", required=True, help="output parquet path (local or s3://)")
    ap.add_argument("--min_rows", type=int, default=30, help="min rows per speaker to keep (COUNT(*) over unioned rows)")
    ap.add_argument("--dataset_col", default=None)
    ap.add_argument("--speaker_col", default=None)
    ap.add_argument("--role_col", default=None, help="set to '' to disable role even if exists")
    args = ap.parse_args()

    con = duckdb.connect(database=":memory:")

    # S3直読みをする場合のみ httpfs をロード（B運用では通らない想定）
    if is_s3(args.metrics):
        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute("SET s3_region='ap-northeast-1';")

    source_sql = build_source_sql(args.metrics)

    # まず 1 行だけ読んで列推定
    sample = con.execute(f"SELECT * FROM {source_sql} LIMIT 1").df()
    cols = list(sample.columns)

    dataset_col, speaker_col, role_col = guess_cols(cols)

    if args.dataset_col:
        dataset_col = args.dataset_col
    if args.speaker_col:
        speaker_col = args.speaker_col

    # role の扱い：明示 '' なら無効化
    if args.role_col is not None:
        if args.role_col == "":
            role_col = None
        else:
            role_col = args.role_col

    group_cols = [dataset_col, speaker_col]
    if role_col and role_col in cols:
        group_cols.append(role_col)
    else:
        role_col = None

    exclude = set(group_cols)
    feat_cols = numeric_feature_cols(sample, exclude=exclude)
    if not feat_cols:
        raise RuntimeError(
            "No numeric feature columns detected from metrics.\n"
            f"Available cols={cols[:200]}..."
        )

    selects = []
    selects.append(f"{dataset_col} AS dataset")
    selects.append(f"{speaker_col} AS speaker_id")
    if role_col:
        selects.append(f"{role_col} AS role")

    # 参考：partition列があるなら出しておくとデバッグ楽（あってもなくてもOK）
    if "table" in cols:
        selects.append('STRING_AGG(DISTINCT "table", \',\') AS tables_seen')

    selects.append("COUNT(*)::BIGINT AS n_rows")

    # 集約（NULLはAVG/STDで無視されるので、table違いで列が無くても大丈夫）
    for c in feat_cols:
        selects.append(f"AVG({c}) AS {c}__mean")
        selects.append(f"STDDEV_SAMP({c}) AS {c}__std")

    select_sql = ",\n  ".join(selects)
    group_sql = ", ".join(group_cols)

    q = f"""
    SELECT
      {select_sql}
    FROM {source_sql}
    GROUP BY {group_sql}
    HAVING COUNT(*) >= {args.min_rows}
    """

    df = con.execute(q).df()

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

    print(json.dumps(
        {
            "rows": int(len(df)),
            "out": out_path,
            "group_cols": group_cols,
            "n_feat_cols": len(feat_cols),
            "note": "read_parquet(..., union_by_name=true, hive_partitioning=true)",
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()

