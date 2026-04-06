
import sys
import os
from collections import defaultdict

# Add the project directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.v2.learning_engine import LearningEngine
from agents.v2.manager import AgentManager

class MockState:
    def __init__(self):
        self.lock = None
        self.logs = []
    def add_log(self, msg):
        self.logs.append(msg)

def test_meta_intelligence():
    print("🧬 [TEST] Initializing Meta-Intelligence Stress Test...")
    state = MockState()
    manager = AgentManager(state)
    engine = LearningEngine(manager)

    print(f"Initial Health: {engine.health_score} | Mode: {engine.system_mode}")

    # 1. Simulate a series of wins
    print("\n[PHASE 1] Simulating winning streak (Institutional quality inputs)...")
    for _ in range(5):
        engine.record_outcome("NIFTY", "SMC_ELITE", "BULLISH", "WIN", 500.0, pattern="BOS + EMA + VWAP")
    
    print(f"Health after win streak: {engine.health_score} | Mode: {engine.system_mode}")
    assert engine.health_score > 75
    assert engine.system_mode == "AGGRESSIVE"

    # 2. Simulate a loss streak
    print("\n[PHASE 2] Simulating Drawdown Event (Survival mode check)...")
    for i in range(4):
        engine.record_outcome("NIFTY", "SMC_ELITE", "BULLISH", "LOSS", -300.0)
        print(f"Loss {i+1}: Health {engine.health_score} | Mode: {engine.system_mode}")
    
    # 3. Verify Defensive Transition
    print(f"\nFinal State: Health {engine.health_score} | Mode: {engine.system_mode} | Risk Multiplier: {engine.global_risk_multiplier}")
    assert engine.system_mode == "DEFENSIVE"
    assert engine.global_risk_multiplier < 1.0

    # 4. Test Trade Scoring under Defensive Mode
    print("\n[PHASE 3] Testing Predictive Scoring in Defensive Mode...")
    base_confidence = 90
    score = engine.compute_trade_score(base_confidence, "SMC_ELITE", "BULLISH", pattern="BOS + EMA + VWAP")
    print(f"Trade Score (Base 90) under Defensive: {score}")
    # Threshold for defensive is 85 in server.py
    print(f"Conclusion: Score {score} vs Threshold 85 -> {'PROCEED' if score >= 85 else 'BLOCK'}")

    print("\n✅ Meta-Intelligence Diagnostic: PASSED")

if __name__ == "__main__":
    test_meta_intelligence()
