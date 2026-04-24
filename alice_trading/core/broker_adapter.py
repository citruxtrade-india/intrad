
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
        from agents.auth_agent import AuthAgent
        # Ensure we don't have stale threads/connections
        await self.disconnect()
        
        try:
            print(f"[ADAPTER] Authenticating user {self.user_id} via AuthAgent...")
            auth = AuthAgent()
            # Ensure AuthAgent uses the current adapter's credentials if they differ 
            # (though they should be from env usually)
            auth.user_id = self.user_id
            auth.api_key = self.api_key
            auth.totp_secret = self.totp_secret
            
            alice_client = auth.login()
            
            if not alice_client or not alice_client.session_id:
                print(f"[ADAPTER] Login failed via AuthAgent.")
                return False
            
            self.alice = alice_client
            print(f"[ADAPTER] Authentication successful. Session: {alice_client.session_id}")
            return await self._establish_websocket()

        except Exception as e:
            print(f"[ADAPTER] Connection error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _establish_websocket(self) -> bool:
        """Set up the WebSocket using the library's built-in method."""
        try:
            alice_client = self.alice
            if not alice_client or not alice_client.session_id:
                return False

            print(f"[ADAPTER] Starting library WebSocket...")
            
            # Reset connection state
            self.is_connected = False
            
            # Start the library's WebSocket
            alice_client.start_websocket(
                socket_open_callback=self._on_library_open,
                socket_close_callback=self._on_library_close,
                socket_error_callback=self._on_library_error,
                subscription_callback=self._on_library_message,
                run_in_background=True
            )
            
            # Wait for connection confirmation (up to 15 seconds)
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
            return False

    def _on_library_open(self):
        print("[ADAPTER] WebSocket Connected (Library)")
        self.is_connected = True

    def _on_library_message(self, message):
        # Forward feed data to the callback
        if self.callback:
            self.callback(message)

    def _on_library_error(self, error):
        print(f"[ADAPTER] WebSocket Error (Library): {error}")
        self.is_connected = False

    def _on_library_close(self):
        print("[ADAPTER] WebSocket Closed (Library)")
        self.is_connected = False
        if self.on_disconnect:
            try: self.on_disconnect()
            except: pass

    async def disconnect(self):
        if self.alice:
            try:
                self.alice.stop_websocket()
            except:
                pass
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
                
                try:
                    instrument = alice_client.get_instrument_by_token(exchange, token)
                except Exception as ex:
                    print(f"[ADAPTER] Resolution exception for {name}: {ex}")
                    instrument = None

                # Fallback: Create a 'Pseudo-Instrument' if resolution failed (e.g. 405)
                # but we have the exchange and token to proceed with WebSocket.
                if not instrument or (isinstance(instrument, dict) and instrument.get('stat') == 'Not_ok'):
                    print(f"[ADAPTER] Resolution failed for {name} ({exchange}:{token}). Using virtual instrument fallback.")
                    # Create a mock instrument object with necessary attributes
                    from collections import namedtuple
                    PseudoInstrument = namedtuple('Instrument', ['exchange', 'token', 'symbol'])
                    instrument = PseudoInstrument(exchange=exchange, token=token, symbol=name)

                instruments.append(instrument)
                print(f"[ADAPTER] Ready for {name} ({exchange}:{token})")
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
