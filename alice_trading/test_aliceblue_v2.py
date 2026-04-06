from alice_blue import AliceBlue
import os
import pyotp
from dotenv import load_dotenv

load_dotenv()

USER_ID = os.getenv("ALICEBLUE_USER_ID", "").strip('"').strip()
PASSWORD = os.getenv("ALICEBLUE_PASSWORD", "").strip('"').strip()
API_KEY = os.getenv("ALICEBLUE_API_KEY", "").strip('"').strip()
TOTP_SECRET = os.getenv("ALICEBLUE_TOTP_SECRET", "").strip('"').strip()

def login_v2():
    print(f"Testing alice_blue v2 login for {USER_ID}...")
    try:
        # Generate TOTP
        otp = pyotp.TOTP(TOTP_SECRET).now()
        print(f"Generated TOTP: {otp}")
        
        # In alice_blue v2.0.4:
        # login_and_get_sessionID(username, password, twoFA, app_id, api_secret)
        # Note: app_id is usually same as userId or 'AliceBlue'
        # Wait, app_id is sent in sso/validAnswer as 'vendor' field.
        
        session_id = AliceBlue.login_and_get_sessionID(
            username=USER_ID.upper(),
            password=PASSWORD,
            twoFA=otp,
            app_id='AliceBlue', # Common default for retail
            api_secret=API_KEY   # In this library, api_secret is the long key
        )
        
        print(f"✅ Success! Session ID: {session_id}")
        
        # Test if session works by making a simple call
        alice = AliceBlue(USER_ID.upper(), session_id)
        profile = alice.get_profile()
        print(f"✅ Profile: {profile.get('accountName')}")
        
    except Exception as e:
        print(f"❌ Login Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    login_v2()
