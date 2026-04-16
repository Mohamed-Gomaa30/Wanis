"""
Audio I/O Module - Unified audio capture and playback.

Combines microphone input and speaker output in one module.
Uses sounddevice for cross-platform audio I/O.
"""

import asyncio
import logging
import threading
from collections import deque
from dataclasses import dataclass
from typing import Optional, Callable

import numpy as np

logger = logging.getLogger(__name__)

try:
    import sounddevice as sd

    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    logger.warning("sounddevice not available - audio I/O disabled")


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    buffer_seconds: float = 30.0

    @classmethod
    def from_dict(cls, d: dict) -> "AudioConfig":
        return cls(
            sample_rate=d.get("sample_rate", 16000),
            channels=d.get("channels", 1),
            buffer_seconds=d.get("buffer_seconds", 30.0),
        )


class AudioInput:
    """Microphone input handler with circular buffer."""

    def __init__(self, config: Optional[AudioConfig] = None):
        if not SOUNDDEVICE_AVAILABLE:
            raise RuntimeError("sounddevice not available")

        if config is None:
            from wanis.utils.config import get_section

            config = AudioConfig.from_dict(get_section("audio"))

        self.config = config
        self._buffer: deque = deque(
            maxlen=int(self.config.sample_rate * self.config.buffer_seconds)
        )
        self._stream = None
        self._recording = False
        self._lock = threading.Lock()
        self._callback: Optional[Callable[[bytes], None]] = None

    def start(
        self,
        device: Optional[int] = None,
        callback: Optional[Callable[[bytes], None]] = None,
    ) -> None:
        """Start capturing audio from microphone.

        Args:
            device: Optional device index (None = default)
            callback: Optional callback for real-time audio chunks (for streaming)
        """
        if self._recording:
            return

        self._callback = callback

        try:
            self._stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                device=device,
                callback=self._audio_callback,
                dtype=np.float32,
            )
            self._stream.start()
            self._recording = True
            logger.info(f"Audio capture started (device={device})")
        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            raise

    def _audio_callback(self, indata, frames, time, status):
        with self._lock:
            audio_data = indata[:, 0]
            self._buffer.extend(audio_data)

            if self._callback:
                audio_int16 = (audio_data * 32767).astype(np.int16)
                self._callback(audio_int16.tobytes())

    def stop(self) -> None:
        """Stop capturing audio."""
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._recording = False
        self._callback = None
        logger.info("Audio capture stopped")

    def get_audio(self, duration_seconds: float = 3.0) -> bytes:
        """Get audio from buffer as PCM int16 bytes.

        Args:
            duration_seconds: Duration to retrieve

        Returns:
            Audio bytes (16-bit PCM, 16kHz, mono)
        """
        samples = int(duration_seconds * self.config.sample_rate)

        with self._lock:
            if len(self._buffer) < samples:
                audio_float = np.array(list(self._buffer), dtype=np.float32)
            else:
                audio_float = np.array(list(self._buffer)[-samples:], dtype=np.float32)

        audio_int16 = (audio_float * 32767).astype(np.int16)
        return audio_int16.tobytes()

    def is_recording(self) -> bool:
        return self._recording

    @staticmethod
    def list_devices() -> list[dict]:
        """List available input devices."""
        if not SOUNDDEVICE_AVAILABLE:
            return []

        devices = sd.query_devices()
        return [
            {"index": i, "name": d["name"], "channels": d["max_input_channels"]}
            for i, d in enumerate(devices)
            if d["max_input_channels"] > 0
        ]


class AudioOutput:
    """Speaker output handler with queue-based playback."""

    def __init__(self, sample_rate: Optional[int] = None):
        if not SOUNDDEVICE_AVAILABLE:
            raise RuntimeError("sounddevice not available")

        if sample_rate is None:
            from wanis.utils.config import get_value

            sample_rate = get_value("audio", "sample_rate", 16000)

        self.sample_rate = sample_rate
        self._playing = False
        self._stop_requested = False
        self._interrupt_requested = False

    def play(self, audio_bytes: bytes, blocking: bool = True) -> None:
        """Play audio bytes.

        Args:
            audio_bytes: PCM int16 audio bytes
            blocking: Wait for playback to complete
        """
        if not audio_bytes:
            return

        audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
        audio_float = audio_int16.astype(np.float32) / 32767.0

        self._playing = True
        self._stop_requested = False
        self._interrupt_requested = False

        try:
            sd.play(audio_float, samplerate=self.sample_rate)
            if blocking:
                sd.wait()
        except Exception as e:
            logger.error(f"Playback error: {e}")
        finally:
            self._playing = False

    async def play_async(self, audio_bytes: bytes) -> None:
        """Play audio asynchronously."""
        await asyncio.to_thread(self.play, audio_bytes, blocking=True)

    async def play_queue(self, audio_queue: asyncio.Queue) -> None:
        """Play audio chunks from a queue.

        Args:
            audio_queue: asyncio.Queue containing audio bytes
        """
        self._playing = True
        self._stop_requested = False

        try:
            while not self._stop_requested:
                try:
                    audio_bytes = await asyncio.wait_for(audio_queue.get(), timeout=0.1)
                    if audio_bytes is None:
                        break
                    await self.play_async(audio_bytes)
                    audio_queue.task_done()
                except asyncio.TimeoutError:
                    continue
        finally:
            self._playing = False

    def stop(self) -> None:
        """Stop current playback."""
        self._stop_requested = True
        sd.stop()

    def interrupt(self) -> None:
        """Signal interruption (for barge-in)."""
        self._interrupt_requested = True
        self.stop()

    def is_playing(self) -> bool:
        return self._playing

    def was_interrupted(self) -> bool:
        return self._interrupt_requested

    @staticmethod
    def list_devices() -> list[dict]:
        """List available output devices."""
        if not SOUNDDEVICE_AVAILABLE:
            return []

        devices = sd.query_devices()
        return [
            {"index": i, "name": d["name"], "channels": d["max_output_channels"]}
            for i, d in enumerate(devices)
            if d["max_output_channels"] > 0
        ]
