"""
Wanis Agent Tools.

Function definitions exposed to the Gemini agent for tool calling.
Implements the connection between the Agent and the Hardware/Services.
"""

import logging
import asyncio
from typing import Dict, Any

# Fix import to use the new core module
from ..core.hardware_interface import HardwareInterface
from ..services.notification_service import notification_service

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
    
    This function should be called when the user complains of illness 
    or when the agent needs to check the user's health status.
    
    Returns:
        JSON dictionary containing 'heart_rate' (bpm) and 'spo2' (percentage).
    """
    if _hardware is None:
        return {"error": "Hardware interface not initialized"}
    
    try:
        logger.info("fetch_vitals: Starting 30-second measurement period...")
        # Simulate the 30-second measurement duration requested by user
        await asyncio.sleep(30)
        
        vitals = await _hardware.get_vitals()
        logger.info(f"fetch_vitals: Measurement complete. HR: {vitals.heart_rate}, SpO2: {vitals.spo2}")
        
        return {
            "heart_rate": vitals.heart_rate,
            "spo2": vitals.spo2,
            "status": "normal" if 60 <= vitals.heart_rate <= 100 else "warning"
        }
    except Exception as e:
        logger.error(f"Error fetching vitals: {e}")
        return {"error": str(e)}


async def search_web(query: str) -> Dict[str, Any]:
    """Searches the web for information to answer the user's question.
    
    Args:
        query: The search query string.
        
    Returns:
        A summary string of the search results.
    """
    logger.info(f"Tool Call: search_web('{query}')")
    # Mock implementation for now
    await asyncio.sleep(1) # Simulate network delay
    return {"result": f"Simulated search results for: '{query}'. [Replace with actual Search API integration]"}


async def initiate_emergency_comms() -> Dict[str, Any]:
    """Triggers an external emergency communication (Phone Call).
    
    Should be called when the user is in distress, has fallen, or requests help.
    
    Returns:
        Status message confirming the alert.
    """
    logger.warning("Tool Call: initiate_emergency_comms called by Agent!")
    await notification_service.make_emergency_call()
    return {"result": "Emergency phone call has been initiated."}


async def send_whatsapp_notification(message: str) -> Dict[str, Any]:
    """Sends a WhatsApp notification to the user's registered contacts (family/doctor).
    
    Args:
        message: The content of the message to send.
        
    Returns:
        Confirmation string.
    """
    logger.info(f"Tool Call: send_whatsapp_notification('{message}')")
    success = await notification_service.send_whatsapp(message)
    if success:
        return {"result": "Message sent successfully via WhatsApp."}
    return {"error": "Failed to send WhatsApp message."}


async def send_telegram_notification(message: str) -> Dict[str, Any]:
    """Sends a Telegram notification to the user's registered contacts (family/doctor).
    
    Args:
        message: The content of the message to send.
        
    Returns:
        Confirmation string.
    """
    logger.info(f"Tool Call: send_telegram_notification('{message}')")
    success = await notification_service.send_telegram(message)
    if success:
        return {"result": "Message sent successfully via Telegram."}
    return {"error": "Failed to send Telegram message."}


# ── Tool Definitions for Gemini ─────────────────────────────────

# List of tool functions to pass to Gemini
TOOLS = [
    fetch_vitals,
    search_web,
    initiate_emergency_comms,
    send_whatsapp_notification,
    send_telegram_notification
]



print("Tools loaded successfully.")