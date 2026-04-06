import requests
import os
from dotenv import load_dotenv

load_dotenv()
USER_ID = os.getenv("ALICEBLUE_USER_ID", "").strip('"').strip()

def test_v2api():
    print(f"Testing V2API for {USER_ID}...")
    url = "https://v2api.aliceblueonline.com/restpy/customer/getAPIEncpkey"
    try:
        r = requests.post(url, json={"userId": USER_ID.upper()})
        print(f"V2 Resp: {r.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_v2api()
