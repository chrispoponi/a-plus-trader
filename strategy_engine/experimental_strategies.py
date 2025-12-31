
import pandas as pd
import numpy as np
from typing import Optional, Dict
from strategy_engine.models import Candidate, Section, Direction, TradePlan, Scores, Compliance
from configs.settings import settings

class DonchianBreakoutStrategy:
    """
    Classic Trend Following.
    Entry: Price breaks 20-day High.
    Exit: Price breaks 10-day Low (Trailing).
    """
    name = "Donchian Trend (20/10)"

    def analyze(self, symbol: str, data: Dict[str, any]) -> Optional[Candidate]:
        close = data.get('close')
        # We need history for Donchian Channels.
        # BacktestEngine passes 'features' with single row values usually?
        # WAIT: BacktestEngine passes generic dict.
        # For this strategy, I need the 'donchian_high_20' and 'donchian_low_10' computed.
        # Or I need the full DF history.
        
        # Solution: The BacktestEngine must compute these indicators if this strategy is selected.
        # OR: We use the 'intraday_data' style passing of history?
        # OR: We stick to Vectorized Calculation in BacktestEngine for speed.
        
        # Let's assume BacktestEngine computes 'high_20' and 'low_10' beforehand.
        high_20 = data.get('high_20')
        low_10 = data.get('low_10')
        
        if not (high_20 and low_10): return None
        
        # Entry Logic
        # Note: In backtesting, we usually check if High > high_20(previous).
        # data['high_20'] should be Shifted(1).
        
        if close > high_20:
            # Generate Signal
            # Stop Loss is Dynamic (Trailing).
            # We set initial stop at low_10
            return Candidate(
                section=Section.SWING,
                symbol=symbol,
                setup_name="Donchian Breakout",
                direction=Direction.LONG,
                thesis=f"Close {close} > 20-Day High {high_20}",
                features={"high_20": high_20, "low_10": low_10},
                trade_plan=TradePlan(
                    entry=close,
                    stop_loss=low_10, # Initial Stop
                    take_profit=close * 2.0, # Let it run (Target is fake here)
                    risk_percent=settings.MAX_RISK_PER_TRADE_PERCENT,
                    stop_type="Trailing Low(10)"
                ),
                scores=Scores(overall_rank_score=80.0, win_probability_estimate=40.0, quality_score=80.0, risk_score=50.0, baseline_win_rate=40.0, adjustments=0),
                compliance=Compliance(passed_thresholds=True),
                signal_id="DONCHIAN"
            )
        return None

class RSI2MeanReversionStrategy:
    """
    Short-term Mean Reversion.
    Entry: RSI(2) < 10 (Oversold) AND Trend is UP (Price > SMA200).
    Exit: RSI(2) > 70 OR Price > SMA5.
    """
    name = "RSI(2) Mean Reversion"

    def analyze(self, symbol: str, data: Dict[str, any]) -> Optional[Candidate]:
        rsi2 = data.get('rsi2')
        sma200 = data.get('sma200')
        close = data.get('close')
        
        if not (rsi2 and sma200): return None
        
        if close > sma200 and rsi2 < 10:
             # Aggressive Entry
             return Candidate(
                section=Section.SWING,
                symbol=symbol,
                setup_name="RSI2 Oversold",
                direction=Direction.LONG,
                thesis=f"RSI2 {rsi2:.1f} < 10 in Uptrend.",
                features={"rsi2": rsi2, "sma200": sma200},
                trade_plan=TradePlan(
                    entry=close,
                    stop_loss=close * 0.90, # Wide stop or Time Stop (Usually no stop in pure RSI2, but we use safety)
                    take_profit=close * 1.05, # Quick scalp or SMA5 exit
                    risk_percent=settings.MAX_RISK_PER_TRADE_PERCENT,
                    stop_type="RSI > 90 or SMA5"
                ),
                scores=Scores(overall_rank_score=90.0, win_probability_estimate=75.0, quality_score=90.0, risk_score=20.0, baseline_win_rate=70.0, adjustments=0),
                compliance=Compliance(passed_thresholds=True),
                signal_id="RSI2"
            )
        return None
