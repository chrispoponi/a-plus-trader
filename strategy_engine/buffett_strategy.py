
from typing import Dict, Optional, List
from strategy_engine.models import Candidate, Section, TradePlan, Direction, Scores, Compliance
import pandas as pd

class BuffettStrategy:
    """
    STRATEGY: Warren Buffett Value Investing (Price Action Proxy)
    LOGIC:
    - ASSUMPTION: The Universe provided (AAPL, KO, JPM, etc) IS the 'Quality List'.
    - ENTRY: Buy when Price is 'On Sale' (< 85% of 52-Week High).
    - EXIT: Hold 1 Year OR if Price recovers to > 105% of 52-Week High.
    """

    def analyze(self, symbol: str, features: Dict[str, any]) -> Optional[Candidate]:
        # 1. Price Check (Cheap relative to 52W High?)
        df = features.get('df')
        if df is None or df.empty: return None
        
        # Current Price vs 52W High (Window 252)
        current_date = features.get('current_date')
        if not current_date: return None 
        
        try:
             idx_loc = df.index.get_loc(current_date)
             # Past 252 bars
             start_loc = max(0, idx_loc - 252)
             past_year = df.iloc[start_loc : idx_loc + 1]
             high_52 = past_year['high'].max()
             
             current_close = features['row']['close']
             
             # FILTER: Price < 0.85 * 52W High (15% Discount)
             if current_close < (0.85 * high_52):
                 
                 # ENTRY
                 return Candidate(
                    section=Section.SWING,
                    symbol=symbol,
                    setup_name="Buffett Value Dip",
                    direction=Direction.LONG,
                    thesis=f"Value Buy. Price ${current_close:.2f} is < 85% of 52W High ${high_52:.2f}.",
                    features={"discount": (1 - current_close/high_52)},
                    trade_plan=TradePlan(
                        entry=current_close,
                        stop_loss=current_close * 0.80, # Wide safety net
                        take_profit=high_52 * 1.05, # Target Recovery + Premium
                        risk_percent=0.01,
                        stop_type="Wide 20%"
                    ),
                    scores=Scores(overall_rank_score=98, win_probability_estimate=85, quality_score=95, risk_score=5, baseline_win_rate=60, adjustments=0),
                    compliance=Compliance(passed_thresholds=True),
                    signal_id=f"BUFFETT_{symbol}_{current_date}"
                )
                 
        except Exception as e:
             return None

        return None
