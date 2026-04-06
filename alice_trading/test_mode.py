import requests
import json
import time

url = "http://localhost:8001/api/v1/system/mode"
headers = {"Content-Type": "application/json"}

modes = ["MOCK", "SIMULATION", "PAPER", "REAL"]

for mode in modes:
    payload = {"mode": mode}
    print(f"Testing mode: {mode}...")
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 20)
    time.sleep(1)
