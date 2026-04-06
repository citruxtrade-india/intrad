import os

path = r"c:\Users\User\OneDrive\Pictures\Desktop\alice_trading\alice_trading\run_log.txt"
if os.path.exists(path):
    with open(path, "rb") as f:
        content = f.read()
        try:
            text = content.decode("utf-16-le")
            print(text[-2000:]) # Last 2000 chars
        except Exception as e:
            print(f"Error decoding: {e}")
            try:
                print(content.decode("utf-8")[-2000:])
            except:
                print("Could not decode even in utf-8")
else:
    print("File not found")
