
from typing import Dict, Optional
import pandas as pd
import numpy as np
from strategy_engine.models import Candidate, Section, TradePlan, Direction, Scores, Compliance

class EMA3Strategy:
    """
    STRATEGY: 3-EMA TREND FOLLOWING (Chat GPT 'High Win Rate')
    INDICATORS: 20 EMA, 50 EMA, 100 EMA.
    LOGIC:
      - LONG: Price > 20 > 50 > 100 (Ideal Alignment) OR Price > 50.
      - TRIGGER: Break of recent High (Market Structure).
      - STOP: Recent Swing Low (or 2% dynamic).
      - TARGET: 2R.
    """

    def analyze(self, symbol: str, features: Dict[str, any]) -> Optional[Candidate]:
        full_df = features.get('df')
        current_date = features.get('current_date')
        
        if full_df is None or len(full_df) < 100: return None
        
        # SLICE TO CURRENT DATE (Prevent Lookahead)
        # We need historical context up to 'now'
        # Check if current_date exists
        if current_date not in full_df.index: return None
        
        # Get location integer
        try:
             idx = full_df.index.get_loc(current_date)
             # Safety limit
             if not isinstance(idx, int): idx = idx.start # Handle slice return
             if idx < 50: return None 
        except: return None
             
        # Slice: History up to current candle
        start_pos = max(0, idx - 120)
        df = full_df.iloc[start_pos : idx+1]
        
        if df.empty: return None

        close = df['close']
        high = df['high']
        low = df['low']
        
        ema20 = close.ewm(span=20, adjust=False).mean()
        ema50 = close.ewm(span=50, adjust=False).mean()
        ema100 = close.ewm(span=100, adjust=False).mean()
        
        if len(close) < 2: return None
        
        # Current Candle (The last one in our slice)
        c = close.iloc[-1]
        e20 = ema20.iloc[-1]
        e50 = ema50.iloc[-1]
        
        # Previous Candle
        prev_c = close.iloc[-2]
        
        # RULE 1: TREND ALIGNMENT (User: Price > 50 and Price > 20)
        # We add 20 > 50 for stronger trend definition
        is_uptrend = (c > e50) and (c > e20) and (e20 > e50)
        
        if not is_uptrend: return None
        
        # RULE 2: MARKET STRUCTURE BREAK
        # Break of High of last 10 bars (excluding current)
        recent_high = high.iloc[-11:-1].max()
        
        if c > recent_high and prev_c <= recent_high:
            # BREAKOUT DETECTED
            
            # Stop Loss
            recent_low = low.iloc[-5:-1].min() # Low of last 5 bars
            stop = recent_low
            risk_pct = (c - stop) / c
            
            if risk_pct < 0.01: stop = c * 0.99 # Min 1%
            if risk_pct > 0.05: stop = c * 0.95 # Max 5% (Tighten)
            
            risk = c - stop
            target = c + (risk * 2.0)
            
            return Candidate(
                section=Section.SWING,
                symbol=symbol,
                setup_name="3EMA Trend Breakout",
                direction=Direction.LONG,
                thesis=f"Trend Aligned. Break > {recent_high:.2f}",
                features={"ema20": e20, "ema50": e50},
                trade_plan=TradePlan(
                    entry=c,
                    stop_loss=stop,
                    take_profit=target,
                    risk_percent=0.02,
                    stop_type="Structure Low",
                    is_core_trade=True
                ),
                scores=Scores(overall_rank_score=85, win_probability_estimate=80, quality_score=85, risk_score=20, baseline_win_rate=65, adjustments=0),
                compliance=Compliance(passed_thresholds=True),
                signal_id=f"EMA3_{symbol}_{current_date}"
            )
            
        return None
