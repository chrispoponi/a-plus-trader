
import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from strategy_engine.backtest_engine import BacktestEngine

def main():
    print("Initializing BUFFETT STRATEGY Backtest...")
    
    # Mix of Quality Growth + Value + Some questionable ones to test filter
    universe = [
        "AAPL", "MSFT", "KO", "JPM", "BAC", "NVDA", "INTC", "TSLA", "CSCO", "PEP",
        "WMT", "COST", "BRK.B", "AMZN", "GOOGL", "XOM", "CVX", "PG", "JNJ", "PFE"
    ]
    
    print("\n\n=== TEST 10: 'BUFFETT VALUE' (Ratios + 52W High Discount) ===")
    print("Logic: ROE > 15%, Debt/Eq < 0.5, Price < 0.85 * 52W High.")
    print("Requires internet for yfinance fundamentals.")
    
    try:
        engine = BacktestEngine(strategy_type='BUFFETT')
        # Run 3 years to allow 'Value' to realize
        engine.run(universe, days=1000)
    except Exception as e:
        print(f"BUFFETT Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
