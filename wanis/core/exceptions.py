"""
Custom exceptions for the Wanis voice pipeline.
"""


class VoicePipelineError(Exception):
    """Base exception for voice pipeline errors."""

    pass


class STTError(VoicePipelineError):
    """Error during speech-to-text processing."""

    pass


class TTSError(VoicePipelineError):
    """Error during text-to-speech synthesis."""

    pass


class VADError(VoicePipelineError):
    """Error during voice activity detection."""

    pass


class AudioIOError(VoicePipelineError):
    """Error during audio input/output."""

    pass


class WebSocketError(VoicePipelineError):
    """Error in WebSocket communication."""

    pass


class HardwareEventError(VoicePipelineError):
    """Error processing hardware events."""

    pass


class ConfigurationError(VoicePipelineError):
    """Error in configuration."""

    pass
