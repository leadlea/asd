#!/usr/bin/env bash
set -euo pipefail

# リポジトリルートへ移動
repo_root="$(cd "$(dirname "$0")" && pwd)"
cd "$repo_root"

# デバイス設定（外から指定がなければ mps を使う）
export WHISPER_DEVICE="${WHISPER_DEVICE:-mps}"
export PYANNOTE_DEVICE="${PYANNOTE_DEVICE:-mps}"
export PYTORCH_ENABLE_MPS_FALLBACK="${PYTORCH_ENABLE_MPS_FALLBACK:-1}"

echo "[run_nanami] WHISPER_DEVICE=${WHISPER_DEVICE}"
echo "[run_nanami] PYANNOTE_DEVICE=${PYANNOTE_DEVICE}"

# 出力ディレクトリ
mkdir -p out/audio/Nanami

# Nanami 配下の mp3 を一気に処理
shopt -s nullglob
files=(audio/Nanami/*.mp3)
if [ ${#files[@]} -eq 0 ]; then
  echo "[run_nanami] audio/Nanami/*.mp3 が見つかりません"
  exit 1
fi

for f in "${files[@]}"; do
  stem="$(basename "$f" .mp3)"
  echo "[run_nanami] processing $f -> out/audio/Nanami/${stem}"
  python audio_mvp/audio_analyze.py \
    --in "$f" \
    --lang ja \
    --model small \
    --out "out/audio/Nanami/${stem}" \
    --auto_assign_child_by_f0 true \
    --assign_mode diar
done

echo "Done. See out/audio/Nanami/<stem>/report.html"
