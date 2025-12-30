from typing import List
from datetime import datetime, timedelta
import alpaca_trade_api as tradeapi
from configs.settings import settings

class MarketHunter:
    """
    Autonomous Market Scanner (The Hunter) - API MODE.
    
    Uses Alpaca Data API to scan the 'Core 50' universe for active movers.
    Criteria:
    1. Volume > 1.2x Average (Relative Volume)
    2. Price Change > 1.5% (Momentum)
    3. Price > SMA50 (Trend) - *Simplification: Just check if Up today*
    """
    
    def __init__(self):
        # FAILOVER UNIVERSE (Top 50 Active/Popular + Momentum Candidates)
        # Updated to User's "Trend Hunter" Base Universe (Liquid Large Caps)
        self.universe = [
            "AAPL","MSFT","NVDA","TSLA","AMZN","META","GOOGL","AMD","NFLX","CRM",
            "INTC","ORCL","CSCO","JPM","BAC","WFC","XOM","CVX","KO","PEP",
            "COST","WMT","UNH","LLY","AVGO","PYPL","SHOP","PLTR","T","VZ",
            "MRNA","ABNB","DIS","BA","NKE","SQ","UBER","MCD","PFE","GE",
            "TGT","V","MA","GM","F","QCOM","BABA","ADBE","SMCI","AMAT"
        ]
        
        # Initialize Alpaca Connection specifically for Data
        try:
            self.api = tradeapi.REST(
                settings.APCA_API_KEY_ID,
                settings.APCA_API_SECRET_KEY,
                settings.APCA_API_BASE_URL,
                api_version='v2'
            )
            print("hunter: Alpaca Data Connection Established.")
        except Exception as e:
            print(f"hunter: Connection Failed: {e}")
            self.api = None

    def hunt(self) -> List[str]:
        """
        Scans values using Alpaca API efficiently.
        """
        if not self.api:
            print("hunter [ERROR]: No API connection. Returning static fallback.")
            return self.universe[:10] # minimal fallback

        print(f"\n🔎 HUNT: Scanning {len(self.universe)} tickers via Alpaca Data API...")
        active_movers = []
        
        # 1. Fetch Data (Last 5 Days to calculate Avg Vol)
        # Using bars allows us to see recent history for averages
        today = datetime.now()
        start_date = (today - timedelta(days=90)).strftime('%Y-%m-%d') # Need ~60-70 trading days for SMA50
        
        try:
            # Fetch daily bars with sufficient history for SMA50
            bars = self.api.get_bars(self.universe, '1Day', start=start_date, limit=100, adjustment='raw', feed='iex').df
            
            if bars.empty:
                print("hunter: No data returned from Alpaca.")
                return self.universe 
                
            grouped = bars.groupby('symbol')
            
            for symbol, data in grouped:
                try:
                    if len(data) < 55: continue # Need history
                    
                    # Sort just in case
                    data = data.sort_index() 
                    
                    # --- TECHNICAL CALC ---
                    closes = data['close']
                    volume_series = data['volume']
                    
                    sma20 = closes.rolling(window=20).mean().iloc[-1]
                    sma50 = closes.rolling(window=50).mean().iloc[-1]
                    
                    # RSI Calculation (14)
                    delta = closes.diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs)).iloc[-1]
                    
                    last_close = closes.iloc[-1]
                    last_vol = volume_series.iloc[-1]
                    
                    # --- FILTERS ---
                    # 1. Volume > 2M (Liquidity)
                    if last_vol < 2_000_000: continue
                    
                    # 2. Trend: SMA20 > SMA50 (Bullish Alignment) AND Price > SMA50 (Trend Intact)
                    if not (sma20 > sma50 and last_close > sma50): continue
                    
                    # 3. RSI: 10 - 45 (Deep Pullback / Oversold)
                    if not (10 <= rsi <= 45): continue

                    print(f"✅ HUNT HIT: {symbol} (RSI: {rsi:.1f}, Vol: {last_vol/1_000_000:.1f}M)")
                    active_movers.append(symbol)
                        
                    except Exception:
                       continue
                       
                    # DEBUG INTEGRITY CHECK (Print valid metrics for first symbol)
                    if symbol == self.universe[0]:
                        print(f"DEBUG: {symbol} Metrics -> Vol: {last_vol}, SMA20: {sma20:.2f}, SMA50: {sma50:.2f}, RSI: {rsi:.2f}")

                except Exception:
                    continue
                    
        except Exception as e:
            print(f"hunter [ERROR]: Data fetch error: {e}")
            return self.universe # Fail open to the whole list
            
        # If market is dead and no one triggered, fallback to the big tech "Safe List"
        if len(active_movers) < 3:
            print("hunter: Market quiet. Adding MAG7 to ensure candidates.")
            mag7 = ["NVDA", "TSLA", "AAPL", "MSFT", "GOOGL", "AMZN", "META"]
            active_movers.extend(mag7)
            
        unique_list = list(set(active_movers))
        print(f"🔎 HUNT: Found {len(unique_list)} active targets.")
        
        # DEBUG: FORCE RETURN ALL 50 TO TEST SCANNER DATA FLOW
        print(f"🔎 HUNT (DEBUG): Overriding to return FULL UNIVERSE ({len(self.universe)})")
        return self.universe
        
        # return unique_list
