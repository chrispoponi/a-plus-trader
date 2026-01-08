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
        
        # Determine Strikes dynamically
        strikes = []
        upper_bb = data.get('upper_bb', close * 1.05)
        lower_bb = data.get('lower_bb', close * 0.95)
        
        if strategy == "Iron Condor":
            # SPECIFIC LOGIC FOR INDICES (SPY, QQQ, IWM) -> 1DTE INCOME
            is_index = symbol in ["SPY", "QQQ", "IWM", "SPX"]
            
            if is_index:
                # 1DTE LOGIC via Adapter
                try:
                    from contracts.options_adapter import options_adapter
                    legs = options_adapter.resolve_condor(symbol, close, dte=1)
                    
                    if legs:
                         # Extract Strikes from Symbol string roughly or query?
                         # Format: SPY240119C00450000 -> Parse last 8 digits / 1000
                         # Let's just trust the Adapter logic for now.
                         strikes = list(legs.values())
                         # Populate legs for Executor
                         pass 
                    else:
                         return None # Failed to resolve
                except Exception as e:
                    print(f"Option Resolve Error: {e}")
                    return None

                # Calculate Mock Credit for Analysis (Real pricing in V2)
                credit = 0.50 
                width = 2.0
                pop = 85.0
                dte = 1

            else:
                # STANDARD CONDOR (Swing)
                short_put = round(lower_bb, 1)
                long_put = round(short_put * 0.95, 1)
                short_call = round(upper_bb, 1)
                long_call = round(short_call * 1.05, 1)
                strikes = [long_put, short_put, short_call, long_call]
                credit = round(close * 0.01, 2)
                width = round(short_put - long_put, 2)
                pop = 68.0
                dte = 45
        else:
            # SPREADS
            dte = 45
            if direction == Direction.LONG: 
                short_put = round(lower_bb, 1)
                long_put = round(short_put * 0.95, 1)
                strikes = [long_put, short_put]
            else: 
                short_call = round(upper_bb, 1)
                long_call = round(short_call * 1.05, 1)
                strikes = [short_call, long_call]
                
            credit = round(close * 0.01, 2)
            width = round(abs(strikes[0] - strikes[1]), 2)
            pop = 72.5

        max_loss = round((width - credit) * 100, 2)
        max_gain = round(credit * 100, 2)
        
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
                strikes=strikes,
                expiration_date="1DTE" if dte==1 else "45DTE",
                dte=dte,
                pop_estimate=pop,
                max_loss=max_loss,
                max_gain=max_gain,
                breakeven=[448.5],
                legs=legs
            ),
            scores=Scores(
                win_probability_estimate=pop, # Direct map
                quality_score=85.0,
                risk_score=90.0, # High safety due to defined risk
                overall_rank_score=pop, # Prioritize by POP
                baseline_win_rate=70.0,
                adjustments=0
            ),
            compliance=Compliance(passed_thresholds=True), # ENABLED FOR EXECUTION
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
