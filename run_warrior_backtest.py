
import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from strategy_engine.backtest_engine import BacktestEngine

def main():
    print("Initializing WARRIOR TRADING (MOMENTUM GAPPERS) Backtest...")
    
    # Small Cap Runners & Meme Stocks (High Volatility Universe)
    # We need stocks that actually HAD 1-min momentum runs.
    universe = [
        "GME", "AMC", "BB", "MARA", "RIOT", "COIN", "PLTR", "SOFI", "HOOD", "OPEN"
    ]
    
    print("\n\n=== TEST 12: 'WARRIOR MOMENTUM' (Small Cap Gappers) ===")
    print("Logic: Impulse -> Pullback (>50% Fib) -> Break Prev High.")
    print("Filter: RelVol > 3x.")
    print("Risk: Cushion Sizing (Theoretical).")
    
    try:
        engine = BacktestEngine(strategy_type='WARRIOR')
        # Run last 30 days (Intraday is heavy, keep it short)
        engine.run(universe, days=30)
    except Exception as e:
        print(f"WARRIOR Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
