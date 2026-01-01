#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import re
import subprocess
from typing import Dict, List, Optional, Tuple

import pandas as pd


RE_CSJ_ID = re.compile(r"^[ASRDN]\d{2}[MF]\d{4}$")
RE_CEJC_ID = re.compile(r"^C\d{3}_\d{3}$")

# CEJC: C001_001_IC01.wav / C001_001_GP01.mp4 など
RE_CEJC_WAV = re.compile(r"^(C\d{3}_\d{3})_([A-Za-z0-9]+)\.wav$", re.IGNORECASE)
RE_CEJC_MP4 = re.compile(r"^(C\d{3}_\d{3})_([A-Za-z0-9]+)\.mp4$", re.IGNORECASE)


def _run(cmd: List[str]) -> str:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace")
    if p.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\nSTDERR:\n{p.stderr}")
    return p.stdout


def s3_ls_recursive(prefix: str) -> List[str]:
    out = _run(["aws", "s3", "ls", prefix, "--recursive"])
    keys: List[str] = []
    for line in out.splitlines():
        parts = line.strip().split()
        if len(parts) >= 4:
            keys.append(parts[3])
    return keys


def s3_uri_join(root: str, key: str) -> str:
    return f"{root.rstrip('/')}/{key}"


def basename(key: str) -> str:
    return key.rsplit("/", 1)[-1]


def stem(key: str) -> str:
    b = basename(key)
    if "." in b:
        return b.rsplit(".", 1)[0]
    return b


def extract_cejc_conversation_id(key: str) -> Optional[str]:
    """
    CEJC の key から conversation_id (C001_001) を安全に抽出。
    パスに /C001_001/ が入る構造なので、path segment を最優先で拾う。
    """
    for part in key.split("/"):
        if RE_CEJC_ID.fullmatch(part):
            return part
    # フォールバック：ファイル名側から拾う
    st = stem(key)
    # C001_001-luu / C001_001-transUnit など
    if st.startswith("C") and len(st) >= 8:
        m = re.search(r"(C\d{3}_\d{3})", st)
        if m:
            return m.group(1)
    return None


def choose_first_sorted(lst: List[str]) -> str:
    return sorted(lst)[0] if lst else ""


def choose_cejc_textgrid(lst: List[str]) -> str:
    """
    代表TextGrid：
    - transUnit を優先（存在すれば）
    - 次に -luu
    - それ以外は先頭
    """
    if not lst:
        return ""
    s = sorted(lst)
    for k in s:
        if k.lower().endswith("transunit.textgrid"):
            return k
    for k in s:
        if k.lower().endswith("-luu.textgrid"):
            return k
    return s[0]


def choose_cejc_eaf(lst: List[str]) -> str:
    if not lst:
        return ""
    s = sorted(lst)
    for k in s:
        if k.lower().endswith("transunit.eaf"):
            return k
    for k in s:
        if k.lower().endswith("-luu.eaf"):
            return k
    return s[0]


def choose_cejc_mp4(lst: List[str]) -> str:
    if not lst:
        return ""
    s = sorted(lst)
    for k in s:
        if k.lower().endswith("_mix.mp4"):
            return k
    for k in s:
        if k.lower().endswith("_gp01.mp4"):
            return k
    return s[0]


def choose_cejc_wav(lst: List[str]) -> str:
    """
    CEJC wav は話者別なので代表は IC01 を優先、なければ先頭。
    """
    if not lst:
        return ""
    s = sorted(lst)
    for k in s:
        if k.lower().endswith("_ic01.wav"):
            return k
    return s[0]


def build_csj_maps(csj_raw: str, csj_release_prefix: str) -> Dict[str, Dict[str, str]]:
    """
    CSJ: conversation_id -> {wav, textgrid, f0}
    """
    root = csj_raw.rstrip("/")
    rel = csj_release_prefix.strip("/")

    tg_prefix = f"{root}/{rel}/PLABEL/TextGrid/"
    f0_prefix = f"{root}/{rel}/PLABEL/f0/"
    wav_prefix = f"{root}/{rel}/WAV/"

    tg_keys = [k for k in s3_ls_recursive(tg_prefix) if k.lower().endswith(".textgrid")]
    f0_keys = [k for k in s3_ls_recursive(f0_prefix) if k.lower().endswith(".f0")]
    wav_keys = [k for k in s3_ls_recursive(wav_prefix) if k.lower().endswith(".wav")]

    tg_map: Dict[str, str] = {}
    for k in tg_keys:
        cid = stem(k)
        if RE_CSJ_ID.fullmatch(cid):
            tg_map[cid] = s3_uri_join(csj_raw, k)

    f0_map: Dict[str, str] = {}
    for k in f0_keys:
        cid = stem(k)
        if RE_CSJ_ID.fullmatch(cid):
            f0_map[cid] = s3_uri_join(csj_raw, k)

    wav_map: Dict[str, str] = {}
    # WAV/core/<id>.wav があればそれ、無ければ最初
    mm: Dict[str, List[str]] = {}
    for k in wav_keys:
        cid = stem(k)
        if RE_CSJ_ID.fullmatch(cid):
            mm.setdefault(cid, []).append(s3_uri_join(csj_raw, k))
    for cid, lst in mm.items():
        core = [x for x in lst if x.lower().endswith(f"/wav/core/{cid.lower()}.wav")]
        wav_map[cid] = core[0] if core else sorted(lst)[0]

    out: Dict[str, Dict[str, str]] = {}
    for cid in set(list(tg_map.keys()) + list(f0_map.keys()) + list(wav_map.keys())):
        out[cid] = {
            "wav": wav_map.get(cid, ""),
            "textgrid": tg_map.get(cid, ""),
            "f0": f0_map.get(cid, ""),
        }
    return out


def build_cejc_maps(
    cejc_raw: str,
    cejc_root_prefix: str = "CEJC/data/",
) -> Dict[str, Dict[str, object]]:
    """
    CEJC: conversation_id -> lists + representative
    """
    root = cejc_raw.rstrip("/")
    rel = cejc_root_prefix.strip("/") + "/"
    prefix = f"{root}/{rel}"

    keys = s3_ls_recursive(prefix)

    # conv -> type -> list(uri)
    mm: Dict[str, Dict[str, List[str]]] = {}
    # conv -> wav_by_speaker
    wav_by_spk: Dict[str, Dict[str, str]] = {}

    for k in keys:
        lk = k.lower()
        if not (lk.endswith(".wav") or lk.endswith(".textgrid") or lk.endswith(".eaf") or lk.endswith(".mp4")):
            continue

        cid = extract_cejc_conversation_id(k)
        if not cid:
            continue

        uri = s3_uri_join(cejc_raw, k)

        if lk.endswith(".wav"):
            mm.setdefault(cid, {}).setdefault("wav", []).append(uri)
            st = stem(k)  # C001_001_IC01
            m = RE_CEJC_WAV.match(st + ".wav")  # stemには拡張子無しなので足す
            if m:
                spk = m.group(2).upper()
                wav_by_spk.setdefault(cid, {})[spk] = uri

        elif lk.endswith(".textgrid"):
            mm.setdefault(cid, {}).setdefault("textgrid", []).append(uri)
        elif lk.endswith(".eaf"):
            mm.setdefault(cid, {}).setdefault("eaf", []).append(uri)
        elif lk.endswith(".mp4"):
            mm.setdefault(cid, {}).setdefault("mp4", []).append(uri)

    out: Dict[str, Dict[str, object]] = {}
    for cid, d in mm.items():
        wav_list = sorted(d.get("wav", []))
        tg_list = sorted(d.get("textgrid", []))
        eaf_list = sorted(d.get("eaf", []))
        mp4_list = sorted(d.get("mp4", []))

        out[cid] = {
            # representative
            "wav": choose_cejc_wav(wav_list),
            "textgrid": choose_cejc_textgrid(tg_list),
            "eaf": choose_cejc_eaf(eaf_list),
            "mp4": choose_cejc_mp4(mp4_list),
            # lists
            "wav_all": wav_list,
            "textgrid_all": tg_list,
            "eaf_all": eaf_list,
            "mp4_all": mp4_list,
            # per speaker wav map (JSON string for portability)
            "wav_by_speaker_json": json.dumps(wav_by_spk.get(cid, {}), ensure_ascii=False),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics_dir", required=True)
    ap.add_argument("--csj_raw", required=True)
    ap.add_argument("--cejc_raw", required=True)
    ap.add_argument("--csj_release_prefix", default="csj/CSJ-9th_merged_20251221_142323")
    ap.add_argument("--cejc_root_prefix", default="CEJC/data/")
    ap.add_argument("--out_local", required=True)
    ap.add_argument("--upload_s3", default="")
    ap.add_argument("--kms_key_arn", default=os.getenv("S3_KMS_KEY_ARN", ""))
    args = ap.parse_args()

    csj_m = pd.read_parquet(os.path.join(args.metrics_dir, "corpus=csj", "table=metrics_sfp", "part-00000.parquet"))
    cejc_m = pd.read_parquet(os.path.join(args.metrics_dir, "corpus=cejc", "table=metrics_sfp", "part-00000.parquet"))

    csj_ids = sorted(csj_m["conversation_id"].astype(str).unique().tolist())
    cejc_ids = sorted(cejc_m["conversation_id"].astype(str).unique().tolist())

    print("gold csj conversation_ids:", len(csj_ids))
    print("gold cejc conversation_ids:", len(cejc_ids))

    csj_map = build_csj_maps(args.csj_raw, args.csj_release_prefix)
    cejc_map = build_cejc_maps(args.cejc_raw, args.cejc_root_prefix)

    rows = []

    for cid in csj_ids:
        d = csj_map.get(cid, {})
        rows.append(
            {
                "dataset": "csj",
                "conversation_id": cid,
                "wav_s3": d.get("wav", ""),
                "textgrid_s3": d.get("textgrid", ""),
                "eaf_s3": "",
                "mp4_s3": "",
                "f0_s3": d.get("f0", ""),
                # list cols (keep empty for csj)
                "wav_s3_all": [],
                "textgrid_s3_all": [],
                "eaf_s3_all": [],
                "mp4_s3_all": [],
                "wav_by_speaker_json": "{}",
            }
        )

    for cid in cejc_ids:
        d = cejc_map.get(cid, {})
        rows.append(
            {
                "dataset": "cejc",
                "conversation_id": cid,
                "wav_s3": d.get("wav", ""),
                "textgrid_s3": d.get("textgrid", ""),
                "eaf_s3": d.get("eaf", ""),
                "mp4_s3": d.get("mp4", ""),
                "f0_s3": "",
                "wav_s3_all": d.get("wav_all", []),
                "textgrid_s3_all": d.get("textgrid_all", []),
                "eaf_s3_all": d.get("eaf_all", []),
                "mp4_s3_all": d.get("mp4_all", []),
                "wav_by_speaker_json": d.get("wav_by_speaker_json", "{}"),
            }
        )

    df = pd.DataFrame(rows)

    for col in ["wav_s3", "textgrid_s3", "eaf_s3", "mp4_s3", "f0_s3"]:
        df[f"has_{col.replace('_s3','')}"] = df[col].astype(str).str.len() > 0

    # counts of lists (debug/next phase)
    df["n_wav_files"] = df["wav_s3_all"].apply(lambda x: len(x) if isinstance(x, list) else 0)
    df["n_mp4_files"] = df["mp4_s3_all"].apply(lambda x: len(x) if isinstance(x, list) else 0)
    df["n_textgrid_files"] = df["textgrid_s3_all"].apply(lambda x: len(x) if isinstance(x, list) else 0)
    df["n_eaf_files"] = df["eaf_s3_all"].apply(lambda x: len(x) if isinstance(x, list) else 0)

    os.makedirs(os.path.dirname(args.out_local) or ".", exist_ok=True)
    df.to_parquet(args.out_local, index=False)

    def summarize(ds: str):
        g = df[df["dataset"] == ds]
        return {
            "rows": int(len(g)),
            "has_wav": int(g["has_wav"].sum()),
            "has_textgrid": int(g["has_textgrid"].sum()),
            "has_eaf": int(g["has_eaf"].sum()),
            "has_mp4": int(g["has_mp4"].sum()),
            "has_f0": int(g["has_f0"].sum()),
            "mean_n_wav_files": float(g["n_wav_files"].mean()) if len(g) else 0.0,
            "mean_n_textgrid_files": float(g["n_textgrid_files"].mean()) if len(g) else 0.0,
        }

    summary = {"out_local": args.out_local, "csj": summarize("csj"), "cejc": summarize("cejc")}
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.upload_s3:
        cmd = ["aws", "s3", "cp", args.out_local, args.upload_s3]
        if args.kms_key_arn:
            cmd += ["--sse", "aws:kms", "--sse-kms-key-id", args.kms_key_arn]
        _run(cmd)
        print(json.dumps({"uploaded": True, "out_s3": args.upload_s3}, ensure_ascii=False))
    else:
        print(json.dumps({"uploaded": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()

