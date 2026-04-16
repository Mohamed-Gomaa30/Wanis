#!/usr/bin/env python3
"""
Hybrid MediaRecorder + VAD + STT server.

Client uses MediaRecorder to capture audio in chunks, sends to server.
Server uses VAD to detect speech boundaries, STT to transcribe.
Combines benefits of both approaches.
"""

import argparse
import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Optional

import numpy as np
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from wanis.voice.vad import VAD, VADConfig
from wanis.voice.stt import STT
from wanis.utils.config import get_config

logger = logging.getLogger("hybrid_server")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class SpeechSegment:
    """Complete speech segment ready for transcription."""

    id: int
    audio: np.ndarray
    start_time: float
    end_time: float

    def get_audio_bytes(self) -> bytes:
        """Convert to PCM int16 bytes for STT."""
        return (self.audio * 32767).astype(np.int16).tobytes()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Hybrid MediaRecorder + VAD + STT Server")

# Global components
vad: Optional[VAD] = None
stt: Optional[STT] = None

# Queues
chunk_queue: Optional[asyncio.Queue] = None
segment_queue: Optional[asyncio.Queue] = None

# Workers
workers: list[asyncio.Task] = []

# Segment counter
segment_counter = 0
segment_lock = asyncio.Lock()


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup():
    global vad, stt, chunk_queue, segment_queue, workers

    logger.info("Starting Hybrid MediaRecorder + VAD + STT server")

    # Initialize VAD
    vad = VAD()
    vad.initialize()
    logger.info("VAD ready")

    # Initialize STT
    stt = STT()
    stt.initialize()
    logger.info("STT ready")

    # Create queues
    chunk_queue = asyncio.Queue(maxsize=500)
    segment_queue = asyncio.Queue(maxsize=200)

    # Start workers
    workers = [
        asyncio.create_task(vad_worker(), name="vad_worker"),
        asyncio.create_task(stt_worker(), name="stt_worker"),
    ]
    logger.info("Workers started")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down workers")
    for w in workers:
        w.cancel()
    await asyncio.gather(*workers, return_exceptions=True)
    logger.info("Shutdown complete")


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    client_id = str(uuid.uuid4())[:8]
    logger.info(f"[{client_id}] WebSocket connection opened")

    try:
        chunk_count = 0
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            if "bytes" in msg and msg["bytes"]:
                chunk_count += 1
                if chunk_count % 10 == 0:
                    logger.debug(f"[{client_id}] Received {chunk_count} chunks")
                await chunk_queue.put((client_id, ws, msg["bytes"], time.time()))
    except WebSocketDisconnect:
        logger.info(f"[{client_id}] Disconnected")
    finally:
        logger.info(
            f"[{client_id}] Connection closed (received {chunk_count} chunks total)"
        )


# ---------------------------------------------------------------------------
# VAD worker - processes audio chunks and detects speech boundaries
# ---------------------------------------------------------------------------
async def vad_worker():
    global segment_counter
    logger.info("[VAD worker] started")
    client_state: dict[str, dict] = {}

    while True:
        try:
            client_id, ws, audio_bytes, recv_time = await asyncio.wait_for(
                chunk_queue.get(), timeout=0.1
            )
        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            break

        # Per-client VAD instance
        if client_id not in client_state:
            cfg = VADConfig.from_dict(get_config().get("vad", {}))
            vad_inst = VAD(config=cfg)
            vad_inst.model = vad.model
            vad_inst._initialized = True
            client_state[client_id] = {"vad": vad_inst}
        vad_inst = client_state[client_id]["vad"]

        event = vad_inst.process(audio_bytes)
        if event:
            if event["type"] == "speech_start":
                logger.debug(f"[{client_id}] speech start")
            elif event["type"] == "speech_end":
                audio_np: np.ndarray = event["audio"]
                async with segment_lock:
                    segment_counter += 1
                    seg_id = segment_counter
                segment = SpeechSegment(
                    id=seg_id,
                    audio=audio_np,
                    start_time=time.time(),
                    end_time=time.time(),
                )
                await segment_queue.put((client_id, ws, segment))
                logger.info(
                    f"[{client_id}] Speech segment {seg_id} ({len(audio_np) / 16:.2f}s)"
                )
        chunk_queue.task_done()
    logger.info("[VAD worker] stopped")


# ---------------------------------------------------------------------------
# STT worker - transcribes speech segments
# ---------------------------------------------------------------------------
async def stt_worker():
    logger.info("[STT worker] started")
    while True:
        try:
            client_id, ws, segment = await asyncio.wait_for(
                segment_queue.get(), timeout=0.1
            )
        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            break
        start = time.time()
        text = stt.transcribe(segment.get_audio_bytes())
        proc_ms = int((time.time() - start) * 1000)
        logger.info(f"[{client_id}] Transcript: '{text}' ({proc_ms}ms)")
        if ws.application_state == ws.state.CONNECTED:
            await ws.send_json(
                {"type": "transcript", "text": text, "processing_time_ms": proc_ms}
            )
        segment_queue.task_done()
    logger.info("[STT worker] stopped")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Hybrid MediaRecorder + VAD + STT server"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument(
        "--config", default="wanis/configs/wanis_config.yaml", help="Config file"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable DEBUG logging")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    uvicorn.run(
        "wanis.web.hybrid_server:app",
        host=args.host,
        port=args.port,
        log_level="debug" if args.verbose else "info",
    )


if __name__ == "__main__":
    main()
