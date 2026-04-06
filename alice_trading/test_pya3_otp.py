import os
import pyotp
from pya3 import Aliceblue
from dotenv import load_dotenv

load_dotenv()

USER_ID = os.getenv("ALICEBLUE_USER_ID", "").strip('"').strip()
API_KEY = os.getenv("ALICEBLUE_API_KEY", "").strip('"').strip()
TOTP_SECRET = os.getenv("ALICEBLUE_TOTP_SECRET", "").strip('"').strip()

def test_pya3_with_otp_field():
    print(f"Testing PYA3 with manual OTP field for {USER_ID}...")
    alice = Aliceblue(user_id=USER_ID, api_key=API_KEY)
    
    # Manually perform the logic of get_session_id but add OTP
    otp = pyotp.TOTP(TOTP_SECRET).now()
    print(f"Current OTP: {otp}")
    
    # 1. Get Enc Key
    enc_res = alice._post("encryption_key", {'userId': USER_ID.upper()})
    enc_key = enc_res.get('encKey')
    print(f"EncKey: {enc_key}")
    
    if not enc_key:
        print("Failed to get EncKey")
        return

    # 2. Checksum
    from pya3.alicebluepy import encrypt_string
    user_data = encrypt_string(USER_ID.upper() + API_KEY + enc_key)
    
    # Try different field names for OTP in the getUserSID payload
    otp_fields = ["otp", "tOtp", "twofa", "two_fa", "twoFA", "tfa"]
    
    for field in otp_fields:
        payload = {
            'userId': USER_ID.upper(), 
            'userData': user_data,
            field: otp
        }
        print(f"\nTrying {field}={otp}...")
        res = alice._post("getsessiondata", payload)
        print(f"Response: {res}")
        if res.get('stat') == 'Ok':
            print("!!! SUCCESS !!!")
            print(f"Session ID: {res.get('sessionID')}")
            return

if __name__ == "__main__":
    test_pya3_with_otp_field()
