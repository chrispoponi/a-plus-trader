from typing import List, Optional, Dict
from strategy_engine.models import Candidate, Section, Direction, TradePlan, Scores, Compliance
from configs.settings import settings

class SwingAnalysis:
    """
    Implements the 'A+ Filters' and 'Grading' logic for Swing Trades.
    """
    
    def grade_candidate(self, symbol: str, data: Dict[str, any], direction: Direction) -> Scores:
        # 1. Trend Alignment (Weight 25 + Bonus 10)
        # 20EMA > 50SMA and slope check
        trend_score = self._score_trend(data, direction)
        
        # 2. Pullback Quality (Weight 20 + Bonus 10)
        # Distance to EMA, candle shape
        structure_score = self._score_structure(data)
        
        # 3. Volume Behavior (Weight 15)
        # Bonus for 'Pocket Pivot' or 'Volume Dry Up'
        vol_score = 15.0 
        if data.get('volume_dry_up'): vol_score += 5
        
        # 4. Sector/Market (Weight 15)
        sector_score = 15.0 
        if data.get('sector_rs'): sector_score += 5
        
        # 5. Overhead Supply (Weight 15)
        supply_score = 15.0 

        # 6. Event Risk (Weight 10)
        event_score = 10.0
        
        # BASE TOTAL
        total_score = trend_score + structure_score + vol_score + sector_score + supply_score + event_score
        
        # Win Prob estimate is correlated to score
        win_prob = 50 + (total_score * 0.3) 
        
        return Scores(
            win_probability_estimate=min(win_prob, 95.0),
            quality_score=total_score,
            risk_score=event_score, 
            overall_rank_score=min(total_score, 99.0), # Cap at 99
            baseline_win_rate=55.0,
            adjustments=total_score - 55.0,
            trend_score=trend_score,
            structure_score=structure_score,
            vol_score=vol_score,
            sector_score=sector_score
        )

    def _score_trend(self, data, direction) -> float:
        ema20 = data.get('ema20')
        sma50 = data.get('sma50')
        if not ema20 or not sma50: return 0.0
        
        if direction == Direction.LONG:
            if ema20 > sma50:
                # Bonus if price is above both
                return 25.0
            return 10.0
        return 0.0

    def _score_structure(self, data) -> float:
        # Mock logic: Hammer + near EMA = High Score
        if data.get('candle_pattern') == 'hammer':
            return 20.0
        return 10.0

class SwingSetup_20_50:
    name = "20/50 Trend Pullback"
    
    def __init__(self):
        self.grader = SwingAnalysis()

    def analyze(self, symbol: str, data: Dict[str, any]) -> Optional[Candidate]:
        # A+ FILTERS
        # 1. Liquidity check (Mocked to True for demo)
        # if data['volume'] < 20000000: return None
        
        # 2. Trend Check
        ema20 = data.get('ema20')
        sma50 = data.get('sma50')
        close = data.get('close')
        
        if not (ema20 and sma50 and close): return None
        
        direction = Direction.LONG if ema20 > sma50 else Direction.SHORT
        
        # ENTRY PATTERN A: Pullback to 20
        # Simple check: Price within 1-2% of EMA20
        dist_pct = abs(close - ema20) / ema20
        if dist_pct > 0.02: 
            return None # Not a tight enough pullback
            
        # PASSES FILTERS -> Grade it
        scores = self.grader.grade_candidate(symbol, data, direction)
        
        if scores.overall_rank_score < settings.MIN_SWING_SCORE:
            return None

        # Plan Trade
        # Stop: Below recent low or 1.5 ATR. Let's use 1.5 ATR if available, else 2%
        atr = data.get('atr', close * 0.02)
        stop_dist = 1.5 * atr
        
        if direction == Direction.LONG:
            entry_price = close
            stop_price = close - stop_dist
            target_price = close + (stop_dist * 2.0)
        else:
            entry_price = close
            stop_price = close + stop_dist
            target_price = close - (stop_dist * 2.0)

        # Sizing Logic placeholder (will be refined in Scanner)
        risk_pct = settings.MAX_RISK_PER_TRADE_PERCENT

        return Candidate(
            section=Section.SWING,
            symbol=symbol,
            setup_name=self.name,
            direction=direction,
            thesis=f"A+ Setup: {scores.overall_rank_score:.0f}/100. Trend aligned. Pullback to 20EMA.",
            features=data,
            trade_plan=TradePlan(
                entry=round(entry_price, 2),
                stop_loss=round(stop_price, 2),
                take_profit=round(target_price, 2),
                risk_percent=risk_pct,
                stop_type="Volatility (1.5 ATR)"
            ),
            scores=scores,
            compliance=Compliance(passed_thresholds=True),
            signal_id=f"{symbol}_SWING_2050"
        )

class SwingStrategyEngine:
    def __init__(self):
        self.setups = [SwingSetup_20_50()]

    def scan(self, symbols: List[str], market_data: Dict[str, dict] = None) -> List[Candidate]:
        candidates = []
        
        # If no data passed (legacy test), fallback or empty
        if not market_data:
            print("SWING ENGINE: No market data provided.")
            return []

        for symbol, data in market_data.items():
            # Data is already computed {close, ema20, sma50, atr...}
            for setup in self.setups:
                res = setup.analyze(symbol, data)
                if res:
                    candidates.append(res)
        return candidates
