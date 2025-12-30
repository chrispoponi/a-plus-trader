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
        direction = Direction.LONG
        
        # Calculate Trend State
        is_bullish = close > sma50 and close > ema20
        is_bearish = close < sma50 and close < ema20
        
        if is_bullish:
            strategy = "Bull Put Spread"
            direction = Direction.LONG
        elif is_bearish:
            strategy = "Bear Call Spread"
            direction = Direction.SHORT
        else:
            # RANGE BOUND -> IRON CONDOR
            strategy = "Iron Condor" 
            direction = Direction.LONG # Neutral
            
        # Mock Option Chain Analysis (Simulating the Greeks)
        # Real logic would query chain, find deltas 0.20/0.05
        
        if strategy == "Iron Condor":
            # Short Put 440, Long Put 430
            # Short Call 480, Long Call 490
            credit = 2.10
            width = 10.0
            pop = 68.0 # Condors usually have slightly lower POP than singular spreads, but higher credit
            if pop < 65.0: return None 
        else:
            # If Bull Put Spread:
            # Sell 450 Put, Buy 440 Put
            credit = 1.50
            width = 10.0
            pop = 72.5
            if pop < 70.0: return None

        max_loss = (width - credit) * 100
        max_gain = credit * 100
        
        return Candidate(
            section=Section.OPTIONS,
            symbol=symbol,
            setup_name=f"High Prob {strategy}",
            direction=direction,
            thesis=f"{strategy} selected. Market is '{'Trending' if is_bullish or is_bearish else 'Ranging'}' (Close vs 50SMA). POP {pop}%.",
            features=data,
            trade_plan=TradePlan(
                entry=credit, # Net credit
                stop_loss=credit * 2.5 if strategy == "Iron Condor" else credit * 2.0, # Condors need wider stops
                take_profit=credit * 0.5, # 50% profit
                risk_percent=settings.MAX_RISK_PER_TRADE_PERCENT
            ),
            options_details=OptionsDetails(
                strategy_type=strategy,
                strikes=[440, 430, 480, 490] if strategy == "Iron Condor" else [450, 440],
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
            compliance=Compliance(passed_thresholds=False), # DISABLED FOR EXECUTION (Research Only)
            signal_id=f"{symbol}_OPT_{strategy.replace(' ','_')}"
        )

    def scan(self, symbols: List[str], market_data: Dict[str, any] = None) -> List[Candidate]:
        candidates = []
        
        if not market_data:
            return []
            
        for symbol in symbols:
            # Use Real Data
            data = market_data.get(symbol)
            if not data: continue
            
            res = self.analyze(symbol, data)
            if res: candidates.append(res)

        return candidates
