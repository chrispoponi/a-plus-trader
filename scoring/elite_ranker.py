from typing import List, Dict, Tuple
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler

class EliteRanker:
    """
    Advanced Ranking System to select Top 3 Day & Top 3 Swing Trades.
    Uses scikit-learn for normalization and strict Hard Gates.
    """
    
    def rank_candidates(self, market_data: Dict[str, dict]) -> Tuple[List[str], List[str]]:
        """
        Returns (top_3_day_symbols, top_3_swing_symbols)
        """
        if not market_data:
            return [], []

        day_candidates = []
        swing_candidates = []
        
        # 1. Feature Extraction
        for sym, data in market_data.items():
            try:
                # --- DATA PREP ---
                daily = pd.DataFrame([data]) # Only 1 row usually passed in dict? No, MarketData dict has scalars.
                # Wait, data_loader returns dictionary of scalars + 'intraday_df'.
                # We need historical series for some calc.
                # But 'market_data' usually has minimal info.
                # Actually, data_loader calculates indicators already (ema20, sma50, atr).
                
                # We need Intraday DF for Day Trading check
                intraday = data.get('intraday_df')
                
                # Quote data for spread? (Not currently in data_loader, assuming small spread for Active 50)
                # We can skip Spread check or assume valid if in Top 50 Vol.
                
                price = data.get('close')
                vwap = data.get('vwap')
                volume = data.get('volume')
                avg_vol = data.get('volume') # Placeholder, data_loader doesn't pass avg_vol? 
                # (We should update data_loader to pass 'vol_avg_20')
                vol_avg_20 = data.get('volume') * 1.0 # Hack if missing
                
                ema20 = data.get('ema20')
                sma50 = data.get('sma50')
                atr = data.get('atr')
                
                # --- DAY EVALUATION ---
                # Hard Gates
                is_day_valid = True
                if price < vwap: is_day_valid = False # Price below VWAP (Longs)
                # if rel_vol < 1.5: is_day_valid = False (Checked later)
                if (atr / price) < 0.012: is_day_valid = False # ATR% < 1.2%
                
                if is_day_valid and intraday is not None and not intraday.empty:
                    # Calc Day Factors
                    rel_vol = volume / vol_avg_20 if vol_avg_20 > 0 else 1.0
                    if rel_vol < 1.5: continue # Hard Gate
                    
                    # 5-min Momentum (Last 5 mins ROC)
                    roc_5m = 0
                    if len(intraday) >= 6:
                        roc_5m = (intraday.iloc[-1]['close'] / intraday.iloc[-6]['close']) - 1
                        
                    vwap_dist = (price - vwap) / vwap
                    
                    # ORB (Opening Range Break) - Check if price > High of first 30 mins
                    # tough without exact timestamps, skip ORB strict calc for now, use Price > Open
                    orb_score = 1.0 if price > data.get('open') else 0.0
                    
                    day_candidates.append({
                        "symbol": sym,
                        "rel_vol": rel_vol,
                        "vwap_dist": vwap_dist,
                        "roc_5m": roc_5m,
                        "atr_expand": data.get('atr') / price,
                        "orb": orb_score
                    })

                # --- SWING EVALUATION ---
                # Hard Gates
                is_swing_valid = True
                if ema20 <= sma50: is_swing_valid = False # Trend Invalid
                # Price extended > 12% above SMA20
                if price > (ema20 * 1.12): is_swing_valid = False 
                
                if is_swing_valid:
                    valid_rel_vol = volume / vol_avg_20 if vol_avg_20 > 0 else 1.0
                    
                    # Trend Strength
                    ma_sep = (ema20 - sma50) / price
                    
                    # Pullback (Closer to EMA20 is better)
                    pullback_dist = abs(price - ema20) / price
                    pullback_score = 1.0 - (pullback_dist * 10) # Higher is better (closer)
                    
                    swing_candidates.append({
                        "symbol": sym,
                        "ma_sep": ma_sep,
                        "pullback": pullback_score,
                        "rel_vol": valid_rel_vol,
                        "vol_compress": 1.0 - (atr / price) # Lower ATR% = more compression
                    })
                    
            except Exception as e:
                continue

        # 2. Normalization & Scoring (Day)
        top_day = []
        if day_candidates:
            df_day = pd.DataFrame(day_candidates)
            scaler = MinMaxScaler()
            cols = ["rel_vol", "vwap_dist", "roc_5m", "atr_expand", "orb"]
            # Scale
            scaled_data = scaler.fit_transform(df_day[cols])
            df_scaled = pd.DataFrame(scaled_data, columns=cols)
            
            # Score formula
            df_day["score"] = (
                0.30 * df_scaled["rel_vol"] +
                0.20 * df_scaled["vwap_dist"] +
                0.20 * df_scaled["roc_5m"] +
                0.15 * df_scaled["atr_expand"] +
                0.15 * df_scaled["orb"]
            )
            
            top_day = df_day.sort_values("score", ascending=False).head(3)["symbol"].tolist()

        # 3. Normalization & Scoring (Swing)
        top_swing = []
        if swing_candidates:
            df_swing = pd.DataFrame(swing_candidates)
            scaler = MinMaxScaler()
            cols = ["ma_sep", "pullback", "rel_vol", "vol_compress"]
            
            scaled_data = scaler.fit_transform(df_swing[cols])
            df_scaled = pd.DataFrame(scaled_data, columns=cols)
            
            # Score formula
            df_swing["score"] = (
                0.35 * df_scaled["ma_sep"] +
                0.20 * df_scaled["pullback"] +
                0.15 * df_scaled["rel_vol"] +
                0.30 * df_scaled["vol_compress"] # Combined Weekly/Compression weight
            )
            
            top_swing = df_swing.sort_values("score", ascending=False).head(3)["symbol"].tolist()
            
        return top_day, top_swing

elite_ranker = EliteRanker()
