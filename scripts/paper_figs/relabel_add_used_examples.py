import json, re, time, argparse
from pathlib import Path

import boto3

def extract_json(text: str):
    # ```json ... ``` or raw {...}
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError("No JSON object found in model output")
    return json.loads(m.group(0))

SYSTEM = "You are a careful research assistant. Output ONLY valid JSON."

def build_prompt(row):
    # 既存ラベルを尊重しつつ、evidenceを必ず引用させる
    labels = row.get("labels", {})
    examples = row.get("examples", [])
    # 例文は短くして渡す（トークン節約）
    ex_lines = []
    for ex in examples[:5]:
        pid = ex.get("example_id")
        prev = (ex.get("prev_text","") or "")[:120]
        resp = (ex.get("resp_text","") or "")[:120]
        ex_lines.append({"example_id": pid, "prev_text": prev, "resp_text": resp})

    # 主要メトリクス（Paper1）だけ抜く
    keys = [
        "PG_pause_p50","PG_pause_mean","PG_pause_p90",
        "PG_resp_gap_p50","PG_resp_gap_mean","PG_resp_gap_p90",
        "PG_overlap_rate","PG_speech_ratio",
        "FILL_rate_per_100chars","FILL_z_log_rate_per_100chars",
        "CL_fillpg_cluster","CL_pca_x","CL_pca_y",
        "atypicality_v0","dataset","speaker_id"
    ]
    feats = {k: row.get(k) for k in keys if k in row}

    prompt = {
        "task": "Revise the existing label output to be audit-ready.",
        "rules": [
            "Return ONLY valid JSON.",
            "Keep labels close to the existing output unless evidence strongly contradicts it.",
            "You MUST cite evidence: used_examples must include at least 1 example_id if examples are provided.",
            "If you mention a feature name in why, it MUST appear in used_features.",
            "Do NOT diagnose. Treat labels as functional interaction-style hypotheses."
        ],
        "existing_labels": labels,
        "features": feats,
        "examples": ex_lines
    }
    return json.dumps(prompt, ensure_ascii=False)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_jsonl", required=True)
    ap.add_argument("--out_jsonl", required=True)
    ap.add_argument("--model_id", default="global.anthropic.claude-opus-4-5-20251101-v1:0")
    ap.add_argument("--region", default="ap-northeast-1")
    ap.add_argument("--max_rows", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=0.2)
    args = ap.parse_args()

    rt = boto3.client("bedrock-runtime", region_name=args.region)

    inp = Path(args.in_jsonl).read_text(encoding="utf-8").splitlines()
    if args.max_rows and args.max_rows > 0:
        inp = inp[:args.max_rows]

    outp = Path(args.out_jsonl)
    outp.parent.mkdir(parents=True, exist_ok=True)

    with outp.open("w", encoding="utf-8") as f:
        for i, line in enumerate(inp, 1):
            row = json.loads(line)
            prompt = build_prompt(row)

            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 900,
                "temperature": 0,
                "system": SYSTEM,
                "messages": [{"role":"user","content":[{"type":"text","text":prompt}]}],
            }
            resp = rt.invoke_model(modelId=args.model_id, body=json.dumps(body))
            txt = json.loads(resp["body"].read())["content"][0]["text"]

            new_labels = extract_json(txt)
            row["labels"] = new_labels

            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            if args.sleep:
                time.sleep(args.sleep)

            if i % 10 == 0:
                print("processed", i)

    print("wrote:", outp, "rows:", len(inp))

if __name__ == "__main__":
    main()
