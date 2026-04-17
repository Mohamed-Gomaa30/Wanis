"""
NeMo Arabic Speech-to-Text Service.

Supports multiple model sources:
- Local .nemo file path (preferred for offline)
- HuggingFace model ID (NAMAA-Space/EgypTalk-ASR-v2)

Usage:
    stt = STT()
    stt.initialize()

    # Transcribe audio
    text = stt.transcribe(audio_bytes)

    # Or use buffer for streaming
    stt.feed(audio_chunk1)
    stt.feed(audio_chunk2)
    text = stt.finalize()
"""

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class STTConfig:
    model_id: str = "NAMAA-Space/EgypTalk-ASR-v2"
    local_model_path: str = "models/stt_ar_fastconformer_hybrid_large_pcd_v1.0.nemo"
    sample_rate: int = 16000
    max_retries: int = 3
    retry_delay: float = 0.1

    @classmethod
    def from_dict(cls, d: dict) -> "STTConfig":
        return cls(
            model_id=d.get("model_id", "NAMAA-Space/EgypTalk-ASR-v2"),
            local_model_path=d.get(
                "local_model_path",
                "models/stt_ar_fastconformer_hybrid_large_pcd_v1.0.nemo",
            ),
            sample_rate=d.get("sample_rate", 16000),
            max_retries=d.get("max_retries", 3),
            retry_delay=d.get("retry_delay", 0.1),
        )


class STT:
    """
    NeMo Arabic Speech-to-Text with batch and buffered transcription.

    Supports two modes:
    1. Batch: stt.transcribe(audio_bytes) -> text
    2. Buffered: stt.feed(chunk) x N, then stt.finalize() -> text
    """

    DEFAULT_MODEL_ID = "NAMAA-Space/EgypTalk-ASR-v2"
    LOCAL_MODEL_PATH = "models/stt_ar_fastconformer_hybrid_large_pcd_v1.0.nemo"
    SAMPLE_RATE = 16000

    def __init__(self, config: Optional[STTConfig] = None):
        if config is None:
            from wanis.utils.config import get_section

            config = STTConfig.from_dict(get_section("stt"))

        self.config = config
        self.model = None
        self._initialized = False

        # Buffer for streaming mode
        self._audio_buffer: list[np.ndarray] = []

        # Metrics
        self._last_processing_time_ms = 0
        self._last_confidence = 0.0

    def initialize(self) -> None:
        """Load the STT model (tries local first, then HuggingFace)."""
        if self._initialized:
            return

        loading_strategies = [
            ("local", self._load_local_model),
            ("huggingface", self._load_huggingface_model),
        ]

        for strategy_name, load_func in loading_strategies:
            try:
                logger.info(f"Attempting to load STT model ({strategy_name})...")
                load_func()
                self._initialized = True
                logger.info(f"STT model loaded successfully ({strategy_name})")
                return
            except Exception as e:
                logger.warning(f"Failed to load ({strategy_name}): {e}")
                continue

        raise RuntimeError("Failed to load STT model from all sources")

    def _load_local_model(self) -> None:
        """Load model from local .nemo file."""
        from nemo.collections.asr.models import EncDecHybridRNNTCTCModel

        local_path = Path(self.config.local_model_path)
        if not local_path.exists():
            raise FileNotFoundError(f"Local model not found: {local_path}")

        logger.info(f"Loading from local file: {local_path}")
        self.model = EncDecHybridRNNTCTCModel.restore_from(str(local_path))

    def _load_huggingface_model(self) -> None:
        """Load model from HuggingFace."""
        from nemo.collections.asr.models import EncDecHybridRNNTCTCModel

        logger.info(f"Loading from HuggingFace: {self.config.model_id}")
        self.model = EncDecHybridRNNTCTCModel.from_pretrained(self.config.model_id)

    def transcribe(self, audio_bytes: bytes) -> str:
        """
        Transcribe audio bytes to text (batch mode).

        Args:
            audio_bytes: Raw audio bytes (16-bit PCM, 16kHz, mono)

        Returns:
            Transcribed text (may be empty string)
        """
        if not self._initialized:
            self.initialize()

        audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
        audio_float = audio_np.astype(np.float32) / 32767.0

        start_time = time.time()

        for attempt in range(self.config.max_retries):
            try:
                transcripts = self.model.transcribe([audio_float])
                self._last_processing_time_ms = int((time.time() - start_time) * 1000)

                if transcripts and len(transcripts) > 0:
                    result = (
                        transcripts[0]
                        if isinstance(transcripts[0], str)
                        else transcripts[0].text
                    )
                    self._last_confidence = 0.8
                    return result
                return ""

            except Exception as e:
                logger.warning(f"Transcription attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    logger.error(
                        f"Transcription failed after {self.config.max_retries} attempts: {e}"
                    )
                    return ""

    def feed(self, audio_bytes: bytes) -> None:
        """
        Feed audio chunk to buffer (buffered mode).

        Args:
            audio_bytes: Raw audio bytes (16-bit PCM, 16kHz, mono)
        """
        if not audio_bytes:
            return

        audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
        self._audio_buffer.append(audio_np)

    def finalize(self) -> str:
        """
        Transcribe all buffered audio and clear buffer.

        Returns:
            Transcribed text (may be empty string)
        """
        if not self._initialized:
            self.initialize()

        if not self._audio_buffer:
            logger.warning("No audio buffered for transcription")
            return ""

        # Combine all chunks
        full_audio = np.concatenate(self._audio_buffer)
        audio_float = full_audio.astype(np.float32) / 32767.0

        logger.info(
            f"Transcribing {len(full_audio)} samples ({len(full_audio) / self.SAMPLE_RATE:.2f}s)"
        )

        start_time = time.time()

        for attempt in range(self.config.max_retries):
            try:
                transcripts = self.model.transcribe([audio_float])
                self._last_processing_time_ms = int((time.time() - start_time) * 1000)

                if transcripts and len(transcripts) > 0:
                    result = (
                        transcripts[0]
                        if isinstance(transcripts[0], str)
                        else transcripts[0].text
                    )
                    self._last_confidence = 0.8
                    logger.info(
                        f"Transcribed: {result} ({self._last_processing_time_ms}ms)"
                    )
                else:
                    result = ""

                # Clear buffer
                self._audio_buffer = []
                return result

            except Exception as e:
                logger.warning(f"Transcription attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    logger.error(
                        f"Transcription failed after {self.config.max_retries} attempts: {e}"
                    )
                    self._audio_buffer = []
                    return ""

    def get_buffer_duration_seconds(self) -> float:
        """Get current buffer duration in seconds."""
        total_samples = sum(len(chunk) for chunk in self._audio_buffer)
        return total_samples / self.SAMPLE_RATE

    def reset(self) -> None:
        """Clear buffer without transcribing."""
        self._audio_buffer = []
        logger.debug("STT buffer cleared")

    def has_audio(self) -> bool:
        """Check if there's audio in the buffer."""
        return len(self._audio_buffer) > 0

    def is_ready(self) -> bool:
        """Check if STT is initialized."""
        return self._initialized

    def get_last_processing_time_ms(self) -> int:
        """Return processing time of last transcription in milliseconds."""
        return self._last_processing_time_ms

    def get_confidence(self) -> float:
        """Return confidence score of last transcription."""
        return self._last_confidence
