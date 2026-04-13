
import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)

class NotificationService:
    """Service to handle external notifications (WhatsApp, Telegram, Calls)."""
    
    def __init__(self, whatsapp_enabled: bool = True, telegram_enabled: bool = True):
        self.whatsapp_enabled = whatsapp_enabled
        self.telegram_enabled = telegram_enabled
        # In a real app, these would hold API keys/clients
        self.whatsapp_config = {} 
        self.telegram_config = {}

    async def send_whatsapp(self, message: str, recipient: str = "Doctor/Family") -> bool:
        """Sends a WhatsApp message."""
        if not self.whatsapp_enabled:
            return False
            
        logger.info(f"NotificationService: Sending WhatsApp to {recipient}: {message}")
        # Simulation: Use Twilio or WhatsApp Business API here
        print(f"\n[WHATSAPP SENT] To: {recipient} | Body: {message}\n")
        await asyncio.sleep(0.5) # Simulate latency
        return True

    async def send_telegram(self, message: str, recipient: str = "Doctor/Family") -> bool:
        """Sends a Telegram message using the HTTP API."""
        if not self.telegram_enabled:
            return False
            
        import os
        import httpx
        
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        
        if not token or not chat_id:
            logger.error("Telegram token or Chat ID not found in environment.")
            # Fallback to simulation print for development
            print(f"\n[TELEGRAM SIMULATION] (Missing Token/ID) To: {recipient} | Body: {message}\n")
            return False

        logger.info(f"NotificationService: Sending REAL Telegram to {chat_id}")
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    print(f"\n[TELEGRAM SENT] Successfully sent to Chat ID: {chat_id}\n")
                    return True
                else:
                    error_msg = f"Telegram API error (Status {response.status_code}): {response.text}"
                    logger.error(error_msg)
                    print(f"\n[TELEGRAM ERROR] {error_msg}\n")
                    return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    async def make_emergency_call(self, recipient: str = "Emergency Services") -> bool:
        """Initiates an emergency phone call."""
        logger.warning(f"NotificationService: INITIATING EMERGENCY CALL TO {recipient}")
        # Simulation: Use Twilio voice API
        print(f"\n[CALL INITIATED] To: {recipient}\n")
        await asyncio.sleep(1.0)
        return True

# Global instance for easy access
notification_service = NotificationService()
