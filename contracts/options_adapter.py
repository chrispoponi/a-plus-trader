import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from configs.settings import settings

class OptionsAdapter:
    def __init__(self):
        # We need two base URLs:
        # 1. Trading/Paper API for Contracts/Orders (v2)
        # 2. Data API for Quotes/Snapshots (v1beta1)
        self.trading_url = settings.APCA_API_BASE_URL # e.g. https://paper-api...
        self.data_url = "https://data.alpaca.markets" # Fixed for options data
        
        self.headers = {
            "APCA-API-KEY-ID": settings.APCA_API_KEY_ID,
            "APCA-API-SECRET-KEY": settings.APCA_API_SECRET_KEY,
            "accept": "application/json"
        }
        
    def _get_trading(self, endpoint: str, params: Dict = None):
        # v2 on Paper URL
        url = f"{self.trading_url}/v2/options/{endpoint}"
        # print(f"DEBUG TRADING: {url}")
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            if resp.status_code == 200: return resp.json()
            else: 
                print(f"Trading API Error {resp.status_code}: {resp.text}")
                return None
        except Exception as e:
            print(f"Trading Req Fail: {e}")
            return None

    def _get_data(self, endpoint: str, params: Dict = None):
        # v1beta1 on Data URL
        url = f"{self.data_url}/v1beta1/options/{endpoint}"
        # print(f"DEBUG DATA: {url}")
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            if resp.status_code == 200: return resp.json()
            else:
                print(f"Data API Error {resp.status_code}: {resp.text}")
                return None
        except Exception as e:
            print(f"Data Req Fail: {e}")
            return None

    def get_chain(self, symbol: str) -> pd.DataFrame:
        """
        Fetches ALL active contracts for a symbol.
        Warning: Can be large. We should filter by expiry if possible.
        """
        # Alpaca allows filtering by expiry range?
        # params = {"underlying_symbol": symbol, "status": "active", "limit": 10000}
        # Actually, let's fetch basic chain.
        data = self._get_trading("contracts", {"underlying_symbol": symbol, "status": "active", "limit": 1000})
        if not data or "option_contracts" not in data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data["option_contracts"])
        
        # Enforce Types
        if 'strike_price' in df.columns:
            df['strike_price'] = pd.to_numeric(df['strike_price'], errors='coerce')
            
        return df

    def get_quotes(self, symbols: List[str]) -> Dict[str, float]:
        """
        Returns Ask Price for list of symbols.
        """
        if not symbols: return {}
        sym_str = ",".join(symbols)
        # Endpoint expects 'symbols' plural for multi-fetch
        # Use Data helper
        data = self._get_data("snapshots", {"symbols": sym_str, "feed": "indicative"})
        # Quotes endpoint provides distinct bid/ask. Snapshots provides latest.
        # Let's use snapshots for latest quote.
        
        results = {}
        if not data or "snapshots" not in data:
            return {}
            
        for sym, snap in data["snapshots"].items():
            # Get Ask Price (Buying) or Bid (Selling)
            # Default to Mid?
            quote = snap.get("latestQuote", {})
            ask = float(quote.get("ap", 0)) # ap = ask price
            bid = float(quote.get("bp", 0)) # bp = bid price
            
            # If 0, try latestTrade?
            if ask == 0:
                trade = snap.get("latestTrade", {})
                ask = float(trade.get("p", 0))
                bid = ask
                
            results[sym] = {"ask": ask, "bid": bid}
            
        return results

    def resolve_condor(self, symbol: str, current_price: float, dte: int = 1) -> Dict[str, str]:
        """
        Resolves 4 legs for an Iron Condor.
        Returns OCC Strings: {long_put, short_put, short_call, long_call}
        """
        # 1. Target Expiry
        target_date_str = (datetime.now() + timedelta(days=dte)).strftime("%Y-%m-%d")
        print(f"DEBUG: Resolving for {target_date_str}")
        
        # 2. Fetch Contracts (Fetch Broad, Filter Local)
        # API Date filtering can be flaky.
        params = {
            "underlying_symbol": symbol,
            "status": "active",
            "limit": 10000 # Ensure we get Puts (SPY chain is huge)
            # "expiration_date": target_date 
        }
        res = self._get_trading("contracts", params)
        if not res or "option_contracts" not in res:
             print(f"No contracts found for {symbol}")
             return {}
             
        df = pd.DataFrame(res["option_contracts"])
        if df.empty: return {}
        
        # Enforce Types
        if 'strike_price' in df.columns:
            df['strike_price'] = pd.to_numeric(df['strike_price'], errors='coerce')

        # Filter Date
        # Ensure string comparison matches
        if 'expiration_date' in df.columns:
            df = df[df['expiration_date'] == target_date_str]
            
        if df.empty:
            print(f"No contracts found for Expiry {target_date_str}")
            return {}
        
        # 3. Calculate Targets (SPY/QQQ Logic)
        # 1DTE Income: Short Strikes ~1.0-1.5% OTM
        dist = current_price * 0.012 # 1.2%
        width = 2.0 # $2 wide wings
        
        target_short_put = current_price - dist
        target_long_put = target_short_put - width
        
        target_short_call = current_price + dist
        target_long_call = target_short_call + width
        
        # 4. Find Closest Matches
        def get_closest(type_, price):
            subset = df[df['type'] == type_].copy()
            if subset.empty: return None
            # Minimize difference
            subset['diff'] = (subset['strike_price'] - price).abs()
            best = subset.nsmallest(1, 'diff').iloc[0]
            # Debug
            # print(f"Target {type_} {price} -> Found {best['strike_price']} ({best['symbol']})")
            return best['symbol']
            
        legs = {
            "long_put": get_closest("put", target_long_put),
            "short_put": get_closest("put", target_short_put),
            "short_call": get_closest("call", target_short_call),
            "long_call": get_closest("call", target_long_call)
        }
        
        # Validation: Ensure all legs found and unique
        if not all(legs.values()):
            print(f"Failed to find all legs for {symbol} (Date: {target_date_str}). Found: {legs}")
            return {}
            
        return legs

options_adapter = OptionsAdapter()
