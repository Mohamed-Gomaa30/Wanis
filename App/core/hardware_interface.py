from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class Vitals:
    heart_rate: int
    spo2: int

class HardwareInterface(ABC):
    """Abstract interface for hardware interactions.
    
    This ensures the core logic is decoupled from specific sensor implementations.
    """
    
    @abstractmethod
    async def get_vitals(self) -> Vitals:
        """Read user vitals from the sensor module.
        
        Returns:
            Vitals object with heart_rate and spo2.
        """
        pass

    @abstractmethod
    async def emergency_comms(self) -> bool:
        """Trigger emergency communications (SMS/Call).
        
        should be called in EMERGENCY state (e.g. Fall).
        
        Returns:
            True if successful, False otherwise.
        """
        pass
        
    @abstractmethod
    async def actuate_dispenser(self, slot_id: int) -> bool:
        """Actuate the pill dispenser motor for a specific slot.
        
        Args:
            slot_id: The identifier for the medication slot.
            
        Returns:
            True if actuation was triggered.
        """
        pass
