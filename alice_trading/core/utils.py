import datetime
import logging
import os
import smtplib
import requests
from email.mime.text import MIMEText
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Antigravity")

def is_market_open() -> bool:
    """Checks if the Indian stock market is currently open (9:15 AM - 3:30 PM IST)."""
    # Force IST (UTC + 5:30)
    utc_now = datetime.datetime.utcnow()
    ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
    
    # Check if it's a weekday (0=Monday, 6=Sunday)
    if ist_now.weekday() >= 5:
        return False
        
    current_time = ist_now.time()
    market_start = datetime.time(9, 15)
    market_end = datetime.time(15, 30)
    
    return market_start <= current_time <= market_end

def send_alert(message: str):
    """Sends an alert via Telegram if configured, otherwise logs to file."""
    logger.info(f"ALERT: {message}")
    
    # Telegram Integration (Optional)
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if bot_token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {"chat_id": chat_id, "text": f"🚀 *Antigravity Alert*\n{message}", "parse_mode": "Markdown"}
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")

class BackoffTimer:
    """Manages exponential backoff intervals for retries."""
    def __init__(self):
        self.intervals = [60, 120, 300, 600] # seconds
        self.current_step = 0
        
    def get_next_delay(self) -> int:
        delay = self.intervals[self.current_step]
        if self.current_step < len(self.intervals) - 1:
            self.current_step += 1
        return delay
        
    def reset(self):
        self.retry_count = 0

def patch_http_headers():
    """
    Deep monkeypatch requests to include a browser-like User-Agent and correct headers.
    This fixes 405 Method Not Allowed errors on Alice Blue API by targeting the Session class.
    """
    from requests import Session
    original_request = Session.request

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9"
    }

    def patched_request(self, method, url, *args, **kwargs):
        # Initialize headers if not present
        if 'headers' not in kwargs or kwargs['headers'] is None:
            kwargs['headers'] = headers.copy()
        else:
            # Update headers but don't overwrite if specified
            for k, v in headers.items():
                if k not in kwargs['headers']:
                    kwargs['headers'][k] = v
        
        # Ensure Content-Type is set for POST/PUT if not specified
        if method.upper() in ["POST", "PUT"]:
            if "Content-Type" not in kwargs['headers']:
                kwargs['headers']["Content-Type"] = "application/json"

        return original_request(self, method, url, *args, **kwargs)

    Session.request = patched_request
    logger.info("Deep HTTP Headers patched for Alice Blue compatibility.")

# Auto-apply patch on import
patch_http_headers()
