#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_pragmatics_gold_from_utterances.py

Inputs
- Utterances parquet on S3 (single file), created by etl_sqlite_to_parquet.py
  Robust expected columns:
    - conversation_id (required)
    - speaker_id      (required)
    - text            (required)
    - start_time / startTime (optional)
    - end_time   / endTime   (optional)
    - utt_index        (optional)  ※ if missing, will be created per conversation
    - utterance_id     (optional)  ※ used as tie-breaker if present
    - corpus, unit_type (optional)

Outputs (to S3)
- {out_prefix}/v{out_version}/corpus={corpus}/table=segments/part-00000.parquet
- {out_prefix}/v{out_version}/corpus={corpus}/table=pairs/part-00000.parquet
- {out_prefix}/v{out_version}/corpus={corpus}/table=metrics_sfp/part-00000.parquet
- {out_prefix}/v{out_version}/corpus={corpus}/table=metrics_resp/part-00000.parquet

Notes
- SFP grouping: NE, NE_Q, YO, NO, NA, MON, NONLEX, NONE, OTHER
- pairs are created only on speaker switches within each conversation
- --loose-aizuchi expands aizuchi detection:
  - marker-only NONLEX like "(L)", "(S)", "(X ##)" treated as aizuchi
  - adds more backchannel tokens (へー/へぇ/ああ/そっか etc.)
  - allows mixed 2-3 token short responses if all tokens are in vocab
"""

from __future__ import annotations

import argparse
import math
import os
import re
import tempfile
import unicodedata
from dataclasses import dataclass
from typing import List, Optional, Tuple

import boto3
import numpy as np
import pandas as pd
import pyarrow.parquet as pq


# -----------------------------
# S3 helpers
# -----------------------------

_S3_RE = re.compile(r"^s3://([^/]+)/(.+)$")


def parse_s3_uri(uri: str) -> Tuple[str, str]:
    m = _S3_RE.match(uri)
    if not m:
        raise ValueError(f"Invalid S3 URI: {uri}")
    return m.group(1), m.group(2)


def s3_download_to_temp(uri: str, region: Optional[str] = None) -> str:
    bucket, key = parse_s3_uri(uri)
    tmp = tempfile.NamedTemporaryFile(suffix=".parquet", delete=False).name
    s3 = boto3.client("s3", region_name=region) if region else boto3.client("s3")
    s3.download_file(bucket, key, tmp)
    return tmp


def s3_upload_file(
    local_path: str,
    uri: str,
    region: Optional[str] = None,
    kms_key_arn: Optional[str] = None,
) -> None:
    bucket, key = parse_s3_uri(uri)
    s3 = boto3.client("s3", region_name=region) if region else boto3.client("s3")

    extra = None
    if kms_key_arn:
        extra = {"ServerSideEncryption": "aws:kms", "SSEKMSKeyId": kms_key_arn}

    if extra:
        s3.upload_file(local_path, bucket, key, ExtraArgs=extra)
    else:
        s3.upload_file(local_path, bucket, key)


def df_to_parquet_temp(df: pd.DataFrame) -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=".parquet", delete=False).name
    df.to_parquet(tmp, index=False, engine="pyarrow")
    return tmp


# -----------------------------
# Normalization utilities
# -----------------------------

_RE_TAIL_PUNCT = re.compile(r"[ 　\t\r\n、，。．\.！!？\?\u2026…～〜ー\-：:]+$")
_RE_SPACES = re.compile(r"\s+")
_RE_PARENS_ALL = re.compile(r"\([^)]*\)")
_RE_AT_ANNOT = re.compile(r"@.+$")  # drop trailing "@..."


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s)


def normalize_tail(text: str) -> str:
    """For SFP/question detection: strip bracket annotations and trailing punctuation."""
    if text is None:
        return ""
    s = nfkc(str(text))
    s = _RE_AT_ANNOT.sub("", s)
    s = _RE_PARENS_ALL.sub(" ", s)
    s = s.strip()
    s = _RE_TAIL_PUNCT.sub("", s)
    s = _RE_SPACES.sub(" ", s).strip()
    return s


# -----------------------------
# NONLEX / NONE detection
# -----------------------------

_RE_ANGLE_TAG = re.compile(r"<[^>]+>")  # CSJ: <FV>, <息> etc.
_RE_HAS_JA = re.compile(r"[ぁ-んァ-ン一-龥]")


def is_none_like(text: str) -> bool:
    if text is None:
        return False
    s = nfkc(str(text)).strip()
    return bool(_RE_ANGLE_TAG.search(s))


def is_nonlex_like(text: str) -> bool:
    """
    Treat utterances starting with '(' (after NFKC+strip) as NONLEX,
    except those containing <...> which are classified as NONE.
    """
    if text is None:
        return False
    s = nfkc(str(text)).strip()
    if not s:
        return True
    if is_none_like(s):
        return False
    return s.startswith("(")


# -----------------------------
# Question detection
# -----------------------------

_RE_Q_MARK = re.compile(r"[？\?]\s*$")
_RE_Q_TAIL = re.compile(r"(か|かな|かね|でしょう|でしょ|だろう|だろ|の)$")


def is_question(text: str) -> bool:
    if text is None:
        return False
    raw = nfkc(str(text)).strip()
    if _RE_Q_MARK.search(raw):
        return True
    tail = normalize_tail(raw)
    if not tail:
        return False
    return bool(_RE_Q_TAIL.search(tail))


# -----------------------------
# SFP grouping
# -----------------------------

def sfp_group(text: str) -> str:
    """
    Return one of: NE, NE_Q, YO, NO, NA, MON, NONLEX, NONE, OTHER
    """
    if text is None:
        return "OTHER"
    raw = nfkc(str(text)).strip()
    if not raw:
        return "NONLEX"

    if is_none_like(raw):
        return "NONE"
    if is_nonlex_like(raw):
        return "NONLEX"

    tail = normalize_tail(raw)
    if not tail:
        return "NONLEX"

    q = is_question(raw)

    # MON
    if tail.endswith("もん") or tail.endswith("もんね") or tail.endswith("もんねえ") or tail.endswith("もんねー"):
        return "MON"

    # "よね" as NE / NE_Q
    if tail.endswith("よね"):
        return "NE_Q" if q else "NE"

    # NE / NE_Q
    if tail.endswith("ね"):
        return "NE_Q" if q else "NE"

    # YO
    if tail.endswith("よ"):
        return "YO"

    # NO
    if tail.endswith("の"):
        return "NO"

    # NA
    if tail.endswith("な"):
        return "NA"

    return "OTHER"


# -----------------------------
# Aizuchi detection (improved)
# -----------------------------

_RE_PARENS_CAPTURE = re.compile(r"\(([^)]*)\)")
_RE_AT_END = re.compile(r"@.+$")
# marker-only: sequences of (...) blocks, no Japanese chars
_RE_ONLY_PAREN_BLOCKS = re.compile(r"^(?:\([^)]*\)\s*)+$")


def _paren_to_token(m: re.Match) -> str:
    inside = m.group(1).strip()
    if not inside:
        return " "
    parts = _RE_SPACES.split(inside)
    cand = parts[-1] if parts else ""
    cand = cand.split("|")[0].strip()
    if _RE_HAS_JA.search(cand):
        return " " + cand + " "
    return " "


def norm_for_aizuchi(text: str) -> str:
    if text is None:
        return ""
    s = nfkc(str(text))
    s = _RE_AT_END.sub("", s)
    s = _RE_PARENS_CAPTURE.sub(_paren_to_token, s)
    s = s.strip()
    s = _RE_TAIL_PUNCT.sub("", s)
    s = _RE_SPACES.sub(" ", s).strip()
    return s


def is_marker_only_nonlex(text: str) -> bool:
    """
    True for things like "(L)", "(S)", "(X ##)", "(D #)" ... i.e.
    - consists only of parenthesis blocks
    - contains no Japanese characters
    """
    if text is None:
        return False
    raw = nfkc(str(text)).strip()
    raw = _RE_AT_END.sub("", raw)
    raw = _RE_TAIL_PUNCT.sub("", raw).strip()
    if not raw:
        return False
    if is_none_like(raw):
        return False
    if _RE_HAS_JA.search(raw):
        return False
    return bool(_RE_ONLY_PAREN_BLOCKS.fullmatch(raw))


# Base aizuchi tokens (strict-ish)
AIZUCHI_BASE = {
    "うん", "はい", "ええ", "そう", "なるほど", "へえ", "ふーん", "うーん",
    "あ", "あー", "え", "えー", "おー",
    "そうだね", "そうですね", "そうなんだ", "そうなんです", "そうです",
}

# Loose additions (more permissive)
AIZUCHI_LOOSE_ADD = {
    "ね", "ん", "はー", "んー", "ううん", "はーい",
    "へー", "へぇ", "ああ", "そっか", "そーか", "なるほどね",
    "お",  # "お。" 系の軽い相槌
    "いやー",  # 迷い/驚き/同調として出るケースが多い
}

# repeat patterns like "うん うん", "そう そう", etc.
_RE_REPEAT = re.compile(
    r"^(?P<w>うん|そう|はい|ええ|へえ|へー|へぇ|ふーん|なるほど|うーん|あー|あ|えー|え|おー|ね|ん|はー|んー|ううん|はーい)"
    r"(?:\s+(?P=w))+$"
)


def is_aizuchi(text: str, loose: bool = False) -> bool:
    if text is None:
        return False

    raw = nfkc(str(text)).strip()
    if not raw:
        return False

    # marker-only NONLEX like (L)/(S)/(X ##) -> treat as aizuchi in loose mode
    if loose and is_marker_only_nonlex(raw):
        return True

    s = norm_for_aizuchi(raw)
    if not s:
        return False

    vocab = set(AIZUCHI_BASE)
    if loose:
        vocab |= AIZUCHI_LOOSE_ADD

    # final small-tsu "えっ" -> "え"
    s2 = re.sub(r"[っッ]+$", "", s)

    # exact / normalized match
    if (s in vocab) or (s2 in vocab):
        return True

    # repeated same-token forms
    if _RE_REPEAT.fullmatch(s):
        return True

    # mixed short forms like "うん うーん", "うーん うん" (loose only)
    if loose:
        toks = s.split()
        if 2 <= len(toks) <= 3 and all((t in vocab) for t in toks):
            return True

    return False


def first_token(text: str) -> str:
    s = norm_for_aizuchi(text)
    if not s:
        return ""
    return s.split(" ", 1)[0]


# -----------------------------
# Core pipeline
# -----------------------------

@dataclass
class Config:
    corpus: str
    utterances_s3: str
    out_s3_prefix: str
    out_version: int
    region: Optional[str]
    kms_key_arn: Optional[str]
    loose_aizuchi: bool


def ensure_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    if "startTime" in df.columns and "start_time" not in df.columns:
        rename_map["startTime"] = "start_time"
    if "endTime" in df.columns and "end_time" not in df.columns:
        rename_map["endTime"] = "end_time"
    if rename_map:
        df = df.rename(columns=rename_map)

    required = {"conversation_id", "speaker_id", "text"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"utterances missing columns: {missing}. cols={list(df.columns)}")
    return df


def build_segments(df_u: pd.DataFrame) -> pd.DataFrame:
    df = df_u.copy()

    df["conversation_id"] = df["conversation_id"].astype(str)
    df["speaker_id"] = df["speaker_id"].astype(str)
    df["text"] = df["text"].astype(str)

    sort_cols: List[str] = []
    if "utt_index" in df.columns:
        df["utt_index"] = pd.to_numeric(df["utt_index"], errors="coerce")
        sort_cols.append("utt_index")
    if "start_time" in df.columns:
        df["start_time"] = pd.to_numeric(df["start_time"], errors="coerce")
        sort_cols.append("start_time")
    if "utterance_id" in df.columns:
        df["_utterance_id_num"] = pd.to_numeric(df["utterance_id"], errors="coerce")
        sort_cols.append("_utterance_id_num")

    if not sort_cols:
        df["_row"] = range(len(df))
        sort_cols = ["_row"]

    df = df.sort_values(["conversation_id"] + sort_cols, kind="mergesort")
    df["utt_index"] = df.groupby("conversation_id").cumcount().astype(int)

    if "start_time" not in df.columns:
        df["start_time"] = pd.NA
    if "end_time" not in df.columns:
        df["end_time"] = pd.NA

    df["is_question"] = df["text"].map(is_question).astype(bool)
    df["sfp_group"] = df["text"].map(sfp_group).astype("string")

    out_cols = [
        "conversation_id", "utt_index", "speaker_id",
        "start_time", "end_time",
        "text", "sfp_group", "is_question",
    ]
    return df[out_cols]


def build_pairs(df_seg: pd.DataFrame, loose_aizuchi: bool) -> pd.DataFrame:
    rows = []
    for cid, g in df_seg.groupby("conversation_id", sort=False):
        g2 = g.sort_values("utt_index", kind="mergesort").reset_index(drop=True)
        for i in range(1, len(g2)):
            if str(g2.at[i, "speaker_id"]) == str(g2.at[i - 1, "speaker_id"]):
                continue
            prev = g2.iloc[i - 1]
            resp = g2.iloc[i]
            r_text = str(resp["text"])

            rows.append(
                {
                    "conversation_id": str(cid),
                    "prev_utt_index": int(prev["utt_index"]),
                    "prev_speaker_id": str(prev["speaker_id"]),
                    "prev_text": str(prev["text"]),
                    "prev_sfp_group": str(prev["sfp_group"]),
                    "resp_utt_index": int(resp["utt_index"]),
                    "resp_speaker_id": str(resp["speaker_id"]),
                    "resp_text": r_text,
                    "resp_first_token": first_token(r_text),
                    "resp_is_aizuchi": bool(is_aizuchi(r_text, loose=loose_aizuchi)),
                    "resp_is_question": bool(resp["is_question"]),
                }
            )

    if not rows:
        return pd.DataFrame(
            columns=[
                "conversation_id",
                "prev_utt_index",
                "prev_speaker_id",
                "prev_text",
                "prev_sfp_group",
                "resp_utt_index",
                "resp_speaker_id",
                "resp_text",
                "resp_first_token",
                "resp_is_aizuchi",
                "resp_is_question",
            ]
        )

    return pd.DataFrame(rows)


def build_metrics_sfp(df_seg: pd.DataFrame) -> pd.DataFrame:
    base = df_seg.copy()
    base["speaker_id"] = base["speaker_id"].astype(str)
    base["conversation_id"] = base["conversation_id"].astype(str)

    n_utt = base.groupby(["conversation_id", "speaker_id"], as_index=False).size().rename(columns={"size": "n_utt"})

    vc = (
        base.groupby(["conversation_id", "speaker_id", "sfp_group"])
        .size()
        .rename("n")
        .reset_index()
    )
    pivot = vc.pivot_table(
        index=["conversation_id", "speaker_id"],
        columns="sfp_group",
        values="n",
        fill_value=0,
        aggfunc="sum",
    ).reset_index()

    for col in ["NE", "NE_Q", "YO", "NO", "NA", "MON", "NONLEX", "NONE", "OTHER"]:
        if col not in pivot.columns:
            pivot[col] = 0

    qrate = (
        base.groupby(["conversation_id", "speaker_id"])["is_question"]
        .mean()
        .reset_index()
        .rename(columns={"is_question": "rate_question"})
    )

    dfm = n_utt.merge(pivot, on=["conversation_id", "speaker_id"], how="left").merge(
        qrate, on=["conversation_id", "speaker_id"], how="left"
    )

    dfm = dfm.rename(
        columns={
            "NE": "n_sfp_NE",
            "NE_Q": "n_sfp_NE_Q",
            "YO": "n_sfp_YO",
            "NO": "n_sfp_NO",
            "NA": "n_sfp_NA",
            "MON": "n_sfp_MON",
            "NONLEX": "n_sfp_NONLEX",
            "NONE": "n_sfp_NONE",
            "OTHER": "n_sfp_OTHER",
        }
    )

    for gname in ["NE", "NE_Q", "YO", "NO", "NA", "MON"]:
        dfm[f"rate_sfp_{gname}"] = (dfm[f"n_sfp_{gname}"] / dfm["n_utt"]).where(dfm["n_utt"] > 0, 0.0)

    # validity/coverage: exclude OTHER + NONLEX + NONE
    dfm["n_valid"] = (dfm["n_utt"] - dfm["n_sfp_OTHER"] - dfm["n_sfp_NONLEX"] - dfm["n_sfp_NONE"]).clip(lower=0)
    dfm["coverage"] = (dfm["n_valid"] / dfm["n_utt"]).where(dfm["n_utt"] > 0, 0.0)

    dfm["rate_NE_valid"] = (dfm["n_sfp_NE"] / dfm["n_valid"]).where(dfm["n_valid"] > 0, 0.0)
    dfm["rate_YO_valid"] = (dfm["n_sfp_YO"] / dfm["n_valid"]).where(dfm["n_valid"] > 0, 0.0)

    cols = [
        "conversation_id",
        "speaker_id",
        "n_utt",
        "n_sfp_NE",
        "n_sfp_NE_Q",
        "n_sfp_YO",
        "n_sfp_NO",
        "n_sfp_NA",
        "n_sfp_MON",
        "n_sfp_NONLEX",
        "n_sfp_NONE",
        "n_sfp_OTHER",
        "n_valid",
        "coverage",
        "rate_sfp_NE",
        "rate_sfp_NE_Q",
        "rate_sfp_YO",
        "rate_question",
        "rate_NE_valid",
        "rate_YO_valid",
    ]
    cols = [c for c in cols if c in dfm.columns]
    return dfm[cols]


def _entropy_from_first_token_counts(counts_df: pd.DataFrame, key_cols: List[str], out_col: str) -> pd.DataFrame:
    """
    counts_df columns: key_cols + ['resp_first_token', 'n']
    Vectorized entropy calculation:
      H = - sum_i p_i log2 p_i
    """
    if counts_df.empty:
        return pd.DataFrame(columns=key_cols + [out_col])

    # per-group total
    totals = counts_df.groupby(key_cols)["n"].transform("sum").astype(float)
    p = counts_df["n"].astype(float) / totals
    # p*log2(p)
    plogp = p * np.log2(p)
    ent = (-counts_df.assign(_plogp=plogp).groupby(key_cols)["_plogp"].sum()).reset_index()
    ent = ent.rename(columns={"_plogp": out_col})
    # numerical cleanup
    ent[out_col] = ent[out_col].where(ent[out_col].abs() > 1e-12, 0.0)
    return ent


def build_metrics_resp(df_pairs: pd.DataFrame) -> pd.DataFrame:
    if df_pairs.empty:
        return pd.DataFrame(
            columns=[
                "conversation_id",
                "speaker_id",
                "n_pairs_total",
                "n_pairs_after_NE",
                "n_pairs_after_YO",
                "RESP_NE_AIZUCHI_RATE",
                "RESP_NE_ENTROPY",
                "RESP_YO_ENTROPY",
            ]
        )

    df = df_pairs.copy()
    df["conversation_id"] = df["conversation_id"].astype(str)
    df["resp_speaker_id"] = df["resp_speaker_id"].astype(str)
    df["prev_sfp_group"] = df["prev_sfp_group"].astype(str)

    key = ["conversation_id", "resp_speaker_id"]

    tot = df.groupby(key).size().rename("n_pairs_total").reset_index()

    after_ne = df[df["prev_sfp_group"].isin(["NE", "NE_Q"])].copy()
    after_yo = df[df["prev_sfp_group"] == "YO"].copy()

    n_ne = after_ne.groupby(key).size().rename("n_pairs_after_NE").reset_index()
    n_yo = after_yo.groupby(key).size().rename("n_pairs_after_YO").reset_index()

    ne_rate = (
        after_ne.groupby(key)["resp_is_aizuchi"]
        .mean()
        .rename("RESP_NE_AIZUCHI_RATE")
        .reset_index()
    )

    # ---- Entropy (NO groupby.apply, so no FutureWarning) ----
    def token_counts(sub: pd.DataFrame) -> pd.DataFrame:
        x = sub[key + ["resp_first_token"]].copy()
        x["resp_first_token"] = x["resp_first_token"].fillna("").astype(str)
        x = x[x["resp_first_token"] != ""]
        if x.empty:
            return pd.DataFrame(columns=key + ["resp_first_token", "n"])
        c = x.groupby(key + ["resp_first_token"]).size().rename("n").reset_index()
        return c

    ne_counts = token_counts(after_ne)
    yo_counts = token_counts(after_yo)

    ne_ent = _entropy_from_first_token_counts(ne_counts, key_cols=key, out_col="RESP_NE_ENTROPY")
    yo_ent = _entropy_from_first_token_counts(yo_counts, key_cols=key, out_col="RESP_YO_ENTROPY")

    out = tot.merge(n_ne, on=key, how="left")
    out = out.merge(n_yo, on=key, how="left")
    out = out.merge(ne_rate, on=key, how="left")
    out = out.merge(ne_ent, on=key, how="left")
    out = out.merge(yo_ent, on=key, how="left")

    out["n_pairs_after_NE"] = out["n_pairs_after_NE"].fillna(0).astype(int)
    out["n_pairs_after_YO"] = out["n_pairs_after_YO"].fillna(0).astype(int)
    out["RESP_NE_AIZUCHI_RATE"] = out["RESP_NE_AIZUCHI_RATE"].fillna(0.0).astype(float)
    out["RESP_NE_ENTROPY"] = out["RESP_NE_ENTROPY"].fillna(0.0).astype(float)
    out["RESP_YO_ENTROPY"] = out["RESP_YO_ENTROPY"].fillna(0.0).astype(float)

    out = out.rename(columns={"resp_speaker_id": "speaker_id"})

    cols = [
        "conversation_id",
        "speaker_id",
        "n_pairs_total",
        "n_pairs_after_NE",
        "n_pairs_after_YO",
        "RESP_NE_AIZUCHI_RATE",
        "RESP_NE_ENTROPY",
        "RESP_YO_ENTROPY",
    ]
    return out[cols]


# -----------------------------
# Main
# -----------------------------

def make_out_uri(out_prefix: str, out_version: int, corpus: str, table: str) -> str:
    base = out_prefix.rstrip("/")
    return f"{base}/v{out_version}/corpus={corpus}/table={table}/part-00000.parquet"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, choices=["cejc", "csj"])
    ap.add_argument("--utterances-s3", required=True)
    ap.add_argument("--out-s3-prefix", required=True)
    ap.add_argument("--out-version", type=int, default=1)
    ap.add_argument("--region", default=None)
    ap.add_argument("--kms-key-arn", default=None)
    ap.add_argument("--loose-aizuchi", action="store_true")
    args = ap.parse_args()

    kms = args.kms_key_arn or os.environ.get("S3_KMS_KEY_ARN")

    cfg = Config(
        corpus=args.corpus,
        utterances_s3=args.utterances_s3,
        out_s3_prefix=args.out_s3_prefix,
        out_version=int(args.out_version),
        region=args.region,
        kms_key_arn=kms,
        loose_aizuchi=bool(args.loose_aizuchi),
    )

    # Load utterances
    src_path = s3_download_to_temp(cfg.utterances_s3, region=cfg.region)
    df_u = pq.read_table(src_path).to_pandas()
    df_u = ensure_required_columns(df_u)

    # Build tables
    seg = build_segments(df_u)
    pairs = build_pairs(seg, loose_aizuchi=cfg.loose_aizuchi)
    met_sfp = build_metrics_sfp(seg)
    met_resp = build_metrics_resp(pairs)

    # Write outputs
    out_seg = make_out_uri(cfg.out_s3_prefix, cfg.out_version, cfg.corpus, "segments")
    out_pairs = make_out_uri(cfg.out_s3_prefix, cfg.out_version, cfg.corpus, "pairs")
    out_msfp = make_out_uri(cfg.out_s3_prefix, cfg.out_version, cfg.corpus, "metrics_sfp")
    out_mresp = make_out_uri(cfg.out_s3_prefix, cfg.out_version, cfg.corpus, "metrics_resp")

    for df, uri in [(seg, out_seg), (pairs, out_pairs), (met_sfp, out_msfp), (met_resp, out_mresp)]:
        tmp = df_to_parquet_temp(df)
        s3_upload_file(tmp, uri, region=cfg.region, kms_key_arn=cfg.kms_key_arn)

    print("OK: wrote")
    print(" ", out_seg)
    print(" ", out_pairs)
    print(" ", out_msfp)
    print(" ", out_mresp)

    # ---- Summary prints ----
    print("\n====================")
    print("CORPUS:", cfg.corpus)
    print("segments rows:", len(seg), "pairs rows:", len(pairs), "metrics_sfp:", len(met_sfp), "metrics_resp:", len(met_resp))

    vc = seg["sfp_group"].value_counts()
    ratio = (vc / vc.sum()).round(4)
    out = pd.DataFrame({"count": vc, "ratio": ratio})
    print(out)

    qrate = float(seg["is_question"].mean()) if len(seg) else 0.0
    print("question_rate:", qrate)

    if len(pairs):
        aiz_rate = float(pairs["resp_is_aizuchi"].mean())
        print("\n")
        print("pairs rows:", len(pairs))
        print("aizuchi rate:", aiz_rate)

        short = pairs[(pairs["resp_is_aizuchi"] == False) & (pairs["resp_text"].astype(str).str.len() <= 12)]
        top = short["resp_text"].value_counts().head(20)
        print("\nTOP20 short responses still non-aizuchi:")
        print(top.astype("Int64"))


if __name__ == "__main__":
    main()

