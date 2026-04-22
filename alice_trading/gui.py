from core.live_data_manager import LiveDataManager
from shared.data_bus import DataBus
from agents.anti_gravity_agent import AntiGravityAgent
import threading
import time

def login():
    from agents.auth_agent import AuthAgent
    alice = AuthAgent().login()
    if alice:
        print("[OK] Login Successful")
    else:
        print("[ERR] Login Failed. Check .env credentials.")
    return alice

def start_live_feed(alice):
    """Start WebSocket via LiveDataManager for maximum stability"""
    if not alice: return

    # Define symbols
    symbols = [
        {"exchange": "NSE", "token": 26000, "name": "NIFTY50"},
        {"exchange": "NSE", "token": 26009, "name": "NIFTY BANK"},
        {"exchange": "BSE", "token": 30, "name": "SENSEX"},
        {"exchange": "NSE", "token": 1394, "name": "HINDUNILVR"},
        {"exchange": "NSE", "token": 1333, "name": "HDFCBANK"},
        {"exchange": "NSE", "token": 1594, "name": "INFY"},
        {"exchange": "NSE", "token": 1348, "name": "HEROMOTOCO"},
        {"exchange": "NSE", "symbol": "RELIANCE", "token": 2885, "name": "RELIANCE"}
    ]

    ldm = LiveDataManager(user_id="admin")
    
    # Credentials from .env are handled by LiveDataManager internally if we set them
    import os
    ldm.set_credentials(
        os.getenv("ALICEBLUE_USER_ID"),
        os.getenv("ALICEBLUE_API_KEY"),
        os.getenv("ALICEBLUE_TOTP_SECRET")
    )

    print("[START] Starting LiveDataManager (Multi-Tenant Engine)...")
    
    # We run the async start in the current thread's event loop
    import asyncio
    async def run_ldm():
        await ldm.start(symbols)
        print("[...] Waiting for live market ticks...")
        while True:
            await asyncio.sleep(5)

    try:
        asyncio.run(run_ldm())
    except KeyboardInterrupt:
        pass
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
