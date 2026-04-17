# Wanis Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-14

## Active Technologies

- **Language**: Python 3.10+
- **Project Type**: Voice-enabled AI application with WebSocket infrastructure

## Project Structure

```text
wanis/
├── configs/
│   └── wanis_config.yaml       # Centralized configuration
│
├── core/                       # Core infrastructure
│   ├── __init__.py
│   ├── exceptions.py           # Custom exceptions
│   ├── models.py               # Data classes
│   ├── memory.py               # Long-term memory
│   ├── context_manager.py      # Daily context
│   ├── hardware_interface.py   # Hardware abstraction
│   └── state_manager.py        # State management
│
├── utils/                      # Shared utilities
│   ├── __init__.py
│   ├── config.py               # Configuration loader (from YAML)
│   └── streaming.py            # SentenceSplitter for LLM output
│
├── voice/                      # Voice pipeline components
│   ├── __init__.py             # Public API exports
│   ├── audio.py                # Audio I/O (mic + speaker)
│   ├── vad.py                  # Silero VAD with event interface
│   ├── stt.py                  # NeMo STT (EgypTalk-ASR-v2)
│   ├── tts.py                  # TTS synthesis (EGTTS-V0.1)
│   ├── sentence_buffer.py      # Sentence boundary detection
│   └── run.py                  # Voice entry point
│
├── pi/                         # Pi-specific hardware modules
│   ├── __init__.py
│   ├── websocket_client.py     # WebSocket client for Pi
│   └── fall_handler.py         # Fall detection handler
│
├── agent/                      # LLM agent (Gemini)
│   ├── __init__.py
│   ├── llm_agent.py            # CompanionAgent
│   ├── prompts.py              # System prompts
│   └── tools.py                # Agent tools
│
├── services/                   # External services
│   ├── __init__.py
│   ├── vitals_processor.py     # Health vitals
│   ├── medication_scheduler.py # Medication reminders
│   ├── hardware_event_handler.py
│   └── notification_service.py
│
├── data/                       # User profiles
│   └── user_profile.json
│
├── tests/                      # Tests
│   ├── voice/
│   │   ├── test_stt_service.py
│   │   ├── test_tts_service.py
│   │   └── test_vad.py
│   └── pi/
│       └── test_websocket_client.py
│
├── run_local.py                # Local mode entry point
├── server.py                   # Hybrid server (Lightning AI side)
├── client.py                   # Hybrid client (laptop side)
└── run_hybrid.sh               # Hybrid mode script
```

## Commands

```bash
# Run local mode (all processing on local machine)
python -m wanis.run_local
python -m wanis.voice.run --mode local

# Run hybrid mode
./wanis/run_hybrid.sh both      # Local test (server + client)
./wanis/run_hybrid.sh server    # Server only
./wanis/run_hybrid.sh client 8000 my.server  # Client only

# Or directly:
python -m wanis.server --port 8000
python -m wanis.client --server ws://localhost:8000/ws

# Run tests
pytest wanis/tests/ -v

# Lint code
ruff check wanis/
```

## Configuration

All configuration is centralized in `wanis/configs/wanis_config.yaml`:

```yaml
audio:
  sample_rate: 16000
  channels: 1

stt:
  model_id: "NAMAA-Space/EgypTalk-ASR-v2"
  local_model_path: "models/stt_ar_fastconformer_hybrid_large_pcd_v1.0.nemo"

tts:
  model_id: "OmarSamir/EGTTS-V0.1"
  speed: 0.85  # Slower for elderly

vad:
  threshold: 0.5
  min_silence_ms: 700

agent:
  model: "gemini-2.0-flash"
  temperature: 0.7
```

### Using Config in Code

```python
from wanis.utils.config import get_config, get_section, get_value

# Get full config
config = get_config()

# Get section
stt_config = get_section("stt")

# Get specific value
speed = get_value("tts", "speed", 0.85)
```

## Code Style

- Python 3.10+: Follow standard conventions
- Use async/await for I/O operations
- Type hints required for public interfaces
- Docstrings in Google style

## Key Dependencies

- NeMo (STT via EgypTalk-ASR-v2)
- TTS library (EGTTS-V0.1)
- Google Gemini API
- FastAPI + Uvicorn
- sounddevice (audio I/O)
- torch (VAD - Silero)
- pytest + pytest-asyncio (testing)

## Common Troubleshooting

### Audio Issues
```bash
# List available audio devices
python -c "import sounddevice as sd; print(sd.query_devices())"

# Use specific device
python -c "from wanis.voice import AudioInput; print(AudioInput.list_devices())"
```

### Model Loading Issues
```bash
# Clear model cache
rm -rf ~/.cache/torch/hub/

# Verify NeMo installation
python -c "from nemo.collections.asr.models import EncDecHybridRNNTCTCModel; print('OK')"
```

### Environment Setup
```bash
# Required environment variables
export GEMINI_API_KEY=your_key_here

# Install dependencies
pip install -r requirements.txt
```

## Recent Changes

- 2026-04-14: Reorganized project structure
  - Moved config.py to utils/
  - Renamed voice_config.yaml to wanis_config.yaml
  - Created run_local.py entry point
  - Consolidated voice modules (audio.py, vad.py, stt.py, tts.py)
  - Added hybrid mode (client.py, server.py)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
