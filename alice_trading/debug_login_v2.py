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

def debug_login_v2():
    print(f"--- Debug Login V2 for {USER_ID} ---")
    base_url = "https://ant.aliceblueonline.com/rest/AliceBlueAPIService/api/"
    
    # Step 1: Enc Key
    url1 = base_url + "customer/getAPIEncpkey"
    r1 = requests.post(url1, json={"userId": USER_ID.upper()})
    res1 = r1.json()
    print(f"EncKey Response: {res1}")
    enc_key = res1.get("encKey")
    if not enc_key:
        print("Failed to get EncKey")
        return

    otp = pyotp.TOTP(TOTP_SECRET).now()
    print(f"Current TOTP: {otp}")

    # Combinations to try for getUserSID
    combinations = [
        ("C1: Default (userId + apiKey + encKey)", encrypt(USER_ID.upper() + API_KEY + enc_key), {}),
        ("C2: Appended TOTP to Checksum (userId + apiKey + encKey + otp)", encrypt(USER_ID.upper() + API_KEY + enc_key + otp), {}),
        ("C3: Checksum + 'otp' field", encrypt(USER_ID.upper() + API_KEY + enc_key), {"otp": otp}),
        ("C4: Checksum + 'two_fa' field", encrypt(USER_ID.upper() + API_KEY + enc_key), {"two_fa": otp}),
        ("C5: Checksum + 'tPin' field", encrypt(USER_ID.upper() + API_KEY + enc_key), {"tPin": otp}),
        ("C6: Checksum + 'twofa' field", encrypt(USER_ID.upper() + API_KEY + enc_key), {"twofa": otp}),
    ]

    url2 = base_url + "customer/getUserSID"
    for label, user_data, extra in combinations:
        payload = {"userId": USER_ID.upper(), "userData": user_data}
        payload.update(extra)
        print(f"\nTrying {label}...")
        try:
            r2 = requests.post(url2, json=payload)
            print(f"Response: {r2.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    debug_login_v2()
