import sys
import os
import time
from core.symbol_search_manager import SymbolSearchManager
from agents.v2.manager import AgentManager
from agents.v2.market_context import MarketContextAgent
from agents.v2.validation import ValidationAgent
from agents.v2.risk_capital import RiskCapitalAgent

def trigger_test():
    print("="*60)
    print(" 🚀 RELIANCE AGENT ACTIVATION SEQUENCE ")
    print("="*60)
    
    # 1. Setup Mock State
    class MockState:
        def __init__(self):
            self.mode = "SIMULATION"
            self.broker = None
            self.instruments = {}
            self.is_running = True

    state = MockState()
    manager = AgentManager(state)
    
    # 2. Register Agents
    mc = MarketContextAgent(manager)
    va = ValidationAgent(manager)
    rc = RiskCapitalAgent(manager)
    
    manager.register_agent("MarketContext", mc)
    manager.register_agent("Validation", va)
    manager.register_agent("RiskCapital", rc)
    
    # 3. Find Reliance
    search = SymbolSearchManager()
    inst = search.get_by_symbol("RELIANCE")
    
    if not inst:
        print("[ERROR] Reliance not found in search manager.")
        return

    print(f"\n[SCAN] Starting Live Analysis: {inst['name']} (NSE:{inst['token']})")
    
    # 4. Trigger Analysis Cycle
    # Simulate some market data for the agents to chew on
    mock_data = {
        "lp": 2985.40,
        "c": 2960.00,
        "v": 1200000,
        "h": 3010.00,
        "l": 2950.00
    }
    
    print("[1/3] Running Market Context Analysis...")
    mc_result = mc.process(inst, mock_data)
    print(f"      Result: {mc_result}")
    
    print("[2/3] Running Intelligence Validation...")
    va_result = va.process(inst, mc_result)
    print(f"      Result: {va_result}")
    
    print("[3/3] Checking Risk & Capital Governor...")
    rc_result = rc.process(inst, va_result)
    print(f"      Result: {rc_result}")
    
    print("\n" + "="*60)
    print(" 🧠 AGENT FINAL VERDICT ")
    print("="*60)
    audit = manager.get_audit_trail()
    for e in audit:
        color = "🟢" if e['state'] == "APPROVED" else "🔴"
        print(f"{color} {e['agent']} -> {e['state']} | {e['reason']}")
    
    print("\n[FINISH] Observation Complete. Check dashboard for live updates.")
    print("="*60)

if __name__ == "__main__":
    trigger_test()
