import requests
import os
from dotenv import load_dotenv

load_dotenv()
USER_ID = os.getenv("ALICEBLUE_USER_ID", "").strip('"').strip()

def test_new_base():
    # Attempting the base URL from the search result
    print(f"Testing a3.aliceblueonline.com base for {USER_ID}...")
    urls = [
        "https://a3.aliceblueonline.com/rest/AliceBlueAPIService/api/customer/getAPIEncpkey",
        "https://a3.aliceblueonline.com/api/customer/getAPIEncpkey",
        "https://a3.aliceblueonline.com/customer/getAPIEncpkey",
    ]
    
    for url in urls:
        print(f"\nTrying {url}...")
        try:
            r = requests.post(url, json={"userId": USER_ID.upper()}, timeout=5)
            print(f"   Status: {r.status_code}")
            print(f"   Body: {r.text[:200]}")
        except Exception as e:
            print(f"   Error: {e}")

if __name__ == "__main__":
    test_new_base()
