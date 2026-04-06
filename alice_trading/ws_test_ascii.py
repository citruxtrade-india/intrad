from pya3 import Aliceblue
import pyotp
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

print("ALICE BLUE WEBSOCKET TEST")

user_id = os.getenv("ALICEBLUE_USER_ID")
api_key = os.getenv("ALICEBLUE_API_KEY")
totp_secret = os.getenv("ALICEBLUE_TOTP_SECRET")

print(f"UID: {user_id}")
print(f"APK: {len(api_key) if api_key else 0}")

try:
    otp = pyotp.TOTP(totp_secret).now()
    alice = Aliceblue(user_id=user_id, api_key=api_key)
    session = alice.get_session_id(otp)
    print(f"Session: {session}")
    
    if not session or not session.get('sessionID'):
         print("LOGIN FAILED. STOPPING TEST.")
         print(f"Error: {session.get('emsg', 'No error message')}")
         exit()

    print("LOGIN SUCCESS. STARTING WS...")

    def on_open():
        print("WS OPENED")
        inst = alice.get_instrument_by_token("NSE", 26000)
        alice.subscribe([inst])
        print(f"SUBSCRIBED: {inst}")

    def on_data(msg):
        print(f"TICK: {msg}")

    def on_error(msg):
        print(f"WS ERROR: {msg}")

    def on_close():
        print("WS CLOSED")

    alice.start_websocket(
        socket_open_callback=on_open,
        socket_close_callback=on_close,
        socket_error_callback=on_error,
        subscription_callback=on_data,
        run_in_background=False
    )

except Exception as e:
    print(f"ERROR: {e}")
