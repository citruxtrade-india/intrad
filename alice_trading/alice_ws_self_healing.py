import time
from alice_blue import AliceBlue

# ===== LOGIN FUNCTION =====
def login():
    print("Logging in...")
    alice = AliceBlue.login_and_get_sessionID(
        username="YOUR_ID",
        password="YOUR_PASSWORD",
        twoFA="YOUR_PIN",
        api_secret="YOUR_API_SECRET",
        app_id="YOUR_APP_ID"
    )
    print("Login successful")
    return alice


# ===== WEBSOCKET START =====
last_tick_time = time.time()

def start_websocket(alice):
    global last_tick_time

    def on_open():
        print("WebSocket Connected")

        # subscribe instruments here
        alice.subscribe(['NSE|26000'])  # example

    def on_message(message):
        global last_tick_time
        last_tick_time = time.time()

        print("Tick:", message)

        # 👉 send this to your strategy engine
        # process_market_data(message)

    def on_error(error):
        print("WebSocket Error:", error)
        raise Exception("WS Error")

    def on_close():
        print("WebSocket Closed")
        raise Exception("WS Closed")

    alice.start_websocket(
        subscribe_callback=on_message,
        socket_open_callback=on_open,
        socket_close_callback=on_close,
        socket_error_callback=on_error,
        run_in_background=False
    )


# ===== MAIN LOOP (SELF-HEALING) =====
while True:
    try:
        alice = login()
        last_tick_time = time.time()

        start_websocket(alice)

    except Exception as e:
        print("Error:", e)

    print("Reconnecting in 5 sec...")
    time.sleep(5)
