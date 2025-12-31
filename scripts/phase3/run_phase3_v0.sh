#!/usr/bin/env bash
# scripts/phase3/run_phase3_v0.sh
set -euo pipefail

: "${S3_KMS_KEY_ARN:?need env S3_KMS_KEY_ARN}"
: "${OUT_GOLD:?need env OUT_GOLD}"
: "${ANALYSIS_OUT:?need env ANALYSIS_OUT}"

export AWS_PAGER=""

GOLD_V13="${OUT_GOLD}/v13"
AN_V13="${ANALYSIS_OUT}/gold=v13"

LOCAL_DIR="artifacts/phase3"
mkdir -p "${LOCAL_DIR}" docs/report

echo "== Phase3 v0 (B: sync metrics to local; autodetect metrics parquet keys) =="
echo "GOLD_V13=${GOLD_V13}"
echo "AN_V13=${AN_V13}"
echo "LOCAL_DIR=${LOCAL_DIR}"

# ------------------------------------------------------------
# 0) gold/v13 配下から “metricsっぽい parquet” をローカルへ sync
#    - metrics/ 配下
#    - */metrics/ 配下（pairs/metrics, segments/metrics 等）
#    - metrics.parquet 等の単一ファイル
# ------------------------------------------------------------
METRICS_LOCAL="${LOCAL_DIR}/metrics_v13"
mkdir -p "${METRICS_LOCAL}"

echo "== [0] Sync metrics-like parquet from S3 to local =="

aws s3 sync "${GOLD_V13}" "${METRICS_LOCAL}" \
  --exclude "*" \
  --include "metrics*.parquet" \
  --include "metrics/*.parquet" \
  --include "metrics/**/*.parquet" \
  --include "*/metrics/*.parquet" \
  --include "*/metrics/**/*.parquet" \
  --include "*metrics*.parquet"

# 件数チェック
N_PARQUET="$(find "${METRICS_LOCAL}" -type f -name "*.parquet" | wc -l | tr -d ' ')"
echo "Synced parquet files: ${N_PARQUET}"

if [[ "${N_PARQUET}" -eq 0 ]]; then
  echo ""
  echo "ERROR: No 'metrics-like' parquet files were found under ${GOLD_V13}."
  echo "---- Diagnostic: list top objects under gold/v13 (first 80 lines) ----"
  aws s3 ls "${GOLD_V13}/" --recursive | head -n 80 || true
  echo "---- Diagnostic: grep 'metrics' under gold/v13 (first 80 lines) ----"
  aws s3 ls "${GOLD_V13}/" --recursive | grep -i metrics | head -n 80 || true
  echo "---- Local files (should be empty) ----"
  find "${METRICS_LOCAL}" -type f | head -n 80 || true
  exit 2
fi

echo "Local sample files (head 20):"
find "${METRICS_LOCAL}" -type f -name "*.parquet" | head -n 20

# ------------------------------------------------------------
# 1) speaker features
# ------------------------------------------------------------
echo "== [1] Build speaker_features.parquet =="
python scripts/phase3/build_speaker_features.py \
  --metrics "${METRICS_LOCAL}" \
  --out "${AN_V13}/features/speaker_features.parquet" \
  --min_rows 30

# ------------------------------------------------------------
# 2) atypicality score v0
# ------------------------------------------------------------
echo "== [2] Compute atypicality_v0.parquet =="
python scripts/phase3/compute_atypicality_v0.py \
  --features "${AN_V13}/features/speaker_features.parquet" \
  --out "${AN_V13}/scores/atypicality_v0.parquet" \
  --topk 10 \
  --scaler robust_z

# ------------------------------------------------------------
# 3) PDF report (GitHub Pages用：ローカルに作る)
# ------------------------------------------------------------
echo "== [3] Download scores to local and build A4 PDF report =="
aws s3 cp "${AN_V13}/scores/atypicality_v0.parquet" "${LOCAL_DIR}/atypicality_v0.parquet"

python scripts/phase3/make_atypicality_report_pdf.py \
  --scores "${LOCAL_DIR}/atypicality_v0.parquet" \
  --out_pdf "docs/report/atypicality_v0_a4.pdf" \
  --topn 30

echo "== DONE =="
echo "  metrics(local): ${METRICS_LOCAL}"
echo "  features(s3):   ${AN_V13}/features/speaker_features.parquet"
echo "  scores(s3):     ${AN_V13}/scores/atypicality_v0.parquet"
echo "  report(local):  docs/report/atypicality_v0_a4.pdf"

