
import asyncio
import datetime
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

# Import centralized pya3 patching utility
from .pya3_utils import Aliceblue, LiveFeedType


class BrokerDataAdapter(ABC):
    @abstractmethod
    async def connect(self) -> bool:
        return False


    @abstractmethod
    async def disconnect(self):
        pass

    @abstractmethod
    async def subscribe(self, symbols: List[Dict[str, Any]]):
        pass

    @abstractmethod
    async def unsubscribe(self, symbols: List[Dict[str, Any]]):
        pass

    @abstractmethod
    async def get_balance(self) -> float:
        return 0.0

class AliceBlueAdapter(BrokerDataAdapter):
    def __init__(self, user_id, api_key, totp_secret, callback, on_disconnect=None):
        self.user_id = user_id
        self.api_key = api_key
        self.totp_secret = totp_secret
        self.callback = callback
        self.on_disconnect = on_disconnect
        self.alice: Optional[Aliceblue] = None
        self.is_connected = False

    async def connect(self) -> bool:
        import pyotp
        # Ensure we don't have stale threads/connections
        await self.disconnect()
        
        try:
            print(f"[ADAPTER] Authenticating user {self.user_id}...")
            alice_client = Aliceblue(user_id=self.user_id, api_key=self.api_key)
            self.alice = alice_client
            
            # Use pyotp to get current TOTP
            otp = pyotp.TOTP(self.totp_secret).now()
            print(f"[ADAPTER] Generated OTP: {otp}")
            
            session_res = alice_client.get_session_id(otp)
            print(f"[ADAPTER] Session Result: {session_res}")
            
            if not session_res or not isinstance(session_res, dict) or not session_res.get("sessionID"):
                print(f"[ADAPTER] Login failed or returned invalid response: {session_res}")
                return False
            
            # Set session ID explicitly if library doesn't
            if getattr(alice_client, 'session_id', None) is None:
                alice_client.session_id = session_res.get('sessionID')
            
            print(f"[ADAPTER] Authentication successful. Session: {alice_client.session_id}")
            
            # Manual WebSocket implementation to bypass broken pya3 version hardcoded to UAT
            import hashlib
            import websocket
            import threading
            
            # Calculate ENC token expected by Alice Blue WebSocket
            # Formula: SHA256(SHA256(session_id))
            sha256_enc1 = hashlib.sha256(alice_client.session_id.encode('utf-8')).hexdigest()
            self.enc_token = hashlib.sha256(sha256_enc1.encode('utf-8')).hexdigest()
            
            # Production WebSocket URL
            ws_url = "wss://ws1.aliceblueonline.com/NorenWS/"
            print(f"[ADAPTER] Connecting to Production WebSocket: {ws_url}")
            
            def run_websocket():
                self.ws_app = websocket.WebSocketApp(
                    ws_url,
                    on_open=self._on_ws_open,
                    on_message=self._on_ws_message,
                    on_error=self._on_ws_error,
                    on_close=self._on_ws_close
                )
                # Hardened for AWS EC2: 
                # ping_interval=20 sends a ping every 20s to stay under AWS NAT 350s timeout.
                # ping_timeout=10 closes the socket if no pong is received in 10s.
                self.ws_app.run_forever(ping_interval=20, ping_timeout=10)

            self.ws_thread = threading.Thread(target=run_websocket, daemon=True)
            self.ws_thread.start()
            print("[ADAPTER] WebSocket thread started.")
            
            # Wait for connection (up to 15 seconds)
            for i in range(30):
                if self.is_connected: 
                    print(f"[ADAPTER] WebSocket open confirmed after {(i+1)*0.5:.1f}s")
                    break
                await asyncio.sleep(0.5)
            
            if not self.is_connected:
                print("[ADAPTER] WebSocket failed to connect within timeout.")
                
            return self.is_connected
        except Exception as e:
            print(f"[ADAPTER] Connection error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _on_ws_open(self, ws):
        import json
        print("[ADAPTER] WebSocket base connection established. Sending auth...")
        init_con = {
            "susertoken": self.enc_token,
            "t": "c",
            "actid": self.user_id + "_API",
            "uid": self.user_id + "_API",
            "source": "API"
        }
        ws.send(json.dumps(init_con))

    def _on_ws_message(self, ws, message):
        import json
        try:
            data = json.loads(message)
            if data.get("s") == "OK" and data.get("t") == "ck":
                self.is_connected = True
                print("[ADAPTER] WebSocket Authentication Successful")
            else:
                # Forward feed data to the callback
                if self.callback:
                    self.callback(data)
        except Exception as e:
            print(f"[ADAPTER] Error processing message: {e}")

    def _on_ws_error(self, ws, error):
        print(f"[ADAPTER] WebSocket Error: {error}")
        self.is_connected = False

    def _on_ws_close(self, ws, close_status, close_msg):
        print(f"[ADAPTER] WebSocket Closed: {close_status} - {close_msg}")
        self.is_connected = False
        if self.on_disconnect:
            try:
                self.on_disconnect()
            except:
                pass

    def _on_open(self):
        self.is_connected = True
        print("[ADAPTER] WebSocket Connected")

    def _on_close(self):
        self.is_connected = False
        print("[ADAPTER] WebSocket Closed")
        if self.on_disconnect:
            try:
                self.on_disconnect()
            except Exception as e:
                print(f"[ADAPTER] Error calling on_disconnect: {e}")

    def _on_error(self, error):
        print(f"[ADAPTER] WebSocket Error: {error}")
        self.is_connected = False
        if self.on_disconnect:
            try:
                self.on_disconnect()
            except Exception as e:
                print(f"[ADAPTER] Error calling on_disconnect: {e}")

    async def disconnect(self):
        if hasattr(self, 'ws_app') and self.ws_app:
            try:
                self.ws_app.close()
            except:
                pass
        if self.alice:
            try:
                # Try multiple possible library method names just in case
                stopper = getattr(self.alice, "stop_websocket", None) or getattr(self.alice, "close_websocket", None)
                if callable(stopper):
                    stopper()
            except Exception as e:
                print(f"[ADAPTER] Error during disconnect: {e}")
        self.is_connected = False

    async def subscribe(self, symbols: List[Dict[str, Any]]):
        alice_client = self.alice
        if not alice_client or not self.is_connected:
            print(f"[ADAPTER] Cannot subscribe: alice={bool(alice_client)}, connected={self.is_connected}")
            return

        instruments = []
        for sym in symbols:
            try:
                exchange = sym.get("exchange", "NSE")
                token = sym.get("token")
                name = sym.get("name", str(token))
                
                instrument = alice_client.get_instrument_by_token(exchange, token)

                if instrument:
                    instruments.append(instrument)
                    print(f"[ADAPTER] Resolved instrument for {name} ({exchange}:{token}): {instrument}")
                else:
                    print(f"[ADAPTER] WARNING: Could not resolve instrument for {name} ({exchange}:{token})")
            except Exception as e:
                print(f"[ADAPTER] Instrument resolution error for {sym}: {e}")
        
        if instruments:
            try:
                # Send manual subscription message since we are controlling the socket
                import json
                sub_params = ""
                for i, inst in enumerate(instruments):
                    end_point = "" if i == len(instruments)-1 else "#"
                    # Handle both dictionary-like and object-like instruments (pya3 returns Instrument object)
                    exch = getattr(inst, 'exchange', getattr(inst, 'exch', 'NSE'))
                    token = getattr(inst, 'token', '')
                    sub_params += f"{exch}|{token}{end_point}"
                
                if sub_params:
                    sub_message = {
                        "t": "t",
                        "k": sub_params,
                        "m": "compact_marketdata"
                    }
                    if hasattr(self, 'ws_app') and self.is_connected:
                        self.ws_app.send(json.dumps(sub_message))
                        print(f"[ADAPTER] Manually sent subscription for {len(instruments)} instruments")
                
                # We also call library subscribe for state tracking if it doesn't crash
                try:
                    alice_client.subscribe(instruments)
                except:
                    pass
            except Exception as e:
                print(f"[ADAPTER] Subscription error: {e}")

    async def get_snapshot(self, exchange: str, token: int) -> Optional[Dict[str, Any]]:
        """Fetch a single scrip data snapshot via REST."""
        alice_client = self.alice
        if not alice_client:
            return None
        
        try:
            # get_instrument_by_token returns metadata
            inst = alice_client.get_instrument_by_token(exchange, token)
            if not inst:
                return None
                
            # get_scrip_info returns the actual REST snapshot (LTP, bid, ask, etc.)
            res = alice_client.get_scrip_info(inst)
            
            if res and isinstance(res, dict) and res.get('stat') == 'Ok':
                # Map technical fields: lp=LTP, c=Close, v=Volume
                ltp_val = float(res.get('lp', 0) or 0)
                if ltp_val <= 0: return None

                return {
                    "ltp": ltp_val,
                    "bid": float(res.get('bp1', 0) or 0),
                    "ask": float(res.get('sp1', 0) or 0),
                    "volume": float(res.get('v', 0) or 0),
                    "close": float(res.get('c', 0) or 0)
                }
        except Exception as e:
            print(f"[ADAPTER] Snapshot error: {e}")
        return None

    async def get_historical_data(self, exchange: str, token: int, timeframe: str = '5', days: int = 2) -> List[Dict[str, Any]]:
        """Fetch historical candle data via REST."""
        alice_client = self.alice
        if not alice_client:
            return []

        try:
            instrument = alice_client.get_instrument_by_token(exchange, token)
            to_datetime = datetime.datetime.now()
            from_datetime = to_datetime - datetime.timedelta(days=days)
            
            # Map timeframe names to pya3 accepted strings if needed
            interval_map = {'1m': '1', '5m': '5', '15m': '15', '1h': '60', '1d': 'D'}
            interval = interval_map.get(timeframe.lower(), timeframe)

            res = alice_client.get_historical(instrument, from_datetime, to_datetime, interval)

            
            if res and isinstance(res, list):
                # Standardize keys: open, high, low, close, volume, timestamp
                candles = []
                for r in res:
                    candles.append({
                        "timestamp": r.get('datetime'),
                        "open": float(r.get('open')),
                        "high": float(r.get('high')),
                        "low": float(r.get('low')),
                        "close": float(r.get('close')),
                        "volume": float(r.get('volume', 0))
                    })
                return candles
        except Exception as e:
            print(f"[ADAPTER] Historical data error: {e}")
        return []

    async def get_balance(self) -> Optional[float]:
        """Fetch real-time account cash balance via Alice Blue REST."""
        alice_client = self.alice
        if not alice_client:
            return None
        try:
            # pya3 returns a list of dictionaries (one per segment or 'ALL')
            res = alice_client.get_balance()
            if isinstance(res, list):
                for margin in res:
                    if margin.get('stat') == 'Ok' and margin.get('symbol') == 'ALL':
                        # Use cashmarginavailable as the primary funding indicator
                        return float(margin.get('cashmarginavailable', 0) or 0)
            elif isinstance(res, dict) and res.get('stat') == 'Ok':
                return float(res.get('cashmarginavailable', 0) or 0)
        except Exception as e:
            print(f"[ADAPTER] Alice Blue balance fetch error: {e}")
        return None

    async def unsubscribe(self, symbols: List[Dict[str, Any]]):
        # pya3 doesn't have a direct unsubscribe for all, but we can try
        pass

class MockAdapter(BrokerDataAdapter):
    """Fallback adapter for unsupported brokers or testing."""
    def __init__(self, broker_name, callback, **kwargs):
        self.broker_name = broker_name
        self.callback = callback
        self.is_connected = False

    async def connect(self) -> bool:
        print(f"[ADAPTER] Connecting to MOCK broker: {self.broker_name}")
        await asyncio.sleep(0.5)
        self.is_connected = True
        return True

    async def disconnect(self):
        self.is_connected = False

    async def subscribe(self, symbols: List[Dict[str, Any]]):
        print(f"[ADAPTER] Mock subscription for {len(symbols)} symbols")

    async def unsubscribe(self, symbols: List[Dict[str, Any]]):
        pass

class BrokerFactory:
    """Universal factory to instantiate the correct broker adapter."""
    @staticmethod
    def get_adapter(broker_name: str, credentials: Dict[str, Any], callback, on_disconnect=None) -> BrokerDataAdapter:
        name = str(broker_name).upper()
        
        if name == "ALICE_BLUE":
            return AliceBlueAdapter(
                user_id=credentials.get("user_id"),
                api_key=credentials.get("api_key"),
                totp_secret=credentials.get("totp_secret"),
                callback=callback,
                on_disconnect=on_disconnect
            )
        
        # Add future brokers here:
        # elif name == "ZERODHA":
        #     return ZerodhaAdapter(...)
        
        print(f"[FACTORY] WARNING: Broker '{broker_name}' not natively supported. Using MockAdapter.")
        return MockAdapter(broker_name, callback)
