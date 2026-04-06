import os
import pyotp
from pya3 import Aliceblue
from dotenv import load_dotenv

load_dotenv()

user_id = os.getenv("ALICEBLUE_USER_ID")
api_key = os.getenv("ALICEBLUE_API_KEY")
totp_secret = os.getenv("ALICEBLUE_TOTP_SECRET")

print(f"UserID: {user_id}")
print(f"API Key Length: {len(api_key) if api_key else 0}")
print(f"TOTP Secret: {totp_secret}")

if not all([user_id, api_key, totp_secret]):
    print("Missing credentials")
    exit()

alice = Aliceblue(user_id=user_id, api_key=api_key)
totp = pyotp.TOTP(totp_secret).now()
print(f"Generated TOTP: {totp}")

try:
    session_res = alice.get_session_id(totp)
    print(f"Full Result: {session_res}")
    
    if isinstance(session_res, dict) and session_res.get("sessionID"):
        print("LOGIN SUCCESSFUL")
    else:
        print("LOGIN FAILED")
        if isinstance(session_res, dict):
            print(f"Error Message: {session_res.get('emsg')}")
except Exception as e:
    print(f"Exception: {e}")
