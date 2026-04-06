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
    
    print(f"User ID: {USER_ID}")
    
    try:
        alice = Aliceblue(user_id=USER_ID, api_key=API_KEY)
        
        # Try getting encryption key first if it exists
        if hasattr(alice, 'get_enc_key'):
            print("Fetching encryption key...")
            enc = alice.get_enc_key()
            print(f"Enc Key Result: {enc}")
            
        token = pyotp.TOTP(TOTP_SECRET).now()
        print(f"Using TOTP: {token}")
        
        session = alice.get_session_id(token)
        print(f"Session Response: {session}")
        
        if session.get('stat') == 'Ok' and not session.get('sessionID'):
            print("\n⚠️ WARNING: Status is 'Ok' but 'sessionID' is missing.")
            print(f"Error Message: {session.get('emsg')}")
            
            # Check if sessionID is under a different key
            for k, v in session.items():
                if 'session' in k.lower():
                    print(f"Found related key: {k} = {v}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    diagnostic()
