import requests
import os
from dotenv import load_dotenv

load_dotenv()
USER_ID = os.getenv("ALICEBLUE_USER_ID", "").strip('"').strip()

def test_openapi():
    print(f"Testing OpenAPI V1 for {USER_ID}...")
    base_url = "https://ant.aliceblueonline.com/open-api/od/v1"
    
    # Try common encryption key endpoints
    endpoints = [
        "/customer/getEncryptionKey",
        "/vendor/getEncryptionKey",
        "/customer/getAPIEncpkey",
        "/vendor/getAPIEncpkey",
        "/sso/getEncryptionKey",
    ]
    
    for ep in endpoints:
        print(f"Trying {ep}...")
        try:
            r = requests.post(base_url + ep, json={"userId": USER_ID.upper()})
            print(f"   Resp: {r.status_code} | {r.text[:200]}")
        except:
            pass

if __name__ == "__main__":
    test_openapi()
