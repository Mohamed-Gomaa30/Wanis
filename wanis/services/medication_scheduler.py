"""
Medication Scheduler for Wanis.

Loads medication schedule from user profile and checks for due medications.
"""

import logging
import json
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

from wanis.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class MedicationScheduler:
    """
    Manages medication reminders based on user profile.

    Loads schedule from user_profile.json and provides
    methods to check for due medications.
    """

    def __init__(self, profile_path: Optional[str] = None):
        """
        Initialize the medication scheduler.

        Args:
            profile_path: Path to user profile JSON file
        """
        self.profile_path = Path(profile_path) if profile_path else None
        self.medications: List[Dict[str, Any]] = []
        self._last_reminder_time: Optional[datetime] = None

        self._load_schedule()

    def _load_schedule(self) -> None:
        """Load medication schedule from profile file."""
        if not self.profile_path or not self.profile_path.exists():
            logger.warning("No user profile found, medication reminders disabled")
            return

        try:
            profile_data = self.profile_path.read_text()
            profile = json.loads(profile_data)

            self.medications = profile.get("medications", [])
            logger.info(f"Loaded {len(self.medications)} medications from profile")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in profile: {e}")
        except Exception as e:
            logger.error(f"Failed to load profile: {e}")

    def check_due_medications(
        self, current_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Check for medications due at the given time.

        Args:
            current_time: Time string in HH:MM format (24-hour)
                          If None, uses current time

        Returns:
            List of due medications with name and slot
        """
        if not self.medications:
            return []

        if current_time is None:
            current_time = datetime.now().strftime("%H:%M")

        due_medications = []

        for med in self.medications:
            med_name = med.get("name", "Unknown")
            times = med.get("times", [])
            slots = med.get("slots", [])

            for i, time in enumerate(times):
                if time == current_time:
                    slot = slots[i] if i < len(slots) else 1
                    due_medications.append(
                        {"name": med_name, "time": time, "slot": slot}
                    )

        return due_medications

    def format_reminder(self, medication_name: str, time: str) -> str:
        """
        Format a medication reminder message in Arabic.

        Args:
            medication_name: Name of the medication
            time: Scheduled time

        Returns:
            Formatted reminder message
        """
        # Convert time to Arabic format
        hour = int(time.split(":")[0])

        # Simple Arabic time formatting
        if hour < 12:
            period = "الصباح"
        elif hour < 18:
            period = "بعد الظهر"
        else:
            period = "المساء"

        return (
            f"حان موعد دواء {medication_name}. "
            f"الساعة الآن {time} {period}. "
            f"من فضلك تناول الدواء."
        )

    def get_next_medication_time(self) -> Optional[str]:
        """
        Get the next scheduled medication time.

        Returns:
            Time string or None if no medications scheduled
        """
        if not self.medications:
            return None

        all_times = []
        for med in self.medications:
            all_times.extend(med.get("times", []))

        if not all_times:
            return None

        # Sort times and find next one
        current_time = datetime.now().strftime("%H:%M")
        future_times = sorted([t for t in all_times if t > current_time])

        if future_times:
            return future_times[0]

        # If no future times today, return first time tomorrow
        return sorted(all_times)[0] if all_times else None

    def acknowledge_medication(self, medication_name: str) -> None:
        """
        Log that a medication was acknowledged.

        Args:
            medication_name: Name of the medication taken
        """
        logger.info(f"Medication acknowledged: {medication_name}")
        self._last_reminder_time = datetime.now()

    def get_last_reminder_time(self) -> Optional[datetime]:
        """Get the timestamp of the last reminder."""
        return self._last_reminder_time

    def reload_schedule(self) -> None:
        """Reload the medication schedule from profile."""
        self._load_schedule()
