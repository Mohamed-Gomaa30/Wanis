"""
Fall Detection Handler for Raspberry Pi.

Plays local alert and sends event to Laptop server.
"""

import logging
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime

from wanis.core.exceptions import HardwareEventError

logger = logging.getLogger(__name__)


class FallHandler:
    """Handles fall detection events."""

    DEFAULT_ALERT_PATH = "assets/alert_fall.wav"

    def __init__(self, ws_client, alert_audio_path: Optional[str] = None):
        self.ws_client = ws_client
        self.alert_audio_path = Path(alert_audio_path or self.DEFAULT_ALERT_PATH)
        self._last_fall_time: Optional[datetime] = None
        self._fall_count = 0

    def play_local_alert(self) -> bool:
        if not self.alert_audio_path.exists():
            logger.warning(f"Alert audio not found: {self.alert_audio_path}")
            return False

        try:
            import subprocess

            subprocess.run(["aplay", str(self.alert_audio_path)], check=False)
            return True
        except Exception as e:
            logger.error(f"Failed to play alert: {e}")
            return False

    async def on_fall_detected(self, location: Optional[str] = None) -> None:
        logger.warning("FALL DETECTED!")

        self.play_local_alert()

        if self.ws_client.is_connected():
            await self.ws_client.send_fall_event(location=location)

    async def trigger_emergency_sequence(self, location: Optional[str] = None) -> dict:
        """
        Trigger the full emergency sequence.

        1. Play local alert
        2. Send WebSocket event
        3. Log the event

        Args:
            location: Optional location of the fall

        Returns:
            dict with status information
        """
        logger.critical("EMERGENCY SEQUENCE TRIGGERED")

        result = {
            "timestamp": datetime.now().isoformat(),
            "location": location,
            "steps": [],
        }

        # Step 1: Play local alert
        alert_played = self.play_local_alert()
        result["steps"].append({"step": "local_alert", "success": alert_played})

        # Step 2: Send WebSocket event
        ws_sent = False
        if self.ws_client.is_connected():
            ws_sent = await self.ws_client.send_fall_event(location=location)
        else:
            logger.warning("WebSocket not connected, cannot send fall event")

        result["steps"].append({"step": "websocket_event", "success": ws_sent})

        # Step 3: Log the event
        self._last_fall_time = datetime.now()
        self._fall_count += 1

        logger.info(
            f"Fall event logged: count={self._fall_count}, "
            f"location={location}, ws_sent={ws_sent}"
        )

        result["steps"].append({"step": "event_logged", "success": True})

        result["fall_count"] = self._fall_count
        result["last_fall_time"] = (
            self._last_fall_time.isoformat() if self._last_fall_time else None
        )

        return result

    def get_last_fall_time(self) -> Optional[datetime]:
        """Get the timestamp of the last fall."""
        return self._last_fall_time

    def get_fall_count(self) -> int:
        """Get the total count of falls detected."""
        return self._fall_count
