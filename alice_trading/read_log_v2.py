import os

path = r"c:\Users\User\OneDrive\Pictures\Desktop\alice_trading\alice_trading\run_log.txt"
if os.path.exists(path):
    with open(path, "rb") as f:
        content = f.read()
        try:
            # Try to decode with utf-16 (it handles BOM)
            text = content.decode("utf-16")
            # Remove any special characters that might break the print
            clean_text = "".join(c for c in text if ord(c) < 128)
            print("--- LOG START ---")
            print(clean_text[-2000:])
            print("--- LOG END ---")
        except Exception as e:
            print(f"Error: {e}")
else:
    print("File not found")
