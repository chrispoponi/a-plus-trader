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
        print("\n🔎 HUNT [DEBUG]: Initiating Autonomous Market Hunt...")
        candidates = []
        
        # 1. Primary: Finviz
        if FINVIZ_AVAILABLE:
            try:
                print("🔎 HUNT [DEBUG]: Attempting Finviz Screener...")
                candidates = self._run_finviz_screener()
                print(f"🔎 HUNT [DEBUG]: Finviz returned {len(candidates)} candidates.")
            except Exception as e:
                print(f"⚠️ HUNT [ERROR]: Finviz Failed ({e}).")
        else:
             print("⚠️ HUNT [DEBUG]: Finviz library not available.")
        
        # 2. Fallback: YFinance Scan of Core List
        # If Finviz returned too few (<5) or failed, run the internal scanner
        if len(candidates) < 5:
            print(f"🔎 HUNT [DEBUG]: Triggering Fallback (Candidates: {len(candidates)}). Scanning {len(self.fallback_core)} core tickers...")
            fallback_candidates = self._run_yfinance_scan(self.fallback_core)
            candidates.extend(fallback_candidates)
            
        final_list = list(set(candidates))
        print(f"✅ HUNT [DEBUG]: Hunt Complete. Returning {len(final_list)} unique targets.")
        return final_list

    def _run_finviz_screener(self) -> List[str]:
        """
        Queries Finviz for 'Top Gainers' with structural filters.
        """
        try:
            foverview = Overview()
            # Filters: Avg Vol > 1M, Price > $10, SMA50 Up, SMA20 Up
            filters_dict = {
                'Average Volume': 'Over 1M',
                'Price': 'Over $10',
                '50-Day Simple Moving Average': 'Price above SMA50',
                '20-Day Simple Moving Average': 'Price above SMA20', 
            }
            
            foverview.set_filter(filters_dict=filters_dict)
            # Get top 30
            df = foverview.screener_view(order='-volume', limit=30)
            
            if df.empty:
                return []
                
            return df['Ticker'].tolist()
        except Exception as e:
            # Re-raise to let parent handle logging
            raise e

    def _run_yfinance_scan(self, universe: List[str]) -> List[str]:
        """
        Scans the fallback universe for Momentum + Volume using YFinance.
        """
        targets = []
        try:
            print(f"🔎 HUNT [DEBUG]: Downloading YFinance data for {len(universe)} symbols...")
            # Batch download for speed - use threads=False to avoid some hanging issues on Docker
            data = yf.download(universe, period="5d", interval="1d", group_by='ticker', progress=False, threads=True)
            print("🔎 HUNT [DEBUG]: Download complete. Processing DataFrames...")
            
            for sym in universe:
                try:
                    # Handle multi-level column issues if yfinance returns them
                    # If download fails for one, it might be missing from 'data' columns
                    if sym not in data.columns.levels[0] if isinstance(data.columns, pd.MultiIndex) else sym not in data:
                        continue

                    df = data[sym]
                    if df.empty or len(df) < 2: 
                        continue
                    
                    last = df.iloc[-1]
                    prev = df.iloc[-2]
                    
                    # Safe access to scalar values
                    close_last = float(last["Close"].iloc[0]) if isinstance(last["Close"], pd.Series) else float(last["Close"])
                    close_prev = float(prev["Close"].iloc[0]) if isinstance(prev["Close"], pd.Series) else float(prev["Close"])
                    vol_last = float(last["Volume"].iloc[0]) if isinstance(last["Volume"], pd.Series) else float(last["Volume"])
                    
                    avg_vol = df["Volume"].mean()
                    avg_vol = float(avg_vol.iloc[0]) if isinstance(avg_vol, pd.Series) else float(avg_vol)
                    
                    change_pct = ((close_last - close_prev) / close_prev) * 100
                    vol_ratio = 0 if avg_vol == 0 else vol_last / avg_vol
                    
                    # Logic: Big Volume OR Big Move
                    if vol_last > 1_000_000:
                        if change_pct > 1.5 or vol_ratio > 1.2:
                            targets.append(sym)
                            # print(f"  -> Found {sym}: {change_pct:.1f}% Move, {vol_ratio:.1f}x Vol")
                            
                except Exception as inner_e:
                    # print(f"  -> Error processing {sym}: {inner_e}")
                    continue
                    
        except Exception as e:
            print(f"⚠️ HUNT [ERROR]: YFinance Scan Critical Fail: {e}")
            return universe[:5] # Emergency Valve
            
        print(f"🔎 HUNT [DEBUG]: YFinance Scanned. Found {len(targets)} active movers.")
        return targets
