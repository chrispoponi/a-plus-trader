
import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from strategy_engine.backtest_engine import BacktestEngine

def main():
    print("Initializing Robust Backtest...")
    
    engine = BacktestEngine()
    
    # EXPANDED UNIVERSE (30 Tickers)
    # Covering: Tech, Finance, Energy, Retail, Travel, Defense
    universe = [
        # Tech / Mag 7
        "NVDA", "TSLA", "AAPL", "AMD", "AMZN", "META", "GOOGL", "MSFT",
        # Growth / Volatility
        "PLTR", "UBER", "COIN", "SHOP", "DKNG", "ROKU", "SOFI",
        # Finance
        "JPM", "BAC", "GS", "WFC",
        # Energy
        "XOM", "CVX", "OXY",
        # Retail/Consumer
        "COST", "WMT", "TGT", "LULU",
        # Travel
        "BA", "DAL", "CCL", "DIS"
    ]
    
    print(f"Targeting {len(universe)} diversified symbols.")
    
    try:
        # Run for full year to capture market regimes
        engine.run(universe, days=365)
    except KeyboardInterrupt:
        print("\nBacktest cancelled.")
    except Exception as e:
        print(f"\nCRITICAL BACKTEST ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
