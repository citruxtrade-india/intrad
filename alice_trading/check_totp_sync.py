import os
import time
import pyotp
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

secret = os.getenv("ALICEBLUE_TOTP_SECRET")
if secret:
    totp = pyotp.TOTP(secret)
    now = datetime.now()
    print(f"Current System Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Generated TOTP: {totp.now()}")
    # Check if a code from 30 seconds ago or 30 seconds from now would be different
    print(f"TOTP (-30s): {totp.at(time.time() - 30)}")
    print(f"TOTP (+30s): {totp.at(time.time() + 30)}")
else:
    print("ALICEBLUE_TOTP_SECRET not found in .env")
