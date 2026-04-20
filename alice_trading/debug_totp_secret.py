import os, base64, binascii
from dotenv import load_dotenv
load_dotenv()
secret = os.getenv("ALICEBLUE_TOTP_SECRET", "").replace(" ", "").strip()
print(f"Length: {len(secret)}")
try:
    decoded = base64.b32decode(secret, casefold=True)
    print("Success")
except binascii.Error as e:
    print(f"Error: {e}")
    # Print hex of the secret to find hidden chars
    print(f"Hex: {secret.encode().hex()}")
