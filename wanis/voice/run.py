"""Wanis Voice Pipeline Entry Point.

Supports two modes:
1. Local mode: Everything runs locally (mic, VAD, STT, LLM, TTS, speaker)
2. Hybrid mode: Mic on laptop, processing on remote server (WebSocket)

Usage:
    python -m wanis.voice.run --mode local
    python -m wanis.voice.run --mode hybrid --server ws://localhost:8000/ws
"""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wanis.voice.audio import AudioInput, AudioOutput
from wanis.voice.vad import VAD
from wanis.voice.stt import STT
from wanis.voice.tts import TTS
from wanis.voice.sentence_buffer import SentenceBuffer
from wanis.utils.config import get_config, set_config_path

logger = logging.getLogger(__name__)


class LocalVoicePipeline:
    """
    Local voice pipeline: All processing on local machine.

    Flow:
    1. Capture audio from microphone
    2. VAD detects speech start/end
    3. STT transcribes speech
    4. LLM generates response
    5. TTS synthesizes audio
    6. Play audio through speaker
    """

    def __init__(self):
        self.config = get_config()

        self.audio_in = AudioInput()
        self.audio_out = AudioOutput()
        self.vad = VAD()
        self.stt = STT()
        self.tts = TTS()

        self._agent = None
        self._sentence_buffer = SentenceBuffer()

        self._running = False

    @property
    def agent(self):
        """Lazy load agent to avoid import errors if not needed."""
        if self._agent is None:
            from wanis.agent.llm_agent import CompanionAgent

            agent_config = self.config.get("agent", {})
            self._agent = CompanionAgent(agent_config)
            self._agent.initialize()
        return self._agent

    async def run(self) -> None:
        """Run the voice pipeline."""
        logger.info("Starting local voice pipeline...")

        logger.info("Initializing VAD...")
        self.vad.initialize()

        logger.info("Initializing STT...")
        self.stt.initialize()

        logger.info("Initializing TTS...")
        self.tts.initialize()

        self._running = True

        logger.info("Starting audio capture...")
        self.audio_in.start(callback=self._on_audio_chunk)

        logger.info("Pipeline running. Speak to interact...")
        logger.info("Press Ctrl+C to stop.")

        try:
            while self._running:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        finally:
            self.stop()

    def _on_audio_chunk(self, audio_bytes: bytes) -> None:
        """Callback for audio chunks from microphone."""
        if not self._running:
            return

        event = self.vad.process(audio_bytes)

        if event:
            if event["type"] == "speech_start":
                logger.info("Speech detected...")
                self.stt.reset()

            elif event["type"] == "speech_end":
                audio_data: np.ndarray = event["audio"]
                audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()

                logger.info("Transcribing...")
                text = self.stt.transcribe(audio_bytes)

                if text:
                    logger.info(f"User: {text}")
                    asyncio.create_task(self._process_response(text))

    async def _process_response(self, user_text: str) -> None:
        """Process user input and generate response."""
        try:
            logger.info("Generating response...")

            full_response = ""
            async for sentence in self.agent.generate_response(user_text):
                full_response += sentence + " "
                logger.info(f"Agent: {sentence}")

                audio = await self.tts.synthesize_async(sentence)
                if audio:
                    await self.audio_out.play_async(audio)

            logger.info(f"Complete response: {full_response.strip()}")

        except Exception as e:
            logger.error(f"Error processing response: {e}")

    def stop(self) -> None:
        """Stop the pipeline."""
        logger.info("Stopping voice pipeline...")
        self._running = False
        self.audio_in.stop()
        self.audio_out.stop()


async def run_local() -> None:
    """Run local mode."""
    pipeline = LocalVoicePipeline()

    def signal_handler(sig, frame):
        pipeline.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    await pipeline.run()


async def run_hybrid(server_url: str) -> None:
    """Run hybrid mode - connect to remote server."""
    from wanis.voice.client import HybridClient

    client = HybridClient(server_url)
    await client.run()


def main():
    parser = argparse.ArgumentParser(description="Wanis Voice Pipeline")
    parser.add_argument(
        "--mode",
        choices=["local", "hybrid"],
        default="local",
        help="Run mode: local (all on machine) or hybrid (mic local, processing remote)",
    )
    parser.add_argument(
        "--server",
        default="ws://localhost:8000/ws",
        help="WebSocket server URL (for hybrid mode)",
    )
    parser.add_argument(
        "--config",
        default="wanis/configs/wanis_config.yaml",
        help="Path to config file",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    set_config_path(args.config)

    if args.mode == "local":
        logger.info("Running in LOCAL mode")
        asyncio.run(run_local())
    else:
        logger.info(f"Running in HYBRID mode, connecting to {args.server}")
        asyncio.run(run_hybrid(args.server))


if __name__ == "__main__":
    main()
