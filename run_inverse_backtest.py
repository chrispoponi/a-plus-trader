
import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from strategy_engine.backtest_engine import BacktestEngine

def main():
    print("Initializing OPTIONS INVERSE Backtest...")
    
    # Standard Tech Universe
    universe = [
        "NVDA", "TSLA", "AAPL", "AMD", "AMZN", "META", "GOOGL", "MSFT", "PLTR", "UBER"
    ]
    
    print("\n\n=== TEST 8: 'THE CONTRARIAN' (Inverse Options Swing) ===")
    print("Logic: If Swing Setup says LONG, we Buy PUTS (10x Lev).")
    print("Theory: Fading the 'obvious' trend.")
    
    try:
        engine = BacktestEngine(strategy_type='OPTIONS_INVERSE')
        engine.run(universe, days=365)
    except Exception as e:
        print(f"INVERSE Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
