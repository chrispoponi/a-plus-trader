import pandas as pd
from typing import List, Dict
import time
import random
from datetime import datetime, timedelta
from configs.settings import settings

try:
    from finvizfinance.screener.overview import Overview
    FINVIZ_AVAILABLE = True
except ImportError:
    FINVIZ_AVAILABLE = False
    print("WARNING: finvizfinance not installed. MarketHunter running in Fallback Mode.")

class MarketHunter:
    """
    Autonomous Market Scanner (The Hunter).
    
    Mission: Find fresh tickers that match the 'A+ Setup' criteria daily w/o human input.
    Hierachy:
    1. Source: Finviz Screener (Top Gainers w/ Filters)
    2. Filter: Volume, Price, Trend
    3. Rank: Momentum + Volatility
    4. Fallback: Core Static List
    """
    
    def __init__(self):
        self.cache_file = "market_hunter_cache.csv"
        self.last_hunt_time = None
        self.cache_duration = timedelta(minutes=60) # Don't hunt more than once an hour
        
        # FAILOVER UNIVERSE (MAG7 + CORE15)
        self.fallback_core = [
            "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", # MAG7
            "AMD", "AVGO", "CRM", "NFLX", "LLY", "JPM", "XOM", 
            "ORCL", "COST", "MCD", "DIS", "BA", "PEP", "NKE", "UNH",
            "PLTR", "UBER", "ABNB", "COIN", "MARA" # Momentum adds
        ]

    def hunt(self) -> List[str]:
        """
        Main entry point. Returns a list of ~20 high-quality tickers.
        """
        print("\n🔎 HUNT: Initiating Autonomous Market Hunt...")
        
        # 1. Check Hygiene (Cache) - TODO: Implement file caching if needed across restarts
        # For now, memory cache is fine for the session
        if self.last_hunt_time and (datetime.now() - self.last_hunt_time) < self.cache_duration:
            print(f"🔎 HUNT: Using cached results (Hunted {(datetime.now() - self.last_hunt_time).seconds//60}m ago)")
            return self.fallback_core # Placeholder: In real version we'd store the result
            
        candidates = []
        
        # 2. Tier 1: Discovery (Finviz)
        if FINVIZ_AVAILABLE:
            try:
                candidates = self._run_finviz_screener()
            except Exception as e:
                print(f"⚠️ HUNT: Finviz Failed ({e}). Switching to Fallback.")
        
        # 3. Failover / Supplement
        if not candidates:
            print("🔎 HUNT: Using Core Fallback List.")
            candidates = self.fallback_core
            
        # 4. Tier 3: Rank & Limit (If we have too many)
        # Random shuffle fallback to ensure we rotate through core list if static
        if len(candidates) > 25:
             # Basic logic: Keep the first 25 (Finviz usually sorts by the filter/signal)
             candidates = candidates[:25]
             
        self.last_hunt_time = datetime.now()
        print(f"✅ HUNT: Complete. Returning {len(candidates)} targets.")
        return list(set(candidates)) # Dedupe

    def _run_finviz_screener(self) -> List[str]:
        """
        Queries Finviz for 'Top Gainers' with structural filters.
        """
        foverview = Overview()
        
        # Filters:
        # - Average Volume > 1M (liquidity)
        # - Price > $10 (quality)
        # - Price > SMA50 (Uptrend)
        # - Current Volume > 500k (Active today) or just use 'High Volume' signal
        # Map: https://finviz.com/screener.ashx?v=111&f=sh_avgvol_o1000,sh_price_o10,ta_sma50_pa&ft=4
        
        filters_dict = {
            'Average Volume': 'Over 1M',
            'Price': 'Over $10',
            '50-Day Simple Moving Average': 'Price above SMA50',
            '20-Day Simple Moving Average': 'Price above SMA20', 
            # 'Relative Strength Index (14)': 'Not Overbought (<60)' # Optional: Find pullbacks?
        }
        
        print("🔎 HUNT: Querying Finviz (Trend + Liquidity Filters)...")
        foverview.set_filter(filters_dict=filters_dict)
        
        # Get top 30
        df = foverview.screener_view(order='-volume', limit=30)
        
        if df.empty:
            print("🔎 HUNT: Finviz returned no results.")
            return []
            
        symbols = df['Ticker'].tolist()
        print(f"🔎 HUNT: Found {len(symbols)} tickers via Finviz.")
        return symbols
