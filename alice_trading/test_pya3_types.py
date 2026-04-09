
from pya3 import Aliceblue
import pyotp
import os
import datetime
from dotenv import load_dotenv

load_dotenv()

user_id = os.getenv("ALICEBLUE_USER_ID")
api_key = os.getenv("ALICEBLUE_API_KEY")
totp_secret = os.getenv("ALICEBLUE_TOTP_SECRET")

otp = pyotp.TOTP(totp_secret).now()
alice = Aliceblue(user_id=user_id, api_key=api_key)
session_res = alice.get_session_id(otp)
print(f"Session Result: {session_res}")

session_id = session_res.get('sessionID')
print(f"Logged in: {str(session_id)[:10]}...")

nifty = alice.get_instrument_by_token("NSE", 26000)
print(f"Instrument Type: {type(nifty)}")
print(f"Instrument: {nifty}")

# Test scrip info
res = alice.get_scrip_info(nifty)
print(f"Scrip Info Type: {type(res)}")
print(f"Scrip Info: {res}")

# Test historical
to_datetime = datetime.datetime.now()
from_datetime = to_datetime - datetime.timedelta(days=1)
hist = alice.get_historical(nifty, from_datetime, to_datetime, '5')
print(f"Historical Type: {type(hist)}")
if hist and isinstance(hist, list) and len(hist) > 0:
    print(f"Single Candle Type: {type(hist[0])}")
    print(f"Single Candle: {hist[0]}")
