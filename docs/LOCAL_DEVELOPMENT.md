# Local Development Guide

This guide covers the local development workflow for the Wanis AI companion project.

## Project Structure

```
wanis/
├── configs/                    # Configuration files
│   └── wanis_config.yaml      # Main configuration
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
│   ├── config.py               # Configuration loader
│   └── streaming.py            # Sentence splitter
│
├── voice/                      # Voice pipeline components
│   ├── __init__.py
│   ├── audio.py                # Audio I/O
│   ├── vad.py                  # Voice Activity Detection
│   ├── stt.py                  # Speech-to-Text
│   ├── tts.py                  # Text-to-Speech
│   ├── sentence_buffer.py      # Sentence boundary detection
│   └── run.py                  # Voice entry point
│
├── pi/                         # Pi-specific modules
│   ├── __init__.py
│   ├── websocket_client.py     # WebSocket client
│   └── fall_handler.py         # Fall detection
│
├── agent/                      # LLM agent
│   ├── __init__.py
│   ├── llm_agent.py            # Companion agent
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
├── web/                        # Web interface
│   ├── hybrid_server.py        # FastAPI server
│   └── static/
│       └── frontend/
│           ├── index.html      # UI
│           ├── style.css      # Styles
│           └── mediastream_app.js  # Client logic
│
├── lightning/ai/               # Lightning AI integration
│   └── voice_litserve.py       # LitServe deployment
│
├── data/                       # User data
│   └── user_profile.json       # User profile
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
├── server.py                   # Hybrid server
├── client.py                   # Hybrid client
├── run_hybrid.sh               # Hybrid mode script
├── requirements.txt            # Python dependencies
└── package.json                # Node.js dependencies
```

## Development Server Setup

### Option 1: Local Mode (Recommended for Development)

Local mode runs all processing on your local machine.

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Run local mode
python -m wanis.run_local
```

**Features**:
- All processing on local machine
- No network latency
- Full control over configuration
- Easy debugging

**Use Cases**:
- Development and testing
- Offline usage
- Privacy-sensitive applications

### Option 2: Hybrid Mode (Server + Client)

Hybrid mode splits processing between server and client.

```bash
# Terminal 1: Start server
python -m wanis.server --port 8000

# Terminal 2: Start client
python -m wanis.client --server ws://localhost:8000/ws
```

**Features**:
- Server-side VAD and STT
- Client-side audio capture
- WebSocket communication
- Scalable architecture

**Use Cases**:
- Multi-user deployment
- Resource-constrained clients
- Cloud-based processing

### Option 3: Lightning AI Deployment

Deploy to Lightning AI for cloud-based processing.

```bash
# Deploy to Lightning AI
python -m wanis.lightning.ai.deploy

# Or use LitServe directly
python -m wanis.lightning.ai.voice_litserve
```

**Features**:
- Cloud-based processing
- Automatic scaling
- GPU acceleration
- Managed infrastructure

**Use Cases**:
- Production deployment
- High-availability requirements
- Resource-intensive processing

## Hot Reload Configuration

### Python Hot Reload

Use `watchfiles` for automatic Python reloading:

```bash
# Install watchfiles
pip install watchfiles

# Run with hot reload
watchfiles "python -m wanis.run_local" wanis/
```

### JavaScript Hot Reload

Use `nodemon` for automatic JavaScript reloading:

```bash
# Install nodemon
npm install -g nodemon

# Run with hot reload
nodemon --watch wanis/static/frontend --exec "python -m wanis.server"
```

### Full Stack Hot Reload

Combine Python and JavaScript hot reload:

```bash
# Terminal 1: Python hot reload
watchfiles "python -m wanis.server" wanis/

# Terminal 2: JavaScript hot reload
nodemon --watch wanis/static/frontend --ext js,html,css --exec "echo 'Frontend updated'"
```

## Debugging Tools

### Python Debugging

#### Using pdb

```bash
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use breakpoint() (Python 3.7+)
breakpoint()
```

#### Using VS Code Debugger

1. Install Python extension for VS Code
2. Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Local Mode",
      "type": "python",
      "request": "launch",
      "module": "wanis.run_local",
      "console": "integratedTerminal",
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    },
    {
      "name": "Python: Server",
      "type": "python",
      "request": "launch",
      "module": "wanis.server",
      "args": ["--port", "8000"],
      "console": "integratedTerminal",
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    }
  ]
}
```

3. Set breakpoints in code
4. Press F5 to start debugging

#### Logging

Enable debug logging:

```bash
export DEBUG=wanis:*  # Linux/Mac
set DEBUG=wanis:*     # Windows
```

Add logging to code:

```python
import logging

logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

### JavaScript Debugging

#### Using Browser DevTools

1. Open browser DevTools (F12)
2. Go to Sources tab
3. Set breakpoints in JavaScript files
4. Reload page to trigger breakpoints

#### Using VS Code Debugger

1. Install JavaScript debugger extension
2. Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Chrome: Launch",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:8000",
      "webRoot": "${workspaceFolder}/wanis/static/frontend"
    }
  ]
}
```

3. Set breakpoints in JavaScript files
4. Press F5 to start debugging

#### Console Logging

Add console logging to code:

```javascript
console.log('Info message');
console.warn('Warning message');
console.error('Error message');
console.debug('Debug message');
```

### WebSocket Debugging

#### Using WebSocket Inspector

1. Open browser DevTools (F12)
2. Go to Network tab
3. Filter by WS (WebSocket)
4. Inspect WebSocket messages

#### Using WebSocket Client

```bash
# Install wscat
npm install -g wscat

# Connect to WebSocket
wscat -c ws://localhost:8000/ws

# Send message
> {"type": "config", "vad": {"threshold": 0.5}}
```

### Audio Debugging

#### Using Audio Recorder

```python
import sounddevice as sd
import numpy as np

# Record audio
duration = 5  # seconds
sample_rate = 16000
recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
sd.wait()

# Save to file
from scipy.io import wavfile
wavfile.write('test.wav', sample_rate, recording)
```

#### Using Audio Visualizer

```python
import matplotlib.pyplot as plt
import numpy as np
from scipy.io import wavfile

# Load audio
sample_rate, audio = wavfile.read('test.wav')

# Plot waveform
plt.figure(figsize=(12, 4))
plt.plot(audio)
plt.title('Audio Waveform')
plt.xlabel('Sample')
plt.ylabel('Amplitude')
plt.show()
```

## Testing Procedures

### Unit Tests

Run unit tests for individual components:

```bash
# Run all unit tests
pytest wanis/tests/ -v

# Run specific test file
pytest wanis/tests/voice/test_vad.py -v

# Run specific test function
pytest wanis/tests/voice/test_vad.py::test_vad_init -v

# Run with coverage
pytest wanis/tests/ --cov=wanis --cov-report=html
```

### Integration Tests

Run integration tests for component interactions:

```bash
# Test VAD integration
pytest wanis/tests/voice/test_vad.py -v

# Test STT integration
pytest wanis/tests/voice/test_stt_service.py -v

# Test TTS integration
pytest wanis/tests/voice/test_tts_service.py -v

# Test WebSocket integration
pytest wanis/tests/pi/test_websocket_client.py -v
```

### End-to-End Tests

Run end-to-end tests for complete workflows:

```bash
# Test local mode
pytest tests/e2e/test_local_mode.py -v

# Test hybrid mode
pytest tests/e2e/test_hybrid_mode.py -v

# Test WebSocket fallback
pytest tests/e2e/test_websocket_fallback.py -v
```

### Manual Testing

#### Test Speech Detection

1. Start the application
2. Grant microphone access
3. Speak into microphone
4. Verify speech is detected
5. Verify transcription is accurate

#### Test AI Companion

1. Start the application
2. Speak to the AI companion
3. Verify response is relevant
4. Verify response is timely
5. Verify voice quality is good

#### Test Fallback Scenarios

1. Disable WebAssembly in browser
2. Verify fallback to WebSocket
3. Verify functionality is maintained
4. Verify performance is acceptable

## Best Practices

### Code Style

#### Python

Follow PEP 8 style guide:

```python
# Good
def process_audio(audio_data: np.ndarray) -> str:
    """Process audio data and return transcription."""
    result = stt_model.transcribe(audio_data)
    return result.text

# Bad
def processAudio(audio):
    r=stt.transcribe(audio)
    return r.text
```

Use type hints:

```python
from typing import Optional

def transcribe(
    audio: np.ndarray,
    language: str = "ar",
    confidence_threshold: float = 0.5
) -> Optional[str]:
    """Transcribe audio with confidence filtering."""
    result = stt_model.transcribe(audio)
    if result.confidence >= confidence_threshold:
        return result.text
    return None
```

#### JavaScript

Follow modern JavaScript conventions:

```javascript
// Good
async function transcribeAudio(audioData) {
  try {
    const response = await fetch('/api/stt/transcribe', {
      method: 'POST',
      headers: { 'Content-Type': 'audio/wav' },
      body: audioData,
    });
    const result = await response.json();
    return result.transcription;
  } catch (error) {
    console.error('Transcription failed:', error);
    throw error;
  }
}

// Bad
function transcribeAudio(audio) {
  fetch('/api/stt/transcribe', {
    method: 'POST',
    body: audio
  }).then(function(res) {
    return res.json();
  }).then(function(result) {
    return result.transcription;
  });
}
```

### Error Handling

#### Python

```python
# Good
try:
    result = stt_model.transcribe(audio_data)
except STTError as e:
    logger.error(f"STT error: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise

# Bad
result = stt_model.transcribe(audio_data)
```

#### JavaScript

```javascript
// Good
async function transcribeAudio(audioData) {
  try {
    const response = await fetch('/api/stt/transcribe', {
      method: 'POST',
      headers: { 'Content-Type': 'audio/wav' },
      body: audioData,
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Transcription failed:', error);
    throw error;
  }
}

// Bad
async function transcribeAudio(audioData) {
  const response = await fetch('/api/stt/transcribe', {
    method: 'POST',
    body: audioData,
  });
  return await response.json();
}
```

### Performance Optimization

#### Python

```python
# Use async/await for I/O operations
async def process_audio_async(audio_data: np.ndarray) -> str:
    result = await stt_model.transcribe_async(audio_data)
    return result.text

# Use caching for expensive operations
from functools import lru_cache

@lru_cache(maxsize=128)
def load_model(model_path: str):
    return load_model_from_disk(model_path)

# Use batch processing
def process_batch(audio_batch: List[np.ndarray]) -> List[str]:
    return [stt_model.transcribe(audio) for audio in audio_batch]
```

#### JavaScript

```javascript
// Use async/await for I/O operations
async function transcribeAudio(audioData) {
  const response = await fetch('/api/stt/transcribe', {
    method: 'POST',
    headers: { 'Content-Type': 'audio/wav' },
    body: audioData,
  });
  return await response.json();
}

// Use request batching
async function transcribeBatch(audioBatch) {
  const promises = audioBatch.map(audio =>
    fetch('/api/stt/transcribe', {
      method: 'POST',
      headers: { 'Content-Type': 'audio/wav' },
      body: audio,
    }).then(res => res.json())
  );
  return Promise.all(promises);
}

// Use debouncing for frequent events
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}
```

### Security Best Practices

#### Input Validation

```python
# Python
def validate_audio(audio_data: np.ndarray) -> bool:
    """Validate audio data."""
    if audio_data is None:
        raise ValueError("Audio data is required")
    if len(audio_data.shape) != 2:
        raise ValueError("Audio must be 2D array")
    if audio_data.shape[1] != 1:
        raise ValueError("Audio must be mono")
    return True
```

```javascript
// JavaScript
function validateAudio(audioData) {
  if (!audioData) {
    throw new Error('Audio data is required');
  }
  if (audioData.length === 0) {
    throw new Error('Audio data is empty');
  }
  return true;
}
```

#### Error Messages

```python
# Python
# Good
raise ValueError("Invalid audio format: expected PCM 16-bit, got PCM 32-bit")

# Bad
raise ValueError("Invalid audio")
```

```javascript
// JavaScript
// Good
throw new Error('Invalid audio format: expected PCM 16-bit, got PCM 32-bit');

// Bad
throw new Error('Invalid audio');
```

### Documentation

#### Code Comments

```python
# Good
def transcribe_audio(
    audio_data: np.ndarray,
    language: str = "ar",
    confidence_threshold: float = 0.5
) -> Optional[str]:
    """
    Transcribe audio data with confidence filtering.

    Args:
        audio_data: Audio data as numpy array (samples, channels)
        language: Language code for transcription (default: "ar")
        confidence_threshold: Minimum confidence score (default: 0.5)

    Returns:
        Transcription text if confidence >= threshold, None otherwise

    Raises:
        ValueError: If audio_data is invalid
        STTError: If transcription fails
    """
    if not validate_audio(audio_data):
        raise ValueError("Invalid audio data")

    result = stt_model.transcribe(audio_data, language=language)
    if result.confidence >= confidence_threshold:
        return result.text
    return None
```

```javascript
// Good
/**
 * Transcribe audio data with confidence filtering.
 *
 * @param {ArrayBuffer} audioData - Audio data as ArrayBuffer
 * @param {string} language - Language code (default: "ar")
 * @param {number} confidenceThreshold - Minimum confidence (default: 0.5)
 * @returns {Promise<string|null>} Transcription text or null
 * @throws {Error} If audio data is invalid or transcription fails
 */
async function transcribeAudio(audioData, language = 'ar', confidenceThreshold = 0.5) {
  if (!validateAudio(audioData)) {
    throw new Error('Invalid audio data');
  }

  const response = await fetch('/api/stt/transcribe', {
    method: 'POST',
    headers: {
      'Content-Type': 'audio/wav',
      'X-Language': language,
    },
    body: audioData,
  });

  const result = await response.json();
  if (result.confidence >= confidenceThreshold) {
    return result.transcription;
  }
  return null;
}
```

## Common Workflows

### Adding a New Feature

1. Create feature branch:
   ```bash
   git checkout -b feature/new-feature
   ```

2. Implement feature:
   - Write code
   - Add tests
   - Update documentation

3. Test feature:
   ```bash
   pytest tests/ -v
   ```

4. Commit changes:
   ```bash
   git add .
   git commit -m "Add new feature"
   ```

5. Push and create PR:
   ```bash
   git push origin feature/new-feature
   ```

### Debugging an Issue

1. Reproduce the issue
2. Add logging/breakpoints
3. Run with debug mode
4. Analyze logs/output
5. Fix the issue
6. Verify fix
7. Add tests

### Updating Dependencies

1. Check for updates:
   ```bash
   pip list --outdated
   npm outdated
   ```

2. Update dependencies:
   ```bash
   pip install -U <package>
   npm update <package>
   ```

3. Test changes:
   ```bash
   pytest tests/ -v
   ```

4. Update requirements:
   ```bash
   pip freeze > requirements.txt
   npm update
   ```

## Performance Monitoring

### Python Profiling

```bash
# Profile with cProfile
python -m cProfile -o profile.stats -m wanis.run_local

# Analyze profile
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"
```

### JavaScript Profiling

1. Open browser DevTools (F12)
2. Go to Performance tab
3. Click Record
4. Perform actions
5. Stop recording
6. Analyze results

### Memory Profiling

```python
# Python memory profiling
import memory_profiler

@memory_profiler.profile
def process_audio(audio_data):
    result = stt_model.transcribe(audio_data)
    return result.text
```

```javascript
// JavaScript memory profiling
console.log('Memory:', performance.memory.usedJSHeapSize);
```

## Continuous Integration

### GitHub Actions

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest wanis/tests/ -v
```

## Additional Resources

- [Python Documentation](https://docs.python.org/3/)
- [JavaScript Documentation](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)

## Getting Help

If you need help with development:

1. Check the [GitHub Issues](https://github.com/your-org/wanis/issues)
2. Join the [Discord Community](https://discord.gg/wanis)
3. Contact the development team at dev@wanis.ai
