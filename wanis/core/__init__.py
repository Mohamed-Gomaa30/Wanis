"""
Wanis Core Module.

Core components, models, and exceptions.
"""

from .hardware_interface import HardwareInterface, Vitals
from .memory import MemoryManager
from .context_manager import context_manager
from .state_manager import RobotState

# Exceptions
from .exceptions import (
    VoicePipelineError,
    STTError,
    TTSError,
    VADError,
    AudioIOError,
    WebSocketError,
    HardwareEventError,
    ConfigurationError,
)

# Data models
from .models import (
    AudioChunk,
    Transcription,
    AgentResponse,
    HardwareEvent,
    VitalsData,
    ConversationTurn,
    VoiceSession,
)

__all__ = [
    # Hardware
    "HardwareInterface",
    "Vitals",
    # Memory
    "MemoryManager",
    "context_manager",
    "RobotState",
    # Exceptions
    "VoicePipelineError",
    "STTError",
    "TTSError",
    "VADError",
    "AudioIOError",
    "WebSocketError",
    "HardwareEventError",
    "ConfigurationError",
    # Data models
    "AudioChunk",
    "Transcription",
    "AgentResponse",
    "HardwareEvent",
    "VitalsData",
    "ConversationTurn",
    "VoiceSession",
]
