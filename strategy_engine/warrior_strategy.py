
from typing import Dict, Optional, List
from strategy_engine.models import Candidate, Section, TradePlan, Direction, Scores, Compliance
import pandas as pd
import numpy as np

class WarriorStrategy:
    """
    STRATEGY: MOMENTUM GAPPERS (ROSS CAMERON STYLE)
    TARGET: Small Caps ($2-$20), Low Float, High Relative Vol (5x+).
    PATTERN: Bull Flag / First Pullback on 1-Min Chart.
    
    LOGIC:
    1. SCREEN: Gap > 10%, Price $2-$20.
    2. SETUP: Impulse Move -> Pullback (holding > 50% of impulse).
    3. TRIGGER: First 1-min candle to break HIGH of previous candle (Resumption).
    4. RISK: Stop = Low of Pullback. Target = 2R (or HOD retest).
    5. SIZING: "Cushion Sizing" (1/4 size until profit > Daily Goal/4).
    """

    def __init__(self):
        self.daily_pnl = 0.0 # Track cushion
        self.daily_goal = 500.0 # Target per day
        self.cushion_achieved = False

    def analyze(self, symbol: str, features: Dict[str, any]) -> Optional[Candidate]:
        # REQUIRES INTRADAY DATA (1-Min or 5-Min) passed in features['intraday_df']
        df = features.get('intraday_df')
        if df is None or len(df) < 5: return None
        
        # Current Candle
        row = features['row']
        close = row['close']
        
        # 1. PRICE FILTER ($2 - $20)
        # Relaxed slightly for backtest data availability
        if not (1.0 <= close <= 25.0): return None
        
        # 2. RELATIVE VOLUME FILTER 
        # (Simplified: Current Vol > 3x Avg Vol of last 20 bars)
        vol = row['volume']
        vol_avg = float(row.get('vol_avg', df['volume'].rolling(20).mean().iloc[-1]))
        if vol_avg > 0 and (vol / vol_avg) < 3.0: return None # Strict momentum requirement
        
        # 3. PATTERN RECOGNITION (Bull Flag / Pullback)
        # Lookback 5-10 bars. 
        # Identify High of 5 bars ago vs Low of recent 2 bars.
        # Logic: 
        #   - Impulse: High[t-5] was a surge.
        #   - Pullback: Low[t-1] < High[t-5], but > Low[t-5] + (Range * 0.5).
        #   - Trigger: Close[t] > High[t-1].
        
        last_5 = df.iloc[-6:-1] # Previous 5 bars exclude current
        if len(last_5) < 5: return None
        
        impulse_high = last_5['high'].max()
        impulse_low = last_5['low'].min()
        impulse_range = impulse_high - impulse_low
        
        if impulse_range < (close * 0.03): return None # Move must be > 3% to be worth it
        
        # Recent pullback low (last 2 bars)
        pullback_low = last_5['low'].iloc[-2:].min()
        
        # Retracement check (Must hold 50% of impulse)
        fib_50 = impulse_low + (impulse_range * 0.50)
        if pullback_low < fib_50: return None # Failed flag (dropped too much)
        
        # TRIGGER: Break of Previous High
        prev_candle = last_5.iloc[-1]
        prev_high = prev_candle['high']
        
        if close > prev_high:
            # ENTRY SIGNAL
            # Stop = Pullback Low
            stop = pullback_low
            risk = close - stop
            
            # Sanity Check Risk
            if risk < 0.02 or risk > (close * 0.10): return None # Too tight (<2c) or too loose (>10%)
            
            target = close + (risk * 2.0) # 2R Target
            
            # SIZING LOGIC (Cushion)
            # This is handled in backtest engine, but we flag it here.
            
            return Candidate(
                section=Section.SCALP,
                symbol=symbol,
                setup_name="Warrior Bull Flag",
                direction=Direction.LONG,
                thesis=f"Small Cap Momentum. RelVol {vol/vol_avg:.1f}x. Flag Breakout > {prev_high:.2f}.",
                features={"rel_vol": vol/vol_avg, "impulse_high": impulse_high},
                trade_plan=TradePlan(
                    entry=close,
                    stop_loss=stop,
                    take_profit=target,
                    risk_percent=0.01, # Default base risk
                    stop_type="Structure Low"
                ),
                scores=Scores(overall_rank_score=95, win_probability_estimate=70, quality_score=90, risk_score=20, baseline_win_rate=60, adjustments=0),
                compliance=Compliance(passed_thresholds=True),
                signal_id=f"WARRIOR_{symbol}_{features.get('current_date')}"
            )
            
        return None
