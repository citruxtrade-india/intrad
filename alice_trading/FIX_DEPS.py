import os
import subprocess
import sys

def run_cmd(cmd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    else:
        print(result.stdout)
    return result.returncode == 0

def fix():
    print("🔍 Fixer for WebSocket Library Conflict & Dependencies")
    print("=" * 60)
    
    # 1. Force uninstall problematic packages
    run_cmd("pip uninstall websocket websocket-client pya3 -y")
    
    # 2. Install pya3 without dependencies
    run_cmd("pip install pya3==1.0.8 --no-deps")
    
    # 3. Install core dependencies manually
    run_cmd("pip install websocket-client==1.6.4 requests pandas pyotp python-dotenv fastapi uvicorn google-generativeai pydantic")
    
    # 4. Verify
    print("\n✅ Verification:")
    try:
        import websocket
        if hasattr(websocket, 'WebSocketApp'):
            print("🚀 websocket.WebSocketApp is FOUND! Fix Successful.")
        else:
            print("❌ websocket.WebSocketApp is STILL MISSING.")
    except ImportError:
        print("❌ websocket library NOT FOUND.")
    
    print("\n✅ Pulling latest code fixes...")
    run_cmd("git pull origin main")
    
    print("\n🎉 DONE! Now run: python3 main.py")

if __name__ == "__main__":
    fix()
