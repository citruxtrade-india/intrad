
import requests
import time
import json

BASE_URL = "http://localhost:8001/api/v1"

def log(msg):
    print(f"[TEST CLIENT] {msg}")

try:
    log("Waiting for server to start...")
    for i in range(10):
        try:
            requests.get(f"{BASE_URL}/system/health", timeout=1)
            break
        except requests.exceptions.ConnectionError:
            time.sleep(1)
            print(".", end="", flush=True)
    print("\nServer connected!")

    # 1. Switch to PAPER (Start Live Feed)
    log("Switching to PAPER mode...")
    r = requests.post(f"{BASE_URL}/system/mode", json={"mode": "PAPER"})
    print(f"Status: {r.status_code}, Response: {r.text}")
    
    if r.status_code == 200:
        log("Waiting 5s for live data...")
        for _ in range(5):
            metrics = requests.get(f"{BASE_URL}/dashboard/metrics").json()
            nifty_data = metrics.get('market_data', {}).get('NIFTY', {})
            print(f"  NIFTY: {nifty_data.get('ltp')} (Status: {nifty_data.get('status')})")
            time.sleep(1)

    # 2. Switch to MOCK (Stop Feed)
    log("Switching to MOCK mode...")
    r = requests.post(f"{BASE_URL}/system/mode", json={"mode": "MOCK"})
    print(f"Status: {r.status_code}, Response: {r.text}")
    time.sleep(2)

    # 3. Switch back to PAPER (Restart Feed)
    log("Switching back to PAPER mode...")
    r = requests.post(f"{BASE_URL}/system/mode", json={"mode": "PAPER"})
    print(f"Status: {r.status_code}, Response: {r.text}")
    
    if r.status_code == 200:
        log("Waiting 5s for live data after restart...")
        for _ in range(5):
            metrics = requests.get(f"{BASE_URL}/dashboard/metrics").json()
            nifty_data = metrics.get('market_data', {}).get('NIFTY', {})
            print(f"  NIFTY: {nifty_data.get('ltp')} (Status: {nifty_data.get('status')})")
            time.sleep(1)

except Exception as e:
    log(f"Test failed: {e}")
