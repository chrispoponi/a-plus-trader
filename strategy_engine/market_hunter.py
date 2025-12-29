import pandas as pd
from typing import List
from datetime import datetime
import yfinance as yf
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
    
    1. Primary: Finviz Screener (Top Gainers with Trend/Vol Filters)
    2. Fallback: YFinance Scan of Top 50 Popular Stocks (Momentum & Volatility)
    """
    
    def __init__(self):
        # FAILOVER UNIVERSE (Top 50 Active/Popular)
        self.fallback_core = [
            "NVDA","TSLA","AAPL","GOOGL","MSFT","META","AMD","PLTR","NFLX",
            "INTC","ORCL","SOFI","AMZN","COST","DIS","JPM","BA","CRM",
            "UBER","MRVL","SQ","ABNB","COIN","MARA","MSTR","Riot",
            "DKNG","HOOD","PANW","CRWD","SNOW","SHOP","TTD","NET",
            "ZS","LULU","NKE","SBUX","MCD","PEP","KO","WMT","TGT",
            "XOM","CVX","OXY","V","MA","AXP","GS"
        ]

    def hunt(self) -> List[str]:
        """
        Main entry point. Returns a list of ~20-30 high-quality tickers.
        """
        print("\n🔎 HUNT: Initiating Autonomous Market Hunt...")
        candidates = []
        
        # 1. Primary: Finviz
        if FINVIZ_AVAILABLE:
            try:
                candidates = self._run_finviz_screener()
            except Exception as e:
                print(f"⚠️ HUNT: Finviz Failed ({e}).")
        
        # 2. Fallback: YFinance Scan of Core List
        # If Finviz returned too few (<5) or failed, run the internal scanner
        if len(candidates) < 5:
            print(f"🔎 HUNT: Running YFinance Fallback on {len(self.fallback_core)} tickers...")
            fallback_candidates = self._run_yfinance_scan(self.fallback_core)
            candidates.extend(fallback_candidates)
            
        print(f"✅ HUNT: Complete. Returning {len(candidates)} targets.")
        return list(set(candidates))

    def _run_finviz_screener(self) -> List[str]:
        """
        Queries Finviz for 'Top Gainers' with structural filters.
        """
        foverview = Overview()
        # Filters: Avg Vol > 1M, Price > $10, SMA50 Up, SMA20 Up
        # This focuses on established uptrends.
        filters_dict = {
            'Average Volume': 'Over 1M',
            'Price': 'Over $10',
            '50-Day Simple Moving Average': 'Price above SMA50',
            '20-Day Simple Moving Average': 'Price above SMA20', 
        }
        
        print("🔎 HUNT: Querying Finviz (Trend + Liquidity)...")
        foverview.set_filter(filters_dict=filters_dict)
        # Get top 30
        df = foverview.screener_view(order='-volume', limit=30)
        
        if df.empty:
            return []
            
        symbols = df['Ticker'].tolist()
        print(f"🔎 HUNT: Finviz found {len(symbols)} tickers.")
        return symbols

    def _run_yfinance_scan(self, universe: List[str]) -> List[str]:
        """
        Scans the fallback universe for Momentum + Volume using YFinance.
        """
        targets = []
        try:
            # Batch download for speed
            string_tickers = " ".join(universe)
            data = yf.download(universe, period="5d", interval="1d", group_by='ticker', progress=False)
            
            for sym in universe:
                try:
                    df = data[sym]
                    if df.empty: continue
                    
                    last = df.iloc[-1]
                    prev = df.iloc[-2]
                    
                    # Metrics
                    change_pct = ((last["Close"] - prev["Close"]) / prev["Close"]) * 100
                    volume = last["Volume"]
                    avg_vol = df["Volume"].mean()
                    vol_ratio = 0 if avg_vol == 0 else volume / avg_vol
                    
                    # CRITERIA:
                    # 1. Liquidity: Volume > 1M (Approx) or just relative volume > 1.0
                    # 2. Momentum: Up > 1% today OR Huge Volume (1.5x average)
                    
                    if volume > 1_000_000:
                        if change_pct > 1.5 or vol_ratio > 1.2:
                            # Basic score to sort by later if needed, but for now just include
                            targets.append(sym)
                            
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"⚠️ HUNT: YFinance Scan Error: {e}")
            return universe[:10] # Worst case, return top 10 safely
            
        print(f"🔎 HUNT: YFinance found {len(targets)} active movers.")
        return targets
