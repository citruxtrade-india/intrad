
import datetime
import json
from collections import defaultdict
from .manager import AgentEvent

class LearningEngine:
    """
    Meta-Intelligence & System Awareness organism.
    Think -> Learn -> Predict -> Self-Aware.
    🧬 Real-time self-diagnostic and global risk governor.
    """
    def __init__(self, manager):
        self.manager = manager
        self.trade_history = []
        self.win_rate_by_strategy = defaultdict(lambda: {"wins": 0, "total": 0, "rate": 0.0})
        self.win_rate_by_market = defaultdict(lambda: {"wins": 0, "total": 0, "rate": 0.0})
        self.win_rate_by_pattern = defaultdict(lambda: {"wins": 0, "total": 0, "rate": 0.0})
        
        # Meta-Intelligence Stats
        self.health_score = 100    # 0-100 Diagnostic health
        self.confidence_index = 1.0 # 0-1.0 Execution confidence
        self.system_mode = "BALANCED" # AGGRESSIVE | BALANCED | DEFENSIVE
        self.market_opportunity = "NORMAL" # LOW | NORMAL | HIGH
        
        self.loss_streak = 0
        self.conservative_mode = False
        self.global_risk_multiplier = 1.0
        self.skipped_trades = []

    def get_status(self):
        """Interface compatibility for AgentManager."""
        return f"ACTIVE | {self.system_mode}"

    def compute_system_health(self):
        """
        Self-Diagnostic Engine.
        Analyzes recent win rates and drawdown to determine machine health.
        """
        recent = self.trade_history[-10:] if self.trade_history else []
        if not recent: return 100
        
        wins = len([t for t in recent if t["result"] == "WIN"])
        win_rate = wins / len(recent)
        
        # Health = Weighted Win Rate + Loss Streak penalty
        health = (win_rate * 100) - (self.loss_streak * 15)
        self.health_score = max(0, min(100, int(health)))
        
        # Determine System Mode
        if self.health_score < 45:
            self.system_mode = "DEFENSIVE"
            self.global_risk_multiplier = 0.4
        elif self.health_score > 75 and self.loss_streak == 0:
            self.system_mode = "AGGRESSIVE" 
            self.global_risk_multiplier = 1.2
        else:
            self.system_mode = "BALANCED"
            self.global_risk_multiplier = 1.0
            
        return self.health_score

    def update_market_opportunity(self, volatility, trend_strength):
        """
        Analyzes macro context to determine opportunity index.
        """
        if volatility == "Low" and trend_strength < 0.3:
            self.market_opportunity = "LOW"
        elif volatility == "Volatile":
            self.market_opportunity = "NORMAL" # Wait for stabilization
        else:
            self.market_opportunity = "HIGH"
        return self.market_opportunity

    def record_outcome(self, symbol, strategy, market_mode, result, pnl, rr=1.2, pattern=None):
        result = result.upper()
        outcome = {
            "symbol": symbol, "strategy": strategy, "market_mode": market_mode,
            "pattern": pattern or "DEFAULT", "result": result, "pnl": round(pnl, 2),
            "rr": rr, "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.trade_history.append(outcome)
        
        # Update Analytics
        for d, k in [(self.win_rate_by_strategy, strategy), 
                     (self.win_rate_by_market, market_mode),
                     (self.win_rate_by_pattern, pattern or "DEFAULT")]:
            s = d[k]
            s["total"] += 1
            if result == "WIN": s["wins"] += 1
            s["rate"] = round(s["wins"] / s["total"], 2)

        # Update Streak and Re-calculate Health
        if result == "LOSS": self.loss_streak += 1
        else: self.loss_streak = 0
        
        self.compute_system_health()
        
        # Meta-Aware Audit
        self.manager.emit_event(AgentEvent(
            symbol=symbol, agent_name="MetaIntelligence", state="NEUTRAL",
            reason=f"System Self-Diagnostic: Health {self.health_score}% | Mode: {self.system_mode}",
            context={
                "health": self.health_score, "mode": self.system_mode,
                "global_multiplier": self.global_risk_multiplier
            },
            confidence=100
        ))

    def compute_trade_score(self, base_confidence, strategy, market_mode, pattern=None):
        """
        Meta-Aware Scoring System.
        """
        score = base_confidence
        pattern = pattern or "DEFAULT"
        
        # 1. Pattern & Strategy Bias (as before)
        p_rate = self.win_rate_by_pattern[pattern]["rate"]
        if self.win_rate_by_pattern[pattern]["total"] >= 3:
            score += 15 if p_rate > 0.70 else (-20 if p_rate < 0.40 else 0)

        # 2. System State Bias
        if self.system_mode == "DEFENSIVE":
            score -= 15 # Double penalty for defense
        elif self.system_mode == "AGGRESSIVE":
            score += 5 # Favor execution in winning streaks
            
        # 3. Opportunity Restriction
        if self.market_opportunity == "LOW":
            score -= 30 # Harsh penalty for grinding markets
            
        return max(0, min(100, int(score)))

    def log_skip(self, symbol, reason, strategy, market_mode, score):
        # same as before...
        skip_entry = {
            "symbol": symbol, "reason": reason, "score": score,
            "system_health": self.health_score, "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.skipped_trades.append(skip_entry)
        self.manager.emit_event(AgentEvent(
            symbol=symbol, agent_name="MetaIntelligence", state="REJECTED",
            reason=f"Meta Skip: {reason} (Health: {self.health_score}%)",
            context={"score": score, "health": self.health_score}, payload=skip_entry,
            confidence=100
        ))

    def get_intelligence_summary(self):
        return {
            "health_score": self.health_score,
            "system_mode": self.system_mode,
            "market_opportunity": self.market_opportunity,
            "win_rate_by_strategy": dict(self.win_rate_by_strategy),
            "total_trades": len(self.trade_history)
        }
