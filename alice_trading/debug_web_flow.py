import requests
import hashlib
import os
import pyotp
import json
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv()

USER_ID = os.getenv("ALICEBLUE_USER_ID", "").strip('"').strip()
PASSWORD = os.getenv("ALICEBLUE_PASSWORD", "").strip('"').strip()
API_KEY = os.getenv("ALICEBLUE_API_KEY", "").strip('"').strip()
TOTP_SECRET = os.getenv("ALICEBLUE_TOTP_SECRET", "").strip('"').strip()

# Crypto helper from alice_blue
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import base64

class CryptoJsAES:
    @staticmethod
    def __pad(data):
        BLOCK_SIZE = 16
        length = BLOCK_SIZE - (len(data) % BLOCK_SIZE)
        return data + (chr(length)*length).encode()

    @staticmethod
    def __bytes_to_key(data, salt, output=48):
        data += salt
        key = hashlib.md5(data).digest()
        final_key = key
        while len(final_key) < output:
            key = hashlib.md5(key + data).digest()
            final_key += key
        return final_key[:output]

    @staticmethod
    def encrypt(message, passphrase):
        salt = os.urandom(8)
        key_iv = CryptoJsAES.__bytes_to_key(passphrase, salt, 32+16)
        key = key_iv[:32]
        iv = key_iv[32:]
        aes = Cipher(algorithms.AES(key), modes.CBC(iv))
        return base64.b64encode(b"Salted__" + salt + aes.encryptor().update(CryptoJsAES.__pad(message)) + aes.encryptor().finalize())

def debug_full_web_flow():
    print(f"--- Full Web Flow Debug for {USER_ID} ---")
    host = "https://ant.aliceblueonline.com/rest/AliceBlueAPIService"
    header = {"Content-Type" : "application/json"}
    
    # 1. Get Enc Key
    r1 = requests.post(f"{host}/customer/getEncryptionKey", json={"userId": USER_ID.upper()})
    encKey = r1.json()["encKey"]
    print(f"EncKey: {encKey}")

    # 2. Web Login
    checksum = CryptoJsAES.encrypt(PASSWORD.encode(), encKey.encode()).decode("utf-8")
    r2 = requests.post(f"{host}/customer/webLogin", json={"userId": USER_ID.upper(), "userData": checksum})
    print(f"WebLogin Resp: {r2.text}")

    # 3. 2FA (TOTP)
    otp = pyotp.TOTP(TOTP_SECRET).now()
    print(f"Current TOTP: {otp}")
    
    # Try different 2FA payloads
    fa_payloads = [
        {"userId": USER_ID.upper(), "otp": otp},
        {"answer1": otp, "userId": USER_ID.upper(), "vendor": "AliceBlue", "sCount": "1", "sIndex": "1"},
        {"userId": USER_ID.upper(), "tfa": otp},
        {"userId": USER_ID.upper(), "twofa": otp},
    ]
    
    for p in fa_payloads:
        print(f"\nTrying 2FA Payload: {p}")
        r3 = requests.post(f"{host}/sso/validAnswer", json=p)
        print(f"Resp Code: {r3.status_code}")
        print(f"Resp Text: {r3.text}")
        
        try:
            res_json = r3.json()
            if "redirectUrl" in res_json:
                print("!!! FOUND REDIRECT URL !!!")
                redi = res_json["redirectUrl"]
                authCode = parse_qs(urlparse(redi).query)['authCode'][0]
                print(f"AuthCode: {authCode}")
                
                # Step 4: Get API session
                # First get API enc key
                r4 = requests.post(f"{host}/api/customer/getAPIEncpkey", json={"userId": USER_ID.upper()})
                print(f"API EncKey Resp: {r4.text}")
                
                # Finally getUserDetails
                final_checksum = hashlib.sha256(f"{USER_ID.upper()}{authCode}{API_KEY}".encode()).hexdigest()
                r5 = requests.post(f"{host}/sso/getUserDetails", json={"checkSum": final_checksum})
                print(f"Final Session Resp: {r5.text}")
                return
        except:
            pass

if __name__ == "__main__":
    debug_full_web_flow()
