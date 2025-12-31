
import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from strategy_engine.backtest_engine import BacktestEngine

def main():
    print("Initializing OPTIONS SIMULATION Backtest...")
    
    universe = [
        "NVDA", "TSLA", "AAPL", "AMD", "AMZN", "META", "GOOGL", "MSFT", "PLTR", "UBER"
    ]
    
    print("\n\n=== TEST 4: 'A+ HYPER-GROWTH' (Leveraged Options Proxy) ===")
    print("Simulating 10x Effective Leverage on 'Elite' Signals.")
    try:
         # Simulates Long Calls instead of Shares
        engine = BacktestEngine(strategy_type='OPTIONS_SIM')
        engine.run(universe, days=365)
    except Exception as e:
        print(f"OPTIONS SIM Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
