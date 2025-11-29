#!/usr/bin/env python
"""
Nanami セッションごとの「指標カバレッジ行列」を生成するスクリプト。

- pragmatics_index_catalog.csv を読み込み
- Nanami/ 以下のセッションディレクトリ (例: 10129, 10225, ...) を走査
- 各 metric × session について:
    - 必要テーブルが存在するか
    - 必要カラムが存在するか
  をチェックして nanami_metric_session_coverage.csv を出力する
"""

import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd


def parse_semicolon_list(value: str) -> List[str]:
    """'a;b;c' → ['a', 'b', 'c'] みたいな簡易パーサ。空なら []。"""
    if pd.isna(value) or value is None:
        return []
    value = str(value).strip()
    if not value:
        return []
    return [item.strip() for item in value.split(";") if item.strip()]


def parse_required_columns(value: str) -> List[Tuple[str, str]]:
    """
    'turns.speaker;turns.text' → [('turns', 'speaker'), ('turns', 'text')] に変換。
    """
    cols = []
    for item in parse_semicolon_list(value):
        if "." in item:
            table, col = item.split(".", 1)
        else:
            # テーブル名が省略されていた場合はそのまま扱う
            table, col = "", item
        cols.append((table.strip(), col.strip()))
    return cols


def load_first_rows_for_tables(session_dir: Path, tables: List[str]) -> Dict[str, pd.DataFrame]:
    """
    指定テーブルの CSV を 1 行だけ読み込んで列名を確認する。
    ファイルがなければ value は None。
    """
    result: Dict[str, pd.DataFrame] = {}
    for t in tables:
        if not t:
            continue
        csv_path = session_dir / f"{t}.csv"
        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path, nrows=1)
            except Exception as e:
                print(f"[WARN] Failed to read {csv_path}: {e}")
                df = None
            result[t] = df
        else:
            result[t] = None
    return result


def determine_availability_status(
    metric_row: pd.Series,
    table_heads: Dict[str, pd.DataFrame],
) -> Tuple[str, List[str], List[str]]:
    """
    metric_row（カタログの1行）と、そのセッションでのテーブルヘッダ情報から
    availability_status / missing_tables / missing_columns を判定。
    """
    requires_tables = parse_semicolon_list(metric_row.get("requires_tables", ""))
    requires_columns = parse_required_columns(metric_row.get("requires_columns", ""))
    requires_annotation = bool(metric_row.get("requires_annotation", 0))

    missing_tables: List[str] = []
    missing_columns: List[str] = []

    # テーブル存在チェック
    for t in requires_tables:
        if not t:
            continue
        if t not in table_heads or table_heads[t] is None:
            missing_tables.append(t)

    # カラム存在チェック（テーブルがある場合のみ）
    for t, col in requires_columns:
        if t and (t not in table_heads or table_heads[t] is None):
            # テーブル自体がない場合は missing_tables にすでに入っているはず
            continue
        if not t:
            # 'col' のみ指定されているケース → どのテーブルかは手動対応でも良い
            continue
        df = table_heads.get(t)
        if df is not None:
            if col not in df.columns:
                missing_columns.append(f"{t}.{col}")

    # availability_status の判定ロジック
    if missing_tables:
        availability_status = "not_available"
    elif missing_columns:
        # カラムが足りない場合：
        #   requires_annotation=1 → アノテーション/前処理でなんとかなる前提なので needs_annotation
        #   それ以外 → not_available 扱い
        availability_status = "needs_annotation" if requires_annotation else "not_available"
    else:
        availability_status = "ready"

    return availability_status, missing_tables, missing_columns


def build_coverage(
    nanami_root: Path,
    catalog_path: Path,
    output_path: Path,
    speaker_roles: List[str] = None,
) -> None:
    """
    Nanami ルートディレクトリと指標カタログ CSV から、
    nanami_metric_session_coverage.csv を生成する。
    """
    if speaker_roles is None:
        # CHI / MOT の2種 + 双方対象の 'BOTH' を基本とする
        speaker_roles = ["CHI", "MOT", "BOTH"]

    catalog_df = pd.read_csv(catalog_path)

    # Nanami/ 以下のサブディレクトリのうち、数字だけの名前をセッションとみなす
    session_dirs = sorted(
        [p for p in nanami_root.iterdir() if p.is_dir() and p.name.isdigit()],
        key=lambda p: p.name,
    )

    rows = []

    # 全 metric で必要となるテーブル名の集合（ヘッダ読み込み最適化用）
    all_required_tables = set()
    for _, mrow in catalog_df.iterrows():
        for t in parse_semicolon_list(mrow.get("requires_tables", "")):
            if t:
                all_required_tables.add(t)

    for session_dir in session_dirs:
        session_id = session_dir.name
        print(f"[INFO] processing session {session_id}")

        # このセッションで必要になりそうなテーブルだけ 1 行読んで列情報を取得
        table_heads = load_first_rows_for_tables(session_dir, sorted(all_required_tables))

        for _, mrow in catalog_df.iterrows():
            metric_id = mrow["metric_id"]

            availability_status, missing_tables, missing_columns = determine_availability_status(
                mrow, table_heads
            )

            # metric_id × session_id × speaker_role の3軸で行を作る（role で分けないならここを1回だけにしてもOK）
            for role in speaker_roles:
                row = {
                    "metric_id": metric_id,
                    "session_id": session_id,
                    "speaker_role": role,
                    "availability_status": availability_status,
                    "missing_tables": ";".join(sorted(set(missing_tables))) if missing_tables else "",
                    "missing_columns": ";".join(sorted(set(missing_columns))) if missing_columns else "",
                    # 以下はひとまず 0 で初期化し、実際に指標を実装・計算したら別途更新
                    "implemented": 1 if str(mrow.get("status_nanami", "")).lower() == "ready" else 0,
                    "computed": 0,
                    "n_tokens_covered": 0,
                    "n_turns_covered": 0,
                    "notes": "",
                }
                rows.append(row)

    coverage_df = pd.DataFrame(rows)
    coverage_df.to_csv(output_path, index=False)
    print(f"[INFO] wrote coverage matrix to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Build Nanami metric-session coverage CSV.")
    parser.add_argument(
        "--nanami-root",
        type=Path,
        required=True,
        help="Nanami ディレクトリへのパス (例: ./audio/Nanami)",
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        required=True,
        help="指標カタログ pragmatics_index_catalog.csv へのパス",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("nanami_metric_session_coverage.csv"),
        help="出力 CSV パス",
    )
    args = parser.parse_args()

    build_coverage(
        nanami_root=args.nanami_root,
        catalog_path=args.catalog,
        output_path=args.out,
    )


if __name__ == "__main__":
    main()
