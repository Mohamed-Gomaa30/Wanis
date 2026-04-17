"""
Async VAD → STT pipeline.

- Captures microphone audio via ``AudioInput``.
- Sends raw PCM bytes to an ``asyncio.Queue`` (producer).
- ``vad_worker`` pulls bytes, runs ``VAD.process`` and emits a ``speech_end`` event containing the full utterance as a NumPy array.
- ``stt_worker`` consumes the utterance, converts it to 16‑bit PCM and calls ``STT.transcribe``.
- ``logger_consumer`` prints the transcription.

All components run concurrently using ``asyncio`` and back‑pressure is enforced via ``maxsize`` on the queues.
"""

import argparse
import numpy as np
import asyncio
import logging
import signal
from typing import Optional

from wanis.voice.audio import AudioInput
from wanis.voice.vad import VAD, VADConfig
from wanis.voice.stt import STT

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Queue definitions (raw PCM -> VAD events -> transcription strings)
# ----------------------------------------------------------------------
audio_q: asyncio.Queue[bytes] = asyncio.Queue(maxsize=10)  # raw PCM chunks from mic
vad_q: asyncio.Queue["np.ndarray"] = asyncio.Queue(
    maxsize=5
)  # completed speech segments
transcript_q: asyncio.Queue[str] = asyncio.Queue(maxsize=5)  # final text strings


# ----------------------------------------------------------------------
# Producer: microphone capture – pushes raw PCM bytes onto ``audio_q``
# ----------------------------------------------------------------------
def _audio_callback(chunk: bytes) -> None:
    """Callback passed to ``AudioInput``.

    ``AudioInput`` runs the callback from a background thread, so we use
    ``asyncio.get_event_loop().call_soon_threadsafe`` to safely put the chunk
    onto the queue.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # No running loop – this can happen during interpreter shutdown.
        return
    # ``call_soon_threadsafe`` is safe from another thread.
    loop.call_soon_threadsafe(asyncio.create_task, audio_q.put(chunk))


async def audio_producer(
    stop_event: asyncio.Event, input_file: Optional[str] = None
) -> None:
    """Start ``AudioInput`` and keep it alive until ``stop_event`` is set."""
    if input_file:
        # Stream raw PCM from a file (int16 little‑endian, 16 kHz mono).
        # The file is expected to contain exactly the format produced by
        # ``AudioInput`` (int16 samples). We read it in modest‑size chunks to
+        # simulate the real‑time microphone callback.
+        chunk_size = 4096  # bytes (~2048 samples)
+        with open(input_file, "rb") as f:
+            logger.info(f"Streaming audio from file: {input_file}")
+            while not stop_event.is_set():
+                data = f.read(chunk_size)
+                if not data:
+                    # EOF – stop the pipeline gracefully.
+                    logger.info("End of input file reached")
+                    stop_event.set()
+                    break
+                await audio_q.put(data)
+                # Small sleep to avoid a tight loop and give other tasks time.
+                await asyncio.sleep(0.01)
+    else:
+        mic = AudioInput()
+        mic.start(callback=_audio_callback)
+        logger.info("Audio capture started (producer)")
+        try:
+            await stop_event.wait()
+        finally:
+            mic.stop()
+            logger.info("Audio capture stopped (producer)")


# ----------------------------------------------------------------------
# VAD worker – consumes raw PCM, runs VAD, emits completed utterance.
# ----------------------------------------------------------------------
async def vad_worker(stop_event: asyncio.Event) -> None:
    vad = VAD()
    vad.initialize()
    logger.info("VAD worker initialized")
    while not stop_event.is_set():
        try:
            chunk = await asyncio.wait_for(audio_q.get(), timeout=0.2)
        except asyncio.TimeoutError:
            continue
        event = vad.process(chunk)
        if event and event.get("type") == "speech_end":
            # ``event["audio"]`` is a NumPy float32 array of the full utterance.
            await vad_q.put(event["audio"])
        audio_q.task_done()
    logger.info("VAD worker exiting")


# ----------------------------------------------------------------------
# STT worker – consumes utterances, transcribes, pushes text.
# ----------------------------------------------------------------------
async def stt_worker(stop_event: asyncio.Event) -> None:
    stt = STT()
    stt.initialize()
    logger.info("STT worker initialized")
    while not stop_event.is_set():
        try:
            audio_np = await asyncio.wait_for(vad_q.get(), timeout=0.2)
        except asyncio.TimeoutError:
            continue
        # Convert float32 [-1, 1] back to int16 PCM bytes expected by STT.
        pcm_bytes = (audio_np * 32767).astype("int16").tobytes()
        text = stt.transcribe(pcm_bytes)
        await transcript_q.put(text if text else "[empty]")
        vad_q.task_done()
    logger.info("STT worker exiting")


# ----------------------------------------------------------------------
# Consumer – simply logs the transcription.
# ----------------------------------------------------------------------
async def logger_consumer(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            txt = await asyncio.wait_for(transcript_q.get(), timeout=0.2)
        except asyncio.TimeoutError:
            continue
        logger.info(f"Transcription: {txt}")
        transcript_q.task_done()
    logger.info("Logger consumer exiting")


# ----------------------------------------------------------------------
# Main orchestration – sets up tasks, handles SIGINT gracefully.
# ----------------------------------------------------------------------
async def async_main(config_path: Optional[str] = None) -> None:
    if config_path:
        from wanis.utils.config import set_config_path

        set_config_path(config_path)

    # Ensure logging is configured (INFO by default, DEBUG with --verbose).
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    stop_event = asyncio.Event()

    def _handle_sigint(*_):
        logger.info("SIGINT received – shutting down…")
        stop_event.set()

    # Register signal handler for graceful shutdown.
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            asyncio.get_running_loop().add_signal_handler(sig, _handle_sigint)
        except NotImplementedError:
            # Windows may not support add_signal_handler – fall back.
            signal.signal(sig, lambda *a: _handle_sigint())

    # Launch all workers.
    tasks = [
        asyncio.create_task(audio_producer(stop_event, input_file=args.input_file), name="audio_producer"),
        asyncio.create_task(vad_worker(stop_event), name="vad_worker"),
        asyncio.create_task(stt_worker(stop_event), name="stt_worker"),
        asyncio.create_task(logger_consumer(stop_event), name="logger_consumer"),
    ]

    # Wait for the stop event – when set, we cancel remaining tasks after cleanup.
    await stop_event.wait()
    # Drain queues gracefully.
    await asyncio.gather(
        *[q.join() for q in (audio_q, vad_q, transcript_q)], return_exceptions=True
    )
    # Cancel tasks that may still be awaiting.
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("Async pipeline terminated")


def main() -> None:
    parser = argparse.ArgumentParser(description="Async VAD → STT demo")
    parser.add_argument(
        "--config",
        default="wanis/configs/wanis_config.yaml",
        help="Path to configuration yaml (default: wanis/configs/wanis_config.yaml)",
    )
    parser.add_argument(
        "--input-file",
        default=None,
        help="Path to a raw PCM (int16, 16kHz, mono) file for offline testing",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    asyncio.run(async_main(config_path=args.config))


if __name__ == "__main__":
    main()
