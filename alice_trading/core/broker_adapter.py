
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
            session_res = alice_client.get_session_id(pyotp.TOTP(self.totp_secret).now())
            
            if not session_res or not isinstance(session_res, dict) or not session_res.get("sessionID"):
                print(f"[ADAPTER] Login failed: {session_res}")
                return False
            
            # Set session ID explicitly if library doesn't
            if getattr(alice_client, 'session_id', None) is None:
                alice_client.session_id = session_res.get('sessionID')
            
            print("[ADAPTER] Authentication successful. Starting WebSocket...")
            
            alice_client.start_websocket(

                socket_open_callback=self._on_open,
                socket_close_callback=self._on_close,
                socket_error_callback=self._on_error,
                subscription_callback=self.callback,
                run_in_background=True
            )
            
            # Wait for connection (up to 15 seconds)
            for i in range(30):
                if self.is_connected: 
                    print(f"[ADAPTER] WebSocket open confirmed after {(i+1)*0.5:.1f}s")
                    break
                await asyncio.sleep(0.5)
            
            return self.is_connected
        except Exception as e:
            print(f"[ADAPTER] Connection error: {e}")
            import traceback
            traceback.print_exc()
            return False

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
        if self.alice:
            try:
                # Try multiple possible method names
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
                # pya3 v1.0.30: subscribe takes (self, instrument_list) only
                alice_client.subscribe(instruments)
                print(f"[ADAPTER] Subscribed to {len(instruments)} instruments successfully")
            except Exception as e:
                print(f"[ADAPTER] Subscription failed: {e}")
                # Try one-by-one as fallback
                for inst in instruments:
                    try:
                        alice_client.subscribe([inst])
                    except Exception as e2:
                        print(f"[ADAPTER] Single subscribe failed for {inst}: {e2}")



    async def get_snapshot(self, exchange: str, token: int) -> Optional[Dict[str, Any]]:
        """Fetch a single scrip data snapshot via REST."""
        alice_client = self.alice
        if not alice_client:
            return None
        
        try:
            instrument = alice_client.get_instrument_by_token(exchange, token)
            res = alice_client.get_scrip_info(instrument)

            
            if res and res.get('stat') == 'Ok':
                # Explicitly check for presence of data to avoid false 0.0
                ltp_raw = res.get('LTP')
                try:
                    ltp_val = float(ltp_raw) if ltp_raw is not None else 0.0
                except ValueError:
                    ltp_val = 0.0

                if ltp_val <= 0:
                    # Placeholder or no-data state
                    return None

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
