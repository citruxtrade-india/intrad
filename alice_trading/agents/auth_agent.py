import os
import json
import pyotp
import datetime
import requests
from pya3 import Aliceblue
from core.utils import logger

class AuthAgent:
    def __init__(self):
        self.user_id = os.getenv("ALICEBLUE_USER_ID")
        self.api_key = os.getenv("ALICEBLUE_API_KEY")
        self.totp_secret = os.getenv("ALICEBLUE_TOTP_SECRET")
        self.session_file = "session.json"

    def login(self):
        """Production-ready login with persistent session caching and date validation."""
        # 1. Check for valid cached session
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, "r") as f:
                    cached = json.load(f)
                
                # Check if session is from today
                cached_date = cached.get("date")
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                
                if cached_date == today and cached.get("sessionID"):
                    logger.info("Reusing existing session from cache.")
                    alice = Aliceblue(user_id=self.user_id, api_key=self.api_key)
                    alice.session_id = cached.get("sessionID")
                    return alice
                else:
                    logger.info("Cached session expired or invalid. Re-authenticating...")
            except Exception as e:
                logger.warning(f"Failed to load session cache: {e}")

        # 2. Perform Fresh Login
        if not all([self.user_id, self.api_key, self.totp_secret]):
            logger.error("Missing broker credentials in .env file.")
            return None

        try:
            logger.info(f"Performing fresh login for {self.user_id}...")
            otp = pyotp.TOTP(self.totp_secret).now()
            alice = Aliceblue(user_id=self.user_id, api_key=self.api_key)
            session_res = alice.get_session_id(otp)

            if isinstance(session_res, dict) and session_res.get("stat") == "Ok":
                session_id = session_res.get("sessionID")
                # Save to cache
                with open(self.session_file, "w") as f:
                    json.dump({
                        "sessionID": session_id,
                        "date": datetime.datetime.now().strftime("%Y-%m-%d")
                    }, f)
                
                alice.session_id = session_id
                logger.info("Login successful and session cached.")
                return alice
            else:
                emsg = session_res.get("emsg") if isinstance(session_res, dict) else str(session_res)
                logger.error(f"Login failed: {emsg} | response={session_res}")
                return None

        except Exception as e:
            logger.error(f"Critical Login Error: {e}")
            return None
