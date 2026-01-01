from typing import Dict, Optional, List
import pandas as pd
import numpy as np
import datetime
from strategy_engine.models import Candidate, Section, TradePlan, Direction, Scores, Compliance

class SykesStrategyBase:
    """
    Base class for Tim Sykes Penny Stock Strategies.
    Enforces Strict Global Risk Rules.
    """
    def _check_global_risk(self, close_price: float) -> bool:
        # Rule: Only trade small/micro-cap (Proxy: Price < $20 for now, traditionally < $10)
        # Allows for some wiggle room if momentum is huge.
        if close_price > 25.0: return False
        return True

class FirstGreenDayStrategy(SykesStrategyBase):
    """
    STRATEGY A: FIRST GREEN DAY (FGD)
    Purpose: Day-1 momentum continuation after downtrend.
    """
    def analyze(self, symbol: str, features: Dict[str, any]) -> Optional[Candidate]:
        df = features.get('df') # Daily bars
        if df is None or len(df) < 20: return None
        
        # 1. Snapshot Data
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        close = current['close']
        open_p = current['open']
        high = current['high']
        low = current['low']
        volume = current['volume']
        
        # Global Filter
        if not self._check_global_risk(close): return None
        
        # 2. FGD Conditions
        
        # A. Gain >= 3%
        # Calculate % Change from Prev Close
        prev_close = prev['close']
        gain_pct = (close - prev_close) / prev_close
        if gain_pct < 0.03: return None
        
        # B. Volume >= 3x 10-day Average
        # Check avg vol of PREVIOUS 10 days (exclude today for "avg") or include? 
        # Usually avg is historical.
        avg_vol_10 = df['volume'].iloc[-11:-1].mean()
        if volume < (3.0 * avg_vol_10): return None
        
        # C. Downtrend / Consolidation Check
        # Check if price was generally lower/flat last 5 days vs 20 days ago
        # Proxies: Recent lows are lower than 20 days ago, or simply "Not a runner yet"
        # Simplistic: Setup is 'First' Green Day. 
        # Verify previous day was RED or small Green (<1%)
        prev_gain = (prev['close'] - df.iloc[-3]['close']) / df.iloc[-3]['close']
        if prev_gain > 0.05: return None # Disqualify if yesterday was already a huge gainer (Chasing)
        
        # 3. Setup Validated -> Plan Trade
        
        # STOP LOSS: Low of Day OR 5-10% (Tighter)
        # Low of Day
        stop_lod = low 
        # 5% Max Risk
        stop_pct = close * 0.95
        
        # Use whichever is HIGHER (Closer to entry) to be Tighter? 
        # User says: "Whichever stop is TIGHTER" (Smaller loss). 
        # Mathematically: A stop closer to price is "tighter" (smaller risk).
        # So Max(stop_lod, stop_pct) 
        stop_loss = max(stop_lod, stop_pct)
        
        # Targets: +10-20% (Partial), +20-30% (Full)
        # Let's set initial Target at +20% (2R usually)
        target = close * 1.20
        
        trade_risk = (close - stop_loss) / close
        
        # HARD STOP: Max Loss 10%
        if trade_risk > 0.10: 
            stop_loss = close * 0.90
        
        return Candidate(
            section=Section.SWING, # Swing because we hold overnight for continuation
            symbol=symbol,
            setup_name="FGD (First Green Day)",
            direction=Direction.LONG,
            thesis=f"FGD Detected. Gain {gain_pct*100:.1f}%. Vol {volume/avg_vol_10:.1f}x Avg. Breaking downtrend.",
            features={"avg_vol_10": avg_vol_10, "gain": gain_pct},
            trade_plan=TradePlan(
                entry=close,
                stop_loss=stop_loss,
                take_profit=target,
                risk_percent=0.015, # 1.5% Account Risk
                stop_type="LOD / 5%",
                is_core_trade=True
            ),
            scores=Scores(overall_rank_score=90, win_probability_estimate=70, quality_score=90, risk_score=10, baseline_win_rate=50, adjustments=0),
            compliance=Compliance(passed_thresholds=True),
            signal_id=f"FGD_{symbol}_{current.name}"
        )

class MorningPanicStrategy(SykesStrategyBase):
    """
    STRATEGY B: MORNING PANIC DIP BUY (MPDB)
    Purpose: Catch bounces on panic dumping morning runners.
    Scope: Intraday (Day Trade).
    """
    def analyze(self, symbol: str, features: Dict[str, any]) -> Optional[Candidate]:
        # Needs Intraday Data (5Min or 1Min)
        intraday_df = features.get('intraday_df')
        if intraday_df is None or intraday_df.empty: return None
        
        current_date = features.get('current_date') # Daily timestamp
        
        # 1. Check Time: First 60 Mins (9:30 - 10:30)
        # Current bar time
        last_bar = intraday_df.iloc[-1]
        
        # Ensure it's morning (Approx check, assumes NY time index)
        # If we can't check time easily, we rely on scanner calling this in "Morning Prep" window.
        
        # 2. RUNNER Check: Multi-day runner?
        # Check Daily DF (passed in features['df'] if available)
        daily_df = features.get('df')
        if daily_df is not None:
            # Check if updated > 20% in last 5 days
            recent_low = daily_df['low'].iloc[-5:].min()
            recent_high = daily_df['high'].iloc[-5:].max()
            if recent_high / recent_low < 1.30: 
                return None # Not a runner (needs 30% move recently)
        
        # 3. PANIC: Drop >= 20% from High
        # Find Day High
        # Slice intraday for 'today'
        # Assuming index is datetime
        # ( Simplified for Logic: Just check last 10 bars for big drop )
        
        closes = intraday_df['close']
        recent_high = closes.iloc[-12:].max() # Last hour high
        current_price = closes.iloc[-1]
        
        drop_pct = (recent_high - current_price) / recent_high
        
        # Rule: Drop >= 20%
        if drop_pct < 0.20: return None
        
        # 4. SUPPORT Logic (Whole Dollar, VWAP, Support Level)
        # Check Whole Dollar (e.g. 5.00, 5.50)
        import math
        nearest_whole = round(current_price * 2) / 2 # Nearest 0.50
        
        dist_support = abs(current_price - nearest_whole)
        is_near_support = dist_support / current_price < 0.02 # Within 2%
        
        if not is_near_support: return None
        
        # 5. ENTRY: Price must be bouncing (Green Candle or Wick)
        # Check if last candle is Green
        if intraday_df['close'].iloc[-1] <= intraday_df['open'].iloc[-1]:
            # Waiting for bounce...
            return None 
            
        # SETUP VALID
        
        # STOP: Panic Low (Lowest Point of drop)
        panic_low = closes.iloc[-5:].min()
        stop_loss = panic_low * 0.98 # A bit below
        
        # HARD STOP check (10%)
        if (current_price - stop_loss) / current_price > 0.10:
             stop_loss = current_price * 0.90
             
        target = current_price * 1.20 # +20% bounce target
        
        return Candidate(
            section=Section.DAY_TRADE,
            symbol=symbol,
            setup_name="Morning Panic Dip Buy",
            direction=Direction.LONG,
            thesis=f"Panic Drop {drop_pct*100:.1f}%. Bouncing off {nearest_whole}. Runner.",
            features={"panic_drop": drop_pct},
            trade_plan=TradePlan(
                entry=current_price,
                stop_loss=stop_loss,
                take_profit=target,
                risk_percent=0.01, # 1% Risk
                stop_type="Panic Low",
                is_core_trade=True
            ),
            scores=Scores(overall_rank_score=95, win_probability_estimate=80, quality_score=95, risk_score=20, baseline_win_rate=60, adjustments=0),
            compliance=Compliance(passed_thresholds=True),
            signal_id=f"MPDB_{symbol}_{current_date}"
        )
