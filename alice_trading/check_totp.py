import os
import pyotp
import time
import datetime
from dotenv import load_dotenv

load_dotenv()

def check_totp_sync():
    secret = os.getenv("ALICEBLUE_TOTP_SECRET")
    print(f"Secret: {secret}")
    totp = pyotp.TOTP(secret)
    
    for i in range(3):
        now = datetime.datetime.now()
        token = totp.now()
        # Get the time remaining in the current 30s window
        remaining = 30 - (time.time() % 30)
        print(f"[{now.strftime('%H:%M:%S')}] Token: {token} (Remains: {remaining:.1f}s)")
        time.sleep(10)

if __name__ == "__main__":
    check_totp_sync()
