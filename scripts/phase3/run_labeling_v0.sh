#!/usr/bin/env bash
set -euo pipefail

: "${OUT_GOLD:?need env OUT_GOLD}"
: "${ANALYSIS_OUT:?need env ANALYSIS_OUT}"
: "${S3_KMS_KEY_ARN:?need env S3_KMS_KEY_ARN}"

: "${AWS_REGION:=ap-northeast-1}"
: "${MODEL_ID:=global.anthropic.claude-opus-4-5-20251101-v1:0}"
: "${MAX_TOKENS:=1400}"
: "${TEMPERATURE:=0.2}"

export AWS_REGION MODEL_ID MAX_TOKENS TEMPERATURE

AN_V13="${ANALYSIS_OUT}/gold=v13"

LOCAL_DIR="artifacts/phase3"
EX_DIR="${LOCAL_DIR}/examples_v13"
mkdir -p "${EX_DIR}" docs/report

echo "== Phase3-2: LLM labeling v0 (HTML report) =="
echo "AN_V13=${AN_V13}"
echo "MODEL_ID=${MODEL_ID}"
echo "AWS_REGION=${AWS_REGION}"

echo "== [0] Sync analysis examples parquet (optional) =="
aws s3 sync "${AN_V13}/examples" "${EX_DIR}" --exclude "*" --include "*.parquet" || true
N_EX="$(find "${EX_DIR}" -type f -name "*.parquet" | wc -l | tr -d ' ')"
echo "examples parquet files: ${N_EX}"

OUTLIERS_CSV="${LOCAL_DIR}/outliers_v0_topK.csv"
if [[ ! -f "${OUTLIERS_CSV}" ]]; then
  echo "ERROR: missing ${OUTLIERS_CSV}"
  exit 2
fi

LABELS_S3="${AN_V13}/labels/labels_v0.parquet"
LABELS_LOCAL="${LOCAL_DIR}/labels_v0.parquet"

echo "== [1] Run labeling (writes to S3; SSE-KMS enforced) =="
python scripts/phase3/label_outliers_with_bedrock_v0.py \
  --outliers_csv "${OUTLIERS_CSV}" \
  --examples_dir "${EX_DIR}" \
  --out_parquet "${LABELS_S3}"

echo "== [2] Download labels and build HTML report =="
aws s3 cp "${LABELS_S3}" "${LABELS_LOCAL}"

python scripts/phase3/make_labels_v0_report_html.py \
  --labels_parquet "${LABELS_LOCAL}" \
  --out_html "docs/report/labels_v0.html" \
  --title "LLM labeling v0 (Bedrock Claude Opus 4.5)" \
  --subtitle "Phase3-2: outliers_v0_topK -> labels_v0 (GitHub Pages)"

echo "== DONE =="
echo "labels(s3):    ${LABELS_S3}"
echo "labels(local): ${LABELS_LOCAL}"
echo "report(local): docs/report/labels_v0.html"

