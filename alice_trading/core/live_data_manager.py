
import asyncio
import time
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from .broker_adapter import AliceBlueAdapter, BrokerDataAdapter, BrokerFactory

class LiveDataManager:
    """
    Multi-Tenant Live Data Manager for Anti-Gravity.
    Handles independent broker connections and data loops for multiple traders.
    """
    _instances = {}

    def __new__(cls, user_id="default", broker_name="ALICE_BLUE"):
        if user_id not in cls._instances:
            instance = super(LiveDataManager, cls).__new__(cls)
            instance._initialized = False
            instance.user_id = user_id
            instance.broker_name = broker_name
            cls._instances[user_id] = instance
        return cls._instances[user_id]

    def __init__(self, user_id="default", broker_name="ALICE_BLUE"):
        if getattr(self, "_initialized", False): return
        self._initialized = True
        
        # State Management
        self.status = "DISCONNECTED" # DISCONNECTED, CONNECTING, CONNECTED, RECONNECTING
        self.broker_name = broker_name
        self.last_update = None
        self.subscriptions = []
        self.market_cache: Dict[str, Dict[str, Any]] = {}
        self.token_to_symbol: Dict[str, str] = {} # Map token -> name
        self.lock = asyncio.Lock()
        
        # Internal Event Handlers
        self.callbacks: List[Callable] = []
        self.events: Dict[str, asyncio.Event] = {}
        
        # Connection Lifecycle
        self.adapter: Optional[BrokerDataAdapter] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._watchdog_task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Config (will be set from environment or user)
        self.credentials = {}
        
        # Pre-populate common mappings to prevent "UNKNOWN" labels
        # ... (rest of __init__)
        self.token_to_symbol.update({
            "26000": "NIFTY 50",
            "26009": "NIFTY BANK",
            "30": "SENSEX",
            "1": "SENSEX", # Fallback for BSE token 1
            "1394": "HINDUNILVR",
            "1333": "HDFCBANK",
            "1594": "INFY",
            "1348": "HEROMOTOCO"
        })
        
        print(f"[LDM] LiveDataManager initialized for {user_id} ({self.broker_name}).")

    def register_token_mapping(self, token: Any, symbol_name: str):
        """Register a token to symbol mapping externally"""
        self.token_to_symbol[str(token)] = str(symbol_name)
        print(f"[LDM] Token {token} mapped to {symbol_name}")

    def set_credentials(self, user_id, api_key, totp_secret, **kwargs):
        """Generic credentials setter."""
        self.credentials = {
            "user_id": str(user_id).strip(),
            "api_key": str(api_key).strip(),
            "totp_secret": str(totp_secret).strip(),
            **kwargs
        }

    def register_callback(self, func: Callable):
        if func not in self.callbacks:
            self.callbacks.append(func)

    async def start(self, symbols: List[Dict[str, Any]]):
        """Connect and subscribe"""
        async with self.lock:
            if self.status in ["CONNECTED", "CONNECTING"]:
                print("[LDM] Already active or connecting.")
                return

            # Capture loop for thread-safe callbacks
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                pass

            self.status = "CONNECTING"
            self.subscriptions = symbols
            
            # Update token mapping
            for s in symbols:
                if s.get("token") and s.get("name"):
                    self.token_to_symbol[str(s["token"])] = s["name"]
            
            # Use Factory to get adapter
            self.adapter = BrokerFactory.get_adapter(
                broker_name=self.broker_name,
                credentials=self.credentials,
                callback=self._handle_raw_tick,
                on_disconnect=self._on_adapter_disconnect
            )

        # Start Watchdog if NOT started
        wt = self._watchdog_task
        if not wt or wt.done():
            self._watchdog_task = asyncio.create_task(self._watchdog_loop())


        # Attempt Connection
        connected = await self.adapter.connect()
        
        async with self.lock:
            if connected:
                self.status = "CONNECTED"
                print("[LDM] Connection established.")
                # Perform Subscriptions
                await self.adapter.subscribe(self.subscriptions)
            else:
                self.status = "DISCONNECTED"
                print("[LDM] Connection failed.")
                # Start reconnection task in background
                asyncio.create_task(self._reconnect_loop())

    async def stop(self):
        """Shutdown connection"""
        async with self.lock:
            self.status = "DISCONNECTED"
            if self.adapter:
                await self.adapter.disconnect()
            
            # Cancel tasks
            if self._reconnect_task:
                self._reconnect_task.cancel()
                self._reconnect_task = None
            if self._watchdog_task:
                self._watchdog_task.cancel()
                self._watchdog_task = None

            self.market_cache.clear()
            self.subscriptions = []
            print("[LDM] Shutdown complete.")

    async def subscribe_symbol(self, symbol_config: Dict[str, Any]):
        """Dynamically add a symbol to current subscription list"""
        async with self.lock:
            # Check if already subscribed
            if any(s.get('token') == symbol_config.get('token') for s in self.subscriptions):
                return
            self.subscriptions.append(symbol_config)
            
            # Update token mapping
            if symbol_config.get("token") and symbol_config.get("name"):
                self.token_to_symbol[str(symbol_config["token"])] = symbol_config["name"]
            if self.adapter and self.status == "CONNECTED":
                await self.adapter.subscribe([symbol_config])

    async def unsubscribe_symbol(self, token: int):
        """Remove a symbol from current subscription list"""
        async with self.lock:
            self.subscriptions = [s for s in self.subscriptions if s.get('token') != token]
            # Adapter usually doesn't support easy unsubscription in older pya3, 
            # but we update our internal tracking.
            if self.adapter and self.status == "CONNECTED":
                # We could call unsubscribe if implemented, but often it's ignored.
                pass

    async def fetch_snapshot(self, exchange: str, token: int, symbol_name: str) -> Optional[Dict[str, Any]]:
        """Force an immediate REST snapshot fetch and update cache"""
        if not self.adapter:
            return None
        
        snap = await self.adapter.get_snapshot(exchange, token)
        if snap:
            tick_data = {
                **snap,
                "timestamp": datetime.now().isoformat(),
                "status": "LIVE"
            }
            async with self.lock:
                self.market_cache[symbol_name] = tick_data
            
            # Bridge to callbacks if needed
            pseudo_msg = {"tk": token, "ts": symbol_name, "lp": snap["ltp"], "v": snap["volume"], "c": snap["close"]}
            for cb in self.callbacks:
                try: cb(pseudo_msg)
                except: pass
                
            return tick_data
        return None

    def _handle_raw_tick(self, message):
        """Standard tick processing bridged from Adapter"""
        if isinstance(message, str):
            try:
                message = json.loads(message)
            except:
                return

        if not isinstance(message, dict):
            return

        # Skip control messages (e.g. {"t": "ck", "s": "OK"})
        if message.get("t") == "ck":
            return

        # Extract basic info
        token = message.get("tk")
        
        # ALWAYS resolve symbol from our token_to_symbol map first (UI key names)
        # Broker 'ts' field has names like 'HDFCBANK-EQ', 'GOLD02APR26', etc.
        # Index instruments (NIFTY/BANKNIFTY/SENSEX) have NO 'ts' at all.
        symbol = self.token_to_symbol.get(str(token))
        if not symbol:
            # Last resort: use broker ts field as fallback
            symbol = message.get("ts", str(token))
        message["ts"] = symbol  # Inject resolved UI key for callbacks
        
        lp = message.get("lp")
        tick_data = {
            "ltp": float(lp) if lp is not None and str(lp) != "0" else None,
            "bid": float(message.get("bp1")) if message.get("bp1") else None,
            "ask": float(message.get("sp1")) if message.get("sp1") else None,
            "volume": float(message.get("v", 0)),
            "timestamp": datetime.now().isoformat(),
            "raw": message
        }

        if tick_data["ltp"] is None: return

        # Update Cache
        self.market_cache[symbol] = tick_data
        self.last_update = datetime.now().isoformat()
        
        # Trigger event if anyone is waiting
        if symbol in self.events:
            self.events[symbol].set()

        # Update legacy DataBus for backward compatibility
        try:
            from shared.data_bus import DataBus
            DataBus().update_data(symbol, tick_data)
        except:
            pass

        # Execute Callbacks
        for cb in self.callbacks:
            try:
                cb(message)
            except Exception as e:
                print(f"[LDM] Callback error: {e}")

    def _on_adapter_disconnect(self):
        """Sync callback from adapter (usually from a thread)"""
        print("[LDM] Adapter reported disconnection.")
        loop = self._loop
        if loop and loop.is_running():
            loop.call_soon_threadsafe(lambda: asyncio.create_task(self._trigger_reconnect()))
        else:
            print("[LDM] No active loop to trigger reconnection.")


    async def _trigger_reconnect(self):
        """Async trigger to start reconnection loop safely"""
        async with self.lock:
            if self.status in ["RECONNECTING", "CONNECTING"]:
                return
            
            print("[LDM] Triggering automatic reconnection...")
            self.status = "DISCONNECTED"
            
            rt = self._reconnect_task
            if not rt or rt.done():
                self._reconnect_task = asyncio.create_task(self._reconnect_loop())


    async def _watchdog_loop(self):
        """Monitor feed health and trigger reconnect if silent for too long"""
        while True:
            try:
                await asyncio.sleep(10)
                last_up = self.last_update
                if self.status == "CONNECTED" and last_up:
                    last_ts = datetime.fromisoformat(last_up)
                    silence_duration = (datetime.now() - last_ts).total_seconds()

                    
                    if silence_duration > 60: # 60 seconds of silence
                        print(f"[LDM] Heartbeat timeout: {silence_duration:.1f}s of silence. Reconnecting...")
                        await self._trigger_reconnect()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[LDM] Watchdog error: {e}")
                await asyncio.sleep(5)

    async def _reconnect_loop(self):
        """Exponential backoff reconnection with subscription restoration"""
        delays = [1, 2, 5, 10, 30]
        idx = 0
        
        while self.status == "DISCONNECTED":
            wait_time = delays[idx]
            print(f"[LDM] Reconnection attempt in {wait_time}s...")
            await asyncio.sleep(wait_time)
            
            idx = min(idx + 1, len(delays) - 1)
            
            # Check if someone else stopped the manager
            if self.status != "DISCONNECTED": 
                print(f"[LDM] Reconnect logic aborted. Status is {self.status}")
                break
            
            async with self.lock:
                self.status = "RECONNECTING"
            
            try:
                print("[LDM] Attempting to reconnect adapter...")
                connected = await self.adapter.connect()
                
                async with self.lock:
                    if connected:
                        self.status = "CONNECTED"
                        print("[LDM] Reconnected successfully. Restoring subscriptions...")
                        # Re-subscribe to ALL symbols in our list
                        if self.subscriptions:
                            await self.adapter.subscribe(self.subscriptions)
                        print(f"[LDM] Restored {len(self.subscriptions)} subscriptions.")
                        break
                    else:
                        self.status = "DISCONNECTED"
                        print("[LDM] Reconnection attempt failed.")
            except Exception as e:
                async with self.lock:
                    self.status = "DISCONNECTED"
                print(f"[LDM] Error during reconnection: {e}")

    def get_status(self):
        return {
            "status": self.status,
            "last_update": self.last_update,
            "cache_size": len(self.market_cache)
        }

    def get_market_snapshot(self, symbol: str = None):
        if symbol:
            return self.market_cache.get(symbol)
        return self.market_cache

    async def wait_for_symbol_data(self, symbol: str, timeout: float = 3.0) -> bool:
        """Wait for symbol data to appear in cache."""
        if symbol in self.market_cache and self.market_cache[symbol].get("ltp") is not None:
            return True
            
        if symbol not in self.events:
            self.events[symbol] = asyncio.Event()
            
        try:
            await asyncio.wait_for(self.events[symbol].wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False
        finally:
            # We keep the event for future waiters or clean up
            pass
