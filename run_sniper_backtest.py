
import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from strategy_engine.backtest_engine import BacktestEngine

def main():
    print("Initializing SNIPER OPTIONS Backtest...")
    
    # Use Mega-Cap Tech + Volatile Names (High Option Liquidity)
    universe = [
        "NVDA", "TSLA", "AMD", "META", "AMZN", "AAPL", "MSFT", "PLTR", "COIN", "MARA"
    ]
    
    print("\n\n=== TEST 5: 'SNIPER MODE' (Intraday Option Scalping) ===")
    print("Logic: Day Trade Signals + 20x Leverage + 1Hr Time Stop.")
    print("STRESS TEST: 90 Days (3 Months) of Intraday Data.")
    try:
        engine = BacktestEngine(strategy_type='SNIPER_OPTIONS')
        # Run last 90 days (Intraday data is heavy)
        engine.run(universe, days=90)
    except Exception as e:
        print(f"SNIPER Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
