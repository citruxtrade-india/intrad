import os
import json
import sys
from agents.v2.stress_test_engine import StressTestEngine

def main():
    print("="*60)
    print(" 🛡️ ALICE REALITY VALIDATION & SYSTEM STRESS ANALYZER 🛡️ ")
    print("="*60)
    print("[INIT] Loading Isolated Agent Intelligence...")
    
    # 1. Initialize Stress Engine with isolated config
    engine = StressTestEngine({
        "initial_capital": 500000.0,
        "risk_per_trade": 0.015  # 1.5% aggressive stress risk
    })
    
    # 2. Run Stress Validation across 4 Controlled Market Scenarios
    # TRENDING_BULL | TRENDING_BEAR | CHOPPY_NOISE | HIGH_VOLATILITY
    print("\n[PHASE 1] Market Scenario Simulation Loop...")
    results = engine.run_multi_dataset_validation()
    
    # 3. Behavioral Performance Matrix
    print("\n" + "="*60)
    print(" 🧠 BEHAVIORAL ANALYTICS & STABILITY MATRIX ")
    print("="*60)
    
    for scenario, res in results.items():
        bh = res.get("behavior", {})
        cn = res.get("consistency", {})
        
        print(f"\n📈 SCENARIO: {scenario}")
        print(f"   Aggression:  [{bh.get('aggression_level', 'N/A')}]")
        print(f"   Selectivity: [{bh.get('selectivity', 'N/A')}]")
        print(f"   Stability:   [{bh.get('stability', 'N/A')}]")
        print(f"   PnL Result:  Rs{res.get('total_pnl', 0):+,.2f} | Win Rate: {res.get('win_rate', 0)}%")
        print(f"   Drawdown:    {res.get('max_drawdown', 0)}% | Total Trades: {res.get('total_trades', 0)}")
        print(f"   Consistency: {cn.get('consistency_score', 0)}/100 ({cn.get('status', 'N/A')})")
        print("-" * 60)
        
    # 4. Final Validation Report Generation
    report = engine.generate_validation_report()
    
    print(f"\n[FINAL STATUS] System Reliability: {report['system_readiness']}")
    print("[FINAL STATUS] Validation Telemetry written to reality_validation_report.json")
    print("="*60)

if __name__ == "__main__":
    main()
