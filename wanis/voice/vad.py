"""
Voice Activity Detection using Silero VAD.

Provides streaming VAD with event-based interface for real-time speech detection.
Emits events when speech starts and ends, useful for pipeline orchestration.

Usage:
    vad = VAD(threshold=0.5, silence_ms=700)
    vad.initialize()

    # Process chunks
    for audio_chunk in audio_stream:
        event = vad.process(audio_chunk)
        if event:
            if event["type"] == "speech_start":
                print("User started speaking")
            elif event["type"] == "speech_end":
                audio = event["audio"]  # Complete speech segment
"""

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available - VAD disabled")


@dataclass
class VADConfig:
    threshold: float = 0.5
    silence_ms: int = 700
    min_speech_ms: int = 250
    sample_rate: int = 16000

    @classmethod
    def from_dict(cls, d: dict) -> "VADConfig":
        return cls(
            threshold=d.get("threshold", 0.5),
            silence_ms=d.get("min_silence_ms", 700),
            min_speech_ms=d.get("min_speech_ms", 250),
            sample_rate=d.get("sample_rate", 16000),
        )


class VAD:
    """
    Streaming Voice Activity Detection with event interface.

    Silero VAD requires exactly 512 samples at 16kHz (32ms chunks).
    This class handles buffering internally, so you can feed any chunk size.

    Events:
        {"type": "speech_start"} - User started speaking
        {"type": "speech_end", "audio": np.ndarray} - User stopped, complete audio
    """

    SAMPLE_RATE = 16000
    CHUNK_SAMPLES = 512  # Silero requirement: 512 samples = 32ms at 16kHz

    def __init__(self, config: Optional[VADConfig] = None):
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not available")

        if config is None:
            from wanis.utils.config import get_section

            config = VADConfig.from_dict(get_section("vad"))

        self.config = config
        self.model = None
        self._initialized = False

        # State
        self._is_speaking = False
        self._silence_samples = 0
        self._speech_chunks: list[np.ndarray] = []
        self._total_speech_samples = 0
        self._audio_buffer = np.array([], dtype=np.float32)

    def initialize(self) -> None:
        """Load the Silero VAD model."""
        if self._initialized:
            return

        logger.info("Loading Silero VAD model...")

        try:
            self.model, _ = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
            )
            self._initialized = True
            logger.info("Silero VAD loaded")
        except Exception as e:
            logger.error(f"Failed to load Silero VAD: {e}")
            raise

    def process(self, audio_bytes: bytes) -> Optional[dict]:
        """
        Process an audio chunk and return event if speech state changed.

        Args:
            audio_bytes: Raw audio bytes (16-bit PCM, 16kHz, mono)

        Returns:
            Event dict or None:
            - {"type": "speech_start"} when user starts speaking
            - {"type": "speech_end", "audio": np.ndarray} when user stops
        """
        if not self._initialized:
            self.initialize()

        # Convert to float32
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
        audio_float = audio_np.astype(np.float32) / 32767.0

        # Add to buffer
        self._audio_buffer = np.concatenate([self._audio_buffer, audio_float])

        # Process in 512-sample chunks
        event = None

        while len(self._audio_buffer) >= self.CHUNK_SAMPLES:
            chunk = self._audio_buffer[: self.CHUNK_SAMPLES]
            self._audio_buffer = self._audio_buffer[self.CHUNK_SAMPLES :]

            # Get speech probability
            chunk_tensor = torch.from_numpy(chunk)
            with torch.no_grad():
                prob = self.model(chunk_tensor, self.SAMPLE_RATE).item()

            is_speech = prob >= self.config.threshold

            if is_speech:
                if not self._is_speaking:
                    # Speech started
                    self._is_speaking = True
                    self._speech_chunks = []
                    self._total_speech_samples = 0
                    self._silence_samples = 0
                    logger.debug(f"Speech START (prob={prob:.2f})")
                    event = {"type": "speech_start", "probability": prob}

                self._silence_samples = 0
                self._speech_chunks.append(chunk)
                self._total_speech_samples += len(chunk)

            else:
                if self._is_speaking:
                    # Still accumulating during silence period
                    self._speech_chunks.append(chunk)
                    self._total_speech_samples += len(chunk)
                    self._silence_samples += len(chunk)

                    silence_duration_ms = (
                        self._silence_samples / self.SAMPLE_RATE
                    ) * 1000
                    speech_duration_ms = (
                        self._total_speech_samples / self.SAMPLE_RATE
                    ) * 1000

                    if silence_duration_ms >= self.config.silence_ms:
                        # Speech ended
                        self._is_speaking = False

                        if speech_duration_ms >= self.config.min_speech_ms:
                            audio_data = np.concatenate(self._speech_chunks)
                            logger.debug(f"Speech END ({speech_duration_ms:.0f}ms)")
                            event = {"type": "speech_end", "audio": audio_data}
                        else:
                            logger.debug(
                                f"Speech too short ({speech_duration_ms:.0f}ms), ignoring"
                            )

                        self._speech_chunks = []
                        self._total_speech_samples = 0
                        self._silence_samples = 0

        return event

    def is_speaking(self) -> bool:
        """Check if currently in speech state."""
        return self._is_speaking

    def reset(self) -> None:
        """Reset VAD state."""
        self._is_speaking = False
        self._silence_samples = 0
        self._speech_chunks = []
        self._total_speech_samples = 0
        self._audio_buffer = np.array([], dtype=np.float32)
        if self._initialized and self.model:
            self.model.reset_states()
        logger.debug("VAD reset")

    def is_ready(self) -> bool:
        """Check if VAD is initialized."""
        return self._initialized
