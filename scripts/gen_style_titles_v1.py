#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

try:
    import boto3
except Exception:
    boto3 = None

PREFERRED_KEY_COLS = [
    "dataset",
    "speaker_id",
    "conversation_id",
    "conv_id",
    "example_id",
    "row_id",
    "id",
]

PREFERRED_FEATURE_COLS = [
    "summary",
    "labels_json",
    "primary_label",
    "atypicality_v0",
    "prompt_features_used_json",
    "top_contrib_json",
    "used_features_json",
    "needs_more_context",
    "missing_json",
]

FALLBACK_TITLE = "命名保留"

SYSTEM_PROMPT = """あなたは会話閲覧ダッシュボード向けの“見出し命名アシスタント”です。
目的は、厳密ラベルではなく閲覧補助用の軽量な会話スタイル名を付けることです。
既存の summary / labels / 特徴量を根拠に、短く覚えやすく、少し笑えて、しかし悪意や侮辱が強すぎない名前を付けてください。

必須ルール:
- 日本語で返す
- タイトルは 8〜22 文字程度を目安
- 以下の型を優先: 「○○の△△」「△△系」「○○っぽい会話」
- 病気・障害・差別属性・露骨な侮辱・人格否定は禁止
- 実在個人名を使う場合は、広く一般に通じる穏当な範囲に留める
- 既存ラベルをそのまま繰り返すだけは禁止
- タイトルは「会話の○○」ばかりに偏らせない
- できるだけ語感に変化をつける（例: 「○○の△△」「△△系」「○○っぽい会話」）
- 単なる機能説明ではなく、会話の空気感・キャラ感・場面感が浮かぶ名前を優先する
- 遊び心を一段強めてよい。日常コメディ、学校、部活、司会、ラジオ、アニメ主人公、脇役っぽさなどの比喩を歓迎する
- ただし内輪ネタすぎる表現は避け、初見でもなんとなく伝わることを優先する
- 「職人」「達人」「マシンガン」「○○系」への依存は避け、同じ語尾を繰り返しすぎない
- 「モブ」「住民」など、人によっては少し雑に見える語はなるべく避ける
- 代わりに「聞き役」「見守り役」「副音声」「観客席」「司会」「案内役」「相棒」など柔らかい比喩を優先する
- くすっと笑えるが、相手を下げない優しい言い回しを優先する
- 説明は1〜3文で簡潔に
- 根拠に使った入力項目名を列挙する
- JSONオブジェクトだけを返す

返却 JSON schema:
{
  "style_title": "会話のジャイアン",
  "style_title_reason": "要約では主導性が強く、labels と pg/ix 系の特徴から押し出しの強い会話運びが見えるため。侮辱になりすぎない範囲で、キャラが伝わる見出しにした。",
  "style_title_confidence": 0.82,
  "style_title_prompt_features_used": ["summary", "labels_json", "primary_label", "pg", "ix"]
}
"""

USER_PROMPT_TEMPLATE = """以下は1件の会話について、既存パイプラインが生成済みの情報です。
この既存情報は変更しません。あなたの役割は style_title 系だけを補助的に追加することです。

# 入力情報
{payload_json}

# 指示
- 会話スタイル名を1件だけ付けてください
- 既存の厳密ラベルではなく、閲覧補助の“通称”です
- summary / labels / pg / ix / fill 等から連想して命名してください
- 悪意は抑えつつ、少しクスッとする見出しにしてください
- タイトルは「会話の○○」ばかりに偏らせない
- できるだけ語感に変化をつける（例: 「○○の△△」「△△系」「○○っぽい会話」）
- 単なる機能説明ではなく、会話の空気感・キャラ感・場面感が浮かぶ名前を優先する
- 遊び心を一段強めてよい。日常コメディ、学校、部活、司会、ラジオ、アニメ主人公、脇役っぽさなどの比喩を歓迎する
- ただし内輪ネタすぎる表現は避け、初見でもなんとなく伝わることを優先する
- 「職人」「達人」「マシンガン」「○○系」への依存は避け、同じ語尾を繰り返しすぎない
- JSONのみ返してください

# 命名の参考トーン
- 会話のジャイアン
- たらちゃんの鋭いツッコミ
- 池上さんの解説チック
- お天気お姉さんのおふざけ
- 学級委員の交通整理
- 深夜ラジオの合いの手
- 司会者モードの会話
- おそるおそる実況中継
- 給食当番のまじめトーク
- 文化祭MCの前のめり
- ずっと予告編みたいな会話
- ちいさく拍手する観客席
- テレビ横の副音声さん
- 迷子センターのていねい案内
- ツッコミ待ちの前説タイム
- ためらいがちな主人公ボイス
"""




@dataclass
class LLMResult:
    style_title: str
    style_title_reason: str
    style_title_confidence: float
    style_title_prompt_features_used: list[str]
    raw_text: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_jsonable(v: Any) -> Any:
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


def select_key_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in PREFERRED_KEY_COLS if c in df.columns]


def select_feature_cols(df: pd.DataFrame) -> list[str]:
    cols: list[str] = []

    # まずは必須の説明系
    cols.extend([c for c in PREFERRED_FEATURE_COLS if c in df.columns])

    # 次にスタイル命名に効きやすい代表特徴だけを追加
    preferred_metric_prefixes = ("PG_", "IX_", "FILL_", "RESP_")
    preferred_metric_names = [
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
    ]

    for c in preferred_metric_names:
        if c in df.columns:
            cols.append(c)

    # 万一上が少なすぎる場合の保険
    if len(cols) < 8:
        for c in df.columns:
            if c.startswith(preferred_metric_prefixes):
                cols.append(c)

    # 重複除去しつつ順序維持
    cols = list(dict.fromkeys(cols))
    return cols


def build_payload(row: pd.Series, feature_cols: list[str]) -> dict[str, Any]:
    payload = {}
    for c in feature_cols:
        if c in row.index:
            payload[c] = normalize_jsonable(row[c])
    return payload


def extract_json_obj(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("No JSON object found in model response")
    return json.loads(m.group(0))


class BedrockTitleGenerator:
    def __init__(self, region: str, model_id: str, temperature: float = 0.7, max_tokens: int = 300):
        if boto3 is None:
            raise RuntimeError("boto3 is required for Bedrock mode")
        self.model_id = model_id
        self.client = boto3.client("bedrock-runtime", region_name=region)
        self.temperature = temperature
        self.max_tokens = max_tokens

    def generate(self, payload: dict[str, Any]) -> LLMResult:
        user_prompt = USER_PROMPT_TEMPLATE.format(
            payload_json=json.dumps(payload, ensure_ascii=False, indent=2)
        )
        resp = self.client.converse(
            modelId=self.model_id,
            system=[{"text": SYSTEM_PROMPT}],
            messages=[
                {
                    "role": "user",
                    "content": [{"text": user_prompt}],
                }
            ],
            inferenceConfig={
                "temperature": self.temperature,
                "maxTokens": self.max_tokens,
            },
        )
        texts = []
        for blk in resp.get("output", {}).get("message", {}).get("content", []):
            if "text" in blk:
                texts.append(blk["text"])
        raw_text = "\n".join(texts).strip()
        obj = extract_json_obj(raw_text)
        return LLMResult(
            style_title=str(obj.get("style_title") or FALLBACK_TITLE),
            style_title_reason=str(obj.get("style_title_reason") or "モデル応答から理由を抽出できませんでした。"),
            style_title_confidence=float(obj.get("style_title_confidence") or 0.0),
            style_title_prompt_features_used=[str(x) for x in (obj.get("style_title_prompt_features_used") or [])],
            raw_text=raw_text,
        )


class DryRunTitleGenerator:
    def __init__(self, model_id: str = "dryrun.rule-based"):
        self.model_id = model_id

    def generate(self, payload: dict[str, Any]) -> LLMResult:
        summary = json.dumps(payload, ensure_ascii=False)
        if any(k in summary for k in ["主導", "主張", "押し", "強め"]):
            title = "会話のジャイアン"
        elif any(k in summary for k in ["解説", "説明", "丁寧", "整理"]):
            title = "池上さんの解説チック"
        elif any(k in summary for k in ["ツッコミ", "切れ味", "鋭い"]):
            title = "たらちゃんの鋭いツッコミ"
        else:
            title = "お天気お姉さんのおふざけ"
        return LLMResult(
            style_title=title,
            style_title_reason="dry-run のため、入力文字列のキーワードから簡易命名しました。",
            style_title_confidence=0.35,
            style_title_prompt_features_used=list(payload.keys())[:5],
            raw_text="{}",
        )


def load_existing_sidecar(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_parquet(path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--model-id", default="us.anthropic.claude-3-5-sonnet-20241022-v2:0")
    ap.add_argument("--region", default=os.getenv("AWS_REGION", "us-east-1"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sleep-sec", type=float, default=0.0)
    ap.add_argument("--temperature", type=float, default=0.9)
    args = ap.parse_args()

    df = pd.read_parquet(args.input)
    if args.limit and args.limit > 0:
        df = df.head(args.limit).copy()

    key_cols = select_key_cols(df)
    feature_cols = select_feature_cols(df)
    if not feature_cols:
        raise SystemExit("No usable feature columns found. Please inspect the input parquet first.")

    existing = load_existing_sidecar(args.output) if args.resume else None
    completed_keys: set[tuple[Any, ...]] = set()
    if existing is not None and key_cols:
        completed_keys = set(tuple(x) for x in existing[key_cols].itertuples(index=False, name=None))

    generator = DryRunTitleGenerator() if args.dry_run else BedrockTitleGenerator(
        region=args.region,
        model_id=args.model_id,
        temperature=args.temperature,
    )

    rows: list[dict[str, Any]] = []
    if existing is not None:
        rows.extend(existing.to_dict(orient="records"))

    processed = 0
    for i, row in df.iterrows():
        key = tuple(row[c] for c in key_cols) if key_cols else (i,)
        if key in completed_keys:
            continue

        payload = build_payload(row, feature_cols)
        record: dict[str, Any] = {c: normalize_jsonable(row[c]) for c in key_cols}
        record["source_row_number"] = int(i)
        record["style_title_model_id"] = generator.model_id
        record["style_title_created_at"] = utc_now_iso()

        try:
            result = generator.generate(payload)
            title = (result.style_title or "").strip() or FALLBACK_TITLE
            reason = (result.style_title_reason or "").strip() or "モデル応答から理由を抽出できませんでした。"
            confidence = min(max(float(result.style_title_confidence), 0.0), 1.0)
            feature_names = result.style_title_prompt_features_used or list(payload.keys())
        except Exception as e:
            title = FALLBACK_TITLE
            reason = f"style title generation failed: {type(e).__name__}: {e}"
            confidence = 0.0
            feature_names = list(payload.keys())

        record["style_title"] = title
        record["style_title_reason"] = reason
        record["style_title_confidence"] = confidence
        record["style_title_prompt_features_used_json"] = json.dumps(feature_names, ensure_ascii=False)
        rows.append(record)
        processed += 1

        if processed % 20 == 0 or processed == 1:
            out_df = pd.DataFrame(rows)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            out_df.to_parquet(args.output, index=False)
            print(f"checkpoint: wrote {len(out_df)} rows -> {args.output}", file=sys.stderr)

        if args.sleep_sec > 0:
            time.sleep(args.sleep_sec)

    out_df = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_parquet(args.output, index=False)
    print(f"DONE: wrote {len(out_df)} rows -> {args.output}")
    print(f"key_cols={key_cols}")
    print(f"feature_cols={feature_cols}")


if __name__ == "__main__":
    main()
