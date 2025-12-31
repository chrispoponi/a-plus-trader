import os
import requests
from datetime import datetime
import pytz
from dotenv import load_dotenv

load_dotenv("secrets.env")

class NotificationService:
    def __init__(self):
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")

    def send_message(self, title: str, message: str, color: int = 0x00ff00):
        """
        Sends a rich embed message to Discord.
        Color Defaults: Green (0x00ff00) for info, Red (0xff0000) for alert.
        """
        if not self.discord_webhook:
            print(f"NO WEBHOOK CONFIGURED. LOG: {title} - {message}")
            return

        payload = {
            "embeds": [
                {
                    "title": title,
                    "description": message,
                    "color": color,
                    "timestamp": datetime.now(pytz.utc).isoformat(),
                    "footer": {"text": "A+ Trader Bot | Harmonic Eagle"}
                }
            ]
        }
        
        try:
            requests.post(self.discord_webhook, json=payload)
        except Exception as e:
            print(f"Failed to send discord alert: {e}")

notifier = NotificationService()
