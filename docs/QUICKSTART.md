# Quickstart Guide

This guide will help you set up the development environment for the Wanis AI companion project in less than 30 minutes.

## Prerequisites

Before you begin, ensure you have the following installed:

### Required Software

- **Node.js**: v18.0.0 or higher
  - Download: https://nodejs.org/
  - Verify: `node --version`

- **Python**: 3.10 or higher
  - Download: https://www.python.org/downloads/
  - Verify: `python --version`

- **Git**: Latest version
  - Download: https://git-scm.com/downloads
  - Verify: `git --version`

### Required Browsers

- **Chrome**: 90+ (recommended for development)
- **Firefox**: 88+
- **Safari**: 14+
- **Edge**: 90+

### Optional Software

- **Docker**: For containerized deployment
  - Download: https://www.docker.com/get-started

- **VS Code**: Recommended IDE
  - Download: https://code.visualstudio.com/

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/wanis.git
cd wanis
```

### Step 2: Install Python Dependencies

```bash
# Create Conda environment with Python 3.10
conda create -n wanis-env python=3.10 -y

# Activate Conda environment
conda activate wanis-env

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Install Node.js Dependencies

```bash
# Install frontend dependencies
npm install
```

### Step 4: Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your values
nano .env
```

Required environment variables:

```bash
# Gemini API Key (required)
GEMINI_API_KEY=your_gemini_api_key_here

# Server Configuration
SERVER_HOST=localhost
SERVER_PORT=8000

# WebSocket Configuration
WS_HOST=localhost
WS_PORT=8000

# STT Configuration
STT_MODEL_PATH=models/stt_ar_fastconformer_hybrid_large_pcd_v1.0.nemo

# TTS Configuration
TTS_MODEL_ID=OmarSamir/EGTTS-V0.1

# Optional: Lightning AI Credentials
LIGHTNING_API_KEY=your_lightning_api_key
LIGHTNING_SPACE_ID=your_space_id
```

### Step 5: Download Models

```bash
# Create models directory
mkdir -p models

# Download STT model (EgypTalk-ASR-v2)
# This will download automatically on first run, or you can download manually:
# wget https://huggingface.co/NAMAA-Space/EgypTalk-ASR-v2/resolve/main/stt_ar_fastconformer_hybrid_large_pcd_v1.0.nemo -O models/stt_ar_fastconformer_hybrid_large_pcd_v1.0.nemo

# Download TTS model (EGTTS-V0.1)
# This will download automatically on first run
```

### Step 6: Verify Installation

```bash
# Verify Python installation
python -c "import torch; print('PyTorch:', torch.__version__)"
python -c "import nemo; print('NeMo:', nemo.__version__)"

# Verify Node.js installation
node --version
npm --version

# Verify environment variables
python -c "import os; print('GEMINI_API_KEY:', os.getenv('GEMINI_API_KEY', 'NOT_SET'))"
```

## Configuration

### Server Configuration

Edit `wanis/configs/wanis_config.yaml`:

```yaml
audio:
  sample_rate: 16000
  channels: 1

stt:
  model_id: "NAMAA-Space/EgypTalk-ASR-v2"
  local_model_path: "models/stt_ar_fastconformer_hybrid_large_pcd_v1.0.nemo"

tts:
  model_id: "OmarSamir/EGTTS-V0.1"
  speed: 0.85

vad:
  threshold: 0.5
  min_silence_ms: 700

agent:
  model: "gemini-2.0-flash"
  temperature: 0.7
```

### Client Configuration

Edit `wanis/static/frontend/config.js`:

```javascript
const CONFIG = {
  // WebSocket URL
  wsUrl: 'ws://localhost:8000/ws',

  // STT API URL
  sttApiUrl: 'http://localhost:8000/api/stt/transcribe',

  // VAD Configuration
  vad: {
    threshold: 0.5,
    minSpeechFrames: 10,
    minSilenceFrames: 20,
    preSpeechPad: 5,
    redemptionFrames: 8,
  },

  // Audio Configuration
  audio: {
    sampleRate: 16000,
    channels: 1,
    chunkSize: 4096,
  },
};
```

## Running the Application

### Option 1: Local Mode (All Processing on Local Machine)

```bash
# Run local mode
python -m wanis.run_local

# Or using the voice module
python -m wanis.voice.run --mode local
```

### Option 2: Hybrid Mode (Server + Client)

```bash
# Start server
python -m wanis.server --port 8000

# In another terminal, start client
python -m wanis.client --server ws://localhost:8000/ws
```

### Option 3: Using the Demo Script

```bash
# Run the MediaStream demo
./run_mediastream_demo.sh
```

### Option 4: Lightning AI Deployment

```bash
# Deploy to Lightning AI
python -m wanis.lightning.ai.deploy

# Or using LitServe directly
python -m wanis.lightning.ai.voice_litserve
```

## Testing

### Run Unit Tests

```bash
# Run all tests
pytest wanis/tests/ -v

# Run specific test module
pytest wanis/tests/voice/test_vad.py -v

# Run with coverage
pytest wanis/tests/ --cov=wanis --cov-report=html
```

### Run Integration Tests

```bash
# Test VAD integration
pytest wanis/tests/voice/test_vad.py -v

# Test STT integration
pytest wanis/tests/voice/test_stt_service.py -v

# Test TTS integration
pytest wanis/tests/voice/test_tts_service.py -v
```

### Test WebSocket Connection

```bash
# Test WebSocket client
pytest wanis/tests/pi/test_websocket_client.py -v
```

### Manual Testing

1. Open your browser to `http://localhost:8000`
2. Grant microphone access when prompted
3. Speak into your microphone
4. Verify that speech is detected and transcribed
5. Verify that the AI companion responds

## Common Issues and Solutions

### Issue 1: Module Not Found Error

**Error**:
```
ModuleNotFoundError: No module named 'nemo'
```

**Solution**:
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue 2: Microphone Access Denied

**Error**:
```
Microphone access denied
```

**Solution**:
1. Check browser permissions
2. Grant microphone access to localhost
3. Try using HTTPS instead of HTTP
4. Check system microphone settings

### Issue 3: Model Loading Failed

**Error**:
```
Failed to load STT model
```

**Solution**:
```bash
# Check if model file exists
ls -la models/

# Download model manually
wget https://huggingface.co/NAMAA-Space/EgypTalk-ASR-v2/resolve/main/stt_ar_fastconformer_hybrid_large_pcd_v1.0.nemo -O models/stt_ar_fastconformer_hybrid_large_pcd_v1.0.nemo

# Check model path in config
nano wanis/configs/wanis_config.yaml
```

### Issue 4: WebSocket Connection Failed

**Error**:
```
WebSocket connection failed
```

**Solution**:
1. Check if server is running
2. Check firewall settings
3. Verify WebSocket URL
4. Check browser console for errors

### Issue 5: High Memory Usage

**Error**:
```
High memory usage detected
```

**Solution**:
```bash
# Reduce batch size in config
nano wanis/configs/wanis_config.yaml

# Use smaller model if available
# Clear model cache
rm -rf ~/.cache/torch/hub/
```

### Issue 6: Slow Response Time

**Error**:
```
Slow response time
```

**Solution**:
1. Check CPU/GPU usage
2. Use GPU acceleration if available
3. Reduce audio chunk size
4. Optimize model configuration

### Issue 7: Browser Compatibility

**Error**:
```
WebAssembly not supported
```

**Solution**:
1. Update browser to latest version
2. Use Chrome 90+ or Firefox 88+
3. Fallback to WebSocket mode
4. Check browser console for errors

### Issue 8: Port Already in Use

**Error**:
```
Port 8000 is already in use
```

**Solution**:
```bash
# Find process using port 8000
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Kill the process
kill -9 <PID>  # Linux/Mac
taskkill /PID <PID> /F  # Windows

# Or use a different port
python -m wanis.server --port 8001
```

## Troubleshooting

### Enable Debug Logging

```bash
# Set environment variable
export DEBUG=wanis:*  # Linux/Mac
set DEBUG=wanis:*     # Windows

# Run with debug logging
python -m wanis.run_local
```

### Check System Requirements

```bash
# Check Python version
python --version

# Check Node.js version
node --version

# Check available memory
free -h  # Linux/Mac
systeminfo | findstr /C:"Total Physical Memory"  # Windows

# Check available GPU (if applicable)
nvidia-smi  # NVIDIA GPU
```

### Verify Audio Devices

```bash
# List available audio devices
python -c "import sounddevice as sd; print(sd.query_devices())"

# Test microphone
python -c "import sounddevice as sd; sd.rec(44100, samplerate=44100, channels=1); sd.wait(); print('OK')"
```

### Clean Installation

```bash
# Remove virtual environment
rm -rf venv  # Linux/Mac
rmdir /s venv  # Windows

# Remove node_modules
rm -rf node_modules

# Remove model cache
rm -rf ~/.cache/torch/hub/

# Reinstall
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
npm install
```

## Next Steps

After completing the setup:

1. Read the [Local Development Guide](LOCAL_DEVELOPMENT.md) for development workflow
2. Review the [Project Structure](../README.md#project-structure)
3. Check out the [API Documentation](docs/API.md)
4. Explore the [Configuration Guide](docs/CONFIGURATION.md)

## Getting Help

If you encounter issues not covered in this guide:

1. Check the [GitHub Issues](https://github.com/your-org/wanis/issues)
2. Join the [Discord Community](https://discord.gg/wanis)
3. Contact support at support@wanis.ai

## Additional Resources

- [Project README](../README.md)
- [API Documentation](docs/API.md)
- [Configuration Guide](docs/CONFIGURATION.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Contributing Guide](CONTRIBUTING.md)

## Verification Checklist

Use this checklist to verify your installation:

- [ ] Node.js v18+ installed
- [ ] Python 3.10+ installed
- [ ] Git installed
- [ ] Repository cloned
- [ ] Python dependencies installed
- [ ] Node.js dependencies installed
- [ ] Environment variables configured
- [ ] Models downloaded
- [ ] Server starts successfully
- [ ] Client connects successfully
- [ ] Microphone access granted
- [ ] Speech detection works
- [ ] Transcription works
- [ ] AI companion responds

## Estimated Setup Time

- **Cloning repository**: 2 minutes
- **Installing dependencies**: 10 minutes
- **Configuring environment**: 5 minutes
- **Downloading models**: 10 minutes (optional, can download on first run)
- **Running tests**: 5 minutes
- **Total**: ~30 minutes

## Tips for Faster Setup

1. Use a fast internet connection for downloading models
2. Use SSD for faster model loading
3. Use GPU acceleration if available
4. Pre-download models to avoid first-run delays
5. Use Docker for consistent environment

## System Requirements

### Minimum Requirements

- **CPU**: 4 cores
- **RAM**: 8GB
- **Storage**: 20GB
- **GPU**: Not required (CPU-only mode)

### Recommended Requirements

- **CPU**: 8 cores
- **RAM**: 16GB
- **Storage**: 50GB SSD
- **GPU**: NVIDIA GPU with 8GB VRAM

### Development Requirements

- **CPU**: 8 cores
- **RAM**: 32GB
- **Storage**: 100GB SSD
- **GPU**: NVIDIA GPU with 16GB VRAM

## License

## Deploy on Lightning.ai

### Prerequisites
- Component definition file `component.yaml` at repository root.
- CI workflow `.github/workflows/ci.yml` for automated builds.
- Deployment script `deploy_lightning.sh`.

### Steps
1. Ensure you have a Lightning.ai account and the CLI installed.
2. Run the deployment script:
   ```bash
   ./deploy_lightning.sh
   ```
3. After the script reports success, verify the component appears in your Lightning.ai dashboard.
4. Use the CI badge in `README.md` to monitor build status.

### Verification
- The script should exit with code 0.
- The component should be listed under *Components* in the Lightning.ai console.
- CI workflow should show a green check on GitHub.

## License

This project is licensed under the MIT License. See [LICENSE](../LICENSE) for details.
