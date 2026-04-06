import os
import pyotp
import json
from pya3 import Aliceblue
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ALICEBLUE_API_KEY", "").strip('"').strip()
USER_ID = os.getenv("ALICEBLUE_USER_ID", "").strip('"').strip()
TOTP_SECRET = os.getenv("ALICEBLUE_TOTP_SECRET", "").strip('"').strip()

def debug_login():
    print(f"DEBUG LOGIN for [{USER_ID}]")
    print(f"API_KEY Length: {len(API_KEY) if API_KEY else 0}")
    print(f"TOTP_SECRET: [{TOTP_SECRET}]")
    try:
        alice = Aliceblue(user_id=USER_ID, api_key=API_KEY)
        totp_val = pyotp.TOTP(TOTP_SECRET).now()
        print(f"Using TOTP: {totp_val}")
        session_res = alice.get_session_id(totp_val)
        
        print("\nFull Session Response:")
        print(json.dumps(session_res, indent=2))
        
        if session_res and isinstance(session_res, dict) and session_res.get("sessionID"):
            print("\n✅ Login SUCCESS! Session ID obtained.")
        else:
            print("\n❌ Login FAILED!")
            
    except Exception as e:
        print(f"\nCaught Exception: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_login()
