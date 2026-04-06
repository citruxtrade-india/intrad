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

def debug_login_v5():
    print(f"--- Debug Login V5 (New Hash Logic) for {USER_ID} ---")
    # Base URL used by most working 2026 scripts
    base_url = "https://ant.aliceblueonline.com/rest/AliceBlueAPIService/api/"
    
    # Step 1: Enc Key
    try:
        r1 = requests.post(base_url + "customer/getAPIEncpkey", json={"userId": USER_ID.upper()})
        res1 = r1.json()
        enc_key = res1.get("encKey")
        if not enc_key:
            print(f"Failed to get encKey: {res1}")
            return
        print(f"EncKey: {enc_key}")
    except Exception as e:
        print(f"Error getting Encrytion Key: {e}")
        return

    otp = pyotp.TOTP(TOTP_SECRET).now()
    print(f"Current TOTP: {otp}")

    u = USER_ID.upper()
    
    # Attempt 1: Standard Hash (No TOTP inside hash)
    # userData = sha256(u + API_KEY + enc_key)
    user_data_std = encrypt(u + API_KEY + enc_key)

    # Attempt 2: Hash with TOTP inside
    # userData = sha256(u + API_KEY + enc_key + otp)
    user_data_with_otp = encrypt(u + API_KEY + enc_key + otp)

    url2 = base_url + "customer/getUserSID"
    
    candidates = [
        # Standard hash with different TOTP fields
        {"userId": u, "userData": user_data_std, "tOtp": otp},
        {"userId": u, "userData": user_data_std, "twoFA": otp},
        # Hash with OTP inside
        {"userId": u, "userData": user_data_with_otp},
        {"userId": u, "userData": user_data_with_otp, "tOtp": otp},
        # Try lowercase userID field?
        {"userid": u, "userData": user_data_std, "tOtp": otp},
    ]
    
    for i, payload in enumerate(candidates):
        print(f"\nTrying Payload Candidate {i+1}: {payload}")
        try:
            r = requests.post(url2, json=payload)
            print(f"   Status: {r.status_code}")
            print(f"   Resp: {r.text}")
            if "sessionID" in r.text or "session_id" in r.text:
                print("\n!!! SUCCESS !!!")
                # print(f"Payload ID {i+1} worked!")
                return
        except Exception as e:
            print(f"   Error: {e}")

if __name__ == "__main__":
    debug_login_v5()
