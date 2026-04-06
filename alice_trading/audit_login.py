import os
import pyotp
import json
import time
from pya3 import Aliceblue
from dotenv import load_dotenv

load_dotenv()

def audit_login():
    uid = os.getenv("ALICEBLUE_USER_ID")
    apk = os.getenv("ALICEBLUE_API_KEY")
    tps = os.getenv("ALICEBLUE_TOTP_SECRET")
    
    print(f"Attempting login for {uid}...")
    
    try:
        alice = Aliceblue(user_id=uid, api_key=apk)
        otp = pyotp.TOTP(tps).now()
        session = alice.get_session_id(otp)
        
        print(f"Session Response: {json.dumps(session, indent=2)}")
        
        if session.get('stat') == 'Ok' and session.get('login') == True:
            print("SUCCESS: Logged in and session active.")
        elif session.get('stat') == 'Ok' and session.get('login') == False:
            print("FAILURE: Broker returned 'Ok' but login is False.")
            print(f"Message from broker: {session.get('emsg')}")
        else:
            print("FAILURE: Session creation failed.")

    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    audit_login()
