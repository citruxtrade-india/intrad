
from .manager import AgentEvent
import collections

class MarketContextAgent:
    """
    Real-Time Market Context Analyzer.
    Hardened for dynamic volatility instead of fixed % thresholds.
    """
    def __init__(self, manager):
        self.manager = manager
        self.status = "ACTIVE"
        # Memory buffer to compute 'Real-time Volatility' (ATR Proxy)
        self.price_history = collections.defaultdict(lambda: collections.deque(maxlen=50))
        # Structure tracking: Last few pivots
        self.pivots = collections.defaultdict(lambda: {"highs": [], "lows": []})

    def get_status(self):
        return self.status

    def _detect_pivots(self, symbol, ltp):
        hist = list(self.price_history[symbol])
        if len(hist) < 5: return
        
        # Simple pivot detection: middle point is highest/lowest in its neighborhood
        p = hist[-3]
        if p > hist[-5] and p > hist[-4] and p > hist[-2] and p > hist[-1]:
            highs = self.pivots[symbol]["highs"]
            if not highs or abs(p - highs[-1]) > (p * 0.0005):
                highs.append(p)
                if len(highs) > 5: highs.pop(0)
        
        if p < hist[-5] and p < hist[-4] and p < hist[-2] and p < hist[-1]:
            lows = self.pivots[symbol]["lows"]
            if not lows or abs(p - lows[-1]) > (p * 0.0005):
                lows.append(p)
                if len(lows) > 5: lows.pop(0)

    def _calculate_ema(self, symbol, period):
        hist = list(self.price_history[symbol])
        if len(hist) < period: return 0
        
        # Simple EMA calculation:
        # EMA = (Price - PrevEMA) * (2 / (Period + 1)) + PrevEMA
        # For the first one, use SMA
        k = 2 / (period + 1)
        ema = sum(hist[:period]) / period
        for p in hist[period:]:
            ema = (p - ema) * k + ema
        return round(ema, 2)

    def process(self, symbol, ltp, close, volume=0, vwap=0):
        # 1. Update Price Memory for true volatility detection
        hist = self.price_history[symbol]
        hist.append(ltp)
        self._detect_pivots(symbol, ltp)
        
        # Calculate Indicators
        ema20 = self._calculate_ema(symbol, 20)
        ema50 = self._calculate_ema(symbol, 50)
        
        # Calculate Dynamic Range (Volatility Proxy)
        if len(hist) > 1:
            curr_range = max(hist) - min(hist)
            avg_price = sum(hist) / len(hist)
            volatility_pct = (curr_range / avg_price) if avg_price > 0 else 0
        else:
            volatility_pct = 0.001 # Default fallback

        # 2. Price Action Analysis (HH/HL detection)
        pivots = self.pivots[symbol]
        pa_desc = "Neutral structure"
        market_mood = "RANGE"
        
        if len(pivots["highs"]) >= 2 and len(pivots["lows"]) >= 2:
            hh = pivots["highs"][-1] > pivots["highs"][-2]
            hl = pivots["lows"][-1] > pivots["lows"][-2]
            lh = pivots["highs"][-1] < pivots["highs"][-2]
            ll = pivots["lows"][-1] < pivots["lows"][-2]
            
            if hh and hl:
                market_mood = "BULLISH"
                pa_desc = "Higher highs and higher lows detected"
            elif lh and ll:
                market_mood = "BEARISH"
                pa_desc = "Lower highs and lower lows detected"
            elif lh and hl:
                market_mood = "RANGE"
                pa_desc = "Symmetric consolidation (LH + HL)"
            elif hh and ll:
                market_mood = "VOLATILE"
                pa_desc = "Expanding range (HH + LL)"

        # 3. Dynamic Trend Analysis
        dynamic_threshold = max(0.0015, volatility_pct * 0.5)
        diff_pct = (ltp - close) / close if close > 0 else 0
        trend = "Sideways"
        state = "NEUTRAL"
        confidence = 55
        
        if diff_pct > dynamic_threshold:
            trend = "Bullish"
            state = "APPROVED" if market_mood == "BULLISH" else "NEUTRAL"
            confidence = min(92, 80 + int((diff_pct / dynamic_threshold) * 5))
        elif diff_pct < -dynamic_threshold:
            trend = "Bearish"
            state = "APPROVED" if market_mood == "BEARISH" else "NEUTRAL"
            confidence = min(92, 80 + int((abs(diff_pct) / dynamic_threshold) * 5))
        
        # 4. Liquidity & Regime Analysis
        v_regime = "Low"
        if volatility_pct > 0.008: v_regime = "High"
        elif volatility_pct > 0.004: v_regime = "Moderate"

        liquidity = "High" if (volume > 2000 or (vwap > 0 and abs(ltp - vwap) < (ltp * 0.001))) else "Moderate"
        
        reason = f"Institutional context: {market_mood} | {pa_desc} | {v_regime} Volatility."
        if state == "NEUTRAL":
            confidence = 50

        context = {
            "trend": trend,
            "ema20": ema20,
            "ema50": ema50,
            "market_mood": market_mood,
            "pa_description": pa_desc,
            "volatility": v_regime,
            "volatility_raw": round(volatility_pct, 5),
            "threshold_used": round(dynamic_threshold, 5),
            "liquidity": liquidity,
            "vwap_dist": round((ltp - vwap), 2) if vwap > 0 else 0
        }
        
        event = AgentEvent(
            symbol=symbol,
            agent_name="MarketContextAgent",
            state=state,
            reason=reason,
            context=context,
            confidence=confidence,
            payload={
                "ltp": ltp, 
                "close": close, 
                "volatility": volatility_pct,
                "market_mood": market_mood,
                "reason": reason
            }
        )
        self.manager.emit_event(event)
        return event.to_dict()

