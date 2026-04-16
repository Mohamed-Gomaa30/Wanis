# Phase 1 – Setup Tasks

*Goal: Provide a clear, inexpensive‑model‑friendly task list that a cheaper LLM can execute without any ambiguity. All tasks are independent where possible and include exact file paths.*

## Tasks

- [X] T013 Create Client‑Side VAD contract (`specs/003-phase1-design-contracts/contracts/vad-client-contract.md`)
- [X] T014 Create Server‑Side STT contract (`specs/003-phase1-design-contracts/contracts/stt-server-contract.md`)
- [X] T015 Create WebSocket fallback contract (`specs/003-phase1-design-contracts/contracts/websocket-fallback-contract.md`)
- [X] T016 Update Quickstart guide with Conda steps (`docs/QUICKSTART.md`)
- [X] T017 Update README with Conda quick‑start snippet

- [X] T001 Initialize a new Git branch `phase1-setup` from `main`
- [X] T002 [P] Create a Conda environment `wanis-env` with Python 3.10 (`conda create -n wanis-env python=3.10 -y`)
- [X] T003 [P] Activate the Conda environment and install core dependencies (`conda activate wanis-env && pip install -r requirements.txt`)
- [X] T004 [P] Verify the Conda environment is active (`which python` should point to the Conda environment’s bin directory)
- [X] T005 [P] Create `wanis/static/frontend/package.json` with minimal content:
```
{
  "name": "wanis-frontend",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "@ricky0123/vad": "^1.0.0"
  },
  "scripts": {
    "build": "echo Build placeholder"
  }
}
```
- [X] T006 [P] Run `npm install` inside `wanis/static/frontend` to pull the `@ricky0123/vad` package
- [X] T007 [P] Add a `.env.example` at the repository root with required keys (`GEMINI_API_KEY`, `MQTT_BROKER_HOST`, etc.)
- [X] T008 [P] Copy `.env.example` to `.env` (do **not** commit `.env`)
- [X] T009 [P] Update `wanis/configs/wanis_config.yaml` with minimal client‑VAD and LitServe sections (see snippet below)
- [X] T010 [P] Create a LitServe launch script `wanis/lightning.ai/run_voice_litserve.sh`:
```
#!/usr/bin/env bash
set -e
poetry run litserve run wanis.lightning.ai.voice_litserve.VoiceLitAPI \
    --host 0.0.0.0 --port 8000 --workers 2 --device cpu
```
- [X] T011 Verify the setup:
  1. Start the LitServe server (`./wanis/lightning.ai/run_voice_litserve.sh`)
  2. Serve the frontend (`cd wanis/static/frontend && python -m http.server 8080`)
  3. Open `http://localhost:8080` and confirm no console errors (VAD library loads)
- [X] T012 Commit all setup files (except `.env`) with the message "Phase 1: Project setup and initial dependencies"

## Configuration Snippet (add to `wanis/configs/wanis_config.yaml`)
```yaml
client_vad:
  enabled: true
  threshold: 0.5
  min_speech_ms: 250
  min_silence_ms: 2000

server_vad:
  enabled: true
  threshold: 0.5
  min_speech_ms: 250
  min_silence_ms: 2000

litserve:
  host: "0.0.0.0"
  port: 8000
  workers: 2
  device: "cpu"
```
