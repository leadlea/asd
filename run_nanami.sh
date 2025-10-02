#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
cd "$repo_root"
mkdir -p out/audio/Nanami
for f in audio/Nanami/*.mp3; do
  stem="$(basename "$f" .mp3)"
  python audio_mvp/audio_analyze.py --in "$f" --lang ja --model small --out "out/audio/Nanami/${stem}" --auto_assign_child_by_f0 true
done
echo "Done. See out/audio/Nanami/<stem>/report.html"
