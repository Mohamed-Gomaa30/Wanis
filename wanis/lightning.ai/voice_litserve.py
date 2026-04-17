#!/usr/bin/env python3
"""LitServe API for Wanis real‑time voice pipeline.

The service receives **raw PCM 16‑bit mono audio chunks** (16 kHz) via a
multipart ``content`` field.  Chunks are fed to a server‑side Silero VAD.  When the
VAD emits a ``speech_end`` event the buffered speech segment is transcribed with
NeMo, passed to the Gemini ``CompanionAgent`` for a streamed response, and each
sentence is synthesized with eGTTS.  The final JSON response contains:

* ``transcription`` – the full text from NeMo.
* ``audio`` – base64‑encoded WAV of the concatenated TTS output.
* ``segments`` – a list of ``{"sentence": ..., "audio": <base64>}`` for each
  generated sentence (useful for progressive playback).

All heavy inference runs on the Lightning AI GPU(s); the browser only streams
chunks and plays back the returned audio.
"""

import base64
import asyncio
import json
import logging
from typing import Any, Dict, List

import lightning as ls
import numpy as np

# Import project components
from wanis.voice.vad import VAD
from wanis.voice.stt import STT
from wanis.voice.tts import TTS
from wanis.agent.llm_agent import CompanionAgent
from wanis.utils.config import get_section

logger = logging.getLogger(__name__)


class VoiceLitAPI(ls.LitAPI):
    """LitServe API exposing a single ``/predict`` endpoint.

    The API works in two phases:
    1. **Chunk ingestion** – each ``POST`` adds the raw bytes to an internal
       buffer and feeds them to ``VAD.process``.
    2. **When VAD signals ``speech_end``** – the buffered audio is transcribed,
       sent to the LLM, synthesized, and the full response is returned.
    """

    def __init__(self) -> None:
        super().__init__()
        # Internal state per‑client (for now we support a single client)
        self._audio_buffer = bytearray()
        self._vad = VAD()
        self._stt = STT()
        self._tts = TTS()
        self._agent: CompanionAgent | None = None
        self._initialized = False

    def _initialize_components(self) -> None:
        if self._initialized:
            return
        logger.info("Initialising VAD, STT, TTS, and LLM agent")
        self._vad.initialize()
        self._stt.initialize()
        self._tts.initialize()
        # Load agent configuration from the global config
        cfg = get_section("agent")
        self._agent = CompanionAgent(cfg)
        self._agent.initialize()
        self._initialized = True
        logger.info("All components ready")

    # ---------------------------------------------------------------------
    # LitServe overrides
    # ---------------------------------------------------------------------
    def decode_request(self, request: Dict[str, Any]) -> Any:
        """Decode multipart ``content`` and feed VAD.

        LitServe passes the raw ``FastAPI`` request dict where uploaded files are
        available under ``request["content"]`` as an ``UploadFile``.
        """
        # Lazily initialise on first request
        if not self._initialized:
            self._initialize_components()

        uploaded = request.get("content")
        if uploaded is None:
            raise ValueError("Missing 'content' field in request")
        # ``uploaded.file`` is a file‑like object
        chunk_bytes = uploaded.file.read()
        if not chunk_bytes:
            return None
        # Feed to VAD – it maintains its own state across calls
        event = self._vad.process(chunk_bytes)
        # Store raw PCM for potential STT usage (only needed until speech_end)
        self._audio_buffer.extend(chunk_bytes)
        return event

    async def predict(self, event: Any) -> Dict[str, Any]:
        """Main prediction logic.

        * If ``event`` is ``None`` or a ``speech_start`` we simply return a
          listening status.
        * On ``speech_end`` we run the full pipeline and reset buffers.
        """
        # No event yet – client is still sending chunks
        if event is None:
            return {"status": "listening"}

        if isinstance(event, dict) and event.get("type") == "speech_start":
            # The VAD already told us speech began – acknowledge.
            return {"status": "listening"}

        # -----------------------------------------------------------------
        # Speech has ended – run STT → LLM → TTS
        # -----------------------------------------------------------------
        if isinstance(event, dict) and event.get("type") == "speech_end":
            # ``event['audio']`` is a NumPy float32 array (range -1..1)
            audio_np: np.ndarray = event["audio"]
            # Convert to 16‑bit PCM for NeMo
            audio_int16 = (audio_np * 32767).astype(np.int16).tobytes()
            # -----------------------------------------------------------------
            # 1) STT with NeMo
            # -----------------------------------------------------------------
            transcription = self._stt.transcribe(audio_int16)
            logger.info("Transcription result: %s", transcription)

            # -----------------------------------------------------------------
            # 2) LLM streaming response (sentences)
            # -----------------------------------------------------------------
            assert self._agent is not None  # ensured by init
            sentences: List[str] = []
            audio_segments: List[bytes] = []
            async for sentence in self._agent.generate_response(transcription):
                sentences.append(sentence)
                # ----------------------------------------------------------------
                # 3) TTS for each sentence (async)
                # ----------------------------------------------------------------
                audio_bytes = await self._tts.synthesize_async(sentence)
                audio_segments.append(audio_bytes)

            # Concatenate all TTS audio for a single playback option
            full_audio = b"".join(audio_segments)
            audio_b64 = base64.b64encode(full_audio).decode()

            # Build per‑sentence payloads (optional but convenient for progressive UI)
            segment_list = []
            for txt, aud in zip(sentences, audio_segments):
                segment_list.append(
                    {
                        "sentence": txt,
                        "audio": base64.b64encode(aud).decode(),
                    }
                )

            # Reset buffers for next utterance
            self._audio_buffer.clear()
            self._vad.reset()

            result = {
                "transcription": transcription,
                "audio": audio_b64,
                "segments": segment_list,
            }
            logger.info("Pipeline complete – returning response")
            return result

        # Unexpected payload – fallback
        logger.warning("Unexpected event type received: %s", event)
        return {"status": "error", "message": "Invalid VAD event"}


# -------------------------------------------------------------------------
# Optional health endpoint – LitServe automatically serves /health, but we add a
# tiny FastAPI app for completeness if needed.
# -------------------------------------------------------------------------

from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


# Note: LitServe will expose the LitAPI at ``/predict``; the FastAPI health
# endpoint is available under the same server.
