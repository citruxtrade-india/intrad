import requests
import hashlib
import os
import pyotp
from dotenv import load_dotenv

load_dotenv()

USER_ID = os.getenv("ALICEBLUE_USER_ID", "").strip('"').strip()
API_KEY = os.getenv("ALICEBLUE_API_KEY", "").strip('"').strip()
TOTP_SECRET = os.getenv("ALICEBLUE_TOTP_SECRET", "").strip('"').strip()

def encrypt_sha256(s):
    return hashlib.sha256(s.encode()).hexdigest()

def debug_checksum_variants():
    print(f"--- Checksum Variant Discovery for {USER_ID} ---")
    base_url = "https://ant.aliceblueonline.com/rest/AliceBlueAPIService/api/"
    
    # 1. Get Enc Key
    try:
        r1 = requests.post(base_url + "customer/getAPIEncpkey", json={"userId": USER_ID.upper()})
        res1 = r1.json()
        enc_key = res1.get("encKey")
        print(f"EncKey: {enc_key}")
    except Exception as e:
        print(f"Failed to get EncKey: {e}")
        return

    if not enc_key:
        print("Empty EncKey received.")
        return

    otp = pyotp.TOTP(TOTP_SECRET).now()
    print(f"Current TOTP: {otp}")

    u = USER_ID.upper()
    a = API_KEY
    e = enc_key
    o = otp

    # Common combinations for Indian brokers (Zerodha/Alice/Upstox style)
    variants = [
        ("u + a + e", encrypt_sha256(u + a + e)),
        ("u + e + a", encrypt_sha256(u + e + a)),
        ("a + u + e", encrypt_sha256(a + u + e)),
        ("a + e + u", encrypt_sha256(a + e + u)),
        ("e + u + a", encrypt_sha256(e + u + a)),
        ("e + a + u", encrypt_sha256(e + a + u)),
        
        # Including TOTP in concatenation (Very common in 2026 versions)
        ("u + a + e + o", encrypt_sha256(u + a + e + o)),
        ("u + a + o + e", encrypt_sha256(u + a + o + e)),
        ("u + o + a + e", encrypt_sha256(u + o + a + e)),
        ("o + u + a + e", encrypt_sha256(o + u + a + e)),
        ("u + e + o + a", encrypt_sha256(u + e + o + a)),
        ("a + e + o + u", encrypt_sha256(a + e + o + u)),
    ]

    target_url = base_url + "customer/getUserSID"
    
    for label, checksum in variants:
        payload = {"userId": u, "userData": checksum}
        print(f"Trying variant: {label}")
        try:
            r = requests.post(target_url, json=payload, headers={"User-Agent": "Codifi API Connect - Python Lib 1.0.30"})
            print(f"   Response: {r.text}")
            if "sessionID" in r.text or "Ok" in r.text:
                print(f"!!! DISCOVERED CORRECT FORMAT: {label} !!!")
                return
        except Exception as ex:
            print(f"   Request Error: {ex}")

if __name__ == "__main__":
    debug_checksum_variants()
