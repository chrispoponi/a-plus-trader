
import sys
import os
import asyncio
from alpaca_trade_api.rest import REST, TimeFrame
from strategy_engine.backtest_engine import BacktestEngine
from configs.settings import settings

# Force sync for simplified script
import nest_asyncio
nest_asyncio.apply()

api = REST(settings.APCA_API_KEY_ID, settings.APCA_API_SECRET_KEY, base_url=settings.APCA_API_BASE_URL)

def get_top_gappers(limit=10):
    print("🔍 SCANNING: Fetching Active Assets...")
    assets = api.list_assets(status='active', asset_class='us_equity')
    
    # Filter for potential small caps (reduce universe size for snapshot limits)
    # Alpaca snapshot limit is generous but let's be efficient.
    # We can't filter by price easily without snapshot, so we grab snapshots for a large chunk?
    # Better: Use Alpaca screener logic if available, or just iterate common exchanges.
    
    symbols = [a.symbol for a in assets if a.exchange in ['NASDAQ', 'NYSE', 'AMEX'] and a.tradable]
    print(f"   Found {len(symbols)} symbols. Fetching Snapshots (Batched)...")
    
    # Batch request (1000 per call usually safe limit)
    chunk_size = 1000
    gappers = []
    
    for i in range(0, len(symbols), chunk_size):
        chunk = symbols[i:i+chunk_size]
        try:
            snapshots = api.get_snapshots(chunk)
            for sym, snap in snapshots.items():
                if not snap.daily_bar: continue
                
                price = snap.daily_bar.c
                open_price = snap.daily_bar.o
                prev_close = snap.prev_daily_bar.c
                
                if not (2.0 <= price <= 20.0): continue # Price Filter
                
                # Gap Calculation (Open vs Prev Close OR Current vs Prev Close for movers)
                # Ross likes Pre-market Gap. Current vs Prev Close roughly approximates "Today's Mover"
                pct_change = (price - prev_close) / prev_close
                
                if pct_change >= 0.10: # +10% Gapper
                    vol = snap.daily_bar.v
                    gappers.append({
                        "symbol": sym,
                        "price": price,
                        "change": pct_change,
                        "volume": vol
                    })
        except Exception as e:
            print(f"   Error fetching chunk {i}: {e}")
            
    # Sort by Top Gainers
    gappers.sort(key=lambda x: x['change'], reverse=True)
    
    print(f"✅ FOUND {len(gappers)} GAPPERS meeting criteria ($2-20, >10%).")
    return [g['symbol'] for g in gappers[:limit]]

def main():
    print("=== WARRIOR 'HUNTER' BACKTEST ===")
    print("1. Scanning LIVE Market for Top Gappers ($2-$20, >10% move).")
    print("2. Running WARRIOR Strategy on identified runners.")
    
    try:
        # 1. LIVE SCAN (Finds what is moving TODAY)
        top_runners = get_top_gappers(limit=5)
        
        if not top_runners:
            print("❌ No gappers found today. Market might be closed or slow.")
            # Fallback for testing: GME, AMC
            print("   Using fallback universe for logic check.")
            top_runners = ["GME", "AMC", "MARA"]
        
        print(f"🎯 TARGETS: {top_runners}")
        
        # 2. BACKTEST on these specific runners
        # Note: Backtest will fetch 'Days=1' or 'Days=5' to see recent action
        engine = BacktestEngine(strategy_type='WARRIOR')
        engine.run(top_runners, days=5) # Test last week's action on these movers
        
    except Exception as e:
        print(f"Hunter Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
