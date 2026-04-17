"""
Wanis Voice Pipeline Module.

Provides speech-to-speech conversation capabilities for Arabic elderly users.
Supports both local and hybrid modes.

Usage:
    # Local mode (all processing on local machine)
    python -m wanis.voice.run --mode local

    # Hybrid mode (mic on laptop, processing on server)
    python -m wanis.voice.server --port 8000  # On server
    python -m wanis.voice.client --server ws://server:8000/ws  # On laptop
"""

import logging

from .audio import AudioInput, AudioOutput, AudioConfig
from .vad import VAD, VADConfig
from .stt import STT, STTConfig
from .tts import TTS, TTSConfig
from .sentence_buffer import SentenceBuffer

logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "AudioInput",
    "AudioOutput",
    "AudioConfig",
    "VAD",
    "VADConfig",
    "STT",
    "STTConfig",
    "TTS",
    "TTSConfig",
    "SentenceBuffer",
]
