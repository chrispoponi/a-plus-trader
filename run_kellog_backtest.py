
import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from strategy_engine.backtest_engine import BacktestEngine

def main():
    print("Initializing KELLOG STRATEGY Backtest...")
    
    # Jack Kellog Focus: Liquid Mid-Caps + High Beta Tech (and Crypto if available, but sticking to Stocks)
    universe = [
        "MARA", "COIN", "PLTR", "RIOT", "AMD", "NVDA", "MSTR", "DKNG", "SOFI", "UBER"
    ]
    
    print("\n\n=== TEST 7: 'KELLOG REVERSAL' (Antigravity Vol-Exhaustion) ===")
    print("Logic: VWAP Reclaim + Volume Surge > 1.5x.")
    try:
        engine = BacktestEngine(strategy_type='KELLOG')
        # Run last 30 days (Intraday heavy)
        engine.run(universe, days=30)
    except Exception as e:
        print(f"KELLOG Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
