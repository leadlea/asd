#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import boto3
import pandas as pd

KEY_COLS = ["dataset", "speaker_id", "conversation_id"]

FEATURE_COLS = [
    "summary",
    "labels_json",
    "primary_label",
    "atypicality_v0",
    "prompt_features_used_json",
    "top_contrib_json",
    "used_features_json",
    "needs_more_context",
    "missing_json",
    "n_utt_total",
    "n_pairs_total",
    "score",
    "tb",
    "PG_speech_ratio",
    "PG_pause_mean",
    "PG_overlap_rate",
    "PG_resp_gap_mean",
    "PG_resp_overlap_rate",
    "IX_prev_question_rate",
    "IX_oirmarker_rate",
    "IX_yesno_rate",
    "IX_lex_overlap_mean",
    "IX_topic_drift_mean",
    "FILL_cnt_total",
    "FILL_rate_per_100chars",
    "FILL_z_log_rate_per_100chars",
    "RESP_NE_AIZUCHI_RATE",
    "RESP_NE_ENTROPY",
    "RESP_YO_ENTROPY",
    "FILL_cnt_ano",
    "FILL_cnt_sono",
    "PG_speech_time",
    "PG_resp_gap_p50",
]

def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def normalize(v):
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass
    if hasattr(v, "item"):
        try:
            return v.item()
        except Exception:
            pass
    if isinstance(v, (dict, list, str, int, float, bool)) or v is None:
        return v
    return str(v)

def extract_json_obj(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))

SYSTEM_PROMPT = """あなたは会話閲覧ダッシュボード向けの“見出し再命名アシスタント”です。
目的は、既存の style_title の重複を減らしながら、意味を保ったまま、より遊び心のある別名に言い換えることです。

必須ルール:
- 日本語で返す
- JSONオブジェクトだけを返す
- 既存タイトルと意味は近く保つが、言い回しはしっかり変える
- 以下の禁止タイトル・禁止語尾に寄せない
- 「聞き役さん」「ためらいがちな聞き役」「うなずき専門」などの量産パターンを避ける
- 悪意・侮辱・差別は避ける
- できるだけ情景・キャラ・場面が浮かぶ言い方にする
- 「モブ」「住民」「職人」「達人」「マシンガン」もなるべく避ける

返却JSON:
{
  "style_title": "図書室でうなずく副音声",
  "style_title_reason": "既存の意味を保ちつつ、重複表現を避けて言い換えた理由",
  "style_title_confidence": 0.79,
  "style_title_prompt_features_used": ["summary", "labels_json", "RESP_NE_AIZUCHI_RATE"]
}
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, type=Path)
    ap.add_argument("--sidecar", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--model-id", required=True)
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--dup-threshold", type=int, default=5)
    ap.add_argument("--sleep-sec", type=float, default=0.2)
    ap.add_argument("--temperature", type=float, default=0.9)
    args = ap.parse_args()

    base = pd.read_parquet(args.base)
    side = pd.read_parquet(args.sidecar)

    merged = base.merge(side, on=KEY_COLS, how="inner", validate="one_to_one")
    vc = merged["style_title"].value_counts()

    target_mask = (merged["style_title"] == "命名保留") | (merged["style_title"].map(vc) >= args.dup_threshold)
    targets = merged[target_mask].copy()
    print("rewrite targets =", len(targets))

    banned_titles = vc[vc >= args.dup_threshold].index.tolist()
    client = boto3.client("bedrock-runtime", region_name=args.region)

    updated = side.copy()

    for i, row in targets.iterrows():
        payload = {}
        for c in FEATURE_COLS:
            if c in row.index:
                payload[c] = normalize(row[c])

        user_prompt = f"""# 現在のタイトル
{row['style_title']}

# 避けたい大量重複タイトル
{json.dumps(banned_titles, ensure_ascii=False)}

# 会話情報
{json.dumps(payload, ensure_ascii=False, indent=2)}

# 指示
- 現在タイトルの意味を大きく外さない
- でも表現はしっかり変える
- 大量重複タイトルやその類型に寄せない
- より情景が浮かぶ、少し遊び心のある見出しにする
- JSONのみ返す
"""

        resp = client.converse(
            modelId=args.model_id,
            system=[{"text": SYSTEM_PROMPT}],
            messages=[{"role": "user", "content": [{"text": user_prompt}]}],
            inferenceConfig={"temperature": args.temperature, "maxTokens": 300},
        )
        texts = []
        for blk in resp.get("output", {}).get("message", {}).get("content", []):
            if "text" in blk:
                texts.append(blk["text"])
        raw = "\n".join(texts).strip()
        obj = extract_json_obj(raw)

        mask = (
            (updated["dataset"] == row["dataset"]) &
            (updated["speaker_id"] == row["speaker_id"]) &
            (updated["conversation_id"] == row["conversation_id"])
        )

        updated.loc[mask, "style_title"] = str(obj.get("style_title") or row["style_title"])
        updated.loc[mask, "style_title_reason"] = str(obj.get("style_title_reason") or row["style_title_reason"])
        updated.loc[mask, "style_title_confidence"] = float(obj.get("style_title_confidence") or row["style_title_confidence"])
        updated.loc[mask, "style_title_prompt_features_used_json"] = json.dumps(
            obj.get("style_title_prompt_features_used") or [],
            ensure_ascii=False
        )
        updated.loc[mask, "style_title_model_id"] = args.model_id
        updated.loc[mask, "style_title_created_at"] = utc_now_iso()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    updated.to_parquet(args.output, index=False)
    print(f"DONE: wrote {len(updated)} rows -> {args.output}")

if __name__ == "__main__":
    main()
