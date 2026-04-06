
import datetime
import threading

class PaperTradingEngine:
    """
    Multi-User Paper Trading Engine for Anti-Gravity.
    Maintains isolated virtual accounts for multiple traders.
    """
    _instances = {}

    def __new__(cls, user_id="default"):
        if user_id not in cls._instances:
            instance = super(PaperTradingEngine, cls).__new__(cls)
            instance._initialized = False
            instance.user_id = user_id
            cls._instances[user_id] = instance
        return cls._instances[user_id]

    def __init__(self, user_id="default"):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.lock = threading.RLock()
        self.reset()

    def reset(self):
        """Reset virtual account state to initial defaults."""
        with self.lock:
            self.virtual_capital = 100000.0
            self.open_positions = {}  # {symbol: {side, qty, entry_price, timestamp}}
            self.trade_history = []
            self.realized_pnl = 0.0
            self.last_trade_id = 0

    def place_order(self, symbol, side, qty, price):
        """Simulate BUY/SELL order execution."""
        with self.lock:
            self.last_trade_id += 1
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Logic for BUY
            if side.upper() == "BUY":
                if symbol in self.open_positions:
                    # Existing position check (simple overwrite or average in complex systems)
                    # For Anti-Gravity, we'll keep it simple as requested.
                    pass
                
                self.open_positions[symbol] = {
                    "side": "LONG",
                    "qty": qty,
                    "entry_price": price,
                    "timestamp": timestamp
                }
            
            # Logic for SELL
            elif side.upper() == "SELL":
                self.open_positions[symbol] = {
                    "side": "SHORT",
                    "qty": qty,
                    "entry_price": price,
                    "timestamp": timestamp
                }

            trade_entry = {
                "id": f"PAP-{self.last_trade_id:04}",
                "symbol": symbol,
                "side": side.upper(),
                "qty": qty,
                "price": price,
                "timestamp": timestamp,
                "type": "ENTRY"
            }
            self.trade_history.append(trade_entry)
            return trade_entry

    def close_position(self, symbol, price):
        """Close an open position and realize PnL."""
        with self.lock:
            if symbol not in self.open_positions:
                return None
            
            pos = self.open_positions.pop(symbol)
            qty = pos["qty"]
            entry = pos["entry_price"]
            side = pos["side"]
            
            pnl = 0
            if side == "LONG":
                pnl = (price - entry) * qty
            else:
                pnl = (entry - price) * qty
                
            self.realized_pnl += pnl
            self.virtual_capital += pnl
            
            self.last_trade_id += 1
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            exit_entry = {
                "id": f"PAP-{self.last_trade_id:04}",
                "symbol": symbol,
                "side": "SELL" if side == "LONG" else "BUY",
                "qty": qty,
                "price": price,
                "pnl": pnl,
                "timestamp": timestamp,
                "type": "EXIT"
            }
            self.trade_history.append(exit_entry)
            return exit_entry

    def get_positions(self):
        with self.lock:
            # Include symbol in the returned position data
            return [{**pos, "symbol": sym} for sym, pos in self.open_positions.items()]

    def get_pnl(self, current_prices=None):
        """
        Calculate combined PnL.
        current_prices: Optional dict {symbol: ltp} to calculate unrealized PnL.
        """
        with self.lock:
            unrealized = 0.0
            if current_prices:
                for sym, pos in self.open_positions.items():
                    ltp = current_prices.get(sym)
                    if ltp:
                        if pos["side"] == "LONG":
                            unrealized += (ltp - pos["entry_price"]) * pos["qty"]
                        else:
                            unrealized += (pos["entry_price"] - ltp) * pos["qty"]
            
            return {
                "realized": self.realized_pnl,
                "unrealized": unrealized,
                "total": self.realized_pnl + unrealized,
                "virtual_capital": self.virtual_capital
            }

    def get_trade_log(self):
        with self.lock:
            return self.trade_history

    def get_state(self):
        """Comprehensive state for UI/API consumption."""
        with self.lock:
            return {
                "balance": self.virtual_capital,
                "realized_pnl": self.realized_pnl,
                "positions": self.open_positions,
                "history": self.trade_history
            }
