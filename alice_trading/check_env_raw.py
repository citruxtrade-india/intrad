import os
from dotenv import load_dotenv

load_dotenv()

def check_env():
    uid = os.getenv("ALICEBLUE_USER_ID")
    apk = os.getenv("ALICEBLUE_API_KEY")
    tps = os.getenv("ALICEBLUE_TOTP_SECRET")
    
    print(f"USER_ID: [{uid}] (Length: {len(uid) if uid else 0})")
    print(f"API_KEY: [{apk}] (Length: {len(apk) if apk else 0})")
    print(f"TOTP_SECRET: [{tps}] (Length: {len(tps) if tps else 0})")

if __name__ == "__main__":
    check_env()
