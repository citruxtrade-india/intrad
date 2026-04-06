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

def debug_login_v3():
    print(f"--- Debug Login V3 for {USER_ID} ---")
    base_url = "https://ant.aliceblueonline.com/rest/AliceBlueAPIService/api/"
    
    # Step 1: Enc Key
    url1 = base_url + "customer/getAPIEncpkey"
    r1 = requests.post(url1, json={"userId": USER_ID.upper()})
    res1 = r1.json()
    print(f"Step 1 (EncKey) Result: {res1}")
    enc_key = res1.get("encKey")
    if not enc_key:
        return

    otp = pyotp.TOTP(TOTP_SECRET).now()
    print(f"Current TOTP: {otp}")

    # Checksum permutations
    u = USER_ID.upper()
    a = API_KEY
    e = enc_key
    o = otp

    checksums = [
         ("u + a + e", encrypt(u + a + e)),
         ("u + e + a", encrypt(u + e + a)),
         ("a + e + u", encrypt(a + e + u)),
         ("a + u + e", encrypt(a + u + e)),
         ("u + a + e + o", encrypt(u + a + e + o)),
         ("SHA(a) + SHA(u) + e", encrypt(encrypt(a) + encrypt(u) + e)), # Some versions use this
    ]

    url2 = base_url + "customer/getUserSID"
    
    for label, user_data in checksums:
        # Try both with and without explicit TOTP field
        payloads = [
            {"label": label, "data": {"userId": u, "userData": user_data}},
            {"label": label + " + otp", "data": {"userId": u, "userData": user_data, "otp": o}},
            {"label": label + " + two_fa", "data": {"userId": u, "userData": user_data, "two_fa": o}},
            {"label": label + " + twofa", "data": {"userId": u, "userData": user_data, "twofa": o}},
        ]
        
        for p in payloads:
            print(f"Trying {p['label']}...")
            try:
                r2 = requests.post(url2, json=p['data'])
                print(f"   Resp: {r2.text}")
                if "sessionID" in r2.text:
                    print(f"!!! SUCCESS WITH {p['label']} !!!")
                    return
            except:
                pass

if __name__ == "__main__":
    debug_login_v3()
