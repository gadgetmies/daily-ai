#!/usr/bin/env bash
# Prepare the local neural TTS stack. Idempotent and safe to re-run.
#
# Cloud TTS APIs (OpenAI, ElevenLabs, Google, Deepgram, Cartesia) are blocked by
# the org egress policy - the proxy 403s the CONNECT. Do not retry them.
# Kokoro-82M runs fully locally; its weights live on GitHub releases, which IS
# allowlisted.
set -euo pipefail

MODEL_DIR="${MODEL_DIR:-/tmp/kokoro}"
REL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"

mkdir -p "$MODEL_DIR"

python3 -c "import kokoro_onnx, soundfile" 2>/dev/null || \
  pip install --break-system-packages -q kokoro-onnx soundfile "misaki[en]"

fetch() {
  local name="$1" min_bytes="$2"
  local dest="$MODEL_DIR/$name"
  if [[ -f "$dest" ]] && [[ $(stat -c%s "$dest") -ge $min_bytes ]]; then
    echo "have $name"; return
  fi
  echo "downloading $name ..."
  curl -sSL --max-time 600 -o "$dest" "$REL/$name"
  [[ $(stat -c%s "$dest") -ge $min_bytes ]] || { echo "short download: $name" >&2; exit 1; }
}

fetch kokoro-v1.0.onnx 300000000
fetch voices-v1.0.bin   20000000

if ! command -v ffmpeg >/dev/null; then
  echo "installing ffmpeg ..."
  (sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg) \
    || apt-get install -y -qq ffmpeg \
    || { echo "could not install ffmpeg" >&2; exit 1; }
fi

echo "TTS ready in $MODEL_DIR"
