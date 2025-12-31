
import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from strategy_engine.backtest_engine import BacktestEngine

def main():
    print("Initializing DAY TRADING Backtest (30 DAYS)...")
    
    # Initialize with 'DAY' strategy
    engine = BacktestEngine(strategy_type='DAY')
    
    # Use Volatile Tickers for Day Trading
    universe = [
        "NVDA", "TSLA", "AMD", 
        "PLTR", "COIN", "MARA",
        "META", "AMZN", "QQQ"
    ]
    
    try:
        # Run last 30 days
        # Warning: This is heavy. 9 symbols * 30 days * 78 bars (5min) = 21,000 bars.
        # engine.fetch processing will take a moment.
        engine.run(universe, days=30)
    except KeyboardInterrupt:
        print("\nBacktest cancelled.")
    except Exception as e:
        print(f"\nCRITICAL BACKTEST ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
