from alpaca_trade_api.rest import REST, TimeFrame
from configs.settings import settings
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, Any, List

class DataLoader:
    def __init__(self):
        if settings.APCA_API_KEY_ID:
            self.api = REST(
                settings.APCA_API_KEY_ID,
                settings.APCA_API_SECRET_KEY,
                base_url=settings.APCA_API_BASE_URL
            )
        else:
            self.api = None
            print("DATA LOAD ERROR: No Alpaca Keys. Real data disabled.")

    def fetch_snapshot(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Fetches daily bars for the last 100 days to calculate indicators.
        Returns a dictionary of symbol -> feature_dict.
        """
        if not self.api:
            return {}

        results = {}
        
        # Determine date range (enough for 50 SMA)
        end_date = (datetime.now()).strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=200)).strftime('%Y-%m-%d')

        print(f"DEBUG: Fetching data for {len(symbols)} symbols...")
        
        # Alpaca allows chunking, but for <100 symbols one call might work or we loop
        # We'll batch to be safe and prevent timeouts on Render Free Tier
        chunk_size = 10
        chunks = [symbols[i:i + chunk_size] for i in range(0, len(symbols), chunk_size)]
        
        for chunk in chunks:
            try:
                print(f"DEBUG: Fetching chunk of {len(chunk)} symbols...")
                bars = self.api.get_bars(
                    chunk,
                    TimeFrame.Day,
                    start=start_date,
                    end=end_date,
                    adjustment='raw',
                    feed='iex'
                ).df
                
                if bars.empty:
                    print("DEBUG: Chunk returned empty.")
                    continue

                # Process per symbol
                for symbol in chunk:
                    # Handle MultiIndex logic
                    if isinstance(bars.index, pd.MultiIndex):
                        try:
                            # Alpaca SDK usually sets symbol as index level 0
                            # But sometimes it's a column if we reset index?
                            # Standard SDK behavior:
                            sym_data = bars.xs(symbol)
                        except KeyError:
                             continue
                    elif 'symbol' in bars.columns:
                        sym_data = bars[bars['symbol'] == symbol].copy()
                    else:
                        continue # Unknown format

                    if len(sym_data) < 20: # RELAXED CONSTRAINT (Was 55)
                        print(f"DEBUG: Dropping {symbol} - Insufficient History ({len(sym_data)} < 20)")
                        continue 

                    processed_data = self._calculate_technicals(sym_data)
                    results[symbol] = processed_data
                    
            except Exception as e:
                print(f"Data Fetch Error (Chunk): {e}")
                continue # Skip bad chunk, keep going
            
        return results

    def _calculate_technicals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Computes EMA20, SMA50, ATR, Volume Profile.
        Takes the last row as the 'current' state.
        """
        # Ensure sorted
        df = df.sort_index()

        # Close
        close = df['close']
        
        # Indicators
        df['ema20'] = close.ewm(span=20, adjust=False).mean()
        df['sma50'] = close.rolling(window=50).mean()
        
        # ATR (14)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        # Volume
        df['vol_avg_20'] = df['volume'].rolling(20).mean()
        
        # Get latest row
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Patterns
        is_hammer = False
        body = abs(curr['close'] - curr['open'])
        lower_wick = min(curr['close'], curr['open']) - curr['low']
        upper_wick = curr['high'] - max(curr['close'], curr['open'])
        if lower_wick > (2 * body) and upper_wick < body:
            is_hammer = True
            
        # Volume Check
        vol_dry_up = curr['volume'] < curr['vol_avg_20'] * 0.7
        
        return {
            "close": float(curr['close']),
            "open": float(curr['open']),
            "high": float(curr['high']),
            "low": float(curr['low']),
            "volume": int(curr['volume']),
            "ema20": float(curr['ema20']),
            "sma50": float(curr['sma50']),
            "atr": float(curr['atr']),
            "candle_pattern": "hammer" if is_hammer else "normal",
            "volume_dry_up": bool(vol_dry_up),
            # Helpers for logic
            "prev_close": float(prev['close'])
        }

data_loader = DataLoader()
