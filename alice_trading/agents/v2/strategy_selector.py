
from .manager import AgentEvent

class StrategySelector:
    """
    Lightweight Strategy Layer.
    Guides agents based on top-level market conditions.
    """
    def __init__(self, manager):
        self.manager = manager
        self.current_strategy = "NEUTRAL"
        self.status = "ACTIVE"

    def get_status(self):
        return self.status

    def analyze_and_guide(self, symbol, context_event):
        """
        Determines the optimal strategy mode based on market mood.
        This guidance is used to refine confidence or filter logic in other agents.
        """
        ctx = context_event.get("context", {})
        mood = ctx.get("market_mood", "RANGE")
        volatility = ctx.get("volatility", "Low")
        
        strategy = "WALK_AWAY" # Default safety
        reason = "Market mood is range-bound or unclear."

        if mood == "BULLISH":
            strategy = "TREND_FOLLOW_LONG"
            reason = "High probability bullish trend detected. Favoring LONG entries."
        elif mood == "BEARISH":
            strategy = "TREND_FOLLOW_SHORT"
            reason = "High probability bearish trend detected. Favoring SHORT entries."
        elif mood == "VOLATILE":
            strategy = "MEAN_REVERSION"
            reason = "Expanding range detected. Looking for mean reversion at extremes."
        elif mood == "RANGE":
            if volatility == "Low":
                strategy = "WAIT_FOR_BREAKOUT"
                reason = "Low volatility range. Awaiting institutional breakout signal."
            else:
                strategy = "SCALPING"
                reason = "High volatility range. Short-term scalp logic recommended."

        self.current_strategy = strategy
        
        # Emit strategy guidance event
        event = AgentEvent(
            symbol=symbol,
            agent_name="StrategySelector",
            state="APPROVED",
            reason=reason,
            context={
                "selected_strategy": strategy,
                "market_mood": mood,
                "volatility": volatility
            },
            confidence=100,
            payload={"strategy": strategy, "reason": reason}
        )
        self.manager.emit_event(event)
        return strategy
