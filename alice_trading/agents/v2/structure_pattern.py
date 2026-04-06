
from .manager import AgentEvent
import collections

class StructurePatternAgent:
    """
    Hardened Structure Analysis Agent.
    Tracks 'Pivots' (Local Highs/Lows) in real-time to detect:
    - BOS (Break of Structure): Follow-through in trend direction.
    - CHoCH (Change of Character): Reversal/Shift in market bias.
    """
    def __init__(self, manager):
        self.manager = manager
        self.status = "ACTIVE"
        # Per-symbol state tracking
        self.market_state = collections.defaultdict(lambda: {
            "last_high": 0.0,
            "last_low": 0.0,
            "swing_highs": collections.deque(maxlen=10),
            "swing_lows": collections.deque(maxlen=10),
            "current_trend": "Neutral", 
            "history": collections.deque(maxlen=50)
        })

    def get_status(self):
        return self.status

    def _update_swings(self, symbol, ltp):
        ms = self.market_state[symbol]
        hist = list(ms["history"])
        if len(hist) < 5: return

        # Pivot detection (similar to MarketContext but for structure)
        p = hist[-3]
        if p > hist[-5] and p > hist[-4] and p > hist[-2] and p > hist[-1]:
            if not ms["swing_highs"] or abs(p - ms["swing_highs"][-1]) > (p * 0.001):
                ms["swing_highs"].append(p)
                ms["last_high"] = p
        
        if p < hist[-5] and p < hist[-4] and p < hist[-2] and p < hist[-1]:
            if not ms["swing_lows"] or abs(p - ms["swing_lows"][-1]) > (p * 0.001):
                ms["swing_lows"].append(p)
                ms["last_low"] = p

    def process(self, symbol, ltp):
        ms = self.market_state[symbol]
        ms["history"].append(ltp)
        self._update_swings(symbol, ltp)
        
        # 1. Initialize if empty
        if ms["last_high"] == 0:
            ms["last_high"] = ltp
            ms["last_low"] = ltp
            return {"state": "NEUTRAL", "reason": "Establishing initial price structure."}

        pattern = "NONE"
        state = "NEUTRAL"
        confidence = 0
        level = 0.0
        reason = "Scanning for structural developments."

        # 2. SMC Logic (BOS / CHoCH)
        # Using swing points for more accurate detection than just session range
        
        # Bullish Analysis
        if ltp > ms["last_high"]:
            level = ms["last_high"]
            if ms["current_trend"] == "Bullish":
                pattern = "BOS"
                reason = f"Bullish BOS: Higher High established at {ltp} (Cleared {level})."
                confidence = 88
            else:
                pattern = "CHoCH"
                reason = f"Bullish CHoCH: Change of character at {ltp} (Transition to Bullish)."
                ms["current_trend"] = "Bullish"
                confidence = 82
            state = "APPROVED"
            ms["last_high"] = ltp

        # Bearish Analysis
        elif ltp < ms["last_low"]:
            level = ms["last_low"]
            if ms["current_trend"] == "Bearish":
                pattern = "BOS"
                reason = f"Bearish BOS: Lower Low established at {ltp} (Cleared {level})."
                confidence = 88
            else:
                pattern = "CHoCH"
                reason = f"Bearish CHoCH: Change of character at {ltp} (Transition to Bearish)."
                ms["current_trend"] = "Bearish"
                confidence = 82
            state = "APPROVED"
            ms["last_low"] = ltp
            
        else:
            reason = "Price trading within established institutional range."

        # 3. Contextual Metadata
        context = {
            "pattern": pattern,
            "level": level,
            "current_bias": ms["current_trend"],
            "support": ms["last_low"],
            "resistance": ms["last_high"],
            "structural_validity": True if pattern != "NONE" else False
        }
        
        event = AgentEvent(
            symbol=symbol,
            agent_name="StructurePatternAgent",
            state=state,
            reason=reason,
            context=context,
            confidence=confidence,
            payload={
                "ltp": ltp, 
                "pattern": pattern, 
                "level": level, 
                "reason": reason
            }
        )
        self.manager.emit_event(event)
        return event.to_dict()
