from typing import List
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import pytz
# New SDK
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.timeframe import TimeFrame
try:
    # ScreenerClient is needed for 'Most Actives'
    from alpaca.data import ScreenerClient
    from alpaca.data.requests import MostActivesRequest, StockBarsRequest
except ImportError:
    print("hunter [WARNING]: ScreenerClient/Requests not found. Using Fallback.")
    ScreenerClient = None
    MostActivesRequest = None
    StockBarsRequest = None

from configs.settings import settings

class MarketHunter:
    """
    Autonomous Market Scanner (The Hunter) - Dynamic Mode.
    
    Uses Alpaca 'Most Actives' to find Volume Leaders.
    Expands universe to include Top Losers and Gainers (Yahoo Finance proxy).
    """
    
    def __init__(self):
        try:
            # 1. Screener Client (New SDK) for Most Actives
            self.screener_client = ScreenerClient(
                settings.APCA_API_KEY_ID,
                settings.APCA_API_SECRET_KEY
            )
            
            # 2. REST Client (Old SDK) for easy Snapshots & Bars
            from alpaca_trade_api.rest import REST
            self.api = REST(
                settings.APCA_API_KEY_ID,
                settings.APCA_API_SECRET_KEY,
                base_url=settings.APCA_API_BASE_URL
            )
            print("hunter: Alpaca Clients Connected.")
            
        except Exception as e:
            print(f"hunter: Connection Failed: {e}")
            self.screener_client = None
            self.api = None
            
        # Fallback list...
        self.fallback_universe = [
            "NVDA","TSLA","AAPL","AMD","AMZN","META","GOOGL","MSFT","NFLX","COIN",
            "MARA","PLTR","DKNG","ROKU","SHOP","SQ","UBER","BA","DIS","PYPL",
            "INTC","AMD","SOFI","AFRM","RFA","F","GM","T","VZ","WBD",
            "PARA","SNAP","PINS","M","AAL","CCL","NCLH","RCL","DAL","UAL",
            "BAC","C","JPM","WFC","XOM","CVX","OXY","MRO","DVN","APA"
        ]

    def hunt(self) -> List[str]:
        """
        Executes the 'Most Actives' scan + Top Losers logic.
        """
        if not self.screener_client or not self.api:
            print("hunter [ERROR]: Clients missing. Returning Fallback.")
            return self.fallback_universe

        print(f"\n🔎 HUNT: Scanning 'Most Actives' & 'Top Movers'...")
        
        try:
            # 1. Pull most active stocks (volume) - Top 200 to catch movers
            req = MostActivesRequest(by="volume", top=200)
            actives = self.screener_client.get_most_actives(req)
            
            # Extract Symbols
            raw_symbols = []
            for a in actives:
                if hasattr(a, 'symbol'): raw_symbols.append(a.symbol)
                elif isinstance(a, dict): raw_symbols.append(a.get('symbol'))
                elif isinstance(a, tuple): raw_symbols.append(a[0])

            print(f"hunter: Retrieved {len(raw_symbols)} active symbols.")
            
            if not raw_symbols:
                 return self.fallback_universe[:50]

            # 2. Fetch Snapshots to get Price Change (Gainers/Losers)
            # Chunking to be safe (though 200 is usually fine)
            snapshots = {}
            chunk_size = 100
            for i in range(0, len(raw_symbols), chunk_size):
                chunk = raw_symbols[i:i+chunk_size]
                try:
                    snaps = self.api.get_snapshots(chunk)
                    snapshots.update(snaps)
                except Exception as e:
                    print(f"hunter: Snapshot error: {e}")

            # 3. Sort Candidates
            candidates = []
            for sym, snap in snapshots.items():
                if not snap.daily_bar: continue
                
                price = snap.daily_bar.c
                prev_close = snap.prev_daily_bar.c
                volume = snap.daily_bar.v
                
                if price < 5 or price > 1000: continue # Filter noise/expensive
                if not prev_close: continue
                
                pct_change = (price - prev_close) / prev_close
                
                candidates.append({
                    "symbol": sym,
                    "change": pct_change,
                    "abs_change": abs(pct_change),
                    "volume": volume,
                    "price": price
                })

            # 4. Bucketing (The "Yahoo Finance" Import Logic)
            df = pd.DataFrame(candidates)
            if df.empty: return self.fallback_universe[:50]
            
            # A. Top Losers (Bottom 10)
            top_losers = df.sort_values("change", ascending=True).head(15)
            print(f"hunter: Found Top Losers: {top_losers['symbol'].tolist()}")

            # B. Top Gainers (Top 10 - Trending)
            top_gainers = df.sort_values("change", ascending=False).head(15)
            
            # C. Most Active (Top 15 by Volume) -- redundant as source is active, but ensures coverage
            most_active = df.sort_values("volume", ascending=False).head(15)
            
            # Combine Sets
            final_set = set()
            final_set.update(top_losers['symbol'].tolist())
            final_set.update(top_gainers['symbol'].tolist())
            final_set.update(most_active['symbol'].tolist())
            
            # Backfill with original "Smart Quality" Logic if needed to reach 50
            # (Re-using simplified score logic on the rest)
            remaining_needed = 50 - len(final_set)
            if remaining_needed > 0:
                # Simple Smart Score: MovAvg Trend
                # Only need 60 days bars for the candidates not yet chosen
                # Optimization: Just pick high volume leftovers
                leftovers = df[~df['symbol'].isin(final_set)]
                if not leftovers.empty:
                    # Sort by volume as proxy for quality
                    fillers = leftovers.sort_values("volume", ascending=False).head(remaining_needed)
                    final_set.update(fillers['symbol'].tolist())

            final_list = list(final_set)
            
            print(f"🔎 HUNT: Returning {len(final_list)} Tickers (Losers/Gainers/Active).")
            return final_list

        except Exception as e:
            print(f"hunter [ERROR]: {e}")
            import traceback
            traceback.print_exc()
            return self.fallback_universe
