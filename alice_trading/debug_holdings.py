"""
Debug script - prints raw Alice Blue holdings & positions response
"""
import os, json
from dotenv import load_dotenv
import pyotp
from pya3 import Aliceblue

load_dotenv()
user_id     = os.getenv("ALICEBLUE_USER_ID")
api_key     = os.getenv("ALICEBLUE_API_KEY")
totp_secret = os.getenv("ALICEBLUE_TOTP_SECRET")

otp = pyotp.TOTP(totp_secret).now()
alice = Aliceblue(user_id=user_id, api_key=api_key)
session_res = alice.get_session_id(otp)

if not (session_res and isinstance(session_res, dict) and session_res.get("sessionID")):
    print("LOGIN FAILED:", session_res)
    exit(1)

if getattr(alice, 'session_id', None) is None:
    alice.session_id = session_res.get('sessionID')
print(f"Logged in: {alice.session_id[:12]}...")

# --- 1. get_holdings ---
print("\n===== get_holdings() =====")
try:
    h = alice.get_holdings()
    print(f"Type: {type(h)}")
    print(json.dumps(h, indent=2, default=str))
except Exception as e:
    print(f"ERROR: {e}")

# --- 2. get_daywise_positions ---
print("\n===== get_daywise_positions() =====")
try:
    p = alice.get_daywise_positions()
    print(f"Type: {type(p)}")
    print(json.dumps(p, indent=2, default=str))
except Exception as e:
    print(f"ERROR: {e}")

# --- 3. get_netwise_positions ---
print("\n===== get_netwise_positions() =====")
try:
    n = alice.get_netwise_positions()
    print(f"Type: {type(n)}")
    print(json.dumps(n, indent=2, default=str))
except Exception as e:
    print(f"ERROR: {e}")

# --- 4. get_order_history ---
print("\n===== get_order_history('') =====")
try:
    oh = alice.get_order_history('')
    print(f"Type: {type(oh)}")
    print(json.dumps(oh, indent=2, default=str))
except Exception as e:
    print(f"ERROR: {e}")
