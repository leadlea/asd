#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSJ speaker_data.csv から conversation_id (=講演ID) 単位の話者属性を作り、
gold(metrics_sfp) から L/R のうち「発話数が多い側」を main_side として speaker_id=conversation_id:side を付与する。

ポイント:
- speaker_data の講演IDは ":" で複数含まれることがあるので explode
- conversation_id 重複が出る場合は、nr/NaN を欠損扱いとして「埋まりが多い行」を採用（品質スコア）
"""

import argparse
from typing import List

import numpy as np
import pandas as pd


def _is_missing(x) -> bool:
    if x is None:
        return True
    if isinstance(x, float) and np.isnan(x):
        return True
    s = str(x).strip()
    if s == "":
        return True
    if s.lower() in {"nan", "none", "null"}:
        return True
    # CSJでよくある欠損表現
    if s.lower() in {"nr", "n/r"}:
        return True
    return False


def _quality_score_row(row: pd.Series, cols: List[str]) -> int:
    score = 0
    for c in cols:
        if c in row.index and not _is_missing(row[c]):
            score += 1
    return score


def build_conversation_meta(speaker_csv: str, encoding: str = "cp932") -> pd.DataFrame:
    sd = pd.read_csv(speaker_csv, encoding=encoding)

    # 講演ID を展開（":" 区切り対応）
    lec = (
        sd.assign(conversation_id=sd["講演ID"].astype(str).str.split(":"))
        .explode("conversation_id")
        .copy()
    )
    lec["conversation_id"] = lec["conversation_id"].astype(str).str.strip()

    # 欲しい列を英名に寄せる
    lec = lec.rename(
        columns={
            "講演者ID": "csj_speaker_person_id",
            "性別": "sex",
            "生年代": "birth_cohort",
            "出生地": "birth_place",
            "居住年数": "residence_years",
            "居住年数（言語形成期）": "residence_years_lang_period",
            "父出身地": "father_birth_place",
            "母出身地": "mother_birth_place",
            "最終学歴": "education",
            "備考": "note",
        }
    )

    keep_cols = [
        "conversation_id",
        "csj_speaker_person_id",
        "sex",
        "birth_cohort",
        "birth_place",
        "residence_years",
        "residence_years_lang_period",
        "father_birth_place",
        "mother_birth_place",
        "education",
        "note",
    ]
    lec = lec[keep_cols]

    # 品質スコアで conversation_id 重複を解決
    score_cols = [
        "sex",
        "birth_cohort",
        "birth_place",
        "residence_years",
        "residence_years_lang_period",
        "father_birth_place",
        "mother_birth_place",
        "education",
    ]
    lec["_qscore"] = lec.apply(lambda r: _quality_score_row(r, score_cols), axis=1)

    # タイブレーク：
    # 1) _qscore 大
    # 2) residence_years が欠損でない
    # 3) education が欠損でない
    # 4) csj_speaker_person_id が小さい（安定化）
    lec["_res_ok"] = lec["residence_years"].apply(lambda x: 0 if _is_missing(x) else 1)
    lec["_edu_ok"] = lec["education"].apply(lambda x: 0 if _is_missing(x) else 1)

    lec_sorted = lec.sort_values(
        by=["conversation_id", "_qscore", "_res_ok", "_edu_ok", "csj_speaker_person_id"],
        ascending=[True, False, False, False, True],
        kind="mergesort",
    )

    # 代表行を採用
    best = lec_sorted.drop_duplicates("conversation_id", keep="first").copy()

    # 重複レポート（参考）
    dup = lec[lec.duplicated("conversation_id", keep=False)].copy()
    print("dup_conversation_id:", dup["conversation_id"].nunique(), "dup_rows:", len(dup))

    # 後始末
    best = best.drop(columns=["_qscore"], errors="ignore")
    return best


def infer_main_side(metrics_sfp_parquet: str) -> pd.DataFrame:
    m = pd.read_parquet(metrics_sfp_parquet)

    # speaker_id は L/R の想定
    pv = (
        m.pivot_table(index="conversation_id", columns="speaker_id", values="n_utt", aggfunc="sum")
        .fillna(0.0)
        .copy()
    )
    pv.columns = [f"n_utt_{c}" for c in pv.columns]
    for col in ["n_utt_L", "n_utt_R"]:
        if col not in pv.columns:
            pv[col] = 0.0

    pv["main_side"] = pv[["n_utt_L", "n_utt_R"]].idxmax(axis=1).str.replace("n_utt_", "", regex=False)
    return pv.reset_index()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--speaker_data_csv", required=True, help="artifacts/tmp_meta/csj_speaker_data.csv")
    ap.add_argument(
        "--metrics_sfp_parquet",
        required=True,
        help="artifacts/phase3/metrics_v13/corpus=csj/table=metrics_sfp/part-00000.parquet",
    )
    ap.add_argument("--out", required=True, help="artifacts/tmp_meta/csj_speaker_meta_v0.parquet")
    ap.add_argument("--encoding", default="cp932")
    args = ap.parse_args()

    conv_meta = build_conversation_meta(args.speaker_data_csv, encoding=args.encoding)
    side = infer_main_side(args.metrics_sfp_parquet)

    # goldに出てくる conversation_id のみ残す（metrics側にあるものが対象）
    conv_meta = conv_meta.merge(side, on="conversation_id", how="inner")

    conv_meta["speaker_id"] = conv_meta["conversation_id"].astype(str) + ":" + conv_meta["main_side"].astype(str)
    conv_meta["dataset"] = "csj"

    out_cols = [
        "dataset",
        "conversation_id",
        "speaker_id",
        "main_side",
        "n_utt_L",
        "n_utt_R",
        "csj_speaker_person_id",
        "sex",
        "birth_cohort",
        "birth_place",
        "residence_years",
        "residence_years_lang_period",
        "father_birth_place",
        "mother_birth_place",
        "education",
        "note",
    ]
    out = conv_meta[out_cols].copy()

    out.to_parquet(args.out, index=False)

    print("wrote:", args.out)
    print("rows:", len(out), "unique conv:", out["conversation_id"].nunique())
    print(out[["conversation_id", "speaker_id", "main_side", "n_utt_L", "n_utt_R", "sex", "birth_cohort", "education"]]
          .head(15).to_string(index=False))


if __name__ == "__main__":
    main()

