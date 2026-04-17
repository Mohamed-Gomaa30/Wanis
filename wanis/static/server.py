import os

# ── Single-process mode (must come before torch/nemo) ──────────────────────
os.environ["NEMO_DISABLE_STRICT_METADATA_CHECK"] = "1"
os.environ["HYDRA_FULL_ERROR"] = "1"
os.environ.setdefault("MASTER_ADDR", "127.0.0.1")
os.environ.setdefault("MASTER_PORT", "29500")
os.environ.setdefault("RANK", "0")
os.environ.setdefault("WORLD_SIZE", "1")
os.environ.setdefault("LOCAL_RANK", "0")

import sys

# ── Block Megatron-FSDP entirely ────────────────────────────────────────────
# Megatron-FSDP detects megatron.core via `from megatron.core import
# parallel_state` inside a try/except at import time.
# Setting these to None in sys.modules causes that import to raise
# ImportError → HAS_MEGATRON_CORE = False → no distributed NCCL groups.
for _key in [
    "megatron.core.parallel_state",
    "megatron.core.distributed",
    "megatron.core.distributed.fsdp",
]:
    sys.modules.setdefault(_key, None)  # only blocks if not yet loaded

import asyncio
import json
import logging
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Wanis components
from wanis.voice.vad import VAD
from wanis.voice.stt import STT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
ENABLE_LLM_TTS = os.getenv("WANIS_ENABLE_LLM_TTS", "0") == "1"

# ----------------------------------------------------------------------
# Global model instances – loaded once for the whole process
# ----------------------------------------------------------------------
vad_engine = VAD()
stt_engine = STT()
tts_engine = None
agent_engine = None


def init_models() -> None:
    """Load base models once; optionally enable LLM+TTS."""
    global agent_engine
    logger.info("Initializing models...")
    vad_engine.initialize()
    stt_engine.initialize()
    if ENABLE_LLM_TTS:
        try:
            from wanis.voice.tts import TTS
            from wanis.agent.llm_agent import CompanionAgent
            from wanis.utils.config import get_section

            global tts_engine
            tts_engine = TTS()
            tts_engine.initialize()
            if agent_engine is None:
                agent_engine = CompanionAgent(get_section("agent"))
                agent_engine.initialize()
            logger.info("All models ready (VAD+STT+LLM+TTS).")
        except Exception as exc:
            logger.warning(
                "LLM/TTS disabled after initialization failure: %s. "
                "Continuing with VAD+STT only.",
                exc,
            )
    else:
        logger.info("All models ready (VAD+STT only).")


init_models()

app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/test")
async def test_page() -> FileResponse:
    return FileResponse(os.path.join(FRONTEND_DIR, "test.html"))


@app.get("/app.css")
async def app_css() -> FileResponse:
    return FileResponse(os.path.join(FRONTEND_DIR, "app.css"))


@app.get("/app.js")
async def app_js() -> FileResponse:
    return FileResponse(os.path.join(FRONTEND_DIR, "app.js"))


class Session:
    """Per‑WebSocket state & queue."""

    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.vad = VAD()
        self.vad.initialize()
        self.queue = asyncio.Queue()  # (request_id, np.ndarray)
        self.is_speaking = False


async def process_queue(session: Session) -> None:
    """Consume VAD‑finished segments and run STT; optional LLM+TTS."""
    while True:
        req_id, audio_np = await session.queue.get()
        try:
            # -------------------- STT --------------------
            pcm_bytes = (audio_np * 32767).astype(np.int16).tobytes()
            transcription = await asyncio.to_thread(stt_engine.transcribe, pcm_bytes)
            logger.info(f"[{req_id}] STT: {transcription}")
            await session.ws.send_json({"type": "transcription", "text": transcription})

            # -------------------- Optional LLM + TTS --------------------
            if ENABLE_LLM_TTS and agent_engine is not None and tts_engine is not None:
                async for sentence in agent_engine.generate_response(transcription):
                    logger.info(f"[{req_id}] LLM sentence: {sentence}")
                    tts_bytes = await tts_engine.synthesize_async(sentence)
                    await session.ws.send_json(
                        {"type": "audio", "sentence": sentence, "data": tts_bytes.hex()}
                    )

            await session.ws.send_json({"type": "done"})

        except Exception as exc:
            logger.exception("Pipeline error")
            await session.ws.send_json({"type": "error", "message": str(exc)})
        finally:
            session.queue.task_done()


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    session = Session(ws)
    worker = asyncio.create_task(process_queue(session))

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)

            if msg.get("type") != "audio_chunk":
                continue

            # Decode the base64 chunk sent by the browser
            import base64
            try:
                chunk_bytes = base64.b64decode(msg["data"], validate=True)
            except Exception:
                await ws.send_json({"type": "error", "message": "Invalid audio chunk encoding"})
                continue

            # Feed to VAD
            event = session.vad.process(chunk_bytes)

            if event:
                if event["type"] == "speech_start":
                    session.is_speaking = True
                    await ws.send_json({"type": "vad", "status": "listening"})
                elif event["type"] == "speech_end":
                    session.is_speaking = False
                    await ws.send_json({"type": "vad", "status": "processing"})
                    await session.queue.put((msg.get("request_id"), event["audio"]))
                    logger.info(f"Queued segment {msg.get('request_id')}")

    except WebSocketDisconnect:
        worker.cancel()
        logger.info("Client disconnected")
    except Exception as exc:
        logger.exception("WebSocket error")
        worker.cancel()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
