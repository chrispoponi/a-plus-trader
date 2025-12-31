
import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from strategy_engine.backtest_engine import BacktestEngine

def main():
    print("Initializing ELITE Strategy Backtest...")
    
    universe = [
        "NVDA", "TSLA", "AAPL", "AMD", "AMZN", "META", "GOOGL", "MSFT", "PLTR", "UBER"
    ]
    
    print("\n\n=== TEST 3: Elite Trend (ADX+RSI) ===")
    try:
        engine = BacktestEngine(strategy_type='ELITE')
        engine.run(universe, days=365)
    except Exception as e:
        print(f"ELITE Strategy Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
