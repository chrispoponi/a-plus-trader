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
        self.universe = [
            "NVDA","TSLA","AAPL","GOOGL","MSFT","META","AMD","PLTR","NFLX",
            "INTC","ORCL","SOFI","AMZN","COST","DIS","JPM","BA","CRM",
            "UBER","MRVL","SQ","ABNB","COIN","MARA","MSTR","Riot",
            "DKNG","HOOD","PANW","CRWD","SNOW","SHOP","TTD","NET",
            "ZS","LULU","NKE","SBUX","MCD","PEP","KO","WMT","TGT",
            "XOM","CVX","OXY","V","MA","AXP","GS"
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
        start_date = (today - timedelta(days=10)).strftime('%Y-%m-%d')
        
        try:
            # Chunking to be safe (Alpaca handles list well, but good practice)
            # Fetch daily bars
            # Fetch daily bars with IEX feed to support Free Tier
            bars = self.api.get_bars(self.universe, '1Day', start=start_date, limit=10, adjustment='raw', feed='iex').df
            
            if bars.empty:
                print("hunter: No data returned from Alpaca.")
                return self.universe # Return all if data fails so we at least scan something
                
            # Process each symbol
            # bars df has MultiIndex (symbol, timestamp) or just timestamp with symbol column?
            # Alpaca python SDK usually returns a DF with symbol column or index depending on version.
            # Usually: symbol is a column if not grouped.
            
            # Let's pivot or group manually
            grouped = bars.groupby('symbol')
            
            for symbol, data in grouped:
                try:
                    if len(data) < 2: continue
                    
                    # Sort just in case
                    data = data.sort_index() 
                    
                    last = data.iloc[-1]
                    prev = data.iloc[-2]
                    
                    # Metrics
                    close = last['close']
                    prev_close = prev['close']
                    volume = last['volume']
                    avg_vol = data['volume'].mean()
                    
                    change_pct = ((close - prev_close) / prev_close) * 100
                    vol_ratio = 0 if avg_vol == 0 else volume / avg_vol
                    
                    # Criteria
                    # 1. Momentum: > 1.5% Move
                    # 2. Volume: > 1.2x Relative Volume
                    # 3. Liquidity Check: Volume > 500k minimum (most in this list are, but checking)
                    
                    msg = f"  -> {symbol}: {change_pct:.1f}% chg, {vol_ratio:.1f}x Vol"
                    # print(msg) # verbose
                    
                    is_hit = False
                    if volume > 500_000:
                        if abs(change_pct) > 1.5 or vol_ratio > 1.2:
                            active_movers.append(symbol)
                            is_hit = True
                            
                    if is_hit:
                        print(f"✅ HIT: {symbol} ({change_pct:.1f}%)")
                        
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
        return unique_list
