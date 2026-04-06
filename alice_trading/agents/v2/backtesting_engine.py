import pandas as pd
import datetime
import os
import json
import logging
import typing


from .market_context import MarketContextAgent
from .structure_pattern import StructurePatternAgent
from .validation import ValidationAgent
from .risk_capital import RiskCapitalAgent
from .manager import AgentEvent

# Configure dedicated isolated logger for backtesting
bt_logger = logging.getLogger("BacktestEngine")
bt_logger.setLevel(logging.INFO)
# Avoid double logging if handlers exist
if not bt_logger.handlers:
    fh = logging.FileHandler("backtest_results.log")
    fh.setFormatter(logging.Formatter('%(message)s'))
    bt_logger.addHandler(fh)

class DummyLock:
    def __enter__(self): pass
    def __exit__(self, exc_type, exc_val, exc_tb): pass

class IsolatedState:
    """Isolated state container to perfectly mimic the real live state but safely separated."""
    def __init__(self, initial_capital):
        self.trades = []
        self.metrics = {
            "total_capital": initial_capital, 
            "used_capital_amount": 0.0,
            "daily_pnl": 0.0
        }
        self.risk_rules = {}
        self.lock = DummyLock()
        
class IsolatedManager:
    """Read-only event manager that isolates agent logic from live system events."""
    def __init__(self, state):
        self.state = state
        self.event_history = []
        
    def emit_event(self, event):
        self.event_history.append(event.to_dict())
        
    def get_audit_trail(self, limit=10):
        return self.event_history[-limit:]

class BacktestingEngine:
    """
    🧪 Data-Driven Analytical Laboratory.
    Isolated pipeline executing historical candles against current agent architecture.
    """
    def __init__(self, config=None):
        self.config = {
            "symbol": "NIFTY",
            "timeframe": "5m",
            "initial_capital": 100000.0,
            "risk_per_trade": 0.01,  # 1% risk per trade
            "stop_loss_pct": 0.005,  # 0.5% stop loss
            "target_pct": 0.01       # 1% profit target
        }
        if config:
            self.config.update(config)
            
        self.results = {
            "total_trades": 0,
            "win_rate": 0.0,
            "loss_rate": 0.0,
            "total_pnl": 0.0,
            "max_drawdown": 0.0,
            "average_rr": 0.0,
            "trades": []
        }

    def run_backtest(self, csv_path):
        """
        Main execution loop for the backtest.
        Reads historical data and runs it through the agent pipeline step-by-step.
        """
        if not os.path.exists(csv_path):
            return {"error": f"Data file {csv_path} not found. Ensure OHLC dataset exists."}

        # 1. Load Data Layer
        try:
            # Requires Date, Open, High, Low, Close, Volume
            df = pd.read_csv(csv_path)
            # Map column names if needed
            cols = [c.lower() for c in df.columns]
            if not any(k in cols for k in ['close', 'ltp', 'c']):
                 # Try skipping headers if corrupted
                 df = pd.read_csv(csv_path, skiprows=1)
            
            # Ensure chronological order
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                df = df.sort_values(by='Date')
                
        except Exception as e:
            return {"error": f"Failed to load historical data: {str(e)}"}

        # Determine target columns dynamically
        col_close = next((c for c in df.columns if 'close' in c.lower() or 'ltp' in c.lower()), df.columns[1])
        col_high = next((c for c in df.columns if 'high' in c.lower()), col_close)
        col_low = next((c for c in df.columns if 'low' in c.lower()), col_close)
        col_date = next((c for c in df.columns if 'date' in c.lower() or 'time' in c.lower()), df.columns[0])

        # 2. Setup Agent Isolation (Read-Only Logic)
        initial_capital = self.config["initial_capital"]
        state = IsolatedState(initial_capital)
        manager = IsolatedManager(state)
        
        ctx_agent = MarketContextAgent(manager)
        pattern_agent = StructurePatternAgent(manager)
        val_agent = ValidationAgent(manager)
        risk_agent = RiskCapitalAgent(manager)
        
        capital = initial_capital
        equity_curve = [capital]
        trades = []
        active_trade: typing.Optional[typing.Dict[str, typing.Any]] = None
        
        total_risk_reward = 0.0
        wins = 0
        losses = 0

        bt_logger.info(f"--- STARTING BACKTEST: {self.config['symbol']} ---")
        bt_logger.info(f"Config: {json.dumps(self.config)}")

        # 3. Simulate Candle-by-Candle Execution
        prev_close = None
        
        for i, row in df.iterrows():
            timestamp = str(row[col_date])
            close = float(row[col_close])
            high = float(row[col_high])
            low = float(row[col_low])
            
            p_close = prev_close if prev_close else close
            
            # --- AGENT PIPELINE REPLAY ---
            ctx_event = ctx_agent.process(self.config["symbol"], close, p_close)
            pattern_event = pattern_agent.process(self.config["symbol"], close)
            val_event = val_agent.validate(self.config["symbol"], close, ctx_event, pattern_event)
            
            # --- SIMULATION ENGINE ---
            if active_trade is not None:
                trade = active_trade
                # Check for Stop Loss or Target Hit
                hit_target = False
                hit_stop = False
                exit_price = 0.0
                
                if trade["direction"] == "LONG":
                    if high >= trade["target"]:
                        hit_target = True
                        exit_price = trade["target"]
                    elif low <= trade["stop_loss"]:
                        hit_stop = True
                        exit_price = trade["stop_loss"]
                else: # SHORT
                    if low <= trade["target"]:
                        hit_target = True
                        exit_price = trade["target"]
                    elif high >= trade["stop_loss"]:
                        hit_stop = True
                        exit_price = trade["stop_loss"]
                        
                # End of day / Data termination (Square off)
                if i == len(df) - 1 and not (hit_target or hit_stop):
                    exit_price = close
                    hit_target = True # Forced exit
                
                if hit_target or hit_stop:
                    # Calculate PnL
                    entry_price = float(trade["entry_price"])
                    target = float(trade["target"])
                    points = (exit_price - entry_price) if trade["direction"] == "LONG" else (entry_price - exit_price)
                    pnl = points * trade["qty"]
                    
                    trade["exit_price"] = exit_price
                    trade["pnl"] = round(float(pnl), 2)
                    trade["result"] = "WIN" if pnl > 0 else "LOSS"
                    trade["exit_time"] = timestamp

                    
                    if pnl > 0:
                        wins += 1
                        # Estimate RR ratio achieved compared to initial risk
                        initial_risk_amount = capital * self.config["risk_per_trade"]
                        if initial_risk_amount > 0:
                            total_risk_reward += (pnl / initial_risk_amount)
                    else:
                        losses += 1
                    
                    capital += pnl
                    equity_curve.append(capital)
                    trades.append(trade)
                    
                    bt_logger.info(json.dumps({
                        "time": timestamp,
                        "action": "EXIT",
                        "trade_id": trade["trade_id"],
                        "pnl": round(float(pnl), 2),
                        "result": trade["result"]
                    }))
                    
                    active_trade = None
                    state.trades = [] # Clear isolated state
            
            elif val_event.get("state") == "APPROVED":
                # Check Risk Agent permissions
                is_safe = risk_agent.check_risk(
                    self.config["symbol"], 
                    close, 
                    {"total_capital": capital, "daily_pnl": capital - initial_capital}
                )
                
                if is_safe:
                    signal = val_event['payload'].get('signal', 'BUY')
                    direction = "LONG" if signal == "BUY" else "SHORT"
                    
                    # Compute sizing
                    risk_amount = capital * self.config["risk_per_trade"]
                    sl_dist = close * self.config["stop_loss_pct"]
                    qty = int(risk_amount / sl_dist) if sl_dist > 0 else 1
                    if qty < 1: qty = 1
                    
                    # Stop & Target levels
                    sl = close - sl_dist if direction == "LONG" else close + sl_dist
                    tgt = close + (close * self.config["target_pct"]) if direction == "LONG" else close - (close * self.config["target_pct"])
                    
                    active_trade = {
                        "trade_id": f"BT_{i:04d}",
                        "symbol": self.config["symbol"],
                        "direction": direction,
                        "entry_time": timestamp,
                        "entry_price": close,
                        "stop_loss": sl,
                        "target": tgt,
                        "qty": qty,
                        "reason": val_event["reason"]
                    }
                    
                    state.trades = [active_trade] # Sync to isolation container
                    
                    bt_logger.info(json.dumps({
                        "time": timestamp,
                        "action": "ENTRY",
                        "signal": direction,
                        "entry_allowed": True,
                        "reason": active_trade["reason"],
                        "trade_id": active_trade["trade_id"]
                    }))
                else:
                    bt_logger.info(json.dumps({
                        "time": timestamp,
                        "signal": val_event['payload'].get('signal', 'BUY'),
                        "entry_allowed": False,
                        "reason": "Risk Protocol Blocked Execution"
                    }))
            
            prev_close = close

        # 4. Performance Metrics Processing
        total_trades = len(trades)
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
        loss_rate = (losses / total_trades * 100) if total_trades > 0 else 0.0
        avg_rr = (total_risk_reward / wins) if wins > 0 else 0.0
        
        # Max Drawdown
        max_seen = initial_capital
        max_dd = 0.0
        for val in equity_curve:
            if val > max_seen:
                max_seen = val
            dd = (max_seen - val) / max_seen
            if dd > max_dd:
                max_dd = dd

        self.results = {
            "total_trades": total_trades,
            "win_rate": round(float(win_rate), 2),
            "loss_rate": round(float(loss_rate), 2),
            "total_pnl": round(float(capital - initial_capital), 2),
            "max_drawdown": round(float(max_dd * 100), 2),
            "average_rr": round(float(avg_rr), 2),
            "final_capital": round(float(capital), 2),
            "trades": typing.cast(typing.List[typing.Dict[str, typing.Any]], trades[-20:]) # Return sample for JSON display
        }

        
        bt_logger.info(f"--- BACKTEST COMPLETE ---")
        bt_logger.info(json.dumps(self.results))
        
        return self.results

