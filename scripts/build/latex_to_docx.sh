#!/usr/bin/env bash
#
# latex_to_docx.sh - paper1_ja.tex を pandoc で docx 化する再現スクリプト
#
# 目的: 山下先生(Word派)・宗田さん・BRM(Word中心)の協働/レビュー/投稿面として、
#       LaTeX(数値・再現ソース) から docx を再現可能に生成する。
#       既存 paper1_ja_st.docx のレイアウトを --reference-doc で再利用する(宗田さん助言)。
#
# 設計上の安全策:
#   - paper1_ja_st.docx(チームの校閲正本)は絶対に上書きしない。出力は build/ 配下の別名。
#   - reference-doc は「スタイルのみ」流用される(本文内容はコピーされない)。
#   - 画像は graphicspath を pandoc が無視するため --resource-path で解決する。
#   - 参考文献は thebibliography(in-file)。.bib/citeproc は不要。
#
# 使い方:
#   bash scripts/build/latex_to_docx.sh                # 既定: paper1_ja.tex -> build/paper1_ja_pandoc.docx
#   bash scripts/build/latex_to_docx.sh INPUT OUTPUT REFDOC
#
# 前提: pandoc がインストール済み(pandoc 3.x で動作確認)。リポジトリルートから実行すること。

set -euo pipefail

# --- リポジトリルートへ移動(\input の相対パス解決のため) ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

# --- 引数(既定値つき) ---
INPUT="${1:-paper1_ja.tex}"
OUTPUT="${2:-build/paper1_ja_pandoc.docx}"
REFDOC="${3:-paper1_ja_st.docx}"
RESOURCE_PATH=".:reports/paper_figs_v2"

# --- 前提チェック ---
if ! command -v pandoc >/dev/null 2>&1; then
  echo "[ERROR] pandoc が見つかりません。インストール例: brew install pandoc" >&2
  exit 1
fi

if [[ ! -f "${INPUT}" ]]; then
  echo "[ERROR] 入力ファイルがありません: ${INPUT}" >&2
  exit 1
fi

# --- 出力先(build/)を上書き安全に用意 ---
mkdir -p "$(dirname "${OUTPUT}")"

# 安全ガード: 出力が校閲正本 paper1_ja_st.docx を指していたら中断
case "$(basename "${OUTPUT}")" in
  paper1_ja_st.docx)
    echo "[ERROR] 出力先が校閲正本 paper1_ja_st.docx です。上書き禁止のため中断します。" >&2
    exit 1
    ;;
esac

# --- reference-doc は存在する場合のみ使用 ---
REF_ARGS=()
if [[ -f "${REFDOC}" ]]; then
  REF_ARGS=(--reference-doc="${REFDOC}")
  echo "[INFO] reference-doc を使用(スタイル流用): ${REFDOC}"
else
  echo "[WARN] reference-doc が見つかりません(${REFDOC})。pandoc 既定スタイルで出力します。"
fi

echo "[INFO] 変換: ${INPUT} -> ${OUTPUT}"
pandoc "${INPUT}" \
  --from=latex \
  --to=docx \
  --output="${OUTPUT}" \
  --resource-path="${RESOURCE_PATH}" \
  --mathml \
  "${REF_ARGS[@]}"

echo "[OK] 生成完了: ${OUTPUT}"
echo "[NEXT] Word で開いて図表・見出し・数式・参考文献の崩れを確認してください。"
