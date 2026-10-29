#!/usr/bin/env bash
# Full pipeline for one episode:  ./make.sh episodes/ep01_toys [preview|final]
set -euo pipefail
EP=${1:?usage: ./make.sh episodes/<episode> [preview|final]}
MODE=${2:-preview}
PY=${PYTHON:-python}   # a Python 3.11 env with bpy, kokoro-onnx, soundfile, pyyaml

$PY pipeline/tts.py "$EP"          # voice.wav, timing.json, captions.ass
$PY pipeline/music.py "$EP"        # music.wav (skip if you supply your own)
if [ "$MODE" = final ]; then
  $PY pipeline/build.py "$EP" --render --scale 100 --samples 32
else
  $PY pipeline/build.py "$EP" --render --scale 50 --samples 8
fi
$PY pipeline/assemble.py "$EP"     # build/<episode>.mp4
