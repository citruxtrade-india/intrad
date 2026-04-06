import requests
import json
import time

BASE_URL = "http://localhost:8001"
USER_ID = "nemturivishnuvardan@gmail.com"
API_KEY = "Password@123"

def test_trading_flow():
    session = requests.Session()
    headers = {"Content-Type": "application/json", "X-User-ID": USER_ID}

    # 1. Login
    print(f"--- 1. Logging in as {USER_ID} ---")
    res = session.post(f"{BASE_URL}/api/v1/auth/login", json={"user_id": USER_ID, "api_key": API_KEY})
    if res.status_code != 200:
        print(f"Login failed: {res.text}")
        return
    print(f"Login Success: {res.json()}")

    # 2. Check System Health
    print(f"\n--- 2. Checking System Health ---")
    res = session.get(f"{BASE_URL}/api/v1/system/health", headers=headers)
    print(f"Health: {res.json()}")

    # 3. Start System
    print(f"\n--- 3. Starting Trading System ---")
    res = session.post(f"{BASE_URL}/api/v1/system/start", headers=headers)
    print(f"Start Response: {res.json()}")

    # 4. Check Agent Statuses
    print(f"\n--- 4. Initial Agent Statuses ---")
    res = session.get(f"{BASE_URL}/api/v1/agents/status", headers=headers)
    print(f"Agents: {json.dumps(res.json(), indent=2)}")

    # 5. Execute Manual Trade
    print(f"\n--- 5. Executing Manual LONG Trade on NIFTY ---")
    trade_data = {
        "symbol": "NIFTY",
        "signal": "BUY",
        "qty": 50,
        "type": "MARKET"
    }
    res = session.post(f"{BASE_URL}/api/v1/order/manual", json=trade_data, headers=headers)
    print(f"Trade Response: {res.json()}")

    # 6. Analyze Agents (Audit Trail)
    print(f"\n--- 6. Analyzing Agent Reasoning (Audit Trail) ---")
    time.sleep(1) # Wait for event emission
    res = session.get(f"{BASE_URL}/api/v1/agents/audit", headers=headers)
    audit = res.json()
    print(f"Recent Audit Events: {len(audit)}")
    for event in audit[-5:]:
        print(f"  [{event['timestamp']}] {event['agent']}: {event['reason']} (Confidence: {event['confidence']})")

if __name__ == "__main__":
    test_trading_flow()
