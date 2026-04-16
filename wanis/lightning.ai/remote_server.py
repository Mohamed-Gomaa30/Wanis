"""
Remote Server - Full Pipeline on Lightning AI.

Receives audio from client, processes through full pipeline, and plays audio locally.

Pipeline: WebSocket → VAD → STT → LLM → TTS → Audio Output

All workers run concurrently as async tasks, using queues for communication.

Usage:
    python -m wanis.lightning.remote_server --port 8000 --verbose
"""

import argparse
import asyncio
import json
import logging
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from wanis.voice.vad import VAD
from wanis.voice.stt import STT
from wanis.voice.tts import TTS
from wanis.voice.audio import AudioOutput
from wanis.utils.config import get_config, set_config_path

logger = logging.getLogger("remote_server")


# =============================================================================
# Data Classes for Queue Messages
# =============================================================================


@dataclass
class SpeechSegment:
    """Complete speech segment ready for transcription."""

    id: int
    audio: np.ndarray  # Float32 audio samples
    start_time: float
    end_time: float

    def get_audio_bytes(self) -> bytes:
        """Convert to PCM int16 bytes."""
        return (self.audio * 32767).astype(np.int16).tobytes()


@dataclass
class TranscriptResult:
    """Transcript from STT."""

    segment_id: int
    text: str
    processing_time_ms: int


@dataclass
class Response:
    """LLM response ready for TTS."""

    segment_id: int
    text: str


@dataclass
class AudioChunk:
    """Audio chunk for playback."""

    segment_id: int
    audio_bytes: bytes


# =============================================================================
# Global State
# =============================================================================

app = FastAPI(title="Wanis Remote Voice Server")

# Global components
vad: VAD = None
stt: STT = None
tts: TTS = None
audio_output: AudioOutput = None

# Queues for concurrent processing
chunk_queue: asyncio.Queue = None
segment_queue: asyncio.Queue = None
transcript_queue: asyncio.Queue = None
response_queue: asyncio.Queue = None
tts_queue: asyncio.Queue = None

# Worker tasks
workers: list[asyncio.Task] = []

# Segment counter
segment_counter = 0
segment_lock = asyncio.Lock()


# =============================================================================
# Startup & Shutdown
# =============================================================================


@app.on_event("startup")
async def startup():
    """Initialize server components and start workers."""
    global vad, stt, tts, audio_output
    global chunk_queue, segment_queue, transcript_queue, response_queue, tts_queue
    global workers

    logger.info("=" * 60)
    logger.info("REMOTE SERVER - Starting up")
    logger.info("=" * 60)

    # Initialize components
    logger.info("Initializing VAD...")
    vad = VAD()
    vad.initialize()
    logger.info("VAD initialized")

    logger.info("Initializing STT...")
    stt = STT()
    stt.initialize()
    logger.info("STT initialized")

    logger.info("Initializing TTS...")
    try:
        tts = TTS()
        tts.initialize()
        logger.info("TTS initialized")
    except Exception as e:
        logger.warning(f"TTS initialization failed: {e}")
        logger.warning(
            "TTS will be disabled. Install with: pip install TTS (requires Python <3.12)"
        )
        tts = None

    logger.info("Initializing Audio Output...")
    audio_output = AudioOutput()
    logger.info("Audio Output initialized")

    # Create queues
    chunk_queue = asyncio.Queue(maxsize=1000)
    segment_queue = asyncio.Queue(maxsize=100)
    transcript_queue = asyncio.Queue(maxsize=100)
    response_queue = asyncio.Queue(maxsize=100)
    tts_queue = asyncio.Queue(maxsize=100)

    # Start worker tasks
    logger.info("Starting worker tasks...")
    workers = [
        asyncio.create_task(vad_worker(), name="vad_worker"),
        asyncio.create_task(stt_worker(), name="stt_worker"),
        asyncio.create_task(llm_worker(), name="llm_worker"),
        asyncio.create_task(tts_worker(), name="tts_worker"),
        asyncio.create_task(audio_output_worker(), name="audio_output_worker"),
    ]

    logger.info("=" * 60)
    logger.info("SERVER READY - Waiting for connections")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown():
    """Stop all workers."""
    logger.info("Shutting down workers...")
    for w in workers:
        w.cancel()
    await asyncio.gather(*workers, return_exceptions=True)
    logger.info("Workers stopped")


# =============================================================================
# WebSocket Endpoint
# =============================================================================


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    WebSocket endpoint for receiving audio stream.

    Protocol:
    - Client sends raw audio chunks (binary, PCM int16, 16kHz, mono)
    - Server sends status and transcript (JSON)

    Server → Client messages:
    - {"type": "transcript", "text": "...", "processing_time_ms": ...}
    - {"type": "status", "state": "listening|transcribing|responding"}
    - {"type": "error", "message": "..."}
    """
    await ws.accept()
    client_id = str(uuid.uuid4())[:8]
    logger.info(f"[{client_id}] Client connected")

    try:
        while True:
            message = await ws.receive()

            if message["type"] == "websocket.disconnect":
                break

            # Binary message = audio chunk
            if "bytes" in message and message["bytes"]:
                audio_bytes = message["bytes"]
                # Queue for VAD processing
                await chunk_queue.put((client_id, ws, audio_bytes, time.time()))

    except WebSocketDisconnect:
        logger.info(f"[{client_id}] Client disconnected")
    except Exception as e:
        logger.error(f"[{client_id}] WebSocket error: {e}")
    finally:
        logger.info(f"[{client_id}] Connection closed")


# =============================================================================
# Worker: VAD (Voice Activity Detection)
# =============================================================================


async def vad_worker():
    """
    VAD worker - processes audio chunks and detects speech segments.

    Continuously processes audio from chunk_queue, runs through VAD,
    and queues complete speech segments.
    """
    global segment_counter

    logger.info("[VAD Worker] Started")

    # Per-client state
    client_states: dict[str, dict] = {}

    while True:
        try:
            client_id, ws, audio_bytes, receive_time = await asyncio.wait_for(
                chunk_queue.get(), timeout=0.1
            )

            # Initialize client state if needed
            if client_id not in client_states:
                client_states[client_id] = {
                    "audio_buffer": [],
                    "vad_buffer": vad.__class__(vad.config),
                }
                client_states[client_id]["vad_buffer"].model = vad.model
                client_states[client_id]["vad_buffer"]._initialized = True

            state = client_states[client_id]

            # Process through VAD
            event = state["vad_buffer"].process(audio_bytes)

            if event:
                if event["type"] == "speech_start":
                    logger.info(f"[{client_id}][VAD] >>> SPEECH START <<<")
                    state["audio_buffer"] = []
                    state["speech_start_time"] = time.time()
                    # Send status to client
                    try:
                        await ws.send(
                            json.dumps({"type": "status", "state": "listening"})
                        )
                    except:
                        pass

                elif event["type"] == "speech_end":
                    # Get complete speech audio
                    audio_data: np.ndarray = event["audio"]
                    duration_ms = len(audio_data) / 16

                    logger.info(f"[{client_id}][VAD] >>> SPEECH END <<<")
                    logger.info(f"[{client_id}][VAD] Duration: {duration_ms:.0f}ms")

                    # Create segment
                    async with segment_lock:
                        segment_counter += 1
                        segment_id = segment_counter

                    segment = SpeechSegment(
                        id=segment_id,
                        audio=audio_data,
                        start_time=state.get("speech_start_time", time.time()),
                        end_time=time.time(),
                    )

                    # Queue for STT
                    await segment_queue.put((client_id, ws, segment))

                    # Reset state
                    state["audio_buffer"] = []

        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[VAD Worker] Error: {e}")

    logger.info("[VAD Worker] Stopped")


# =============================================================================
# Worker: STT (Speech-to-Text)
# =============================================================================


async def stt_worker():
    """
    STT worker - transcribes speech segments.

    Waits for segments from segment_queue, transcribes using NeMo,
    and queues transcripts.
    """
    logger.info("[STT Worker] Started")

    while True:
        try:
            client_id, ws, segment = await asyncio.wait_for(
                segment_queue.get(), timeout=0.1
            )

            logger.info(f"[{client_id}][STT] Transcribing segment #{segment.id}")
            logger.info(
                f"[{client_id}][STT] Audio duration: {len(segment.audio) / 16:.0f}ms"
            )

            # Send status
            try:
                await ws.send(json.dumps({"type": "status", "state": "transcribing"}))
            except:
                pass

            # Transcribe
            start_time = time.time()
            audio_bytes = segment.get_audio_bytes()
            text = stt.transcribe(audio_bytes)
            processing_time_ms = int((time.time() - start_time) * 1000)

            if text:
                logger.info(f"[{client_id}][STT] >>> TRANSCRIPT: {text}")
                logger.info(
                    f"[{client_id}][STT] Processing time: {processing_time_ms}ms"
                )

                # Send transcript to client
                try:
                    await ws.send(
                        json.dumps(
                            {
                                "type": "transcript",
                                "text": text,
                                "processing_time_ms": processing_time_ms,
                            }
                        )
                    )
                except:
                    pass

                # Queue for LLM
                result = TranscriptResult(
                    segment_id=segment.id,
                    text=text,
                    processing_time_ms=processing_time_ms,
                )
                await transcript_queue.put((client_id, ws, result))
            else:
                logger.warning(f"[{client_id}][STT] No speech detected in segment")

        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[STT Worker] Error: {e}")

    logger.info("[STT Worker] Stopped")


# =============================================================================
# Worker: LLM (Language Model)
# =============================================================================


async def llm_worker():
    """
    LLM worker - generates responses.

    Waits for transcripts, generates responses using Gemini,
    and queues for TTS.
    """
    logger.info("[LLM Worker] Started")

    # Lazy load agent
    agent = None

    while True:
        try:
            client_id, ws, transcript = await asyncio.wait_for(
                transcript_queue.get(), timeout=0.1
            )

            # Lazy load agent
            if agent is None:
                from wanis.agent.llm_agent import CompanionAgent

                config = get_config()
                agent_config = config.get("agent", {})
                agent = CompanionAgent(agent_config)
                agent.initialize()
                logger.info("[LLM Worker] Agent initialized")

            logger.info(
                f"[{client_id}][LLM] Generating response for: {transcript.text}"
            )

            # Send status
            try:
                await ws.send(json.dumps({"type": "status", "state": "responding"}))
            except:
                pass

            # Generate response (streaming)
            full_response = ""
            async for sentence in agent.generate_response(transcript.text):
                full_response += sentence + " "
                logger.info(f"[{client_id}][LLM] Sentence: {sentence}")

                # Queue each sentence for TTS
                response = Response(
                    segment_id=transcript.segment_id,
                    text=sentence,
                )
                await response_queue.put((client_id, ws, response))

            logger.info(f"[{client_id}][LLM] Full response: {full_response.strip()}")

        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[LLM Worker] Error: {e}")

    logger.info("[LLM Worker] Stopped")


# =============================================================================
# Worker: TTS (Text-to-Speech)
# =============================================================================


async def tts_worker():
    """
    TTS worker - synthesizes speech.

    Waits for responses, synthesizes using EGTTS,
    and queues audio for playback.
    """
    global tts

    if tts is None:
        logger.warning("[TTS Worker] TTS not available, skipping synthesis")
        return

    logger.info("[TTS Worker] Started")

    while True:
        try:
            client_id, ws, response = await asyncio.wait_for(
                response_queue.get(), timeout=0.1
            )

            logger.info(f"[{client_id}][TTS] Synthesizing: {response.text[:50]}...")

            # Synthesize
            start_time = time.time()
            audio_bytes = await tts.synthesize_async(response.text)
            processing_time_ms = int((time.time() - start_time) * 1000)

            if audio_bytes:
                logger.info(
                    f"[{client_id}][TTS] Audio: {len(audio_bytes)} bytes, {processing_time_ms}ms"
                )

                # Queue for playback
                chunk = AudioChunk(
                    segment_id=response.segment_id,
                    audio_bytes=audio_bytes,
                )
                await tts_queue.put((client_id, chunk))
            else:
                logger.warning(f"[{client_id}][TTS] No audio generated")

        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[TTS Worker] Error: {e}")

    logger.info("[TTS Worker] Stopped")


# =============================================================================
# Worker: Audio Output
# =============================================================================


async def audio_output_worker():
    """
    Audio output worker - plays synthesized audio.

    Waits for audio chunks and plays them through speaker.
    """
    logger.info("[Audio Output Worker] Started")

    while True:
        try:
            client_id, chunk = await asyncio.wait_for(tts_queue.get(), timeout=0.1)

            logger.info(
                f"[{client_id}][Audio] Playing audio: {len(chunk.audio_bytes)} bytes"
            )

            # Play audio
            await audio_output.play_async(chunk.audio_bytes)

            logger.info(f"[{client_id}][Audio] Playback complete")

        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[Audio Output Worker] Error: {e}")

    logger.info("[Audio Output Worker] Stopped")


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description="Wanis Remote Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--config",
        default="wanis/configs/wanis_config.yaml",
        help="Path to config file",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    set_config_path(args.config)

    logger.info(f"Starting server on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
