"""
Vitals Processor for Wanis.

Receives vitals data, evaluates health status, and formats for agent.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from wanis.core.exceptions import HardwareEventError
from wanis.core.models import VitalsData

logger = logging.getLogger(__name__)


class VitalsProcessor:
    """
    Processes vitals data from hardware sensors.

    Evaluates health status and provides formatted output for agent.
    """

    def __init__(self):
        self._latest_vitals: Optional[VitalsData] = None
        self._vitals_history: list = []
        self._max_history = 100

    def process_vitals(
        self, heart_rate: int, spo2: int, duration_s: int = 30
    ) -> VitalsData:
        """
        Process incoming vitals data.

        Args:
            heart_rate: Beats per minute (40-200 range)
            spo2: Blood oxygen percentage (70-100 range)
            duration_s: Measurement duration in seconds

        Returns:
            VitalsData with evaluated status
        """
        # Validate ranges
        if not (40 <= heart_rate <= 200):
            logger.warning(f"Heart rate {heart_rate} outside normal range (40-200)")

        if not (70 <= spo2 <= 100):
            logger.warning(f"SpO2 {spo2} outside normal range (70-100)")

        vitals = VitalsData(heart_rate=heart_rate, spo2=spo2, duration_s=duration_s)

        self._latest_vitals = vitals
        self._add_to_history(vitals)

        logger.info(
            f"Processed vitals: HR={heart_rate}, SpO2={spo2}, status={vitals.status}"
        )

        return vitals

    def _add_to_history(self, vitals: VitalsData) -> None:
        """Add vitals to history, maintaining max size."""
        self._vitals_history.append(
            {"vitals": vitals, "timestamp": datetime.now().isoformat()}
        )

        if len(self._vitals_history) > self._max_history:
            self._vitals_history = self._vitals_history[-self._max_history :]

    def get_latest_vitals(self) -> Optional[VitalsData]:
        """Get the most recent vitals data."""
        return self._latest_vitals

    def get_status_message(self, language: str = "ar") -> str:
        """
        Get a formatted status message in the specified language.

        Args:
            language: 'ar' for Arabic, 'en' for English

        Returns:
            Formatted status message
        """
        if not self._latest_vitals:
            return (
                "لم يتم قياس المؤشرات بعد"
                if language == "ar"
                else "No vitals measured yet"
            )

        vitals = self._latest_vitals

        if language == "ar":
            status_text = {"normal": "طبيعي", "warning": "تحذير", "critical": "حرج"}

            return (
                f"معدل ضربات القلب: {vitals.heart_rate} في الدقيقة. "
                f"نسبة الأكسجين: {vitals.spo2} بالمائة. "
                f"الحالة: {status_text.get(vitals.status, vitals.status)}"
            )
        else:
            return (
                f"Heart rate: {vitals.heart_rate} bpm. "
                f"Oxygen saturation: {vitals.spo2}%. "
                f"Status: {vitals.status}"
            )

    def get_health_context(self) -> Optional[Dict[str, Any]]:
        """
        Get health context for agent.

        Returns:
            dict with health status or None if no vitals
        """
        if not self._latest_vitals:
            return None

        return {
            "heart_rate": self._latest_vitals.heart_rate,
            "spo2": self._latest_vitals.spo2,
            "status": self._latest_vitals.status,
            "duration_s": self._latest_vitals.duration_s,
        }

    def get_vitals_history(self, limit: int = 10) -> list:
        """Get recent vitals history."""
        return self._vitals_history[-limit:]

    def clear_vitals(self) -> None:
        """Clear current vitals data."""
        self._latest_vitals = None

    def is_critical(self) -> bool:
        """Check if latest vitals are critical."""
        return self._latest_vitals is not None and self._latest_vitals.is_critical()

    def is_warning(self) -> bool:
        """Check if latest vitals show warning."""
        return self._latest_vitals is not None and self._latest_vitals.is_warning()

    def is_normal(self) -> bool:
        """Check if latest vitals are normal."""
        return self._latest_vitals is None or self._latest_vitals.is_normal()
