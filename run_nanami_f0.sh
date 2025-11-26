#!/usr/bin/env bash
set -euo pipefail

# リポジトリルートへ
repo_root="$(cd "$(dirname "$0")" && pwd)"
cd "$repo_root"

# 出力ルート（F0版用に別ディレクトリにする）
OUT_ROOT="out_f0/audio/Nanami"
mkdir -p "$OUT_ROOT"

# Whisper は MPS を試しつつ、ダメなら CPU にフォールバック（asr_whisper.py でハンドリング済み）
export WHISPER_DEVICE="mps"

echo "[run_nanami_f0] WHISPER_DEVICE=${WHISPER_DEVICE}"
echo "[run_nanami_f0] output root=${OUT_ROOT}"

# Nanami 配下の mp3 をすべて処理（10129〜20319 の8本）
for f in audio/Nanami/*.mp3; do
  stem="$(basename "$f" .mp3)"
  echo "[run_nanami_f0] processing $f -> ${OUT_ROOT}/${stem}"

  python audio_mvp/audio_analyze.py \
    --in "$f" \
    --lang ja \
    --model small \
    --out "${OUT_ROOT}/${stem}" \
    --auto_assign_child_by_f0 true \
    --assign_mode f0
done

echo "Done. See ${OUT_ROOT}/<stem>/report.html"
