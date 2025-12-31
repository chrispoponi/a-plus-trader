
import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from strategy_engine.backtest_engine import BacktestEngine

def main():
    print("Initializing RSI-BANDS Strategy Backtest...")
    
    # Volatile Tech + ETFs (Mean Reversion works well on ETFs like TQQQ/SOXL)
    universe = [
        "NVDA", "TSLA", "AMD", "META", "AMZN", "MSFT", "GOOGL", "NFLX",
        "TQQQ", "SOXL" 
    ]
    
    print("\n\n=== TEST 11: 'RSI-BANDS REVERSION' (Dip Buyer) ===")
    print("Logic: Entry @ RSI < 40 + Lower BB. Exit @ RSI > 75 or Upper BB.")
    print("Feature: PROFIT PROTECTION (Sell if > +0.5% and Red Candle).")
    
    try:
        engine = BacktestEngine(strategy_type='RSI_BANDS')
        # Run last 365 days
        engine.run(universe, days=365)
    except Exception as e:
        print(f"RSI-BANDS Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
