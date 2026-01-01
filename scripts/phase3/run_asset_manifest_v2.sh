#!/usr/bin/env bash
set -euo pipefail

: "${CSJ_RAW:?need env CSJ_RAW}"
: "${CEJC_RAW:?need env CEJC_RAW}"
: "${S3_KMS_KEY_ARN:?need env S3_KMS_KEY_ARN}"
: "${ANALYSIS_OUT:?need env ANALYSIS_OUT}"

METRICS_DIR="${METRICS_DIR:-artifacts/phase3/metrics_v13}"
CSJ_RELEASE_PREFIX="${CSJ_RELEASE_PREFIX:-csj/CSJ-9th_merged_20251221_142323}"
CEJC_ROOT_PREFIX="${CEJC_ROOT_PREFIX:-CEJC/data/}"

LOCAL_OUT="${LOCAL_OUT:-artifacts/tmp_meta/asset_manifest_v2.parquet}"
OUT_S3="${OUT_S3:-$ANALYSIS_OUT/gold=v13/assets/asset_manifest_v2.parquet}"

echo "== asset_manifest v2 =="
echo "CSJ_RAW=$CSJ_RAW"
echo "CEJC_RAW=$CEJC_RAW"
echo "METRICS_DIR=$METRICS_DIR"
echo "CSJ_RELEASE_PREFIX=$CSJ_RELEASE_PREFIX"
echo "CEJC_ROOT_PREFIX=$CEJC_ROOT_PREFIX"
echo "LOCAL_OUT=$LOCAL_OUT"
echo "OUT_S3=$OUT_S3"

mkdir -p "$(dirname "$LOCAL_OUT")"

python scripts/phase3/build_asset_manifest_v2.py \
  --metrics_dir "$METRICS_DIR" \
  --csj_raw "$CSJ_RAW" \
  --cejc_raw "$CEJC_RAW" \
  --csj_release_prefix "$CSJ_RELEASE_PREFIX" \
  --cejc_root_prefix "$CEJC_ROOT_PREFIX" \
  --out_local "$LOCAL_OUT" \
  --upload_s3 "$OUT_S3" \
  --kms_key_arn "$S3_KMS_KEY_ARN"

echo "== quick check: CEJC wav coverage (raw vs manifest) =="
aws s3 ls "$CEJC_RAW/CEJC/data/" --recursive \
  | awk '{print $4}' \
  | grep -Ei '\.wav$' \
  | grep -oE 'C[0-9]{3}_[0-9]{3}' \
  | sort -u > artifacts/tmp_meta/cejc_raw_wav_ids.txt

python - <<'PY'
import pandas as pd
raw=set(open("artifacts/tmp_meta/cejc_raw_wav_ids.txt").read().split())
df=pd.read_parquet("artifacts/tmp_meta/asset_manifest_v2.parquet")
man=set(df[(df.dataset=="cejc") & (df.has_wav==True)].conversation_id.astype(str))
missing=sorted(raw-man)
print("raw wav ids:", len(raw))
print("manifest has_wav:", len(man))
print("missing (raw - manifest):", missing)
PY

echo "== done =="
echo "local: $LOCAL_OUT"
echo "s3:    $OUT_S3"

