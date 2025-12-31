
import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from strategy_engine.backtest_engine import BacktestEngine

def main():
    print("Initializing VWAP SNIPER Backtest...")
    
    # High Liquidity Tickers as requested
    universe = [
        "SPY", "QQQ", "NVDA", "TSLA", "IWM", "AAPL", "AMD", "META", "AMZN", "MSFT"
    ]
    
    print("\n\n=== TEST 6: 'VWAP SNIPER' (Intraday Trend + Reversion) ===")
    print("Logic: EMA20 Trend + VWAP Pullback + RSI2 Reversion.")
    print("This strategy relies on precise intraday patterns (5Min bars used).")
    try:
        engine = BacktestEngine(strategy_type='VWAP_SNIPER')
        # Run last 30 days
        engine.run(universe, days=30)
    except Exception as e:
        print(f"VWAP SNIPER Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
