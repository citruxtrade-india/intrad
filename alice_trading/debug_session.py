import os
import pyotp
import time
from pya3 import Aliceblue
from dotenv import load_dotenv

load_dotenv()

def diagnostic():
    USER_ID = os.getenv("ALICEBLUE_USER_ID")
    API_KEY = os.getenv("ALICEBLUE_API_KEY")
    TOTP_SECRET = os.getenv("ALICEBLUE_TOTP_SECRET")
    
    print(f"UID: {USER_ID}")
    print(f"Secret: {TOTP_SECRET}")
    
    try:
        totp = pyotp.TOTP(TOTP_SECRET)
        token = totp.now()
        print(f"Generated TOTP: {token}")
        
        alice = Aliceblue(user_id=USER_ID, api_key=API_KEY)
        session = alice.get_session_id(token)
        
        print(f"Full Session Response: {session}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    diagnostic()
