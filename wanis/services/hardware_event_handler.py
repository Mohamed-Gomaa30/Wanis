"""
Hardware Event Handler for Wanis.

Receives WebSocket events and triggers appropriate actions.
"""

import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime

from wanis.core.exceptions import HardwareEventError
from wanis.core.models import HardwareEvent, VitalsData

logger = logging.getLogger(__name__)


class HardwareEventHandler:
    """
    Handles hardware events received via WebSocket.

    Routes events to appropriate handlers and triggers agent actions.
    """

    def __init__(self, pipeline=None, agent=None):
        """
        Initialize the hardware event handler.

        Args:
            pipeline: VoicePipeline instance for processing events
            agent: CompanionAgent instance for emergency responses
        """
        self.pipeline = pipeline
        self.agent = agent
        self._event_handlers: Dict[str, Callable] = {}
        self._latest_vitals: Optional[VitalsData] = None
        self._pending_fall_response = False
        self._event_log: list = []

    def handle_event(self, event: HardwareEvent) -> Dict[str, Any]:
        """
        Handle a hardware event.

        Args:
            event: HardwareEvent to process

        Returns:
            dict with handling result
        """
        logger.info(f"Handling event: {event.event_type}")

        self._event_log.append(
            {
                "event_id": event.event_id,
                "type": event.event_type,
                "timestamp": datetime.now().isoformat(),
            }
        )

        if event.event_type == "fall_event":
            return self._handle_fall_event(event)
        elif event.event_type == "vitals":
            return self._handle_vitals_event(event)
        elif event.event_type == "pill_dispensed":
            return self._handle_pill_event(event)
        else:
            logger.warning(f"Unknown event type: {event.event_type}")
            return {"status": "unknown", "event_type": event.event_type}

    def _handle_fall_event(self, event: HardwareEvent) -> Dict[str, Any]:
        """
        Handle fall detection event.

        Sets fall_flag=True for next agent response.
        """
        logger.critical(f"Fall event received: {event.event_id}")

        self._pending_fall_response = True

        location = event.data.get("location", "unknown")

        return {
            "status": "handled",
            "event_type": "fall_event",
            "fall_flag_set": True,
            "location": location,
            "message": "هل أنت بخير؟",  # "Are you okay?"
        }

    def _handle_vitals_event(self, event: HardwareEvent) -> Dict[str, Any]:
        """
        Handle vitals measurement event.

        Stores latest vitals and determines health status.
        """
        heart_rate = event.data.get("heart_rate")
        spo2 = event.data.get("spo2")

        if heart_rate is None or spo2 is None:
            return {"status": "error", "message": "Missing vitals data"}

        self._latest_vitals = VitalsData(heart_rate=heart_rate, spo2=spo2)

        return {
            "status": "handled",
            "event_type": "vitals",
            "heart_rate": heart_rate,
            "spo2": spo2,
            "health_status": self._latest_vitals.status,
        }

    def _handle_pill_event(self, event: HardwareEvent) -> Dict[str, Any]:
        """
        Handle pill dispensed event.

        Logs medication acknowledgment.
        """
        slot_id = event.data.get("slot_id")
        success = event.data.get("success", True)

        logger.info(f"Pill dispensed: slot={slot_id}, success={success}")

        return {
            "status": "handled",
            "event_type": "pill_dispensed",
            "slot_id": slot_id,
            "success": success,
        }

    def should_set_fall_flag(self) -> bool:
        """Check if fall flag should be set for next response."""
        return self._pending_fall_response

    def clear_fall_flag(self) -> None:
        """Clear the pending fall flag."""
        self._pending_fall_response = False

    def get_latest_vitals(self) -> Optional[VitalsData]:
        """Get the latest vitals data."""
        return self._latest_vitals

    def get_health_status(self) -> Optional[Dict[str, Any]]:
        """Get health status for agent context."""
        if self._latest_vitals:
            return {
                "heart_rate": self._latest_vitals.heart_rate,
                "spo2": self._latest_vitals.spo2,
                "status": self._latest_vitals.status,
            }
        return None

    def register_handler(self, event_type: str, handler: Callable) -> None:
        """Register a custom handler for an event type."""
        self._event_handlers[event_type] = handler

    def get_event_log(self, limit: int = 100) -> list:
        """Get recent event log."""
        return self._event_log[-limit:]
