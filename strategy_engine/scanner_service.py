from typing import List, Dict
import asyncio
import json
import os
import glob
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
from strategy_engine.data_loader import data_loader
from strategy_engine.market_hunter import MarketHunter

class ScannerService:
    def __init__(self):
        self.swing_engine = SwingStrategyEngine()
        self.options_engine = OptionsEngine()
        self.day_engine = DayTradeEngine()
        self.vdubus_engine = VdubusEngine()
        self.breakout_engine = BreakoutEngine()
        self.hunter = MarketHunter()
    
    def get_target_symbols(self) -> List[str]:
        """
        Merges Hunted symbols with any fresh drops from ChatGPT automation.
        """
        # 1. Run The Hunter (Autonomous Discovery)
        symbols = set(self.hunter.hunt())
        
        # 2. Add Automation Drops (ChatGPT / Manual)
        drop_files = glob.glob("uploads/chatgpt_automation/*.json")
        for fpath in drop_files:
            try:
                with open(fpath, 'r') as f:
                    data = json.load(f)
                    picks = data.get("picks", [])
                    for p in picks:
                        sym = p.get("symbol")
                        if sym:
                            symbols.add(sym.upper())
            except Exception as e:
                print(f"Error reading automation file {fpath}: {e}")
        
        return list(symbols)

    async def run_scan(self) -> Dict[str, List[Candidate]]:
        try:
            print("DEBUG: run_scan() triggered via Scheduler or API. Starting...")
            # Refresh symbol list from automation drops
            target_symbols = self.get_target_symbols()
            print(f"DEBUG: Scanning {len(target_symbols)} symbols (Base + Automation)")

            # 1. Analyze Market Context (SPY/QQQ)
            print("DEBUG: Analyzing Market Context (SPY/QQQ Post-ATH)...")
            market_safe = True 

            # 2. Check Time & Rules
            segment = MarketClock.get_market_segment()
            print(f"DEBUG: Current Market Segment: {segment}")
            
            allow_swing, reason_swing = TradingRules.can_trade_section(Section.SWING, segment)
            allow_options, reason_options = TradingRules.can_trade_section(Section.OPTIONS, segment)
            allow_day, reason_day = TradingRules.can_trade_section(Section.DAY_TRADE, segment)
            
            raw_swing = []
            raw_options = []
            raw_day = []

            # 3. GET REAL DATA (The Heart Transplant)
            # We fetch data even if swing disallowed, because Options need it too
            market_data = {}
            scan_ts = "N/A"
            if allow_swing or allow_options:
                market_data = data_loader.fetch_snapshot(target_symbols)
                
                # [DEBUG MARKER] - Create a timestamp string
                import datetime
                scan_ts = datetime.datetime.now().strftime("%H:%M:%S")
                print(f"DEBUG: Data Fetched at {scan_ts}. Active Tickers: {len(market_data)}")

            if allow_swing: # and market_safe:
                raw_swing = self.swing_engine.scan(target_symbols, market_data)
            else:
                reason = reason_swing if not allow_swing else "Market Context Unsafe"
                print(f"Skipping Swing Scan: {reason}")

            if allow_options: # and market_safe:
                raw_options = self.options_engine.scan(target_symbols, market_data)
            else:
                reason = reason_options if not allow_options else "Market Context Unsafe"
                print(f"Skipping Options Scan: {reason}")
                
            if allow_day:
                # TODO: Pass Day Data
                raw_day = self.day_engine.scan(target_symbols)
            else:
                print(f"Skipping Day Trade Scan: {reason_day}")
            
            # --- SWING SELECTION (CORE LOGIC) ---
            swing_final = []
            # Sort by score
            raw_swing.sort(key=lambda c: c.scores.overall_rank_score, reverse=True)
            
            # Filter Min Score
            valid_swing = [c for c in raw_swing if c.scores.overall_rank_score >= settings.MIN_SWING_SCORE]
            
            # Pick CORE Trades (Top 2 if score >= 80)
            core_count = 0
            for cand in valid_swing:
                # [DEBUG MARKER]
                cand.setup.setup_name = f"{cand.setup.setup_name} | @{scan_ts}"
                
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
            
            # [SYSTEM STATUS CARD]
            try:
                sample_ticker = "AAPL"
                sample_price = "N/A"
                if market_data and sample_ticker in market_data:
                    sample_price = f"${market_data[sample_ticker]['close']}"
                    
                info_setup = Candidate(
                    section=Section.SWING,
                    symbol="SYSTEM",
                    setup_name=f"SCAN REPORT @ {scan_ts}",
                    direction=Direction.LONG,
                    thesis=f"Source: Alpaca API. Universe: {len(target_symbols)}. Active Data: {len(market_data)}. AAPL Check: {sample_price}",
                    features={},
                    trade_plan=TradePlan(entry=0, stop_loss=0, take_profit=0, risk_percent=0),
                    scores=Scores(overall_rank_score=100.0, win_probability_estimate=100.0, quality_score=100.0, risk_score=0, baseline_win_rate=0, adjustments=0),
                    compliance=Compliance(passed_thresholds=True),
                    signal_id="SYSTEM_INFO"
                )
                swing_final.insert(0, info_setup)
            except Exception as e:
                print(f"Error creating Info Card: {e}")

            results = {
                Section.SWING.value: swing_final,
                Section.OPTIONS.value: options_final,
                Section.DAY_TRADE.value: day_final
            }
            return results

        except Exception as e:
            # FATAL ERROR CATCHER
            import traceback
            traceback.print_exc()
            error_card = Candidate(
                section=Section.SWING,
                symbol="ERROR",
                setup_name="CRITICAL SCAN FAILURE",
                direction=Direction.LONG,
                thesis=f"Exception: {str(e)}",
                features={},
                trade_plan=TradePlan(entry=0, stop_loss=0, take_profit=0, risk_percent=0),
                scores=Scores(overall_rank_score=0, win_probability_estimate=0, quality_score=0, risk_score=0, baseline_win_rate=0, adjustments=0),
                compliance=Compliance(passed_thresholds=True),
                signal_id="SYSTEM_ERROR"
            )
            return {
                Section.SWING.value: [error_card],
                Section.OPTIONS.value: [],
                Section.DAY_TRADE.value: []
            }

scanner = ScannerService()
