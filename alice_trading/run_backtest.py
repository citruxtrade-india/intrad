import argparse
import json
import os
import sys

# Ensure module pathing is correct
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.v2.backtesting_engine import BacktestingEngine

def main():
    parser = argparse.ArgumentParser(description="Isolated Strategy Backtesting Engine")
    parser.add_argument("--data", default="NSE.csv", help="Path to historical OHLC CSV data")
    parser.add_argument("--symbol", default="NIFTY", help="Symbol to backtest")
    parser.add_argument("--capital", type=float, default=100000.0, help="Starting Capital")
    parser.add_argument("--risk", type=float, default=0.01, help="Risk per trade (0.01 = 1 pct)")
    
    args = parser.parse_args()

    # If the user targets NSE.csv which is actually a master list, or missing file, make dummy
    if args.data == "NSE.csv" or not os.path.exists(args.data):
        print(f"[BACKTEST ENGINE] Notice: Generating 1000 bars of synthetic OHLC for {args.symbol} to replace {args.data} for testing...")
        args.data = "synthetic_backtest.csv"
        import random
        from datetime import datetime, timedelta
        with open(args.data, "w") as f:
            f.write("Date,Open,High,Low,Close,Volume\n")
            p = 20000.0
            t = datetime.now() - timedelta(days=30)
            for i in range(1000):
                o = p
                h = o + random.uniform(0, 50)
                l = o - random.uniform(0, 50)
                c = random.uniform(l, h)
                f.write(f"{t.strftime('%Y-%m-%d %H:%M:%S')},{o:.2f},{h:.2f},{l:.2f},{c:.2f},100\n")
                p = c
                t += timedelta(minutes=5)

    print(f"\n[BACKTEST ENGINE] Initializing Laboratory for {args.symbol}...")
    print(f"[BACKTEST ENGINE] Configuration: Capital=₹{args.capital}, Risk={args.risk*100}% per trade")
    
    config = {
        "symbol": args.symbol,
        "initial_capital": args.capital,
        "risk_per_trade": args.risk,
        "stop_loss_pct": 0.005,
        "target_pct": 0.01
    }
    
    engine = BacktestingEngine(config=config)
    
    print("\n[BACKTEST ENGINE] Running simulation... (This will read agent logic strictly in read-only mode).")
    
    results = engine.run_backtest(args.data)
    
    if "error" in results:
        print(f"\n[ERROR] {results['error']}")
        sys.exit(1)
        
    print("\n" + "="*50)
    print(" 🧪 BACKTEST PERFORMANCE DETAILED REPORT 🧪 ")
    print("="*50)
    print(f"Total Evaluated Trades:  {results['total_trades']}")
    print(f"System Win Rate (%):     {results['win_rate']}%")
    print(f"System Loss Rate (%):    {results['loss_rate']}%")
    print(f"Max Strategy Drawdown:   {results['max_drawdown']}%")
    print(f"Average R:R Achieved:    {results['average_rr']} R")
    print("-" * 50)
    print(f"Final Capital:           ₹{results.get('final_capital', 0)}")
    print(f"Total Net P&L:           ₹{results['total_pnl']}")
    print("="*50)
    print("\n[BACKTEST ENGINE] Full audit telemetry saved to 'backtest_results.log'")

if __name__ == "__main__":
    main()
