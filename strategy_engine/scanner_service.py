from typing import List, Dict
import asyncio
from strategy_engine.swing_setups import SwingStrategyEngine
from strategy_engine.options_strategy import OptionsEngine
from strategy_engine.day_trade_strategy import DayTradeEngine
from scoring.ranker import ranker
from configs.settings import settings
from strategy_engine.models import Section, Candidate
from utils.market_clock import MarketClock
from configs.trading_rules import TradingRules
from scoring.llm_analysis import llm_analyzer
from strategy_engine.indicators.vdubus_engine import VdubusEngine
from strategy_engine.indicators.breakout_engine import BreakoutEngine

class ScannerService:
    def __init__(self):
        self.swing_engine = SwingStrategyEngine()
        self.options_engine = OptionsEngine()
        self.day_engine = DayTradeEngine()
        self.vdubus_engine = VdubusEngine()
        self.breakout_engine = BreakoutEngine()
        # Stub symbols for now
        self.symbols = ["AAPL", "TSLA", "NVDA", "SPY", "AMD", "META", "MSFT", "GOOGL"]

    # ... (existing code for run_scan up to selection logic) ...
        
        # --- SWING SELECTION (CORE LOGIC) ---
        swing_final = []
        # Sort by score
        raw_swing.sort(key=lambda c: c.scores.overall_rank_score, reverse=True)
        
        # Filter Min Score
        valid_swing = [c for c in raw_swing if c.scores.overall_rank_score >= settings.MIN_SWING_SCORE]
        
        # Pick CORE Trades (Top 2 if score >= 80)
        core_count = 0
        for cand in valid_swing:
            is_core = False
            if core_count < 2 and cand.scores.overall_rank_score >= settings.MIN_A_PLUS_SWING_SCORE:
                cand.trade_plan.is_core_trade = True
                cand.trade_plan.risk_percent = settings.CORE_RISK_PER_TRADE_PERCENT
                is_core = True
                core_count += 1
            else:
                 cand.trade_plan.risk_percent = settings.MAX_RISK_PER_TRADE_PERCENT
            
            # AI SANITY CHECK
            if is_core:
                # We await the analysis (or just call it wrapper if it was sync)
                # Since LLM is slow, we might just mock it for now or ensure it's async
                try:
                    cand.ai_analysis = await llm_analyzer.analyze_candidate(cand)
                except Exception as e:
                    print(f"AI Analysis Failed: {e}")
                    cand.ai_analysis = "AI Analysis Error"

            swing_final.append(cand)
            
        # --- OPTIONS SELECTION ---
        options_final = raw_options[:3] 

        # --- DAY SELECTION ---
        day_final = raw_day[:3] 
        
        results = {
            Section.SWING.value: swing_final,
            Section.OPTIONS.value: options_final,
            Section.DAY_TRADE.value: day_final
        }
        
        return results

scanner = ScannerService()
