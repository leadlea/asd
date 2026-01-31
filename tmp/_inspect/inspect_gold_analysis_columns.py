#!/usr/bin/env python3
"""
特徴量棚卸し（完全版）確定用スクリプト
gold(v13) と analysis(v1) の実カラム一覧を出力する
"""
import pandas as pd
from pathlib import Path

def inspect_parquet(path: str, label: str):
    """parquetファイルを読み込んで shape, columns, head(3) を返す"""
    try:
        df = pd.read_parquet(path)
        return {
            "label": label,
            "path": path,
            "exists": True,
            "shape": df.shape,
            "columns": list(df.columns),
            "head": df.head(3).to_dict(orient="records")
        }
    except Exception as e:
        return {
            "label": label,
            "path": path,
            "exists": False,
            "error": str(e)
        }

def format_columns_by_prefix(columns):
    """列を接頭辞で分類"""
    prefixes = {
        "IX_": [],
        "FILL_": [],
        "PG_": [],
        "RESP_": [],
        "SFP_": [],
        "CL_": [],
        "LLM_": [],
        "other": []
    }
    
    for col in columns:
        matched = False
        for prefix in prefixes.keys():
            if prefix != "other" and col.startswith(prefix):
                prefixes[prefix].append(col)
                matched = True
                break
        if not matched:
            prefixes["other"].append(col)
    
    return prefixes

def main():
    print("# 特徴量棚卸し（完全版）- 実カラム一覧\n")
    print("## 目的")
    print("gold(v13) と analysis(v1) の実際のカラム構成を確定する\n")
    
    # Phase5 (v13相当) のファイルを調査
    print("## A. gold/v13 相当データ（ローカル artifacts/phase5）\n")
    
    # pg_metrics_v13 系を調査
    pg_files = [
        ("artifacts/phase5/pg_metrics_v13.parquet", "pg_metrics_v13 (メイン)"),
        ("artifacts/phase5/pg_metrics_v13_PG.parquet", "pg_metrics_v13_PG (PG接頭辞版)"),
        ("artifacts/phase5/pg_metrics_v13_raw.parquet", "pg_metrics_v13_raw"),
        ("artifacts/phase5/pg_metrics_v13_from_labels.parquet", "pg_metrics_v13_from_labels"),
    ]
    
    for path, label in pg_files:
        result = inspect_parquet(path, label)
        if result["exists"]:
            print(f"### {label}")
            print(f"- **ファイル**: `{path}`")
            print(f"- **shape**: {result['shape']}")
            print(f"- **列数**: {len(result['columns'])}")
            print(f"- **columns**:")
            for col in result['columns']:
                print(f"  - {col}")
            print()
        else:
            print(f"### {label}")
            print(f"- **ファイル**: `{path}`")
            print(f"- **存在しない**: {result.get('error', 'N/A')}")
            print()
    
    # Phase56 (analysis相当) のファイルを調査
    print("\n## B. analysis/v1 相当データ（ローカル artifacts/phase56_full_20260104_024221）\n")
    
    analysis_files = [
        ("artifacts/phase56_full_20260104_024221/labels_tb500_force_csj20.parquet", "labels_tb500 (ベース)"),
        ("artifacts/phase56_full_20260104_024221/labels_tb500_force_csj20_fill_ui.parquet", "labels_tb500_fill_ui (FILL統合版)"),
        ("artifacts/phase56_full_20260104_024221/pg_metrics_force_csj20.parquet", "pg_metrics (pause/gap)"),
        ("artifacts/phase56_full_20260104_024221/_htmlfix4/labels_tb500_with_CL.parquet", "labels_with_CL (クラスタ統合版)"),
    ]
    
    for path, label in analysis_files:
        result = inspect_parquet(path, label)
        if result["exists"]:
            print(f"### {label}")
            print(f"- **ファイル**: `{path}`")
            print(f"- **shape**: {result['shape']}")
            print(f"- **列数**: {len(result['columns'])}")
            
            # 接頭辞で分類
            categorized = format_columns_by_prefix(result['columns'])
            
            print(f"- **列の分類**:")
            for prefix, cols in categorized.items():
                if cols:
                    print(f"  - **{prefix}** ({len(cols)}列):")
                    for col in cols:
                        print(f"    - {col}")
            print()
        else:
            print(f"### {label}")
            print(f"- **ファイル**: `{path}`")
            print(f"- **存在しない**: {result.get('error', 'N/A')}")
            print()
    
    # サマリー
    print("\n## C. 確定事項サマリー\n")
    
    # 最も完全なファイルを特定
    main_analysis = inspect_parquet(
        "artifacts/phase56_full_20260104_024221/labels_tb500_force_csj20_fill_ui.parquet",
        "メイン分析ファイル"
    )
    
    if main_analysis["exists"]:
        categorized = format_columns_by_prefix(main_analysis['columns'])
        print("### 話者特徴量の実体（analysis/v1）")
        print(f"- **ファイル**: `{main_analysis['path']}`")
        print(f"- **総列数**: {len(main_analysis['columns'])}")
        print()
        
        for prefix in ["IX_", "FILL_", "PG_", "RESP_", "SFP_", "CL_"]:
            cols = categorized.get(prefix, [])
            if cols:
                print(f"#### {prefix}系 ({len(cols)}列)")
                for col in cols:
                    print(f"- {col}")
                print()
        
        # LLM関連
        llm_cols = [c for c in main_analysis['columns'] if 'label' in c.lower() or 'prompt' in c.lower() or 'llm' in c.lower()]
        if llm_cols:
            print(f"#### LLM関連 ({len(llm_cols)}列)")
            for col in llm_cols:
                print(f"- {col}")
            print()

if __name__ == "__main__":
    main()
