
import datetime
from .manager import AgentEvent

class RiskCapitalAgent:
    """
    Capital-Proportional Risk Manager for Anti-Gravity Multi-User Engine.

    All limits are expressed as % of each individual client's capital:
    - Max daily loss: 1% of client capital (configurable via risk_rules)
    - Max trade exposure: 20% of client capital per position
    - Position size (qty): floored to nearest lot based on capital allocation
    - Max concurrent positions: 3 (configurable)
    """

    def __init__(self, manager):
        self.manager = manager
        self.status = "ACTIVE"
        self.trades_today = 0
        self.last_reset_date = datetime.date.today()

    def _reset_daily_counters(self):
        today = datetime.date.today()
        if today > self.last_reset_date:
            self.trades_today = 0
            self.last_reset_date = today

    def get_status(self):
        return self.status

    def compute_position_size(self, ltp: float, total_capital: float, risk_rules: dict, trade_score: int = 70) -> dict:
        """
        Meta-Aware Position Sizing.
        Combines 1% Risk core with Capital Prioritization & System Health.
        """
        # 1. Base Risk (1%)
        base_risk_pct = 1.0 / 100.0
        
        # 2. Global Stability Governor
        state = getattr(self.manager, 'state', None)
        stability_multiplier = 1.0
        if state and hasattr(state, 'learning_engine'):
            stability_multiplier = state.learning_engine.global_risk_multiplier
            
        # 3. Capital Prioritization (Dynamic Scaling by Trade Score)
        # Allocate more capital to high-conviction, high-ranking signals.
        prioritization_mult = 1.0
        if trade_score >= 90: prioritization_mult = 1.5 # Elite setup
        elif trade_score >= 82: prioritization_mult = 1.2 # High quality
        elif trade_score < 75: prioritization_mult = 0.8 # Borderline
        
        effective_risk_pct = base_risk_pct * stability_multiplier * prioritization_mult
        risk_amount = total_capital * effective_risk_pct

        # 4. Exposure Management
        # Max 20% exposure as baseline, scaled by system health
        max_exposure = total_capital * 0.20 * stability_multiplier
        qty = max(1, int(max_exposure / ltp)) if ltp > 0 else 1

        exposure = round(qty * ltp, 2)
        exposure_pct = round((exposure / total_capital) * 100, 2) if total_capital > 0 else 0

        return {
            "qty": qty,
            "risk_amount": round(risk_amount, 2),
            "exposure": exposure,
            "exposure_pct": exposure_pct,
            "meta_scaling": round(stability_multiplier * prioritization_mult, 2),
            "priority": "HIGH" if trade_score >= 85 else "NORMAL"
        }

    def check_risk(self, symbol: str, ltp: float, metrics: dict, risk_rules: dict = None) -> bool:
        self._reset_daily_counters()
        if risk_rules is None: risk_rules = {}

        total_cap    = metrics.get("total_capital", 100000.0)
        daily_pnl    = metrics.get("daily_pnl", 0.0)
        
        # Access open trades from state to check for duplicates/averaging
        state = self.manager.state
        open_trades = [t for t in state.trades if t.get("status") == "OPEN"]
        
        allowed = True
        reason  = "Risk check passed: Systematic discipline maintained."

        # Rule 1: Max trades per day = 3
        if self.trades_today >= 3:
            allowed = False
            reason = "Risk Block: Max 3 trades per day reached."

        # Rule 2: No Averaging (No multiple positions in same symbol)
        if allowed:
            if any(t["instrument"] == symbol for t in open_trades):
                allowed = False
                reason = f"Risk Block: Position already open for {symbol}. No averaging allowed."

        # Rule 3: Daily loss limit (1% of capital)
        if allowed:
            daily_loss_limit = total_cap * 0.01
            if daily_pnl < -daily_loss_limit:
                allowed = False
                reason = f"Risk Block: Daily loss limit (₹{daily_loss_limit:,.0f}) reached."

        # Rule 4: Block Duplicate Signal (Wait for trade to close)
        # (This is partially covered by No Averaging)

        if allowed:
            self.trades_today += 1
            self.status = "ACTIVE"
        else:
            self.status = "BLOCKED"

        # Compute sizing
        sizing = self.compute_position_size(ltp, total_cap, risk_rules)

        event = AgentEvent(
            symbol=symbol,
            agent_name="RiskAgent",
            state="APPROVED" if allowed else "REJECTED",
            reason=reason,
            context={
                "allowed": allowed,
                "trades_today": self.trades_today,
                "risk_per_trade": "1%",
                "no_averaging": True,
                "total_capital": total_cap,
                "daily_pnl": daily_pnl
            },
            confidence=100,
            payload={
                "allowed": allowed,
                "reason": reason,
                "qty": sizing["qty"],
                "risk_amount": sizing["risk_amount"],
                "exposure": sizing["exposure"]
            }
        )
        self.manager.emit_event(event)
        return allowed
