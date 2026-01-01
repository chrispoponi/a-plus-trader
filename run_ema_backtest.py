
import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from strategy_engine.backtest_engine import BacktestEngine

def main():
    print("Initializing 3-EMA (Trend Bot) Strategy Backtest...")
    
    # Trend Followers work best on strong Mega Caps and Indices
    universe = [
        "AAPL", "NVDA", "TSLA", "MSFT", "AMZN", "GOOGL", "AMD", "META", "SPY", "QQQ"
    ]
    
    print("\n\n=== TEST 13: '3-EMA TREND BOT' ===")
    print("Logic: Price > 20 > 50 EMA + Structure Breakout.")
    print("Goal: Capture major trend legs (High Win Rate).")
    
    try:
        engine = BacktestEngine(strategy_type='EMA3')
        # Run last 365 days (Needs daily trend context)
        engine.run(universe, days=365)
    except Exception as e:
        print(f"EMA3 Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
