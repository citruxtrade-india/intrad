
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from server import session_mgr

try:
    print("Attempting to get state for test user...")
    state = session_mgr.get_state("test@example.com")
    print("Success!")
except Exception as e:
    print(f"Failed with error: {e}")
    import traceback
    traceback.print_exc()
