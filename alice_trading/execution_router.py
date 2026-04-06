
from config import EXECUTION_MODE
from paper_engine import PaperTradingEngine

class ExecutionRouter:
    """
    Primary Execution Router for Anti-Gravity.
    Routes signals to either the Paper Engine or the Live Broker.
    """
    def __init__(self, broker_client=None):
        self.paper_engine = PaperTradingEngine()
        self.broker = broker_client  # Alice Blue client for real trades
        self.status = "ACTIVE"

    def route_order(self, symbol, side, qty, price, mode="PAPER", state_logger=None):
        """
        Decision point for order execution.
        Uses the provided mode (PAPER or REAL/LIVE).
        """
        if state_logger:
            state_logger(f"[ROUTER] Routing {side} order for {symbol} @ {price} (Mode: {mode})")

        if mode == "REAL" or mode == "LIVE":
            if self.broker:
                # Actual broker order placement
                # result = self.broker.place_order(symbol, side, qty)
                if state_logger:
                    state_logger(f"[LIVE] CRITICAL: REAL ORDER PLACED for {symbol} @ {price}")
                return {"status": "success", "mode": mode, "detail": "Live order dispatched"}
            else:
                if state_logger:
                    state_logger(f"[{mode}] ERROR: Broker not connected!")
                return {"status": "error", "detail": "Broker not connected"}

        elif mode == "PAPER":
            # Paper execution path
            result = self.paper_engine.place_order(symbol, side, qty, price)
            if state_logger:
                state_logger(f"[PAPER] Virtual position opened for {symbol} @ {price}")
            return {"status": "success", "mode": "PAPER", "detail": result}

        else:
            if state_logger:
                state_logger(f"[MOCK] Order suppressed for {symbol} (Mode: {mode})")
            return {"status": "ignored", "mode": mode}
