"""
Live Tick Debugger
==================
Connects to Alice Blue, subscribes to NIFTY 50, and prints raw incoming ticks.
Run this to see EXACTLY what the broker sends in `ts` (trading symbol) field.
"""
import os, time, pyotp
from dotenv import load_dotenv

load_dotenv()
USER_ID      = os.getenv("ALICEBLUE_USER_ID","").strip()
API_KEY      = os.getenv("ALICEBLUE_API_KEY","").strip()
TOTP_SECRET  = os.getenv("ALICEBLUE_TOTP_SECRET","").strip()

# ---- pya3 patch ----
import pya3.alicebluepy
from datetime import time as dt_time
from time import sleep as t_sleep
if hasattr(pya3.alicebluepy, 'time') and not callable(pya3.alicebluepy.time):
    pya3.alicebluepy.time = dt_time
if not hasattr(pya3.alicebluepy, 'sleep'):
    pya3.alicebluepy.sleep = t_sleep

from pya3 import Aliceblue, LiveFeedType

# ---- AUTH ----
print("[1] Authenticating...")
alice = Aliceblue(user_id=USER_ID, api_key=API_KEY)
totp = pyotp.TOTP(TOTP_SECRET).now()
res  = alice.get_session_id(totp)
print(f"    Session response: {res}")
if not res or not isinstance(res, dict) or not res.get("sessionID"):
    print("[FAIL] Could not authenticate. Exiting.")
    exit(1)
if getattr(alice, 'session_id', None) is None:
    alice.session_id = res.get('sessionID')
print("[OK] Auth success!")

# ---- INSTRUMENTS ----
print("[2] Fetching instruments...")
nifty     = alice.get_instrument_by_token("NSE", 26000)     # NIFTY 50
banknifty = alice.get_instrument_by_token("NSE", 26009)     # NIFTY BANK
sensex    = alice.get_instrument_by_token("BSE", 1)          # SENSEX
hdfcbank  = alice.get_instrument_by_token("NSE", 1333)       # HDFCBANK
hindunilvr= alice.get_instrument_by_token("NSE", 1394)       # HINDUNILVR
# MCX - updated tokens (FUTCOM nearest expiry)
gold      = alice.get_instrument_by_token("MCX", 454818)     # GOLD APR26
silver    = alice.get_instrument_by_token("MCX", 451666)     # SILVER MAR26
crudeoil  = alice.get_instrument_by_token("MCX", 472789)     # CRUDEOIL MAR26
natgas    = alice.get_instrument_by_token("MCX", 475112)     # NATGASMINI MAR26

instruments = [
    ("NIFTY",      nifty),
    ("BANKNIFTY",  banknifty),
    ("SENSEX",     sensex),
    ("HDFCBANK",   hdfcbank),
    ("HINDUNILVR", hindunilvr),
    ("GOLD",       gold),
    ("SILVER",     silver),
    ("CRUDEOIL",   crudeoil),
    ("NATGASMINI", natgas),
]
print("[2] Instrument objects:")
for label, inst in instruments:
    print(f"     {label}: {inst}")

instr_list = [i[1] for i in instruments if i[1] is not None]
print(f"[2] Will subscribe {len(instr_list)} instruments")

# ---- CALLBACKS ----
tick_count = 0

def on_open():
    global tick_count
    print("[WS] Socket OPENED - subscribing now...")
    try:
        alice.subscribe(instr_list, LiveFeedType.TICK_DATA)
        print(f"[WS] Subscribed {len(instr_list)} instruments via TICK_DATA")
    except Exception as e:
        print(f"[WS] TICK_DATA subscribe failed: {e}. Trying MARKET_DATA...")
        try:
            alice.subscribe(instr_list, LiveFeedType.MARKET_DATA)
            print(f"[WS] Subscribed via MARKET_DATA")
        except Exception as e2:
            print(f"[WS] MARKET_DATA also failed: {e2}. Trying bare subscribe...")
            try:
                alice.subscribe(instr_list)
                print("[WS] Subscribed via bare subscribe")
            except Exception as e3:
                print(f"[WS] All subscribe attempts failed: {e3}")

def on_close():
    print("[WS] Socket CLOSED")

def on_error(err):
    print(f"[WS] Error: {err}")

def on_tick(msg):
    global tick_count
    tick_count += 1
    # Print first 20 ticks fully, then only every 100
    if tick_count <= 20 or tick_count % 100 == 0:
        print(f"[TICK #{tick_count}] {msg}")

print("[3] Starting WebSocket...")
alice.start_websocket(
    socket_open_callback=on_open,
    socket_close_callback=on_close,
    socket_error_callback=on_error,
    subscription_callback=on_tick,
    run_in_background=True
)

print("[4] Waiting 30 seconds for ticks...")
start = time.time()
while time.time() - start < 30:
    time.sleep(2)
    print(f"    ... {int(time.time()-start)}s elapsed | ticks received: {tick_count}")
    if tick_count >= 5:
        print("[OK] Data is flowing! Test passed.")
        break

print(f"\n[RESULT] Total ticks in 30s: {tick_count}")
if tick_count == 0:
    print("[FAIL] No ticks received. Check:")
    print("  1. Is market open? NSE: 9:15-15:30, MCX: 9:00-23:30")
    print("  2. Did authenticate require fresh daily login?")
    print("  3. Did WebSocket open callback fire?")
else:
    print("[OK] Live feed is working.")
