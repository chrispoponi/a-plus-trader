
import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from strategy_engine.backtest_engine import BacktestEngine

def main():
    print("Initializing CLASSIC STRATEGIES Backtest...")
    
    # Define Universes
    tech_universe = [
        "NVDA", "TSLA", "AAPL", "AMD", "AMZN", "META", "GOOGL", "MSFT", "PLTR", "UBER"
    ]
    
    # 1. TEST RSI2 (Mean Reversion)
    # Expected: High Win Rate, smaller gains.
    print("\n\n=== TEST 1: RSI(2) Mean Reversion ===")
    try:
        engine_rsi = BacktestEngine(strategy_type='RSI2')
        engine_rsi.run(tech_universe, days=365)
    except Exception as e:
        print(f"RSI2 Failed: {e}")

    # 2. TEST DONCHIAN (Trend Following)
    # Expected: Lower Win Rate, big winners.
    print("\n\n=== TEST 2: Donchian Breakout (20/10) ===")
    try:
        engine_donchian = BacktestEngine(strategy_type='DONCHIAN')
        engine_donchian.run(tech_universe, days=365)
    except Exception as e:
        print(f"Donchian Failed: {e}")

if __name__ == "__main__":
    main()
