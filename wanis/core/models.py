"""
Data classes for the Wanis voice pipeline.

Matches entity definitions from data-model.md.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid


@dataclass
class AudioChunk:
    """Raw audio data container for capturing and transmitting audio."""

    data: bytes
    sample_rate: int = 16000
    channels: int = 1
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: int = 0

    def __post_init__(self):
        if self.duration_ms == 0 and self.data:
            self.duration_ms = int(len(self.data) / 2 / (self.sample_rate / 1000))

    @classmethod
    def from_bytes(cls, data: bytes, sample_rate: int = 16000) -> "AudioChunk":
        return cls(data=data, sample_rate=sample_rate)


@dataclass
class Transcription:
    """Output from the STT service containing recognized text."""

    text: str
    confidence: float = 0.0
    audio_chunk_id: Optional[str] = None
    language: str = "ar-EG"
    processing_time_ms: int = 0

    @classmethod
    def empty(cls) -> "Transcription":
        return cls(text="")


@dataclass
class AgentResponse:
    """Response from the CompanionAgent with streaming support."""

    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sentences: List[str] = field(default_factory=list)
    fall_flag: bool = False
    health_status: Optional[Dict[str, Any]] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class HardwareEvent:
    """Event from Raspberry Pi hardware sensors."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""  # "fall_event", "vitals", "pill_dispensed"
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "pi-001"

    @classmethod
    def fall_event(
        cls, location: Optional[str] = None, acceleration_g: float = 0.0
    ) -> "HardwareEvent":
        return cls(
            event_type="fall_event",
            data={
                "location": location,
                "acceleration_g": acceleration_g,
                "detected_by": "mpu6050",
            },
        )

    @classmethod
    def vitals_event(
        cls, heart_rate: int, spo2: int, duration_s: int = 30
    ) -> "HardwareEvent":
        return cls(
            event_type="vitals",
            data={
                "heart_rate": heart_rate,
                "spo2": spo2,
                "measurement_duration_s": duration_s,
                "sensor_id": "max30102",
            },
        )

    @classmethod
    def pill_dispensed_event(
        cls, slot_id: int, success: bool = True
    ) -> "HardwareEvent":
        return cls(
            event_type="pill_dispensed", data={"slot_id": slot_id, "success": success}
        )


@dataclass
class VitalsData:
    """Health measurement from vitals sensor."""

    heart_rate: int
    spo2: int
    measurement_time: datetime = field(default_factory=datetime.utcnow)
    status: str = "normal"  # "normal", "warning", "critical"
    duration_s: int = 30

    def __post_init__(self):
        self.status = self._determine_status()

    def _determine_status(self) -> str:
        """Determine health status based on vital signs."""
        # Critical conditions
        if self.heart_rate < 50 or self.heart_rate > 120:
            return "critical"
        if self.spo2 < 90:
            return "critical"

        # Warning conditions
        if self.heart_rate < 60 or self.heart_rate > 100:
            return "warning"
        if self.spo2 < 95:
            return "warning"

        return "normal"

    def is_normal(self) -> bool:
        return self.status == "normal"

    def is_warning(self) -> bool:
        return self.status == "warning"

    def is_critical(self) -> bool:
        return self.status == "critical"


@dataclass
class ConversationTurn:
    """Single turn in a conversation."""

    turn_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_input: Optional[Transcription] = None
    agent_response: Optional[AgentResponse] = None
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    interrupted: bool = False


@dataclass
class VoiceSession:
    """Complete voice session context."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    turns: List[ConversationTurn] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    state: str = "IDLE"  # "IDLE", "ACTIVE", "PAUSED", "ENDED", "EMERGENCY"
