import requests
import hashlib
import os
import pyotp
from dotenv import load_dotenv

load_dotenv()

USER_ID = os.getenv("ALICEBLUE_USER_ID", "").strip('"').strip()
API_KEY = os.getenv("ALICEBLUE_API_KEY", "").strip('"').strip()
TOTP_SECRET = os.getenv("ALICEBLUE_TOTP_SECRET", "").strip('"').strip()

def encrypt(s):
    return hashlib.sha256(s.encode()).hexdigest()

def debug_login_v4():
    print(f"--- Debug Login V4 (tOtp + twoFA) for {USER_ID} ---")
    base_url = "https://ant.aliceblueonline.com/rest/AliceBlueAPIService/api/"
    
    # Step 1: Enc Key
    r1 = requests.post(base_url + "customer/getAPIEncpkey", json={"userId": USER_ID.upper()})
    enc_key = r1.json().get("encKey")
    print(f"EncKey: {enc_key}")

    otp = pyotp.TOTP(TOTP_SECRET).now()
    print(f"Current TOTP: {otp}")

    u = USER_ID.upper()
    user_data = encrypt(u + API_KEY + enc_key)

    url2 = base_url + "customer/getUserSID"
    
    # New attempts for 2026
    candidates = [
        {"userId": u, "userData": user_data, "tOtp": otp},
        {"userId": u, "userData": user_data, "twofa": otp},
        {"userId": u, "userData": user_data, "twoFA": otp},
        {"userId": u, "userData": user_data, "two_fa": otp},
        {"userId": u, "userData": user_data, "otp": otp},
        # Maybe userData changed
        {"userId": u, "userData": encrypt(u + API_KEY + enc_key + otp)}, 
        {"userId": u, "userData": encrypt(u + API_KEY + enc_key), "tOtp": otp, "vendor": "AliceBlue"},
    ]
    
    for payload in candidates:
        print(f"\nTrying Payload: {payload}")
        try:
            r = requests.post(url2, json=payload)
            print(f"   Resp: {r.text}")
            if "sessionID" in r.text:
                print("!!! SUCCESS !!!")
                return
        except Exception as e:
            print(f"   Error: {e}")

if __name__ == "__main__":
    debug_login_v4()
