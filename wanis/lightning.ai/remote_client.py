"""
Remote Client - Thin Client for Laptop.

Captures audio from local microphone and streams to Lightning AI server.
This is a THIN client - no VAD, STT, or TTS processing.
All processing happens on the server.

Usage:
    python -m wanis.lightning.remote_client --server ws://SERVER_IP:8000/ws
"""

import argparse
import asyncio
import json
import logging
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wanis.voice.audio import AudioInput
from wanis.utils.config import set_config_path

logger = logging.getLogger("remote_client")


class RemoteClient:
    """
    Thin client for remote voice processing.

    Responsibilities:
    - Capture audio from microphone
    - Stream raw audio to server via WebSocket
    - Display transcript from server (optional)

    NO processing:
    - NO VAD
    - NO STT
    - NO TTS
    - NO audio playback
    """

    def __init__(self, server_url: str):
        self.server_url = server_url
        self.audio_in = AudioInput()

        self._ws = None
        self._running = False
        self._connected = False

        # Metrics for logging
        self._chunk_count = 0
        self._total_bytes_sent = 0
        self._start_time = None

    async def run(self) -> None:
        """Run the remote client."""
        logger.info("=" * 60)
        logger.info("REMOTE CLIENT - Starting")
        logger.info("=" * 60)
        logger.info(f"Server URL: {self.server_url}")

        self._running = True

        try:
            import websockets
        except ImportError:
            logger.error(
                "websockets not installed. Install with: pip install websockets"
            )
            raise

        logger.info("Connecting to server...")

        try:
            async with websockets.connect(self.server_url) as ws:
                self._ws = ws
                self._connected = True
                self._start_time = time.time()
                self._chunk_count = 0
                self._total_bytes_sent = 0

                logger.info("Connected to server!")
                logger.info("=" * 60)
                logger.info("SPEAK NOW - Audio is streaming to server...")
                logger.info("Press Ctrl+C to stop")
                logger.info("=" * 60)

                # Start audio capture with callback
                self.audio_in.start(callback=lambda b: self._on_audio_chunk(b, ws))

                try:
                    # Receive messages from server (transcripts, status)
                    async for message in ws:
                        await self._handle_server_message(message)
                except websockets.ConnectionClosed:
                    logger.info("Server disconnected")

        except Exception as e:
            logger.error(f"Connection error: {e}")
            raise
        finally:
            self.stop()

    def _on_audio_chunk(self, audio_bytes: bytes, ws) -> None:
        """
        Callback for audio chunks from microphone.

        Streams raw audio to server continuously.
        """
        if not self._running or not self._connected:
            return

        # Track metrics
        self._chunk_count += 1
        self._total_bytes_sent += len(audio_bytes)

        # Log every 50 chunks (approximately every 1.6 seconds at 32ms chunks)
        if self._chunk_count % 50 == 0:
            elapsed = time.time() - self._start_time if self._start_time else 1
            kbps = (self._total_bytes_sent * 8 / 1024) / elapsed
            logger.info(
                f"[STREAM] Chunk #{self._chunk_count} | "
                f"{len(audio_bytes)} bytes | "
                f"{kbps:.1f} KB/s | "
                f"Total: {self._total_bytes_sent / 1024:.1f} KB"
            )

        # Send audio chunk to server
        asyncio.create_task(ws.send(audio_bytes))

    async def _handle_server_message(self, message) -> None:
        """Handle message from server."""
        if isinstance(message, bytes):
            # Binary message (not expected in thin client mode)
            logger.debug(f"Received binary: {len(message)} bytes")

        elif isinstance(message, str):
            # JSON message
            try:
                data = json.loads(message)
                msg_type = data.get("type")

                if msg_type == "transcript":
                    logger.info("=" * 60)
                    logger.info(f">>> TRANSCRIPT: {data.get('text')}")
                    if "processing_time_ms" in data:
                        logger.info(
                            f">>> Processing time: {data['processing_time_ms']}ms"
                        )
                    logger.info("=" * 60)

                elif msg_type == "status":
                    state = data.get("state")
                    logger.debug(f"Server status: {state}")

                elif msg_type == "error":
                    logger.error(f"Server error: {data.get('message')}")

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from server: {message[:100]}")

    def stop(self) -> None:
        """Stop the client."""
        logger.info("Stopping remote client...")
        self._running = False
        self._connected = False

        # Log final statistics
        if self._start_time and self._chunk_count > 0:
            elapsed = time.time() - self._start_time
            logger.info("=" * 60)
            logger.info("SESSION STATISTICS")
            logger.info("=" * 60)
            logger.info(f"Total duration: {elapsed:.1f} seconds")
            logger.info(f"Total chunks sent: {self._chunk_count}")
            logger.info(f"Total bytes sent: {self._total_bytes_sent / 1024:.1f} KB")
            logger.info(
                f"Average rate: {(self._total_bytes_sent * 8 / 1024) / elapsed:.1f} KB/s"
            )
            logger.info("=" * 60)

        self.audio_in.stop()


async def main():
    """Entry point for remote client."""
    parser = argparse.ArgumentParser(description="Wanis Remote Client (Thin)")
    parser.add_argument(
        "--server",
        required=True,
        help="WebSocket server URL (e.g., ws://localhost:8000/ws)",
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

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    set_config_path(args.config)

    client = RemoteClient(args.server)

    def signal_handler(sig, frame):
        client.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    await client.run()


if __name__ == "__main__":
    asyncio.run(main())
