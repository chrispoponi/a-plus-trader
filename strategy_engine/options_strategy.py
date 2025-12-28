from typing import List, Optional, Dict
from strategy_engine.models import Candidate, Section, Direction, TradePlan, Scores, Compliance, OptionsDetails, Action
from configs.settings import settings

class OptionsEngine:
    """
    Focus: High Probability (POP > 70%), Defined Risk.
    Strategies: Bull Put Spread, Bear Call Spread, Iron Condor.
    """
    
    def analyze(self, symbol: str, data: Dict[str, any]) -> Optional[Candidate]:
        # Filter: Liquidity (Mocked)
        # if data['adv'] < 30000000: return None
        
        # Determine Regime
        ema20 = data.get('ema20')
        sma50 = data.get('sma50')
        close = data.get('close')
        
        if not (ema20 and sma50 and close): return None
        
        # Strategy Selection Logic
        strategy = None
        if close > sma50 and close > ema20:
            strategy = "Bull Put Spread"
            direction = Direction.LONG
        elif close < sma50 and close < ema20:
            strategy = "Bear Call Spread"
            direction = Direction.SHORT
        else:
            strategy = "Iron Condor" # Range bound
            direction = Direction.LONG # Neutral usually treated as long for scaffolding
            
        # Mock Option Chain Analysis
        # Real logic would query chain, find deltas 0.20/0.05
        
        # If Bull Put Spread:
        # Sell 450 Put, Buy 440 Put
        credit = 1.50
        width = 10.0
        max_loss = (width - credit) * 100
        max_gain = credit * 100
        pop = 72.5 # Estimated
        
        if pop < 70.0: return None # Strict rule
        
        return Candidate(
            section=Section.OPTIONS,
            symbol=symbol,
            setup_name=f"High Prob {strategy}",
            direction=direction,
            thesis=f"{strategy} selected based on trend. POP estimated at {pop}%. Defined risk.",
            features=data,
            trade_plan=TradePlan(
                entry=credit, # Net credit
                stop_loss=credit * 2.0, # 2x credit stop
                take_profit=credit * 0.5, # 50% profit
                risk_percent=settings.MAX_RISK_PER_TRADE_PERCENT
            ),
            options_details=OptionsDetails(
                strategy_type=strategy,
                strikes=[450.0, 440.0],
                expiration_date="2024-02-16",
                dte=45,
                pop_estimate=pop,
                max_loss=max_loss,
                max_gain=max_gain,
                breakeven=[448.5]
            ),
            scores=Scores(
                win_probability_estimate=pop, # Direct map
                quality_score=85.0,
                risk_score=90.0, # High safety due to defined risk
                overall_rank_score=pop, # Prioritize by POP
                baseline_win_rate=70.0,
                adjustments=0
            ),
            compliance=Compliance(passed_thresholds=True),
            signal_id=f"{symbol}_OPT_{strategy.replace(' ','_')}"
        )

    def scan(self, symbols: List[str]) -> List[Candidate]:
        candidates = []
        for symbol in symbols:
            # Mock Data
            if symbol in ["NVDA", "SPY"]:
                data = {"close": 460.0, "ema20": 458.0, "sma50": 430.0} # Bullish
                res = self.analyze(symbol, data)
                if res: candidates.append(res)
        return candidates
