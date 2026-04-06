import datetime
from .manager import AgentEvent

class ExecutionEngine:
    def __init__(self, manager):
        self.manager = manager
        self.status = "ACTIVE"
        self.last_trade_id = 0
        self.current_strategy = "TREND_FOLLOW"
        self.current_mood = "BULLISH"
        self.current_genome = "DEFAULT"

    def get_status(self):
        return self.status

    def route_execution(self, symbol, ltp, signal, state):
        """Primary router — capital-proportional position sizing per client."""
        # Compute capital-proportional quantity for this client
        from agents.v2.risk_capital import RiskCapitalAgent
        risk_agent = getattr(state, 'risk_capital_agent', None)
        if risk_agent:
            sizing = risk_agent.compute_position_size(
                ltp,
                state.metrics.get("total_capital", 100000),
                getattr(state, 'risk_rules', {}),
                trade_score=getattr(self, 'last_score_cache', 70)
            )
            qty = sizing["qty"]
        else:
            qty = 1  # Safe fallback

        side = "BUY" if "BUY" in signal.upper() or "LONG" in signal.upper() else "SELL"

        # Route to correct execution path
        mode = state.execution_mode
        if mode == "PAPER":
            return state.execution_router.route_order(symbol, side, qty, ltp, state_logger=state.add_log)
        elif mode == "REAL":
            return state.execution_router.route_order(symbol, side, qty, ltp, state_logger=state.add_log)
        elif mode == "SIMULATION":
            return self.execute_simulation(symbol, ltp, signal, state, qty=qty)
        else:  # MOCK
            return self.execute_mock(symbol, ltp, signal, state)

    def close_all_active(self, state, ltp):
        """Emergency square off - hook for learning memory."""
        with state.lock:
            for t in state.trades:
                if t["status"] == "OPEN":
                    pnl = (ltp - t["entry_price"]) * t["qty"]
                    if t["direction"] == "SHORT": pnl = -pnl
                    
                    # Update Memory with Pattern Genome
                    state.learning_engine.record_outcome(
                        t["instrument"], 
                        t.get("strategy", "TREND_FOLLOW"),
                        t.get("market_mode", "BULLISH"),
                        "WIN" if pnl > 0 else "LOSS",
                        pnl,
                        rr=1.5,
                        pattern=t.get("pattern_genome", "DEFAULT")
                    )
            state.trades = []

    def execute_mock(self, symbol, ltp, signal, state):
        state.add_log(f"[MOCK] Signal {signal} detected for {symbol} @ {ltp}. No action taken.")
        return "MOCK-MODE"

    def execute_simulation(self, symbol, ltp, signal, state, qty=1):
        return self._place_virtual_order(symbol, ltp, signal, state, "SIMULATION", qty=qty)

    def execute_paper(self, symbol, ltp, signal, state):
        return self._place_virtual_order(symbol, ltp, signal, state, "PAPER")

    def execute_real(self, symbol, ltp, signal, state):
        if not state.alice:
            state.add_log("[REAL] CRITICAL: Broker not connected. Order BLOCKED for safety.")
            return None
            
        try:
            # Placeholder for actual Alice Blue order placement
            state.add_log(f"[REAL] >>> PLACING LIVE BROKER ORDER: {symbol} | {signal} @ {ltp}")
            return "LIVE-ORD"
        except Exception as e:
            state.add_log(f"[REAL] BROKER REJECTION: {str(e)}")
            return None

    def _place_virtual_order(self, symbol, ltp, signal, state, mode_label, qty=1):
        self.last_trade_id += 1
        prefix = "SIM" if mode_label == "SIMULATION" else "PAP"
        trade_id = f"{prefix}-{self.last_trade_id:03}"
        
        # New trade object with memory metadata
        new_trade = {
            "id": trade_id,
            "instrument": symbol,
            "direction": "LONG" if signal == "BUY" else "SHORT",
            "qty": qty,
            "entry_price": ltp,
            "current_price": ltp,
            "pnl": 0.0,
            "status": "OPEN",
            "mode": mode_label,
            "strategy": self.current_strategy,
            "market_mode": self.current_mood,
            "pattern_genome": self.current_genome,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with state.lock:
            state.trades.append(new_trade)
            if len(state.trades) > 50: state.trades.pop(0)

        # Emit audit event
        self.manager.emit_event(AgentEvent(
            symbol=symbol,
            agent_name="ExecutionAgent",
            state="APPROVED",
            reason=f"Virtual order {trade_id} @ {ltp}. [LEARNING MEMORY STORED]",
            context={
                "trade_id": trade_id,
                "strategy": self.current_strategy,
                "market_mode": self.current_mood,
            },
            confidence=100
        ))
        
        state.add_log(f"[{mode_label}] Intelligence stored for {trade_id} ({self.current_strategy})")
        return trade_id
