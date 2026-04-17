#!/usr/bin/env bash
# Run MediaStream + AudioWorklet + VAD + STT demo
# Usage: ./run_mediastream_demo.sh [--port 8000] [--ui-port 8080]

set -e

# Default values
PORT=8001
UI_PORT=8080

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --port)
      PORT="$2"
      shift 2
      ;;
    --ui-port)
      UI_PORT="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Kill any existing processes
fuser -k $PORT/tcp 2>/dev/null || true
fuser -k $UI_PORT/tcp 2>/dev/null || true
sleep 0.5

# Start MediaStream + VAD + STT server
echo "[run_mediastream_demo] Starting MediaStream + VAD + STT server..."
python -m wanis.web.hybrid_server --port $PORT &
SERVER_PID=$!

echo "[run_mediastream_demo] Server started (PID $SERVER_PID) on http://0.0.0.0:$PORT"

# Give server time to load models
sleep 3

# Serve the static UI
pushd wanis/static/frontend > /dev/null
python -m http.server $UI_PORT &
UI_PID=$!
popd > /dev/null

echo "[run_mediastream_demo] UI served on http://localhost:$UI_PORT (PID $UI_PID)"

# Print instructions
cat <<EOF

--- MediaStream + AudioWorklet + VAD + STT Demo Ready ---
* Open browser: http://localhost:$UI_PORT
* Click "Start" - MediaStream captures raw audio
* AudioWorklet processes audio in real-time
* VAD detects speech boundaries
* STT transcribes complete utterances
* Transcription appears below the canvas

Press Ctrl+C to stop both services

EOF

# Cleanup on exit
cleanup() {
  echo "\n[run_mediastream_demo] Shutting down..."
  kill $SERVER_PID $UI_PID 2>/dev/null || true
  wait $SERVER_PID $UI_PID 2>/dev/null || true
  echo "[run_mediastream_demo] All processes terminated"
  exit 0
}

trap cleanup SIGINT SIGTERM

# Wait indefinitely
while true; do sleep 1; done
