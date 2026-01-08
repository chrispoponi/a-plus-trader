from contracts.options_adapter import options_adapter
from configs.settings import settings
import sys
import pandas as pd

def verify():
    print(f"🦅 HARMONIC EAGLE: Options Engine Verification ({settings.TRADING_MODE})")
    
    symbol = "SPY"
    
    try:
        # Test 1: Get Chain
        print("\n1. Fetching Option Chain (Paper API)...")
        df = options_adapter.get_chain(symbol)
        if df.empty:
            print("FAIL: No Chain Found.")
            return
            
        print(f"   SUCCESS: Chain size {len(df)}")
        print(df[['symbol', 'strike_price', 'expiration_date', 'type']].head(3))
        
        # Test 2: Resolve Condor
        mid_strike = df['strike_price'].median()
        print(f"\n2. Resolving Iron Condor Scaffolding (Reference: ${mid_strike})...")
        
        # Use dte=0 strictly for testing availability (Today's expiry)
        legs = options_adapter.resolve_condor(symbol, mid_strike, dte=0)
        
        if not legs:
             print("   FAIL: Could not resolve legs (Likely no 0DTE matches found).")
             # Try DTE 1 just in case
             print("   Retrying with DTE=1...")
             legs = options_adapter.resolve_condor(symbol, mid_strike, dte=1)
        
        if not legs:
             print("   FAIL: Could not resolve legs on Retry.")
             return
             
        print(f"   SUCCESS: Resolved Structure:")
        for k, v in legs.items():
            print(f"     - {k}: {v}")
             
        # Test 3: Get Quotes
        print(f"\n3. Fetching Live Quotes (Data API)...")
        quotes = options_adapter.get_quotes(list(legs.values()))
        
        if not quotes:
             print("   FAIL: Quotes returned empty (404/Error).")
        else:
             print(f"   SUCCESS: Retrieved Pricing Data:")
             for sym, data in quotes.items():
                 print(f"     - {sym}: Ask ${data.get('ask')} | Bid ${data.get('bid')}")
             
    except Exception as e:
        print(f"CRASH: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify()
