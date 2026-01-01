#!/usr/bin/env bash
set -euo pipefail

: "${CSJ_RAW:?need env CSJ_RAW}"
: "${CEJC_RAW:?need env CEJC_RAW}"
: "${ANALYSIS_OUT:?need env ANALYSIS_OUT}"

CSJ_RELEASE_PREFIX="${CSJ_RELEASE_PREFIX:-csj/CSJ-9th_merged_20251221_142323}"
CEJC_ROOT_PREFIX="${CEJC_ROOT_PREFIX:-CEJC/data/}"
METRICS_DIR="${METRICS_DIR:-artifacts/phase3/metrics_v13}"
LOCAL_OUT="${LOCAL_OUT:-artifacts/tmp_meta/asset_manifest_v0.parquet}"
OUT_S3="${OUT_S3:-${ANALYSIS_OUT}/gold=v13/assets/asset_manifest_v0.parquet}"

mkdir -p "$(dirname "$LOCAL_OUT")"

echo "== asset_manifest v0 (CEJC multi-file aware) =="
echo "CSJ_RAW=$CSJ_RAW"
echo "CEJC_RAW=$CEJC_RAW"
echo "CSJ_RELEASE_PREFIX=$CSJ_RELEASE_PREFIX"
echo "CEJC_ROOT_PREFIX=$CEJC_ROOT_PREFIX"
echo "METRICS_DIR=$METRICS_DIR"
echo "LOCAL_OUT=$LOCAL_OUT"
echo "OUT_S3=$OUT_S3"
echo "S3_KMS_KEY_ARN=${S3_KMS_KEY_ARN:-}"

python scripts/phase3/build_asset_manifest_v0.py \
  --metrics_dir "$METRICS_DIR" \
  --csj_raw "$CSJ_RAW" \
  --cejc_raw "$CEJC_RAW" \
  --csj_release_prefix "$CSJ_RELEASE_PREFIX" \
  --cejc_root_prefix "$CEJC_ROOT_PREFIX" \
  --out_local "$LOCAL_OUT" \
  --upload_s3 "$OUT_S3" \
  --kms_key_arn "${S3_KMS_KEY_ARN:-}"

echo "== done =="
echo "local: $LOCAL_OUT"
echo "s3:    $OUT_S3"

