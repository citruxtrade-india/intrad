
import math

class CandlestickPatternEngine:
    def __init__(self):
        # Configuration for pattern sensitivity
        self.doji_threshold = 0.1 # Real body is < 10% of total range
        self.hammer_ratio = 2.0  # Lower shadow is at least 2x the body

    def detect_patterns(self, ohlc_data):
        """
        Detects patterns in a list of OHLC dictionaries.
        Expects: [{'open': 100, 'high': 105, 'low': 95, 'close': 102, 'timestamp': '...'}, ...]
        Returns: list of pattern matches
        """
        if len(ohlc_data) < 5:
            return []

        patterns = []
        for i in range(1, len(ohlc_data)):
            candle = ohlc_data[i]
            prev = ohlc_data[i-1]
            
            # Basic Candle Props
            body = abs(candle['close'] - candle['open'])
            total_range = candle['high'] - candle['low']
            if total_range == 0: continue
            
            upper_shadow = candle['high'] - max(candle['open'], candle['close'])
            lower_shadow = min(candle['open'], candle['close']) - candle['low']
            
            is_bullish = candle['close'] > candle['open']
            is_bearish = candle['close'] < candle['open']
            
            # 1. Doji
            if body <= total_range * self.doji_threshold:
                patterns.append({
                    "type": "Doji",
                    "timestamp": candle['timestamp'],
                    "index": i,
                    "sentiment": "Neutral/Indecision",
                    "strength": 0.5
                })

            # 2. Hammer (Potential Reversal)
            if lower_shadow >= body * self.hammer_ratio and upper_shadow <= body * 0.5:
                patterns.append({
                    "type": "Hammer",
                    "timestamp": candle['timestamp'],
                    "index": i,
                    "sentiment": "Bullish Reversal",
                    "strength": 0.7
                })

            # 3. Shooting Star (Bearish Reversal)
            if upper_shadow >= body * self.hammer_ratio and lower_shadow <= body * 0.5:
                patterns.append({
                    "type": "Shooting Star",
                    "timestamp": candle['timestamp'],
                    "index": i,
                    "sentiment": "Bearish Reversal",
                    "strength": 0.7
                })

            # 4. Engulfing
            # Bullish Engulfing
            if prev['close'] < prev['open'] and candle['close'] > candle['open'] and \
               candle['open'] <= prev['close'] and candle['close'] >= prev['open']:
                patterns.append({
                    "type": "Bullish Engulfing",
                    "timestamp": candle['timestamp'],
                    "index": i,
                    "sentiment": "Bullish",
                    "strength": 0.85
                })
            # Bearish Engulfing
            elif prev['close'] > prev['open'] and candle['close'] < candle['open'] and \
                 candle['open'] >= prev['close'] and candle['close'] <= prev['open']:
                patterns.append({
                    "type": "Bearish Engulfing",
                    "timestamp": candle['timestamp'],
                    "index": i,
                    "sentiment": "Bearish",
                    "strength": 0.85
                })

            # 5. Inside Bar
            if candle['high'] < prev['high'] and candle['low'] > prev['low']:
                patterns.append({
                    "type": "Inside Bar",
                    "timestamp": candle['timestamp'],
                    "index": i,
                    "sentiment": "Consolidation",
                    "strength": 0.6
                })

            # 6. Outside Bar
            if candle['high'] > prev['high'] and candle['low'] < prev['low']:
                patterns.append({
                    "type": "Outside Bar",
                    "timestamp": candle['timestamp'],
                    "index": i,
                    "sentiment": "Volatility Expansion",
                    "strength": 0.6
                })

        # Multi-Candle Patterns (Morning/Evening Star - Requires 3 candles)
        for i in range(2, len(ohlc_data)):
            c1 = ohlc_data[i-2]
            c2 = ohlc_data[i-1]
            c3 = ohlc_data[i]
            
            # Morning Star
            if c1['close'] < c1['open'] and \
               abs(c2['close'] - c2['open']) < (c1['high']-c1['low']) * 0.3 and \
               c3['close'] > c3['open'] and c3['close'] > (c1['open'] + c1['close'])/2:
                patterns.append({
                    "type": "Morning Star",
                    "timestamp": c3['timestamp'],
                    "index": i,
                    "sentiment": "Bullish Reversal",
                    "strength": 0.9
                })
                
            # Evening Star
            if c1['close'] > c1['open'] and \
               abs(c2['close'] - c2['open']) < (c1['high']-c1['low']) * 0.3 and \
               c3['close'] < c3['open'] and c3['close'] < (c1['open'] + c1['close'])/2:
                patterns.append({
                    "type": "Evening Star",
                    "timestamp": c3['timestamp'],
                    "index": i,
                    "sentiment": "Bearish Reversal",
                    "strength": 0.9
                })

        return patterns
