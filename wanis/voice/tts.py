"""
Arabic Text-to-Speech Service using EGTTS-V0.1.

Uses OmarSamir/EGTTS-V0.1 model for Egyptian Arabic synthesis.
Optimized for elderly users with slower speech rate.

Usage:
    tts = TTS()
    tts.initialize()

    # Synthesize text
    audio_bytes = tts.synthesize("صباح الفل")

    # Async streaming
    async for audio_chunk in tts.synthesize_streaming(text):
        await play(audio_chunk)
"""

import asyncio
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)


@dataclass
class TTSConfig:
    model_id: str = "OmarSamir/EGTTS-V0.1"
    language: str = "ar"
    speed: float = 0.85
    sample_rate: int = 16000

    @classmethod
    def from_dict(cls, d: dict) -> "TTSConfig":
        return cls(
            model_id=d.get("model_id", "OmarSamir/EGTTS-V0.1"),
            language=d.get("language", "ar"),
            speed=d.get("speed", 0.85),
            sample_rate=d.get("sample_rate", 16000),
        )


class TTS:
    """
    Arabic Text-to-Speech using EGTTS-V0.1.

    Configurable speed for elderly users (slower = easier to understand).
    """

    DEFAULT_MODEL_ID = "OmarSamir/EGTTS-V0.1"
    SAMPLE_RATE = 16000

    def __init__(self, config: Optional[TTSConfig] = None):
        if config is None:
            from wanis.utils.config import get_section

            config = TTSConfig.from_dict(get_section("tts"))

        self.config = config
        self.tts = None
        self._initialized = False

    def initialize(self) -> None:
        """Load the TTS model."""
        if self._initialized:
            return

        logger.info(f"Loading TTS model: {self.config.model_id}")

        try:
            from TTS.api import TTS

            self.tts = TTS(model_name=self.config.model_id, progress_bar=False)
            self._initialized = True
            logger.info(f"TTS model loaded successfully")

        except ImportError:
            logger.error("TTS library not installed. Install with: pip install TTS")
            raise RuntimeError("TTS library not installed")

        except Exception as e:
            logger.error(f"Failed to load TTS model: {e}")
            raise

    def synthesize(self, text: str, speed: Optional[float] = None) -> bytes:
        """
        Synthesize text to audio bytes.

        Args:
            text: Text to synthesize
            speed: Speech speed multiplier (None = use config default)

        Returns:
            Audio bytes (WAV format)
        """
        if not self._initialized:
            self.initialize()

        if not text or not text.strip():
            return b""

        speed = speed or self.config.speed

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                output_path = f.name

            self.tts.tts_to_file(
                text=text,
                file_path=output_path,
                language=self.config.language,
                speed=speed,
            )

            audio_bytes = Path(output_path).read_bytes()
            os.unlink(output_path)

            logger.debug(f"Synthesized {len(text)} chars -> {len(audio_bytes)} bytes")
            return audio_bytes

        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return b""

    async def synthesize_async(self, text: str, speed: Optional[float] = None) -> bytes:
        """Synthesize text asynchronously."""
        return await asyncio.to_thread(self.synthesize, text, speed)

    async def synthesize_streaming(
        self, text: str, speed: Optional[float] = None
    ) -> AsyncGenerator[bytes, None]:
        """
        Synthesize text in a streaming manner.

        Note: This implementation synthesizes the full text at once,
        but yields it as a single chunk for consistency with async interface.
        Future optimization could split text and synthesize parts in parallel.

        Args:
            text: Text to synthesize
            speed: Speech speed multiplier

        Yields:
            Audio bytes for playback
        """
        audio_bytes = await self.synthesize_async(text, speed)
        if audio_bytes:
            yield audio_bytes

    def is_ready(self) -> bool:
        """Check if TTS is initialized."""
        return self._initialized
