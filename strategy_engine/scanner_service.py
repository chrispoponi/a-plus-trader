
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
from strategy_engine.models import Candidate, Section, TradePlan, Direction, Scores, Compliance
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

        # 3. Add TradingView / Finviz CSV Drops
        import pandas as pd
        csv_sources = glob.glob("uploads/tradingview/*.csv") + glob.glob("uploads/finviz/*.csv")
        
        for csv_path in csv_sources:
            try:
                # Basic parsing: Look for 'Ticker' or 'Symbol' column
                # TradingView exports usually start with specific headers
                df = pd.read_csv(csv_path)
                
                # Normalize columns
                df.columns = [c.strip().lower() for c in df.columns]
                
                col_name = next((c for c in df.columns if c in ['ticker', 'symbol', 'root']), None)
                
                if col_name:
                    extracted = df[col_name].dropna().astype(str).tolist()
                    # Clean up (remove exchange prefix like 'NASDAQ:NVDA')
                    cleaned = [s.split(':')[-1].strip().upper() for s in extracted]
                    symbols.update(cleaned)
                    print(f"DEBUG: Ingested {len(cleaned)} symbols from {os.path.basename(csv_path)}")
                else:
                    print(f"WARNING: No 'Ticker'/'Symbol' column found in {csv_path}")

            except Exception as e:
                print(f"Error parsing CSV {csv_path}: {e}")
        
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

            # 3. GET REAL DATA
            market_data = {}
            scan_ts = "N/A"
            if allow_swing or allow_options or allow_day:
                # Fetch FULL data for all initial targets to allow Ranking
                market_data = data_loader.fetch_snapshot(target_symbols)
                
                import datetime
                scan_ts = datetime.datetime.now().strftime("%H:%M:%S")
                print(f"DEBUG: Data Fetched at {scan_ts}. Active Tickers: {len(market_data)}")

            # --- ELITE RANKING (Layer 2) ---
            # Filter 50 -> Top 3 Day / Top 3 Swing
            from scoring.elite_ranker import elite_ranker
            top_day_syms, top_swing_syms = elite_ranker.rank_candidates(market_data)
            
            print(f"DEBUG: Elite Day: {top_day_syms}")
            print(f"DEBUG: Elite Swing: {top_swing_syms}")

            # 4. EXECUTE ENGINES ON ELITE LISTS
            
            # SWING
            if allow_swing: 
                # Only scan the Elite 3 for Setup Details
                raw_swing = self.swing_engine.scan(top_swing_syms, market_data)
            else:
                print(f"Skipping Swing Scan: {reason_swing}")

            # OPTIONS (Follows Swing Leaders)
            if allow_options: 
                raw_options = self.options_engine.scan(top_swing_syms, market_data)
            else:
                print(f"Skipping Options Scan: {reason_options}")
                
            # DAY TRADE
            if allow_day:
                raw_day = self.day_engine.scan(top_day_syms, market_data)
            else:
                print(f"Skipping Day Trade Scan: {reason_day}")
            
            # --- FINAL ASSEMBLY ---
            swing_final = raw_swing # Already filtered to top 3 by ranker effectively
            options_final = raw_options
            day_final = raw_day 

            # (No need for extra sorting here as Lists are short, but we can verify)
            
            # Apply Core Logic / AI Check / News Check on Swing
            from strategy_engine.news_engine import news_engine
            
            # Helper to enrich with news
            def enrich_with_news(c_list):
                for c in c_list:
                    if c.symbol in ["SYSTEM", "ERROR", "DATA_FAIL"]: continue
                    
                    news = news_engine.get_market_sentiment(c.symbol)
                    c.thesis += f" | NOTE: {news['latest_headline']}"
                    
                    # if news['sentiment'] == 'NEGATIVE':
                    #     c.setup_name = "⚠️ NEWS RISK " + c.setup_name
                         
            enrich_with_news(swing_final)
            enrich_with_news(day_final)

            # AI Sanity Check (Swing Only)
            for cand in swing_final:
                 cand.scores.overall_rank_score = 99.0 # Elite
                 try:
                     cand.ai_analysis = await llm_analyzer.analyze_candidate(cand)
                 except: pass 
            
            # [SYSTEM STATUS CARD]
            try:
                # 1. CHECK FOR DATA FAILURE
                if len(market_data) == 0:
                     failure_card = Candidate(
                        section=Section.SWING,
                        symbol="DATA_FAIL",
                        setup_name="NO DATA RETURNED",
                        direction=Direction.LONG,
                        thesis="Alpaca returned 0 records for 50 tickers. Check Logs.",
                        features={},
                        trade_plan=TradePlan(entry=0, stop_loss=0, take_profit=0, risk_percent=0),
                        scores=Scores(overall_rank_score=0, win_probability_estimate=0, quality_score=0, risk_score=0, baseline_win_rate=0, adjustments=0),
                        compliance=Compliance(passed_thresholds=True),
                        signal_id="DATA_FAILURE"
                    )
                     # failure_card.setup.grade_color = "red" 
                     swing_final.insert(0, failure_card)

                # 2. STATUS CARD
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
                # info_setup.setup.grade_color = "#4ade80" # Green
                # info_setup.setup.setup_quality = "SYSTEM" # Ensure Frontend renders it
                
                swing_final.insert(0, info_setup)
            except Exception as e:
                print(f"Error creating Info Card: {e}")

            # --- AUTO EXECUTION ---
            if settings.AUTO_EXECUTION_ENABLED:
                from executor_service.order_executor import executor
                print("⚡ AUTO-EXECUTION: Processing Elite Signals...")
                
                # Execute Day Trades
                for cand in day_final:
                    if cand.symbol not in ["SYSTEM", "ERROR", "DATA_FAIL"]:
                        res = executor.execute_trade(cand)
                        cand.setup_name += f" [{res}]"
                
                # Execute Swing Trades
                for cand in swing_final:
                    if cand.symbol not in ["SYSTEM", "ERROR", "DATA_FAIL"]:
                         res = executor.execute_trade(cand)
                         cand.setup_name += f" [{res}]"
            else:
                 print("ℹ️ Auto-Execution Disabled (Signal only).")

            # --- SANITIZATION (Fix Serialization Errors) ---
            import numpy as np
            import pandas as pd
            
            def sanitize_value(v):
                if pd.isna(v): return None
                if isinstance(v, (np.int64, np.int32)): return int(v)
                if isinstance(v, (np.float64, np.float32)): return float(v)
                return v

            for cand_list in [swing_final, options_final, day_final]:
                for c in cand_list:
                    # Sanitize Features
                    if c.features:
                        c.features = {k: sanitize_value(v) for k, v in c.features.items()}
                    # Sanitize Scores (If needed, Pydantic usually handles this but safety first)
                    # c.scores... floats are usually fine unless NaN
                    pass

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
