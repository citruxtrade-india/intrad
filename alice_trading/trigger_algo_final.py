import requests
import json

BASE_URL = "http://localhost:8001"
USER_ID = "nemturivishnuvardan@gmail.com"

def trigger_webhook_trade():
    url = f"{BASE_URL}/webhook"
    payload = {
        "symbol": "NIFTY",
        "side": "BUY",
        "qty": 50
    }
    headers = {
        "Content-Type": "application/json",
        "X-User-ID": USER_ID
    }
    
    print(f"Triggering ALGO trade simulation via webhook for {USER_ID}...")
    res = requests.post(url, json=payload, headers=headers)
    print(f"Status: {res.status_code}")
    print(f"Result: {res.text}")

if __name__ == "__main__":
    trigger_webhook_trade()
