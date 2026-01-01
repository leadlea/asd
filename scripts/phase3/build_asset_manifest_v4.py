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
RE_CEJC_BASE = re.compile(r"^C\d{3}_\d{3}$", re.IGNORECASE)
RE_CEJC_VARIANT = re.compile(r"^(C\d{3}_\d{3})([a-z])$", re.IGNORECASE)  # C002_006a
RE_CEJC_VARIANT_IN_BASENAME = re.compile(r"^(C\d{3}_\d{3})([a-z])?(?=[_-])", re.IGNORECASE)
RE_CEJC_WAV_BASENAME = re.compile(r"^(C\d{3}_\d{3})([a-z])?_([A-Za-z0-9]+)\.wav$", re.IGNORECASE)


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
    return b.rsplit(".", 1)[0] if "." in b else b


def normalize_cejc_base(cid: str) -> str:
    """
    C002_006a -> C002_006
    C002_006 -> C002_006
    """
    m = RE_CEJC_VARIANT.match(cid.strip())
    return m.group(1) if m else cid.strip()


def extract_cejc_base_from_path(key: str) -> Optional[str]:
    parts = key.split("/")
    for part in reversed(parts):
        if RE_CEJC_BASE.fullmatch(part):
            return part
    return None


def extract_cejc_variant_from_basename(b: str) -> Optional[str]:
    """
    'C002_006a_IC01.wav' -> 'C002_006a'
    'C002_006a-luu.TextGrid' -> 'C002_006a'
    'C001_001_IC01.wav' -> 'C001_001'
    """
    m = RE_CEJC_VARIANT_IN_BASENAME.match(b)
    if not m:
        return None
    base = m.group(1).upper()
    suf = (m.group(2) or "").lower()
    return f"{base}{suf}" if suf else base


def choose_cejc_textgrid(lst: List[str]) -> str:
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
    if not lst:
        return ""
    s = sorted(lst)
    for k in s:
        if k.lower().endswith("_ic01.wav"):
            return k
    return s[0]


def build_csj_map(csj_raw: str, csj_release_prefix: str) -> Dict[str, Dict[str, object]]:
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

    wav_multi: Dict[str, List[str]] = {}
    for k in wav_keys:
        cid = stem(k)
        if RE_CSJ_ID.fullmatch(cid):
            wav_multi.setdefault(cid, []).append(s3_uri_join(csj_raw, k))

    wav_map: Dict[str, str] = {}
    for cid, lst in wav_multi.items():
        core = [x for x in lst if x.lower().endswith(f"/wav/core/{cid.lower()}.wav")]
        wav_map[cid] = core[0] if core else sorted(lst)[0]

    out: Dict[str, Dict[str, object]] = {}
    for cid in set(list(tg_map.keys()) + list(f0_map.keys()) + list(wav_map.keys())):
        wav = str(wav_map.get(cid, ""))
        tg = str(tg_map.get(cid, ""))
        f0 = str(f0_map.get(cid, ""))

        out[cid] = {
            "wav": wav,
            "textgrid": tg,
            "f0": f0,
            "wav_all": [wav] if wav else [],
            "textgrid_all": [tg] if tg else [],
        }
    return out


def build_cejc_variant_map(cejc_raw: str, cejc_root_prefix: str) -> Dict[str, Dict[str, object]]:
    """
    ✅ CEJCは「variant conversation_id」を主キーにして作る。
    goldの conversation_id（C002_006a等）と 1:1 にJOINできる。
    """
    root = cejc_raw.rstrip("/")
    rel = cejc_root_prefix.strip("/") + "/"
    prefix = f"{root}/{rel}"

    keys = s3_ls_recursive(prefix)

    # variant_id -> kind -> list[uri]
    mm: Dict[str, Dict[str, List[str]]] = {}
    wav_by_spk: Dict[str, Dict[str, List[str]]] = {}  # variant_id -> speaker -> [uris]

    def add(vid: str, kind: str, uri: str):
        mm.setdefault(vid, {}).setdefault(kind, []).append(uri)

    for k in keys:
        lk = k.lower()
        if not (lk.endswith(".wav") or lk.endswith(".textgrid") or lk.endswith(".eaf") or lk.endswith(".mp4")):
            continue

        base = extract_cejc_base_from_path(k)
        if not base:
            continue

        b = basename(k)
        vid = extract_cejc_variant_from_basename(b)  # C002_006a or C001_001
        if not vid:
            # まれにパターン外のファイルがあれば base に寄せる
            vid = base.upper()

        uri = s3_uri_join(cejc_raw, k)

        if lk.endswith(".wav"):
            add(vid, "wav", uri)
            m = RE_CEJC_WAV_BASENAME.match(b)
            if m:
                spk = m.group(3).upper()
                wav_by_spk.setdefault(vid, {}).setdefault(spk, []).append(uri)
        elif lk.endswith(".textgrid"):
            add(vid, "textgrid", uri)
        elif lk.endswith(".eaf"):
            add(vid, "eaf", uri)
        elif lk.endswith(".mp4"):
            add(vid, "mp4", uri)

    out: Dict[str, Dict[str, object]] = {}
    for vid, d in mm.items():
        wav_list = sorted(d.get("wav", []))
        tg_list = sorted(d.get("textgrid", []))
        eaf_list = sorted(d.get("eaf", []))
        mp4_list = sorted(d.get("mp4", []))

        out[vid] = {
            "conversation_id": vid,
            "conversation_id_base": normalize_cejc_base(vid).upper(),
            "wav": choose_cejc_wav(wav_list),
            "textgrid": choose_cejc_textgrid(tg_list),
            "eaf": choose_cejc_eaf(eaf_list),
            "mp4": choose_cejc_mp4(mp4_list),
            "wav_all": wav_list,
            "textgrid_all": tg_list,
            "eaf_all": eaf_list,
            "mp4_all": mp4_list,
            "wav_by_speaker_json": json.dumps(wav_by_spk.get(vid, {}), ensure_ascii=False),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics_dir", required=True)
    ap.add_argument("--csj_raw", required=True)
    ap.add_argument("--cejc_raw", required=True)
    ap.add_argument("--csj_release_prefix", required=True)
    ap.add_argument("--cejc_root_prefix", required=True)
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

    csj_map = build_csj_map(args.csj_raw, args.csj_release_prefix)
    cejc_vmap = build_cejc_variant_map(args.cejc_raw, args.cejc_root_prefix)

    rows = []

    # CSJ
    for cid in csj_ids:
        d = csj_map.get(cid, {})
        rows.append(
            dict(
                dataset="csj",
                conversation_id=cid,
                conversation_id_base=cid,
                wav_s3=str(d.get("wav", "")),
                textgrid_s3=str(d.get("textgrid", "")),
                eaf_s3="",
                mp4_s3="",
                f0_s3=str(d.get("f0", "")),
                wav_s3_all=d.get("wav_all", []),
                textgrid_s3_all=d.get("textgrid_all", []),
                eaf_s3_all=[],
                mp4_s3_all=[],
                wav_by_speaker_json="{}",
            )
        )

    # CEJC (goldのIDに完全一致させる)
    miss = 0
    for cid in cejc_ids:
        u = cid.strip()
        d = cejc_vmap.get(u)
        if d is None:
            # 念のため base に落として再検索（goldがbaseのケース）
            base = normalize_cejc_base(u).upper()
            d = cejc_vmap.get(base)
        if d is None:
            miss += 1
            d = {
                "conversation_id": u,
                "conversation_id_base": normalize_cejc_base(u).upper(),
                "wav": "",
                "textgrid": "",
                "eaf": "",
                "mp4": "",
                "wav_all": [],
                "textgrid_all": [],
                "eaf_all": [],
                "mp4_all": [],
                "wav_by_speaker_json": "{}",
            }

        rows.append(
            dict(
                dataset="cejc",
                conversation_id=u,
                conversation_id_base=str(d.get("conversation_id_base", normalize_cejc_base(u).upper())),
                wav_s3=str(d.get("wav", "")),
                textgrid_s3=str(d.get("textgrid", "")),
                eaf_s3=str(d.get("eaf", "")),
                mp4_s3=str(d.get("mp4", "")),
                f0_s3="",
                wav_s3_all=d.get("wav_all", []),
                textgrid_s3_all=d.get("textgrid_all", []),
                eaf_s3_all=d.get("eaf_all", []),
                mp4_s3_all=d.get("mp4_all", []),
                wav_by_speaker_json=str(d.get("wav_by_speaker_json", "{}")),
            )
        )

    df = pd.DataFrame(rows)

    for col in ["wav_s3", "textgrid_s3", "eaf_s3", "mp4_s3", "f0_s3"]:
        df[f"has_{col.replace('_s3','')}"] = df[col].astype(str).str.len() > 0

    df["n_wav_files"] = df["wav_s3_all"].apply(lambda x: len(x) if isinstance(x, list) else 0)
    df["n_textgrid_files"] = df["textgrid_s3_all"].apply(lambda x: len(x) if isinstance(x, list) else 0)
    df["n_eaf_files"] = df["eaf_s3_all"].apply(lambda x: len(x) if isinstance(x, list) else 0)
    df["n_mp4_files"] = df["mp4_s3_all"].apply(lambda x: len(x) if isinstance(x, list) else 0)

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
            "miss_gold_join": int(miss) if ds == "cejc" else 0,
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

