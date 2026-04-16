"""
WebSocket Client for Raspberry Pi.
"""

import logging
import json
import asyncio
import time
from typing import Optional
from datetime import datetime

from wanis.core.exceptions import WebSocketError

logger = logging.getLogger(__name__)

try:
    import websockets

    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False


class PiWebSocketClient:
    """WebSocket client for Raspberry Pi hardware."""

    DEFAULT_RECONNECT_INTERVAL = 5.0
    MAX_RECONNECT_INTERVAL = 60.0
    RECONNECT_BACKOFF_FACTOR = 2.0

    def __init__(
        self, server_url: str, reconnect_interval: float = DEFAULT_RECONNECT_INTERVAL
    ):
        if not WEBSOCKETS_AVAILABLE:
            raise WebSocketError("websockets not available")

        self.server_url = server_url
        self.reconnect_interval = reconnect_interval
        self.ws = None
        self._connected = False
        self._current_reconnect_delay = reconnect_interval

    async def connect(self) -> bool:
        try:
            self.ws = await websockets.connect(self.server_url)
            self._connected = True
            self._current_reconnect_delay = (
                self.reconnect_interval
            )  # Reset on successful connect
            logger.info(f"Connected to {self.server_url}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    async def reconnect_with_backoff(self, max_attempts: int = 10) -> bool:
        """
        Reconnect with exponential backoff.

        Args:
            max_attempts: Maximum number of reconnection attempts

        Returns:
            True if connected, False if max attempts exceeded
        """
        for attempt in range(max_attempts):
            logger.info(f"Reconnection attempt {attempt + 1}/{max_attempts}")

            if await self.connect():
                return True

            wait_time = min(self._current_reconnect_delay, self.MAX_RECONNECT_INTERVAL)
            logger.info(f"Waiting {wait_time}s before next attempt...")
            await asyncio.sleep(wait_time)

            # Exponential backoff
            self._current_reconnect_delay *= self.RECONNECT_BACKOFF_FACTOR

        logger.error(f"Failed to reconnect after {max_attempts} attempts")
        return False

    async def disconnect(self) -> None:
        self._connected = False
        if self.ws:
            await self.ws.close()
            self.ws = None

    async def send_event(self, event_type: str, data: dict) -> bool:
        if not self._connected or not self.ws:
            return False

        message = {
            "type": event_type,
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            **data,
        }

        try:
            await self.ws.send(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Send failed: {e}")
            self._connected = False
            return False

    async def send_fall_event(self, location: Optional[str] = None) -> bool:
        return await self.send_event("fall_event", {"location": location})

    async def send_vitals(self, heart_rate: int, spo2: int) -> bool:
        return await self.send_event("vitals", {"heart_rate": heart_rate, "spo2": spo2})

    async def send_pill_dispensed(self, slot_id: int, success: bool = True) -> bool:
        return await self.send_event(
            "pill_dispensed", {"slot_id": slot_id, "success": success}
        )

    def is_connected(self) -> bool:
        return self._connected
