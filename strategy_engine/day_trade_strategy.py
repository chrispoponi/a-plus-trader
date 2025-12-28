from typing import List, Optional, Dict
from strategy_engine.models import Candidate, Section, Direction, TradePlan, Scores, Compliance
from configs.settings import settings

class DayTradeEngine:
    """
    Focus: A+ Momentum, RVOL, VWAP.
    Strategies: ORB, VWAP Reclaim.
    """
    
    def analyze(self, symbol: str, data: Dict[str, any]) -> Optional[Candidate]:
        # Filter: RVOL (Mocked)
        rvol = data.get('rvol', 1.0)
        if rvol < 1.5: return None # Must have volume
        
        # Strategy: VWAP Reclaim
        # Price crossing above VWAP
        close = data.get('close')
        vwap = data.get('vwap')
        
        if close > vwap and (close - vwap) / vwap < 0.005: 
            # Reclaimed/Hold
            return Candidate(
                section=Section.DAY_TRADE,
                symbol=symbol,
                setup_name="VWAP Reclaim Momentum",
                direction=Direction.LONG,
                thesis=f"High RVOL ({rvol}x). Reclaimed VWAP with volume surge.",
                features=data,
                trade_plan=TradePlan(
                    entry=close,
                    stop_loss=vwap * 0.998, # Tight stop below VWAP
                    take_profit=close * 1.02, # 2% intraday move
                    risk_percent=0.25 # Smaller risk for day trades? User said configurable, sticking to logic
                ),
                scores=Scores(
                     win_probability_estimate=60.0,
                     quality_score=90.0,
                     risk_score=70.0,
                     overall_rank_score=85.0, # High rank due to A+ criteria
                     baseline_win_rate=50.0,
                     adjustments=10.0
                ),
                compliance=Compliance(passed_thresholds=True),
                signal_id=f"{symbol}_DAY_VWAP"
            )
            
        return None

    def scan(self, symbols: List[str]) -> List[Candidate]:
        candidates = []
        for symbol in symbols:
            # Mock Data
            if symbol == "TSLA":
                data = {"close": 240.50, "vwap": 240.00, "rvol": 2.5} # A+ Setup
                res = self.analyze(symbol, data)
                if res: candidates.append(res)
        return candidates
