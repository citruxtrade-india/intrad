import requests
import json
import hashlib
import os
import pyotp
from dotenv import load_dotenv

load_dotenv()

USER_ID = os.getenv("ALICEBLUE_USER_ID", "").strip('"').strip()
API_KEY = os.getenv("ALICEBLUE_API_KEY", "").strip('"').strip()
TOTP_SECRET = os.getenv("ALICEBLUE_TOTP_SECRET", "").strip('"').strip()

def encrypt_string(hashing):
    return hashlib.sha256(hashing.encode()).hexdigest()

def manual_login():
    print(f"Manual login test for {USER_ID}")
    base_url = "https://ant.aliceblueonline.com/rest/AliceBlueAPIService/api/"
    
    # Step 1: Get Encryption Key
    try:
        url = base_url + "customer/getAPIEncpkey"
        payload = {"userId": USER_ID.upper()}
        r1 = requests.post(url, json=payload)
        res1 = r1.json()
        print(f"Step 1 Response: {res1}")
        
        if res1.get("stat") != "Ok" or not res1.get("encKey"):
            print("Failed at Step 1")
            return
            
        enc_key = res1["encKey"]
        
        # Step 2: Get Session Data using TOTP
        # The new flow requires TOTP as 'two_fa' parameter or similar.
        # But pya3 1.0.30 (old) used 'userData' = sha256(userId + apiKey + encKey)
        
        user_data = encrypt_string(USER_ID.upper() + API_KEY + enc_key)
        otp = pyotp.TOTP(TOTP_SECRET).now()
        
        # Trial A: Old protocol
        print(f"Trial A (Old Protocol)...")
        url2 = base_url + "customer/getUserSID"
        payload2 = {"userId": USER_ID.upper(), "userData": user_data}
        r2 = requests.post(url2, json=payload2)
        print(f"Trial A Response: {r2.text}")
        
        # Trial B: New protocol (TOTP in payload)
        print(f"Trial B (New Protocol with TOTP)...")
        payload3 = {"userId": USER_ID.upper(), "userData": user_data, "two_fa": otp}
        r3 = requests.post(url2, json=payload3)
        print(f"Trial B Response: {r3.text}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    manual_login()
