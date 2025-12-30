from typing import List
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import pytz
# New SDK
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockMostActivesRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from configs.settings import settings

class MarketHunter:
    """
    Autonomous Market Scanner (The Hunter) - Dynamic Mode.
    
    Uses Alpaca 'Most Actives' to pull the top 100 volume leaders,
    then filters and ranks them into two buckets:
    1. Day Trade (Liquidity + Momentum + ATR)
    2. Swing Trade (Trend + Liquidity + ROC)
    
    Returns exactly 50 symbols.
    """
    
    def __init__(self):
        try:
            self.client = StockHistoricalDataClient(
                settings.APCA_API_KEY_ID,
                settings.APCA_API_SECRET_KEY
            )
            print("hunter: Alpaca Data Client (v2) Established.")
        except Exception as e:
            print(f"hunter: Connection Failed: {e}")
            self.client = None
            
        # Fallback list just in case Mainnet Screener fails (e.g. on Paper/Mock)
        self.fallback_universe = [
            "NVDA","TSLA","AAPL","AMD","AMZN","META","GOOGL","MSFT","NFLX","COIN",
            "MARA","PLTR","DKNG","ROKU","SHOP","SQ","UBER","BA","DIS","PYPL",
            "INTC","AMD","SOFI","AFRM","RFA","F","GM","T","VZ","WBD",
            "PARA","SNAP","PINS","M","AAL","CCL","NCLH","RCL","DAL","UAL",
            "BAC","C","JPM","WFC","XOM","CVX","OXY","MRO","DVN","APA"
        ]

    def hunt(self) -> List[str]:
        """
        Executes the 'Most Actives' scan and bucket logic.
        """
        if not self.client:
            print("hunter [ERROR]: No Client. Returning Fallback.")
            return self.fallback_universe

        print(f"\n🔎 HUNT: Scanning 'Most Actives' via Alpaca...")
        
        try:
            # 1. Pull most active stocks (volume)
            # Note: This endpoint might require a funded/live key for full data?
            # On Paper/Free tier it might be limited. We try.
            actives = self.client.get_stock_most_actives(
                StockMostActivesRequest(by="volume", top=100)
            )
            
            raw_symbols = [a.symbol for a in actives]
            print(f"hunter: Retrieved {len(raw_symbols)} active symbols.")
            
            if not raw_symbols:
                 print("hunter: No actives returned. Using fallback.")
                 return self.fallback_universe[:50]

            # 2. Pull 60 days of daily bars
            end = datetime.now(pytz.UTC)
            start = end - timedelta(days=60)
            
            # Batch fetch
            bars = self.client.get_stock_bars(
                StockBarsRequest(
                    symbol_or_symbols=raw_symbols,
                    timeframe=TimeFrame.Day,
                    start=start,
                    end=end,
                    feed='iex'  # Use IEX for free tier compatibility
                )
            ).df
            
            if bars.empty:
                print("hunter: No bar data returned.")
                return self.fallback_universe[:50]

            results = []
            
            # Process each symbol
            # Alpaca-py returns MultiIndex (symbol, timestamp)
            # Get list of unique symbols in the dataframe
            if isinstance(bars.index, pd.MultiIndex):
                unique_syms = bars.index.get_level_values(0).unique()
            else:
                # Should be multi-index, but handle edge case
                unique_syms = bars['symbol'].unique() if 'symbol' in bars.columns else []

            for sym in unique_syms:
                try:
                    # Extract dataframe for this symbol
                    if isinstance(bars.index, pd.MultiIndex):
                        df = bars.loc[sym].copy()
                    else:
                        df = bars[bars['symbol'] == sym].copy()
                        
                    if len(df) < 50: continue

                    # Indicators
                    df["sma20"] = df["close"].rolling(20).mean()
                    df["sma50"] = df["close"].rolling(50).mean()
                    df["atr"] = (df["high"] - df["low"]).rolling(14).mean()

                    price = df["close"].iloc[-1]
                    volume = df["volume"].iloc[-1]
                    avg_vol = df["volume"].rolling(20).mean().iloc[-1]

                    # Basic Filters
                    # Liquidity: > 2M Avg Vol
                    # Price: $5 - $500
                    if avg_vol < 2_000_000 or price < 5 or price > 500:
                        continue

                    rel_vol = volume / avg_vol if avg_vol > 0 else 1.0
                    atr_pct = df["atr"].iloc[-1] / price
                    
                    # Rate of Change
                    roc_1d = (df["close"].iloc[-1] / df["close"].iloc[-2]) - 1
                    roc_5d = (df["close"].iloc[-1] / df["close"].iloc[-6]) - 1

                    # Scores
                    day_score = (0.45 * rel_vol) + (0.35 * roc_1d) + (0.20 * atr_pct)
                    
                    trend_diff = (df["sma20"].iloc[-1] - df["sma50"].iloc[-1]) / price
                    swing_score = (0.60 * trend_diff) + (0.25 * rel_vol) + (0.15 * roc_5d)
                    
                    trend_up = df["sma20"].iloc[-1] > df["sma50"].iloc[-1]

                    results.append({
                        "symbol": sym,
                        "trend_20_over_50": trend_up,
                        "day_score": day_score,
                        "swing_score": swing_score
                    })
                except Exception:
                    continue
            
            print(f"hunter: Calculated scores for {len(results)} valid candidates.")
            
            # 3. Select Top 50
            res_df = pd.DataFrame(results)
            if res_df.empty:
                 return self.fallback_universe[:50]

            # Day Bucket (Top 25)
            day_bucket = res_df.sort_values("day_score", ascending=False).head(25)
            
            # Swing Bucket (Top 25 who are trending up)
            swing_bucket = res_df[res_df["trend_20_over_50"]].sort_values("swing_score", ascending=False).head(25)
            
            # Merge
            final_df = pd.concat([day_bucket, swing_bucket]).drop_duplicates("symbol").head(50)
            
            final_list = final_df["symbol"].tolist()
            
            # Backfill if we have < 50
            if len(final_list) < 50:
                needed = 50 - len(final_list)
                print(f"hunter: Lists short ({len(final_list)}). Backfilling from fallback.")
                for f in self.fallback_universe:
                    if f not in final_list:
                        final_list.append(f)
                        if len(final_list) >= 50: break
            
            print(f"🔎 HUNT: Returning {len(final_list)} Dynamic Tickers.")
            return final_list

        except Exception as e:
            print(f"hunter [ERROR]: {e}")
            return self.fallback_universe
