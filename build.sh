#!/usr/bin/env bash
# ALGENZA Explainer Video Engine - Linux / macOS / Docker Build Pipeline
set -e
cd "$(dirname "$0")"

echo "================================================================="
echo "    ▲  ALGENZA VIDEO ENGINE - HIGH-PERFORMANCE VIDEO BUILDER"
echo "       algenza.com  ·  Lead Architect: Muhammad Hassan"
echo "================================================================="

# 1. Install dependencies
python3 -m pip install -r requirements.txt --quiet

# 2. Voiceover
[ -f v8.wav ] && [ -f tts.json ] || python3 tts.py

# 3. Audio mix & lip-sync
python3 mix.py

# 4. Render frames & compile MP4 (16:9 Landscape default)
ASPECT="${ASPECT:-16:9}"
WORKERS="${WORKERS:-4}"
python3 cli.py build --aspect "$ASPECT" --workers "$WORKERS" --skip-tts --skip-mix

echo "Done! Final video generated in assets/"
