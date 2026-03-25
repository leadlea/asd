import json, re, time, argparse
from pathlib import Path
import boto3

SYSTEM = "You are a careful research assistant. Output ONLY valid JSON. No markdown."

FEAT_RE = re.compile(r"\b(?:PG|FILL|IX|RESP|CL)_[A-Za-z0-9_]+\b")

def extract_json(text: str):
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError("No JSON object found in model output")
    return json.loads(m.group(0))

def feat_mentions(s: str):
    return set(FEAT_RE.findall(s or ""))

def violations(out_labels: dict, examples_present: bool):
    v=[]
    labs = out_labels.get("labels", None)
    if not isinstance(labs, list) or len(labs)==0:
        v.append("labels must be a non-empty list")
        return v
    if examples_present:
        for i, lab in enumerate(labs):
            ue = lab.get("used_examples", None)
            if not isinstance(ue, list) or len(ue)==0:
                v.append(f"label[{i}].used_examples must be non-empty when examples are provided")
    for i, lab in enumerate(labs):
        why = lab.get("why","") or ""
        mentioned = feat_mentions(why)
        uf = set(lab.get("used_features", []) or [])
        missing = sorted([m for m in mentioned if m not in uf])
        if missing:
            v.append(f"label[{i}] why mentions {missing} but missing from used_features")
    return v

def call_bedrock(rt, model_id, prompt, max_tokens=900):
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": 0,
        "system": SYSTEM,
        "messages": [{"role":"user","content":[{"type":"text","text":prompt}]}],
    }
    resp = rt.invoke_model(modelId=model_id, body=json.dumps(body))
    txt = json.loads(resp["body"].read())["content"][0]["text"]
    return extract_json(txt)

def build_prompt(row, max_examples=10):
    labels = row.get("labels", {})
    examples = row.get("examples", []) or []
    ex_lines=[]
    for ex in examples[:max_examples]:
        ex_lines.append({
            "example_id": ex.get("example_id"),
            "prev_text": (ex.get("prev_text","") or "")[:220],
            "resp_text": (ex.get("resp_text","") or "")[:220],
        })

    # 主要特徴だけ渡す（多すぎ防止）
    keys = [k for k in row.keys() if any(k.startswith(p) for p in ("PG_","FILL_","IX_","RESP_","CL_"))]
    keys = sorted(keys)[:120]
    feats = {k: row.get(k) for k in keys}

    schema_example = {
        "labels":[
            {
                "label":"HESITATION|BACKCHANNEL|OTHER|...",
                "confidence":0.0,
                "why":"... cite like [example_id] ...",
                "used_features":["PG_pause_p50","..."],
                "used_examples":["example_id_1","example_id_2"]
            }
        ],
        "summary":"...",
        "needs_more_context": False,
        "missing":[]
    }

    prompt = {
        "task": "Revise the existing label output to be audit-ready.",
        "hard_rules": [
            "Return ONLY valid JSON (no markdown).",
            "Do NOT diagnose. Labels are functional hypotheses.",
            "If examples are provided, EVERY label MUST include used_examples with >=1 example_id.",
            "In why, include citations like [example_id] for evidence you used.",
            "If you mention a feature name (PG_*, FILL_* etc.), it MUST appear in used_features.",
            "labels list must not be empty."
        ],
        "output_schema_example": schema_example,
        "existing_labels": labels,
        "features": feats,
        "examples": ex_lines
    }
    return json.dumps(prompt, ensure_ascii=False)

def build_fix_prompt(bad_json, vios, example_ids):
    prompt = {
        "task": "Fix the JSON to satisfy hard_rules. Return ONLY corrected JSON.",
        "violations": vios,
        "available_example_ids": example_ids,
        "bad_json": bad_json
    }
    return json.dumps(prompt, ensure_ascii=False)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_jsonl", required=True)
    ap.add_argument("--out_jsonl", required=True)
    ap.add_argument("--model_id", default="global.anthropic.claude-opus-4-5-20251101-v1:0")
    ap.add_argument("--region", default="ap-northeast-1")
    ap.add_argument("--max_retries", type=int, default=3)
    ap.add_argument("--max_examples", type=int, default=10)
    ap.add_argument("--sleep", type=float, default=0.2)
    args = ap.parse_args()

    rt = boto3.client("bedrock-runtime", region_name=args.region)

    rows = [json.loads(x) for x in Path(args.in_jsonl).read_text(encoding="utf-8").splitlines() if x.strip()]
    outp = Path(args.out_jsonl)
    outp.parent.mkdir(parents=True, exist_ok=True)

    with outp.open("w", encoding="utf-8") as f:
        for row in rows:
            examples = row.get("examples", []) or []
            ex_present = len(examples) > 0
            ex_ids = [ex.get("example_id") for ex in examples[:args.max_examples] if ex.get("example_id")]

            prompt = build_prompt(row, max_examples=args.max_examples)
            out_labels = call_bedrock(rt, args.model_id, prompt)

            vios = violations(out_labels, ex_present)
            tries = 0
            while vios and tries < args.max_retries:
                tries += 1
                fix_prompt = build_fix_prompt(out_labels, vios, ex_ids)
                out_labels = call_bedrock(rt, args.model_id, fix_prompt)
                vios = violations(out_labels, ex_present)

            if vios:
                miss = list(out_labels.get("missing", []) or [])
                miss.append("rule_violation_unresolved")
                out_labels["missing"] = miss
                out_labels["needs_more_context"] = True

            row["labels"] = out_labels
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            if args.sleep:
                time.sleep(args.sleep)

    print("wrote:", outp, "rows:", len(rows))

if __name__ == "__main__":
    main()
