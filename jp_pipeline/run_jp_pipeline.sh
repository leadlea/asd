#!/usr/bin/env bash
set -euo pipefail
CONF="${1:-./jp_pipeline/config_jp.yaml}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"
[ -f jp_pipeline/jp_pipeline/__init__.py ] || : > jp_pipeline/jp_pipeline/__init__.py
PYTHONPATH="$REPO_ROOT/jp_pipeline" python -m jp_pipeline.compute_metrics "$CONF"
DASH=$(sed -n 's/^[[:space:]]*dashboard_html:[[:space:]]*//p' "$CONF" | head -n1)
echo "Done. Dashboard -> ${DASH:-<set output.dashboard_html in config>}"
