# scripts/phase3/label_outliers_with_bedrock_v0.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3
import duckdb
import pandas as pd

# =========================
# Config (Bedrock Claude)
# =========================
DEFAULT_MODEL_ID = "global.anthropic.claude-opus-4-5-20251101-v1:0"
MODEL_ID = os.getenv("MODEL_ID", DEFAULT_MODEL_ID)
AWS_REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1"))

MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1400"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))

S3_KMS_KEY_ARN = os.getenv("S3_KMS_KEY_ARN", "").strip()

bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)

# =========================
# JSON helpers
# =========================
def _parse_json_lenient(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    t = text.strip()
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass

    i = t.find("{")
    j = t.rfind("}")
    if i >= 0 and j > i:
        cut = t[i : j + 1]
        try:
            obj = json.loads(cut)
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    return None


def _safe_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def _safe_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _safe_str(x: Any) -> str:
    return str(x) if x is not None else ""


def _clamp01(x: Any) -> float:
    try:
        v = float(x)
    except Exception:
        return 0.0
    return 0.0 if v < 0.0 else 1.0 if v > 1.0 else v


# =========================
# Bedrock invoke
# =========================
def invoke_claude(system: str, user: str, max_tokens: int, temperature: float) -> str:
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": user}],
        "system": system,
    }

    resp = bedrock_runtime.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(body).encode("utf-8"),
        accept="application/json",
        contentType="application/json",
    )

    raw = resp["body"].read()
    obj = json.loads(raw)
    content = obj.get("content") or []
    texts: List[str] = []
    for c in content:
        if isinstance(c, dict) and c.get("type") == "text":
            texts.append(c.get("text") or "")
    return "\n".join(texts).strip()


# =========================
# Label schema
# =========================
ALLOWED_LABELS = [
    "QUESTION",
    "BACKCHANNEL",
    "REPAIR",
    "TOPIC_SHIFT",
    "DISCOURSE_MARKER",
    "HESITATION",
    "NEGATION_OPPOSITION",
    "OTHER",
]

SYSTEM_PROMPT = """あなたは会話データ（日本語）の語用論的な「機能ラベリング」を行う研究アシスタントです。

重要（厳守）:
- 入力に無い会話文・事実は絶対に作らない
- 断定しない。「可能性」「示唆」で述べる
- 出力は必ず JSON のみ（余計な文章は禁止）
- labels は allowed_labels から選ぶ（新しいラベル名を作らない）
- 根拠は「top_features（z）」または「examples（例文）」のどちらかに必ず紐づける
- examples が空/不足の場合は needs_more_context=true に寄せる
"""

USER_TEMPLATE = """以下は「逸脱（atypicality）」上位の対象（outlier候補）です。

# target (outlier)
{target_json}

# top_features (寄与特徴: z の大きい順; これは数値根拠)
{top_features_json}

# examples (参照例文; 入力にある範囲だけ使う。無ければ空)
{examples_json}

# allowed_labels
{allowed_labels_json}

# 出力スキーマ（このJSONだけを返す）
{{
  "labels": [
    {{
      "label": "QUESTION|BACKCHANNEL|REPAIR|TOPIC_SHIFT|DISCOURSE_MARKER|HESITATION|NEGATION_OPPOSITION|OTHER",
      "confidence": 0.0,
      "why": "根拠（top_features の feature 名と z、または examples の index を明示）",
      "used_features": ["feature名...（top_features から）"],
      "used_examples": [0]
    }}
  ],
  "summary": "結論を短く（日本語）",
  "needs_more_context": true,
  "missing": ["不足（例: transcript/examples不足 など）"]
}}

# ルール
- labels は最大3件
- used_features は top_features 内の feature 名のみ
- used_examples は examples の index のみ
- examples が空なら needs_more_context=true を基本にする
"""


# =========================
# Examples loader (optional)
# =========================
@dataclass
class ExamplesIndex:
    con: duckdb.DuckDBPyConnection
    view_name: str
    dataset_col: str
    metric_col: str
    text_col: str


def _guess_col(cols: List[str], candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in cols:
            return c
    for cand in candidates:
        for c in cols:
            if cand.lower() in c.lower():
                return c
    return None


def _metric_key_from_feature(feature: str) -> str:
    s = feature
    s = re.sub(r"^(sfp__|resp__)", "", s)
    s = re.sub(r"(__wmean|__mean|__avg|__sum)$", "", s)
    return s


def build_examples_index(examples_dir: str) -> Optional[ExamplesIndex]:
    root = Path(examples_dir)
    files = sorted([str(p) for p in root.rglob("*.parquet") if p.is_file()])
    if not files:
        return None

    con = duckdb.connect(database=":memory:")

    # ✅ SyntaxError回避：クォート安全に組み立て
    items = ",".join(["'" + p.replace("'", "''") + "'" for p in files])

    con.execute(
        f"CREATE TEMP VIEW examples AS "
        f"SELECT * FROM read_parquet([{items}], union_by_name=true, hive_partitioning=true)"
    )

    sample = con.execute("SELECT * FROM examples LIMIT 1").df()
    cols = list(sample.columns)

    dataset_col = _guess_col(cols, ["dataset", "corpus"])
    metric_col = _guess_col(cols, ["metric_id", "metric", "metric_key", "feature", "metric_name_en"])
    text_col = _guess_col(cols, ["text", "example", "utterance", "snippet", "context", "content"])

    if not dataset_col or not metric_col or not text_col:
        return None

    return ExamplesIndex(con=con, view_name="examples", dataset_col=dataset_col, metric_col=metric_col, text_col=text_col)


def fetch_examples(
    ex: Optional[ExamplesIndex],
    dataset: str,
    metric_keys: List[str],
    per_key: int = 2,
    max_total: int = 6,
) -> List[Dict[str, Any]]:
    if ex is None:
        return []

    out: List[Dict[str, Any]] = []
    seen = set()

    for mk in metric_keys:
        q = f"""
        SELECT
          {ex.metric_col} AS metric,
          {ex.text_col} AS text
        FROM {ex.view_name}
        WHERE {ex.dataset_col} = ?
          AND (CAST({ex.metric_col} AS VARCHAR) = ? OR CAST({ex.metric_col} AS VARCHAR) LIKE ?)
        LIMIT ?
        """
        rows = ex.con.execute(q, [dataset, mk, f"%{mk}%", per_key]).df()
        for _, r in rows.iterrows():
            key = (str(r["metric"]), str(r["text"])[:80])
            if key in seen:
                continue
            seen.add(key)
            out.append({"metric": str(r["metric"]), "text": str(r["text"])})
            if len(out) >= max_total:
                return out
    return out


# =========================
# Core labeling
# =========================
def _extract_top_features(top_contrib_json: Any, topn: int = 6) -> List[Dict[str, Any]]:
    if top_contrib_json is None:
        return []

    obj = None
    if isinstance(top_contrib_json, str):
        try:
            obj = json.loads(top_contrib_json)
        except Exception:
            obj = None
    elif isinstance(top_contrib_json, list):
        obj = top_contrib_json

    feats: List[Dict[str, Any]] = []
    for it in (obj or []):
        if not isinstance(it, dict):
            continue
        f = it.get("feature")
        if not isinstance(f, str):
            continue
        z = it.get("z")
        absz = it.get("abs_z")
        try:
            zf = float(z) if z is not None else None
        except Exception:
            zf = None
        try:
            az = float(absz) if absz is not None else None
        except Exception:
            az = None
        feats.append({"feature": f, "z": zf, "abs_z": az})

    feats.sort(key=lambda d: (d["abs_z"] if d.get("abs_z") is not None else -1.0), reverse=True)
    return feats[:topn]


def _filter_used_features(requested: Any, top_features: List[Dict[str, Any]]) -> List[str]:
    allowed = {d["feature"] for d in top_features if "feature" in d}
    out: List[str] = []
    for x in _safe_list(requested):
        if isinstance(x, str) and x in allowed:
            out.append(x)
    return out


def label_one(
    row: Dict[str, Any],
    examples_index: Optional[ExamplesIndex],
) -> Dict[str, Any]:
    dataset = str(row.get("dataset") or row.get("corpus") or "")
    speaker_id = str(row.get("speaker_id") or "")
    score = row.get("atypicality_v0")

    top_features = _extract_top_features(row.get("top_contrib_json"), topn=6)
    metric_keys = [_metric_key_from_feature(d["feature"]) for d in top_features if d.get("feature")]
    examples = fetch_examples(examples_index, dataset, metric_keys, per_key=2, max_total=6)

    target = {
        "dataset": dataset,
        "speaker_id": speaker_id,
        "atypicality_v0": float(score) if score is not None else None,
    }

    user_prompt = USER_TEMPLATE.format(
        target_json=json.dumps(target, ensure_ascii=False),
        top_features_json=json.dumps(top_features, ensure_ascii=False),
        examples_json=json.dumps(examples, ensure_ascii=False),
        allowed_labels_json=json.dumps(ALLOWED_LABELS, ensure_ascii=False),
    )

    try:
        raw = invoke_claude(SYSTEM_PROMPT, user_prompt, max_tokens=MAX_TOKENS, temperature=TEMPERATURE)
        obj = _parse_json_lenient(raw)
        if not obj:
            return {
                **target,
                "ok": True,
                "labels_json": json.dumps({}, ensure_ascii=False),
                "labels_text": "",
                "fallback": True,
                "error": "llm_json_parse_failed",
                "raw_head": (raw or "")[:800],
                "top_features_json": json.dumps(top_features, ensure_ascii=False),
                "examples_json": json.dumps(examples, ensure_ascii=False),
            }

        labels_in = _safe_list(obj.get("labels"))[:3]
        fixed_labels = []
        for it in labels_in:
            d = _safe_dict(it)
            lab = str(d.get("label") or "OTHER")
            if lab not in ALLOWED_LABELS:
                lab = "OTHER"
            fixed_labels.append(
                {
                    "label": lab,
                    "confidence": _clamp01(d.get("confidence")),
                    "why": _safe_str(d.get("why")).strip(),
                    "used_features": _filter_used_features(d.get("used_features"), top_features),
                    "used_examples": [
                        int(x)
                        for x in _safe_list(d.get("used_examples"))
                        if isinstance(x, int) and 0 <= x < len(examples)
                    ],
                }
            )

        summary = _safe_str(obj.get("summary")).strip()
        needs_more = (
            bool(obj.get("needs_more_context"))
            if obj.get("needs_more_context") is not None
            else (len(examples) == 0)
        )
        missing = [str(x) for x in _safe_list(obj.get("missing")) if isinstance(x, str)]
        if len(examples) == 0 and "examples_missing" not in missing:
            missing.append("examples_missing")

        return {
            **target,
            "ok": True,
            "labels_json": json.dumps(
                {"labels": fixed_labels, "summary": summary, "needs_more_context": needs_more, "missing": missing},
                ensure_ascii=False,
            ),
            "labels_text": summary,
            "fallback": False,
            "error": "",
            "raw_head": "",
            "top_features_json": json.dumps(top_features, ensure_ascii=False),
            "examples_json": json.dumps(examples, ensure_ascii=False),
        }

    except Exception as e:
        return {
            **target,
            "ok": True,
            "labels_json": json.dumps({}, ensure_ascii=False),
            "labels_text": "",
            "fallback": True,
            "error": str(e),
            "raw_head": "",
            "top_features_json": json.dumps(top_features, ensure_ascii=False),
            "examples_json": json.dumps(examples, ensure_ascii=False),
        }


def _require_kms_for_s3(out_path: str) -> None:
    if out_path.startswith("s3://") and not S3_KMS_KEY_ARN:
        raise RuntimeError("S3_KMS_KEY_ARN is required for s3:// output (bucket policy enforces SSE-KMS).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outliers_csv", required=True)
    ap.add_argument("--examples_dir", default="", help="optional local dir of analysis/v1/gold=v13/examples parquet")
    ap.add_argument("--out_parquet", required=True, help="local or s3:// output labels parquet")
    ap.add_argument("--limit", type=int, default=0, help="0=all")
    args = ap.parse_args()

    _require_kms_for_s3(args.out_parquet)

    df = pd.read_csv(args.outliers_csv)

    if "dataset" not in df.columns and "corpus" in df.columns:
        df["dataset"] = df["corpus"]

    for col in ["dataset", "speaker_id", "atypicality_v0", "top_contrib_json"]:
        if col not in df.columns:
            raise RuntimeError(f"outliers_csv must have '{col}' column")

    if args.limit and args.limit > 0:
        df = df.head(args.limit).copy()

    examples_index = build_examples_index(args.examples_dir) if args.examples_dir else None

    rows: List[Dict[str, Any]] = []
    for _, r in df.iterrows():
        rec = label_one(r.to_dict(), examples_index)
        rec["model_id"] = MODEL_ID
        rec["region"] = AWS_REGION
        # ✅ timezone-aware UTC
        rec["created_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        rows.append(rec)

    out_df = pd.DataFrame(rows)

    out_path = args.out_parquet

    if out_path.startswith("s3://"):
        with tempfile.TemporaryDirectory() as td:
            local_out = str(Path(td) / "labels_v0.parquet")
            out_df.to_parquet(local_out, index=False)

            cmd = ["aws", "s3", "cp", local_out, out_path, "--sse", "aws:kms", "--sse-kms-key-id", S3_KMS_KEY_ARN]
            subprocess.run(cmd, check=True)
    else:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        out_df.to_parquet(out_path, index=False)

    print(
        json.dumps(
            {
                "rows": int(len(out_df)),
                "out": out_path,
                "model_id": MODEL_ID,
                "region": AWS_REGION,
                "used_examples": bool(examples_index is not None),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

