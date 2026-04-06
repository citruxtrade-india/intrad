import os
import pyotp
import json
import time
from pya3 import Aliceblue
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ALICEBLUE_API_KEY", "").strip('"').strip()
USER_ID = os.getenv("ALICEBLUE_USER_ID", "").strip('"').strip()
TOTP_SECRET = os.getenv("ALICEBLUE_TOTP_SECRET", "").strip('"').strip()

def test_offset_logins():
    print(f"Brute-forcing time drift (System: {time.strftime('%H:%M:%S')})")
    offsets = [-180, -150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300]
    
    for offset in offsets:
        totp = pyotp.TOTP(TOTP_SECRET)
        token = totp.at(time.time() + offset)
        print(f"Trying Offset: {offset:4}s | Token: {token}...", end="", flush=True)
        
        try:
            alice = Aliceblue(user_id=USER_ID, api_key=API_KEY)
            res = alice.get_session_id(token)
            if res and isinstance(res, dict) and res.get("sessionID"):
                print(" ✅ SUCCESS!")
                print(f"DRAG FIX: Add {offset} seconds to your TOTP generation.")
                return offset
            else:
                print(f" ❌ {res.get('emsg') if isinstance(res, dict) else 'Error'}")
        except Exception as e:
            print(f" ❌ Exception: {e}")
            
        time.sleep(1) # Rate limit protection

if __name__ == "__main__":
    test_offset_logins()
