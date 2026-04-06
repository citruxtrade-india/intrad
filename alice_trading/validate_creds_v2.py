import os
import pyotp
import base64
from dotenv import load_dotenv

load_dotenv()

secret = os.getenv("ALICEBLUE_TOTP_SECRET")

if not secret:
    print("Error: Secret missing")
else:
    print(f"Secret: {secret[:2]}{'*' * (len(secret)-4)}{secret[-2:]}")
    print(f"Length: {len(secret)}")
    try:
        # Check if valid base32
        base64.b32decode(secret, casefold=True)
        print("Success: Valid Base32")
    except Exception as e:
        print(f"Error: Invalid Base32: {e}")

uid = os.getenv("ALICEBLUE_USER_ID")
apk = os.getenv("ALICEBLUE_API_KEY")
print(f"User ID: [{uid}]")
print(f"API Key Length: {len(apk) if apk else 0}")
