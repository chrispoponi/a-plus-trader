
import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from strategy_engine.backtest_engine import BacktestEngine

def main():
    print("Initializing CONGRESS Strategy Backtest...")
    
    # Famous "Nancy Pelosi" Tickers
    universe = [
        "NVDA", "MSFT", "PANW", "AMZN", "AAPL", "PLTR", "TSLA", "GOOGL"
    ]
    
    print("\n\n=== TEST 9: 'NANCY PELOSI' (Congressional Copy-Trade) ===")
    print("Logic: If Disclosure == BUY, Enter. Hold 30 Days.")
    print("Simulated Trades: NVDA, MSFT, PANW based on public record.")
    
    try:
        engine = BacktestEngine(strategy_type='CONGRESS')
        # Run last 3 years to catch the 2023/2024 Pelosi moves
        engine.run(universe, days=720) 
    except Exception as e:
        print(f"CONGRESS Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
