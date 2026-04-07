
from .manager import AgentEvent

class ValidationAgent:
    def __init__(self, manager):
        self.manager = manager
        self.status = "ACTIVE"

    def get_status(self):
        return self.status

    def validate(self, symbol, ltp, context_event, pattern_event):
        # 1. Component Extraction
        ctx = context_event.get("context", {})
        mood = ctx.get("market_mood", "RANGE")
        signal = pattern_event.get("context", {}).get("pattern", "NONE")
        
        ema20 = ctx.get("ema20", 0)
        ema50 = ctx.get("ema50", 0)
        vwap_dist = ctx.get("vwap_dist", 0)
        
        # 2. Confluence Flags
        ema_aligned = False
        if ema20 > 0 and ema50 > 0:
            if mood == "BULLISH" and ema20 > ema50: ema_aligned = True
            if mood == "BEARISH" and ema20 < ema50: ema_aligned = True
            
        vwap_support = False
        if vwap_dist is not None:
            if mood == "BULLISH" and vwap_dist >= 0: vwap_support = True
            if mood == "BEARISH" and vwap_dist <= 0: vwap_support = True
        else:
            vwap_support = True
            
        allowed = False
        state = "REJECTED"
        confidence = 45
        reason = "Awaiting Trend + Structure alignment."

        # 3. Pattern Genome Calculation
        # DNA of the trade for Predictive Memory
        genome_parts = [mood, signal]
        if ema_aligned: genome_parts.append("EMA")
        if vwap_support: genome_parts.append("VWAP")
        pattern_genome = " + ".join(genome_parts)
        
        # 4. Confluence Rules
        if mood == "BULLISH" and signal == "BOS":
            if ema_aligned and vwap_support:
                allowed = True
                state = "APPROVED"
                confidence = 88
                reason = f"Elite Pattern: {pattern_genome} confirmed."
            else:
                state = "FILTERED"
                confidence = 68 # Increased from 65
                reason = "BOS detected, but pending EMA/VWAP alignment."
        elif mood == "BEARISH" and signal == "CHoCH":
            allowed = True
            state = "APPROVED"
            confidence = 85
            reason = "Character Change (CHoCH) detected in Bearish context."
        elif signal != "NONE":
            state = "FILTERED"
            confidence = 60 # Increased from 50
            reason = f"Filtered: {mood} context incompatible with {signal} signal."
        
        # 5. Pre-Trade Bias (Predictive boost)
        # Higher confidence for known 'Strong' genomes
        if "BOS + EMA + VWAP" in pattern_genome:
            confidence += 5 # Pre-bias boost for institutional favorite
        
        context = {
            "entry_allowed": allowed,
            "ema_aligned": ema_aligned,
            "vwap_support": vwap_support,
            "pattern_genome": pattern_genome,
            "HTF_agreement": True if confidence > 80 else False
        }
        
        event = AgentEvent(
            symbol=symbol,
            agent_name="ValidationAgent",
            state=state,
            reason=reason,
            context=context,
            confidence=confidence,
            payload={
                "symbol": symbol,
                "signal": "BUY" if mood == "BULLISH" and allowed else ("SELL" if mood == "BEARISH" and allowed else "NONE"),
                "confidence": round(confidence / 100, 2),
                "entry_allowed": allowed,
                "reason": reason,
                "pattern_genome": pattern_genome
            }
        )
        self.manager.emit_event(event)
        return event.to_dict()
