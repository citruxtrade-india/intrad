import pyotp
import time
import os
from dotenv import load_dotenv

load_dotenv()

totp_secret = os.getenv("ALICEBLUE_TOTP_SECRET")
print(f"System Time: {time.ctime()}")
print(f"TOTP Secret: {totp_secret}")

if totp_secret:
    try:
        totp = pyotp.TOTP(totp_secret.strip())
        print(f"Current TOTP: {totp.now()}")
    except Exception as e:
        print(f"Error generating TOTP: {e}")
else:
    print("No TOTP Secret found.")
