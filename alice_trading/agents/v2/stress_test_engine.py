import os
import json
import pandas as pd
import datetime
from .backtesting_engine import BacktestingEngine, IsolatedState, IsolatedManager

class StressTestEngine:
    """
    🏗️ Reality Validation & System Stress Layer.
    Observes and validates existing agent intelligence under extreme market scenarios.
    Isolates all analytics to prevent live system interference.
    """
    def __init__(self, base_config=None):
        self.base_config = base_config or {
            "initial_capital": 100000.0,
            "risk_per_trade": 0.01
        }
        self.scenarios = {
            "TRENDING_BULL": {"file": "synthetic_trending_bull.csv", "desc": "Sustained upward momentum 2024-style"},
            "TRENDING_BEAR": {"file": "synthetic_trending_bear.csv", "desc": "Aggressive crash scenario"},
            "CHOPPY_NOISE": {"file": "synthetic_choppy.csv", "desc": "Low volatility horizontal grinding"},
            "HIGH_VOLATILITY": {"file": "synthetic_volatile.csv", "desc": "Extreme whipsaws and gap scenarios"}
        }
        self.stress_results = {}

    def generate_stress_scenarios(self):
        """Generates the 4 core reality datasets if they don't exist."""
        import random
        for name, meta in self.scenarios.items():
            path = meta["file"]
            if os.path.exists(path): continue
            
            print(f"[STRESS TEST] Generating Scenario Dataset: {name}")
            data = []
            p = 20000.0
            t = datetime.datetime.now() - datetime.timedelta(days=30)
            
            for i in range(500):
                o = p
                # Scenario specific price action
                if name == "TRENDING_BULL": move = random.uniform(-10, 60)
                elif name == "TRENDING_BEAR": move = random.uniform(-60, 10)
                elif name == "CHOPPY_NOISE": move = random.uniform(-20, 20)
                elif name == "HIGH_VOLATILITY": move = random.uniform(-150, 150)
                else: move = random.uniform(-30, 30)
                
                h = o + (move if move > 0 else 0) + random.uniform(0, 20)
                l = o + (move if move < 0 else 0) - random.uniform(0, 20)
                c = o + move
                
                data.append([t.strftime('%Y-%m-%d %H:%M:%S'), o, h, l, c, 1000])
                p = c
                t += datetime.timedelta(minutes=15)
                
            df = pd.DataFrame(data, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
            df.to_csv(path, index=False)

    def run_multi_dataset_validation(self):
        """Runs the backtest engine across all scenarios to observe behavior patterns."""
        self.generate_stress_scenarios()
        summary = {}
        
        for name, meta in self.scenarios.items():
            print(f"[STRESS TEST] Validating Intelligence on {name}...")
            engine = BacktestingEngine(config={**self.base_config, "symbol": name})
            res = engine.run_backtest(meta["file"])
            
            # Behavioral derivation
            res["behavior"] = self._analyze_behavior(res)
            res["consistency"] = self._evaluate_consistency(res)
            
            summary[name] = res
            
        self.stress_results = summary
        return summary

    def _analyze_behavior(self, res):
        """Behavioral Analytics Layer (Aggression/Selectivity/Stability)"""
        trades = res.get("total_trades", 0)
        win_rate = res.get("win_rate", 0)
        
        # Aggression: Frequency of attempts
        aggression = "LOW"
        if trades > 15: aggression = "HIGH"
        elif trades > 5: aggression = "MEDIUM"
        
        # Selectivity: Inverse of noise participation (using win_rate as proxy for quality)
        selectivity = "STRICT"
        if win_rate < 40: selectivity = "LOOSE"
        elif win_rate < 60: selectivity = "BALANCED"
        
        # Stability: Max Drawdown relative to PnL
        stability = "STABLE"
        if res.get("max_drawdown", 0) > 10: stability = "UNSTABLE"
        elif res.get("max_drawdown", 0) > 5: stability = "VOLATILE"
        
        return {
            "aggression_level": aggression,
            "selectivity": selectivity,
            "stability": stability
        }

    def _evaluate_consistency(self, res):
        """Consistency Validation Engine"""
        trades_list = res.get("trades", [])
        if not trades_list:
            return {
                "consistency_score": 0.0,
                "variance": 0.0,
                "status": "INSUFFICIENT_DATA"
            }
        
        # Calculate Variance of PnL results
        pnls = [t["pnl"] for t in trades_list]
        avg_pnl = sum(pnls) / len(pnls)
        variance = sum((x - avg_pnl) ** 2 for x in pnls) / len(pnls)
        
        consistency_score = 100 - min(100, (variance ** 0.5) / 10)
        
        return {
            "consistency_score": round(consistency_score, 2),
            "variance": round(variance, 2),
            "status": "REPLICABLE" if consistency_score > 70 else "CONDITION_DEPENDENT"
        }

    def generate_validation_report(self):
        """Outputs a permanent stress validation log for audit."""
        report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "scenarios_evaluated": list(self.stress_results.keys()),
            "system_readiness": "CERTIFIED" if all(
                s.get("consistency", {}).get("consistency_score", 0) > 50
                for s in self.stress_results.values()
            ) else "REQUIRES_REVIEW",
            "detailed_metrics": self.stress_results
        }
        
        with open("reality_validation_report.json", "w") as f:
            json.dump(report, f, indent=4)
        print(f"\n[VALIDATION] Reality Validation Report generated: reality_validation_report.json")
        return report
