#!/usr/bin/env bash
set -euo pipefail

# =========================
# Inventory RAW CSJ/CEJC buckets
# Usage:
#   bash scripts/phase3/run_inventory_raw_buckets.sh
#
# Options:
#   MAX_KEYS=50000            # objects scanned per bucket (partial scan)
#   REGION=ap-northeast-1
#   OUT_DIR=artifacts/inventory_raw
#   TREE_DEPTH=3
#   MAX_SAMPLES_PER_EXT=12
# =========================

REGION="${REGION:-${AWS_DEFAULT_REGION:-ap-northeast-1}}"
MAX_KEYS="${MAX_KEYS:-50000}"
OUT_DIR="${OUT_DIR:-artifacts/inventory_raw}"
TREE_DEPTH="${TREE_DEPTH:-3}"
MAX_SAMPLES_PER_EXT="${MAX_SAMPLES_PER_EXT:-12}"

BUCKETS=(
  "leadlea-csj-backup-982534361827-20251223-002451"
  "leadlea-cejc-backup-982534361827-20251219"
)

echo "== Inventory RAW buckets =="
echo "REGION=$REGION"
echo "MAX_KEYS=$MAX_KEYS"
echo "OUT_DIR=$OUT_DIR"
echo "TREE_DEPTH=$TREE_DEPTH"
echo "MAX_SAMPLES_PER_EXT=$MAX_SAMPLES_PER_EXT"
mkdir -p "$OUT_DIR"

python scripts/phase3/inventory_s3_buckets_assets.py \
  --region "$REGION" \
  --out_dir "$OUT_DIR" \
  --max_keys "$MAX_KEYS" \
  --tree_depth "$TREE_DEPTH" \
  --max_samples_per_ext "$MAX_SAMPLES_PER_EXT" \
  --buckets "${BUCKETS[@]}" \
  --write_html \
  --write_md

echo "== DONE =="
ls -lh "$OUT_DIR" | sed -n '1,120p'
echo ""
echo "Open:"
echo "  $OUT_DIR/inventory_summary.html"

