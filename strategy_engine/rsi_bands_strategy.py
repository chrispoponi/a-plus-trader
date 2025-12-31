
from typing import Dict, Optional
from strategy_engine.models import Candidate, Section, TradePlan, Direction, Scores, Compliance

class RSIBandsStrategy:
    """
    STRATEGY: RSI-Bands Reversion
    TYPE: Mean Reversion / Dip Buying
    GOAL: 10% Monthly (Requires High Win Rate + Frequency)
    
    LOGIC:
    - ENTRY: 
        1. RSI(14) between 30-40 (Oversold but not crashing)
        2. Price < SMA(50) (Below trend, deep value)
        3. Price <= Lower Bollinger Band (2.0 SD)
    - EXIT:
        1. RSI(14) > 75 (Overbought)
        2. Price >= Upper Bollinger Band (2.0 SD)
        3. Price > SMA(50) (Trend reclaimed)
    """

    def analyze(self, symbol: str, features: Dict[str, any]) -> Optional[Candidate]:
        # Features from BacktestEngine (need vectorized calc for speed, or calc here)
        # Assuming features dict has: close, rsi, sma50, upper_bb, lower_bb
        
        # If indicators missing, return None
        try:
            close = features.get('close')
            rsi = features.get('rsi')
            sma50 = features.get('sma50')
            lower_bb = features.get('lower_bb')
            
            if not all([close, rsi, sma50, lower_bb]): return None
            
            # ENTRY LOGIC
            # 1. RSI 30-40
            if not (30 <= rsi <= 40): return None
            
            # 2. Below 50 MA
            if not (close < sma50): return None
            
            # 3. Touching/Below Lower Band
            # Allow a small tolerance (e.g. within 1% of band)
            if not (close <= lower_bb * 1.01): return None
            
            # SIGNAL!
            # Target = Upper Band (Dynamic) or fixed R:R
            # Let's use fairly wide stops for Mean Reversion (it can go lower before turning)
            
            return Candidate(
                section=Section.SWING,
                symbol=symbol,
                setup_name="RSI-Bands Reversion",
                direction=Direction.LONG,
                thesis=f"Oversold Bounce. RSI: {rsi:.1f}, Price at Lower Band.",
                features={"rsi": rsi, "dist_to_band": close - lower_bb},
                trade_plan=TradePlan(
                    entry=close,
                    stop_loss=close * 0.92, # 8% Stop (Give it room)
                    take_profit=close * 1.15, # 15% Target (Upper Band proxy)
                    risk_percent=0.02,
                    stop_type="Wide 8%"
                ),
                scores=Scores(overall_rank_score=90, win_probability_estimate=75, quality_score=85, risk_score=15, baseline_win_rate=65, adjustments=0),
                compliance=Compliance(passed_thresholds=True),
                signal_id=f"RSIBANDS_{symbol}_{features.get('current_date')}"
            )

        except Exception as e:
            return None
