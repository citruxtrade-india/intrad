
from pya3 import Aliceblue
import pyotp
import os
import datetime
from dotenv import load_dotenv

load_dotenv()

user_id = os.getenv("ALICEBLUE_USER_ID")
api_key = os.getenv("ALICEBLUE_API_KEY")
totp_secret = os.getenv("ALICEBLUE_TOTP_SECRET")

otp = pyotp.TOTP(totp_secret).now()
alice = Aliceblue(user_id=user_id, api_key=api_key)
session_res = alice.get_session_id(otp)

if session_res and isinstance(session_res, dict) and session_res.get('sessionID'):
    alice.session_id = session_res.get('sessionID')
    print(f"Logged in: {alice.session_id[:10]}...")
    
    # Test balance
    try:
        bal = alice.get_balance()
        print(f"Balance Type: {type(bal)}")
        print(f"Balance: {bal}")
    except Exception as e:
        print(f"Balance Error: {e}")
else:
    print(f"Login failed: {session_res}")
