from agents.auth_agent import AuthAgent
from agents.live_market_agent import start_market_feed, data_bus
from agents.anti_gravity_agent import AntiGravityAgent
import time
import threading

def login():
    alice = AuthAgent().login()
    if alice:
        print("[OK] Login Successful")
    else:
        print("[ERR] Login Failed. Check .env credentials.")
    return alice

def start_live_feed(alice):
    """Start WebSocket and subscribe to live market data"""
    if not alice:
        print("[ERR] Live feed aborted: session is None.")
        return

    # Define symbols to subscribe to
    symbols_to_subscribe = [
        {"exchange": "NSE", "token": 26000, "name": "NIFTY50"},
        {"exchange": "NSE", "token": 26009, "name": "NIFTY BANK"},
        {"exchange": "BSE", "token": 30, "name": "SENSEX"},
        {"exchange": "NSE", "symbol": "RELIANCE", "name": "RELIANCE"}
    ]
    start_market_feed(alice, symbols_to_subscribe)

    # Heartbeat: print status every 5 seconds
    print("[...] Waiting for live market ticks...")
    while True:
        # current_data = data_bus.get_all_data()
        # tick_count = len(current_data)
        time.sleep(5) 

def anti_gravity_loop():
    """Run Anti-Gravity analysis in a loop"""
    agent = AntiGravityAgent()
    print("[MKT] Starting Anti-Gravity Agent...")

    try:
        while True:
            agent.run_cycle()
            time.sleep(1)  # Analyze every second (fast reaction)
    except KeyboardInterrupt:
        print("\n[ERR] Analysis stopped")

def main():
    alice = login()

    if not alice:
        print("Exiting due to login failure.")
        return

    # Start analysis in background thread
    analysis_thread = threading.Thread(target=anti_gravity_loop)
    analysis_thread.daemon = True
    analysis_thread.start()

    # START LIVE FEED IN MAIN THREAD (Required by some SDK versions for signal handling)
    try:
        start_live_feed(alice)
    except KeyboardInterrupt:
        print("\nShutting down...") 
