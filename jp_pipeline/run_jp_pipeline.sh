#!/usr/bin/env bash
# run_jp_pipeline.sh (unified)
# .cha → 9分窓 → CSV/HTML を実行し、オプションで GitHub Pages(/docs) または S3/CloudFront に公開します。
# Usage:
#   bash jp_pipeline/run_jp_pipeline.sh \
#     [--config ./jp_pipeline/config_jp.yaml] \
#     [--publish docs|s3] \
#     [--s3-bucket YOUR_BUCKET] \
#     [--s3-prefix asd/jp]
#
# Examples:
#   bash jp_pipeline/run_jp_pipeline.sh --publish docs
#   bash jp_pipeline/run_jp_pipeline.sh --publish s3 --s3-bucket my-bucket --s3-prefix asd/jp
#
# Env (s3):
#   S3_BUCKET, S3_PREFIX (fallback), CF_DIST_ID (optional for invalidation)

set -euo pipefail

# --- defaults ---
CONF="./jp_pipeline/config_jp.yaml"
PUBLISH_MODE=""       # "", "docs", or "s3"
S3_BUCKET="${S3_BUCKET:-${BUCKET:-}}"
S3_PREFIX="${S3_PREFIX:-asd/jp}"
GIT_MSG="${GIT_MSG:-docs(jp): publish JP 9-min dashboard}"

# --- parse args ---
while [ $# -gt 0 ]; do
  case "$1" in
    -c|--config)    CONF="$2"; shift 2 ;;
    --publish)      PUBLISH_MODE="${2:-}"; shift 2 ;;
    --s3-bucket)    S3_BUCKET="${2:-}"; shift 2 ;;
    --s3-prefix)    S3_PREFIX="${2:-}"; shift 2 ;;
    -h|--help)
      sed -n '1,40p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "[warn] unknown arg: $1" >&2; shift ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

# ensure package import path exists
[ -f jp_pipeline/jp_pipeline/__init__.py ] || : > jp_pipeline/jp_pipeline/__init__.py

# --- run pipeline ---
PYTHONPATH="$REPO_ROOT/jp_pipeline" python -m jp_pipeline.compute_metrics "$CONF"

# --- read dashboard_html from YAML (single-line key) ---
DASH_REL="$(awk -F: '/^[[:space:]]*dashboard_html[[:space:]]*:/ {out=$2; sub(/^[[:space:]]+/,"",out); sub(/[[:space:]]+$/,"",out); gsub(/'\''/,"",out); gsub(/"/,"",out); print out; exit}' "$CONF" || true)"
[ -n "$DASH_REL" ] || DASH_REL="docs/jp_miipro_dashboard.html"

# resolve absolute path
case "$DASH_REL" in
  /*) DASH_ABS="$DASH_REL" ;;
  *)  DASH_ABS="$REPO_ROOT/$DASH_REL" ;;
esac

if [ ! -f "$DASH_ABS" ]; then
  echo "[error] dashboard not found: $DASH_ABS" >&2
  exit 1
fi

echo "Done. Dashboard -> \"$DASH_REL\""

# --- publish: docs or s3 ---
if [ -z "${PUBLISH_MODE:-}" ]; then
  exit 0
fi

if [ "$PUBLISH_MODE" = "docs" ]; then
  # Ensure a clean URL under /docs/jp/
  JP_DIR="$REPO_ROOT/docs/jp"
  mkdir -p "$JP_DIR"
  cp -f "$DASH_ABS" "$JP_DIR/index.html"

  # Also add the original dashboard (wherever it is) if it lives in docs/
  ADD_PATHS=( "docs/jp/index.html" )
  case "$DASH_ABS" in
    "$REPO_ROOT"/docs/*) ADD_PATHS+=( "$DASH_REL" ) ;;
  esac

  # Commit & push (best-effort)
  git add "${ADD_PATHS[@]}" || true
  git commit -m "$GIT_MSG" || echo "nothing to commit"
  git push || true

  echo "Published to GitHub Pages (docs). If enabled: https://<org-or-user>.github.io/<repo>/jp/"

elif [ "$PUBLISH_MODE" = "s3" ]; then
  if ! command -v aws >/dev/null 2>&1; then
    echo "[error] aws CLI not found. Install AWS CLI or use --publish docs." >&2
    exit 1
  fi
  if [ -z "${S3_BUCKET:-}" ]; then
    echo "[error] S3 bucket not specified. Use --s3-bucket or set S3_BUCKET/BUCKET env." >&2
    exit 1
  fi

  # Upload as index.html at the given prefix
  aws s3 cp "$DASH_ABS" "s3://$S3_BUCKET/$S3_PREFIX/index.html" \
    --content-type "text/html; charset=utf-8" \
    --cache-control "no-cache"

  # Optional CloudFront invalidation
  if [ -n "${CF_DIST_ID:-}" ]; then
    aws cloudfront create-invalidation \
      --distribution-id "$CF_DIST_ID" \
      --paths "/$S3_PREFIX/*" >/dev/null
    echo "CloudFront invalidation created for /$S3_PREFIX/*"
  fi

  echo "Uploaded → s3://$S3_BUCKET/$S3_PREFIX/index.html"
  echo "If using static website hosting or CDN, access via your configured domain."

else
  echo "[warn] unknown --publish mode: $PUBLISH_MODE (use: docs|s3). Skipping publish." >&2
fi
