#!/usr/bin/env bash
# Launcher for the Wanis Voice LitServe API
# Usage: ./run_voice_litserve.sh [--host 0.0.0.0] [--port 8000] [--workers 2]

HOST=${1:-0.0.0.0}
PORT=${2:-8000}
WORKERS=${3:-2}

# litserve command – the module path is wanis.lightning.ai.voice_litserve:VoiceLitAPI
litserve run wanis.lightning.ai.voice_litserve.VoiceLitAPI \
    --host $HOST \
    --port $PORT \
    --workers $WORKERS \
    --device cuda
