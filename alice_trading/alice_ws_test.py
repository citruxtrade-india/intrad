"""
🧪 Alice Blue WebSocket Test
Simple test to verify WebSocket connection and live data flow
"""

from pya3 import Aliceblue
import pyotp
import os
import time
from dotenv import load_dotenv

# Load credentials
load_dotenv()

print("=" * 70)
print("ALICE BLUE WEBSOCKET TEST")
print("=" * 70)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: AUTHENTICATE
# ─────────────────────────────────────────────────────────────────────────────

print("\n[1/4] Authenticating with Alice Blue...")

user_id = os.getenv("ALICEBLUE_USER_ID")
api_key = os.getenv("ALICEBLUE_API_KEY")
totp_secret = os.getenv("ALICEBLUE_TOTP_SECRET", "").replace(" ", "").strip()

if not all([user_id, api_key, totp_secret]):
    print("[ERROR] Missing credentials in .env file")
    exit(1)

try:
    otp = pyotp.TOTP(totp_secret).now()
    print(f"   Generated OTP: {otp}")
    
    alice = Aliceblue(user_id=user_id, api_key=api_key)
    session_res = alice.get_session_id(otp)
    
    print(f"   Session response: {session_res}")
    
    if not isinstance(session_res, dict) or session_res.get("stat") != "Ok":
        print(f"[ERROR] Login failed! Error: {session_res.get('emsg') if isinstance(session_res, dict) else session_res}")
        exit(1)
        
    session_id = session_res.get("sessionID")
    if not session_id:
        print("[ERROR] Login failed - No sessionID in response")
        exit(1)
    
    print(f"[SUCCESS] Login successful. Session ID: {session_id[:5]}...")
    
except Exception as e:
    print(f"[ERROR] Authentication error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: SETUP CALLBACKS
# ─────────────────────────────────────────────────────────────────────────────

print("\n[2/4] Setting up WebSocket callbacks...")

tick_count = 0
is_connected = False

# Symbol Mapping for display
symbol_map = {
    "26000": "NIFTY 50",
    "26009": "BANK NIFTY",
    "1394": "HINDUNILVR",
    "1333": "HDFCBANK"
}

def socket_open():
    """Called when WebSocket connects"""
    global is_connected
    is_connected = True
    print("[SUCCESS] WebSocket Connected")
    
    # Subscribe to multiple instruments
    instruments = [
        alice.get_instrument_by_token("NSE", 26000), # Nifty
        alice.get_instrument_by_token("NSE", 26009), # BankNifty
        alice.get_instrument_by_token("NSE", 1394),  # HUL
        alice.get_instrument_by_token("NSE", 1333),  # HDFC Bank
    ]
    
    # Filter None values
    valid_instruments = [i for i in instruments if i]
    
    try:
        from pya3 import LiveFeedType
    except Exception:
        LiveFeedType = None

    if LiveFeedType:
        alice.subscribe(valid_instruments, LiveFeedType.MARKET_DATA)
    else:
        alice.subscribe(valid_instruments)
        
    print(f"[MARKET] Subscribed to: {[i.symbol for i in valid_instruments]}")

def socket_close():
    """Called when WebSocket closes"""
    global is_connected
    is_connected = False
    print("[CLOSED] WebSocket Closed")

def socket_error(message):
    """Called on WebSocket error"""
    print(f"[WARNING] WebSocket Error: {message}")

def feed_data(message):
    """Called for each live tick"""
    global tick_count
    tick_count += 1
    
    token = str(message.get("tk", ""))
    symbol = message.get("ts", symbol_map.get(token, f"TOKEN:{token}"))
    price = message.get("lp", 0)
    volume = message.get("v", 0)
    
    if tick_count % 10 == 0:  # Log every 10th tick
        print(f"[TICK #{tick_count}]: {symbol:<12} @ {price:>10.2f} (Vol: {volume})")

print("[OK] Callbacks ready")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: START WEBSOCKET
# ─────────────────────────────────────────────────────────────────────────────

print("\n[3/4] Starting WebSocket...")

try:
    alice.start_websocket(
        socket_open_callback=socket_open,
        socket_close_callback=socket_close,
        socket_error_callback=socket_error,
        subscription_callback=feed_data,
        run_in_background=True
    )
    print("[OK] WebSocket started in background")
    
except Exception as e:
    print(f"[ERROR] WebSocket start error: {e}")
    exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: WAIT FOR DATA
# ─────────────────────────────────────────────────────────────────────────────

print("\n[4/4] Waiting for live data (60 seconds)...")
print("-" * 70)

start_time = time.time()
prev_tick_count = 0

while time.time() - start_time < 60:
    elapsed = int(time.time() - start_time)
    
    # Print status every 10 seconds
    if elapsed % 10 == 0 and elapsed > 0:
        status = "CONNECTED" if is_connected else "DISCONNECTED"
        ticks_per_sec = (tick_count - prev_tick_count) / 10 if prev_tick_count > 0 else 0
        print(f"{status} | Ticks: {tick_count} | Rate: {ticks_per_sec:.1f}/sec")
        prev_tick_count = tick_count
    
    time.sleep(1)

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "-" * 70)
print("TEST SUMMARY")
print("-" * 70)

if tick_count > 0:
    print(f"[PASSED] TEST SUCCESSFUL")
    print(f"   Total ticks received: {tick_count}")
    print(f"   Average rate: {tick_count/60:.1f} ticks/second")
    print(f"   WebSocket: {'CONNECTED' if is_connected else 'DISCONNECTED'}")
else:
    print(f"[FAILED] No ticks received")
    print(f"   This could mean:")
    print(f"   1. Market is closed (9:15 AM - 3:30 PM IST only)")
    print(f"   2. WebSocket connection failed")
    print(f"   3. Subscription didn't work")
    print(f"   4. API permissions issue")

print("\n" + "=" * 70)
