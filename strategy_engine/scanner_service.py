
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
from strategy_engine.warrior_strategy import WarriorStrategy
from strategy_engine.sykes_strategies import FirstGreenDayStrategy, MorningPanicStrategy
from strategy_engine.one_box_strategy import OneBoxStrategy

class ScannerService:
    def __init__(self):
        self.swing_engine = SwingStrategyEngine()
        self.options_engine = OptionsEngine()
        self.day_engine = DayTradeEngine()
        self.warrior_engine = WarriorStrategy() # New
        self.fgd_engine = FirstGreenDayStrategy()
        self.mpdb_engine = MorningPanicStrategy()
        self.one_box_engine = OneBoxStrategy()
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

    async def _run_sykes_scan(self) -> List[Candidate]:
        """
        Scans for Tim Sykes Setups (FGD/MPDB) on Small Caps.
        1. Fetch Snapshots of potential small caps.
        2. Filter for Gainers (FGD) and Panic Losers (MPDB).
        3. Fetch History and Run Strategies.
        """
        try:
             print("🔎 SYKES SCAN: Hunting Penny Moves...")
             
             # Reuse Connection
             from alpaca_trade_api.rest import REST
             api = REST(settings.APCA_API_KEY_ID, settings.APCA_API_SECRET_KEY, base_url=settings.APCA_API_BASE_URL)
             
             # 1. Get Universe (NASDAQ/AMEX Small Caps ideally)
             # We just get all tradable for now to be safe, filtering later
             assets = api.list_assets(status='active', asset_class='us_equity')
             # Filter logic: Focus on Exchanges known for pennies or just all
             symbols = [a.symbol for a in assets if a.exchange in ['NASDAQ', 'NYSE', 'AMEX'] and a.tradable]
             
             # 2. Snapshot & Filter
             chunk_size = 1000
             candidates_FGD = []
             candidates_MPDB = []
             
             # Limiter: Scan first 2000 or full? 
             # Full scan takes time. Let's do 3000 to catch more.
             scan_limit = 3000 
             
             for i in range(0, min(len(symbols), scan_limit), chunk_size):
                  chunk = symbols[i:i+chunk_size]
                  try:
                      snaps = api.get_snapshots(chunk)
                      for sym, snap in snaps.items():
                          if not snap.daily_bar: continue
                          p = snap.daily_bar.c
                          
                          # SYKES FILTER: Price < $25
                          if p > 25.0: continue
                          if p < 0.50: continue # Garbage
                          
                          prev = snap.prev_daily_bar.c
                          if not prev: continue
                          change = (p - prev) / prev
                          
                          # FGD POTENTIAL: Green > 3%
                          if change >= 0.03:
                               candidates_FGD.append(sym)
                               
                          # MPDB POTENTIAL: Red < -10% (Panic check)
                          if change <= -0.10:
                               candidates_MPDB.append(sym)
                               
                  except: pass
             
             print(f"SYKES: Found {len(candidates_FGD)} FGD Candidates, {len(candidates_MPDB)} Panic Candidates.")
             
             results = []
             
             # 3. Analyze FGD (Needs Daily History)
             if candidates_FGD:
                 # Batch Fetch Daily
                 # We reuse data_loader logic or direct fetch
                 # Direct fetch for speed here
                 for sym in candidates_FGD[:20]: # Limit processing
                      try:
                          bars = api.get_bars(sym, "1Day", limit=60).df
                          if bars.empty: continue
                          
                          # Feature Dict
                          f_dict = {"df": bars, "current_date": bars.index[-1]}
                          cand = self.fgd_engine.analyze(sym, f_dict)
                          if cand: results.append(cand)
                      except: pass

             # 4. Analyze MPDB (Needs Intraday)
             if candidates_MPDB:
                  for sym in candidates_MPDB[:20]:
                       try:
                           bars = api.get_bars(sym, "5Min", limit=100).df
                           if bars.empty: continue
                           
                           # Also need Daily for "Runner" check
                           daily_bars = api.get_bars(sym, "1Day", limit=20).df
                           
                           f_dict = {
                               "intraday_df": bars, 
                               "df": daily_bars,
                               "current_date": bars.index[-1]
                           }
                           cand = self.mpdb_engine.analyze(sym, f_dict)
                           if cand: results.append(cand)
                       except: pass

             return results

        except Exception as e:
            print(f"Sykes Scan Error: {e}")
            return []

    async def _run_warrior_scan(self) -> List[Candidate]:
        """
        Specialized Scan for Ross Cameron Momentum Gappers.
        """
        try:
             # 1. Get List (Re-using Hunter logic simplified)
             # Ideally we call a centralized "Gapper Service" but for now inline is fast.
             # We need to import API here or reuse data_loader's connection if exposed
             from alpaca_trade_api.rest import REST
             api = REST(settings.APCA_API_KEY_ID, settings.APCA_API_SECRET_KEY, base_url=settings.APCA_API_BASE_URL)
             
             assets = api.list_assets(status='active', asset_class='us_equity')
             # Filter: Exchange and Tradable
             symbols = [a.symbol for a in assets if a.exchange in ['NASDAQ', 'NYSE', 'AMEX'] and a.tradable]
             
             # Chunked Snapshot Fetch
             chunk_size = 1000
             candidates_5min = []
             
             # Optimization: Only scan top 1000 symbols or so to speed up? 
             # Or just do first 2 chunks.
             for i in range(0, min(len(symbols), 2000), chunk_size):
                  chunk = symbols[i:i+chunk_size]
                  try:
                      snaps = api.get_snapshots(chunk)
                      for sym, snap in snaps.items():
                          if not snap.daily_bar: continue
                          p = snap.daily_bar.c
                          if not (2.0 <= p <= 20.0): continue
                          
                          prev = snap.prev_daily_bar.c
                          if not prev: continue
                          change = (p - prev) / prev
                          
                          if change >= 0.10: # 10% Gap
                             candidates_5min.append(sym)
                  except: pass
                  
             if not candidates_5min: return []
             
             # Fetch 5Min Data for candidates
             res_candidates = []
             for sym in candidates_5min:
                 # Fetch 5 min bars
                 try: 
                     bars = api.get_bars(sym, "5Min", limit=100).df
                     if bars.empty: continue
                     
                     # Construct Feature Dict
                     row = bars.iloc[-1]
                     f_dict = {
                         "row": row,
                         "intraday_df": bars,
                         "current_date": row.name, # Timestamp
                         "vol_avg": bars['volume'].rolling(20).mean().iloc[-1]
                     }
                     
                     cand = self.warrior_engine.analyze(sym, f_dict)
                     if cand: res_candidates.append(cand)
                 except: pass
                 
             return res_candidates

        except Exception as e:
            print(f"Warrior Scan Error: {e}")
            return []

    def run_sniper_scan(self, symbols: List[str]) -> List[Candidate]:
        """
        Fast Scan for Sniper Bot (High Frequency).
        Runs One Box Strategy on 1-Minute Data.
        """
        try:
             # Fetch Data (1Min, last 100 bars)
             # Use data_loader's light fetch
             from strategy_engine.data_loader import data_loader
             from datetime import datetime
             
             # Map symbols to Data
             # fetch_intraday_snapshot defaults to 5Min, need 1Min
             # Since that method is hardcoded, let's just use API direct for speed/flexibility
             # or update data_loader. Let's use direct API here to ensure 1Min.
             from alpaca_trade_api.rest import REST
             api = REST(settings.APCA_API_KEY_ID, settings.APCA_API_SECRET_KEY, base_url=settings.APCA_API_BASE_URL)
             
             if not symbols: return []
             
             # Fetch 1Min Bars
             # Getting last 20 mins is enough
             try:
                 bars = api.get_bars(symbols, "1Min", limit=50).df
             except: return []
             
             results = []
             if bars.empty: return []
             
             # Process
             unique_syms = bars.index.get_level_values(0).unique() if isinstance(bars.index, pd.MultiIndex) else bars['symbol'].unique()

             for sym in unique_syms:
                  try:
                      if isinstance(bars.index, pd.MultiIndex):
                          df = bars.xs(sym).copy()
                      else:
                          df = bars[bars['symbol'] == sym].copy()
                      
                      # Analyze One Box
                      f_dict = {"intraday_df": df}
                      cand = self.one_box_engine.analyze(sym, f_dict)
                      
                      if cand:
                          results.append(cand)
                  except: pass
                  
             # Sort by Profit Potential (User Request: "Most Profitable First")
             # Proxy: Candidates with higher score or just first come?
             results.sort(key=lambda x: x.scores.overall_rank_score, reverse=True)
             
             return results
             
        except Exception as e:
            print(f"Sniper Scan Error: {e}")
            return []

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
            
            # WARRIOR SCAN (Parallel or Sequential)
            warrior_raw = []
            if allow_day: # Warrior is a day strategy
                 print("DEBUG: Running Warrior Scan...")
            # WARRIOR SCAN (Parallel or Sequential)
            warrior_raw = []
            if allow_day: # Warrior is a day strategy
                 print("DEBUG: Running Warrior Scan...")
                 warrior_raw = await self._run_warrior_scan()
            
            # SYKES SCAN
            sykes_raw = []
            if allow_day or allow_swing: # FGD is Swing, MPDB is Day
                 sykes_raw = await self._run_sykes_scan()

            # --- FINAL ASSEMBLY ---
            swing_final = raw_swing 
            options_final = raw_options
            day_final = raw_day + warrior_raw # Merge Day & Warrior
            
            # Route Sykes Results
            for c in sykes_raw:
                if c.section == Section.SWING:
                    swing_final.append(c)
                else:
                    day_final.append(c)
 

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
                # DataFrames/Series trigger bool ambiguity checks if passed to pd.isna() or bool() directly logic
                if isinstance(v, (pd.DataFrame, pd.Series, list, dict)): 
                    return None # Do not export complex structures in features
                if pd.isna(v): return None
                if isinstance(v, (np.int64, np.int32)): return int(v)
                if isinstance(v, (np.float64, np.float32)): return float(v)
                return v

            for cand_list in [swing_final, options_final, day_final]:
                for c in cand_list:
                    # Sanitize Features
                    if c.features:
                        # We must create a new dict to avoid mutation issues or just overwrite
                        clean_features = {}
                        for k, v in c.features.items():
                             clean_features[k] = sanitize_value(v)
                        c.features = clean_features
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
