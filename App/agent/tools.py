"""
Wanis Agent Tools.

Function definitions exposed to the Gemini agent for tool calling.
Implements the connection between the Agent and the Hardware/Services.
"""

import logging
from typing import Dict, Any

from ..core.hardware_interface import HardwareInterface

logger = logging.getLogger(__name__)


# Global hardware instance (injected by Orchestrator)
_hardware: HardwareInterface | None = None


def inject_hardware(hardware: HardwareInterface):
    """Inject the hardware interface instance."""
    global _hardware
    _hardware = hardware


# ── Tool Functions ──────────────────────────────────────────────

async def fetch_vitals() -> Dict[str, Any]:
    """Reads the user's current vital signs (Heart Rate, SpO2).
    
    Returns:
        JSON dictionary containing 'heart_rate' (bpm) and 'spo2' (percentage).
    """
    if _hardware is None:
        return {"error": "Hardware interface not initialized"}
    
    vitals = await _hardware.get_vitals()
    return {
        "heart_rate": vitals.heart_rate,
        "spo2": vitals.spo2,
        "status": "normal" if 60 <= vitals.heart_rate <= 100 else "warning"
    }


async def search_web(query: str) -> str:
    """Searches the web for information to answer the user's question.
    
    Args:
        query: The search query string.
        
    Returns:
        A summary string of the search results.
    """
    logger.info(f"Tool Call: search_web('{query}')")
    # Mock implementation for now
    await asyncio.sleep(1) # Simulate network delay
    return f"Simulated search results for: '{query}'. [Replace with actual Search API integration]"


async def initiate_emergency_comms() -> str:
    """Triggers an external emergency communication to care providers/family.
    
    Should be called when the user is in distress, has fallen, or requests help.
    
    Returns:
        Status message confirming the alert.
    """
    logger.warning("Tool Call: initiate_emergency_comms called by Agent!")
    if _hardware:
        await _hardware.emergency_comms()
        return "Emergency alert sent successfully to registered contacts."
    return "Failed to access hardware for emergency alert."


async def alert_pill_dispenser(medication_name: str = "medication") -> str:
    """Notify the user to take their medication. 
    Notes: The physical dispenser opens automatically; this is for the verbal alert context.
    
    Args:
        medication_name: Name of the medication (optional).
        
    Returns:
        Confirmation string.
    """
    logger.info(f"Tool Call: alert_pill_dispenser for '{medication_name}'")
    # Logic to sync with dispenser could go here
    return f"Dispenser activated for {medication_name}. User notified."


# ── Tool Definitions for Gemini ─────────────────────────────────

# List of tool functions to pass to Gemini
TOOLS = [
    fetch_vitals,
    search_web,
    initiate_emergency_comms,
    alert_pill_dispenser
]
