
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta, time
from typing import List, Dict, Any
from alpaca_trade_api.rest import REST, TimeFrame
from configs.settings import settings
from strategy_engine.swing_setups import SwingSetup_20_50
from strategy_engine.day_trade_strategy import DayTradeEngine
from strategy_engine.experimental_strategies import DonchianBreakoutStrategy, RSI2MeanReversionStrategy
from strategy_engine.elite_strategy import SwingSetup_Elite
from strategy_engine.kellog_strategy import KellogStrategy
from strategy_engine.congress_strategy import CongressStrategy
from strategy_engine.buffett_strategy import BuffettStrategy
from strategy_engine.rsi_bands_strategy import RSIBandsStrategy
from strategy_engine.warrior_strategy import WarriorStrategy
from strategy_engine.models import Direction
import warnings

# Suppress pandas future warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

class BacktestEngine:
    def __init__(self, strategy_type='SWING'):
        if not settings.APCA_API_KEY_ID:
            print("BACKTEST: No API Keys found in settings. Cannot fetch data.")
            return

        self.api = REST(
            settings.APCA_API_KEY_ID,
            settings.APCA_API_SECRET_KEY,
            base_url=settings.APCA_API_BASE_URL
        )
        self.strategy_type = strategy_type
        
        if strategy_type == 'SWING':
            self.setup = SwingSetup_20_50()
        elif strategy_type == 'DAY':
            self.setup = DayTradeEngine()
        elif strategy_type == 'DONCHIAN':
            self.setup = DonchianBreakoutStrategy()
        elif strategy_type == 'RSI2':
            self.setup = RSI2MeanReversionStrategy()
        elif strategy_type == 'ELITE':
            self.setup = SwingSetup_Elite()
        elif strategy_type == 'OPTIONS_SIM':
            self.setup = SwingSetup_Elite() # Signals from Elite, Execution is Options
        elif strategy_type == 'OPTIONS_INVERSE':
            self.setup = SwingSetup_Elite() # Signals from Elite, Inverted Execution
        elif strategy_type == 'SNIPER_OPTIONS':
            self.setup = DayTradeEngine() # Signals from Day Trade, Execution is Options
        elif strategy_type == 'KELLOG':
            self.setup = KellogStrategy()
        elif strategy_type == 'CONGRESS':
            self.setup = CongressStrategy()
        elif strategy_type == 'BUFFETT':
            self.setup = BuffettStrategy()
        elif strategy_type == 'RSI_BANDS':
            self.setup = RSIBandsStrategy()
        elif strategy_type == 'WARRIOR':
            self.setup = WarriorStrategy()
            
        self.initial_capital = 100000.0
        self.cash = self.initial_capital
        self.positions = [] # List of active position dicts
        self.trade_log = [] # List of closed trades
        self.equity_curve = [] # List of {date, equity}
        
    def fetch_backtest_data(self, symbols: List[str], days: int, timeframe_str='1Day') -> Dict[str, pd.DataFrame]:
        """
        Fetches historical data.
        If '1Day', computes vectorized swing indicators.
        If '5Min', returns raw data for DayTradeEngine to process iteratively.
        """
        print(f"BACKTEST: Fetching {days} days of history ({timeframe_str}) for {len(symbols)} symbols...")
        
        # Calculate start date
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Determine TimeFrame object
        tf = TimeFrame.Day
        if timeframe_str == '5Min':
             # We use string directly in get_bars usually, but let's try strict object if needed
             # For simplicity, passing string '5Min' is supported by get_bars
             tf = '5Min'

        # Batch Fetch
        try:
            bars = self.api.get_bars(
                symbols,
                tf,
                start=start_date,
                end=end_date,
                adjustment='raw',
                feed='iex'
            ).df
        except Exception as e:
            print(f"BACKTEST ERROR: API Fetch failed: {e}")
            return {}

        results = {}
        
        if bars.empty:
            return results

        # Process per symbol
        unique_syms = bars.index.get_level_values(0).unique() if isinstance(bars.index, pd.MultiIndex) else bars['symbol'].unique()
        
        for sym in unique_syms:
            # Extract DF
            if isinstance(bars.index, pd.MultiIndex):
                df = bars.xs(sym).copy()
            else:
                df = bars[bars['symbol'] == sym].copy()
                # If index is already timestamp, great.
                pass
            
            # Ensure sorted
            df.sort_index(inplace=True)
            
            if self.strategy_type == 'SWING':
                # --- SWING INDICATORS (Vectorized) ---
                df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
                df['sma50'] = df['close'].rolling(window=50).mean()
                
                # ATR
                high_low = df['high'] - df['low']
                high_close = (df['high'] - df['close'].shift()).abs()
                low_close = (df['low'] - df['close'].shift()).abs()
                ranges = pd.concat([high_low, high_close, low_close], axis=1)
                true_range = np.max(ranges, axis=1)
                df['atr'] = true_range.rolling(14).mean()
                
                # Helpers
                df['vol_avg_20'] = df['volume'].rolling(20).mean()
                df['prev_close'] = df['close'].shift(1)
                
                # Patterns
                body = (df['close'] - df['open']).abs()
                lower_wick = np.minimum(df['close'], df['open']) - df['low']
                upper_wick = df['high'] - np.maximum(df['close'], df['open'])
                df['is_hammer'] = (lower_wick > (2 * body)) & (upper_wick < body)
                df['candle_pattern'] = np.where(df['is_hammer'], 'hammer', 'normal')
                df['volume_dry_up'] = df['volume'] < (df['vol_avg_20'] * 0.7)
                df['sector_rs'] = False 
                
            elif self.strategy_type == 'KELLOG':
                # Need VWAP, ATR, and Volume Average for exits
                # VWAP (Cumulative calculation, typically intraday)
                # For daily bars, a simple approximation or using a different indicator might be needed.
                # Assuming 'vwap' is available or calculated by the strategy engine for intraday.
                # For daily, we'll use a simple moving average as a proxy if VWAP isn't directly available.
                df['vwap'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()
                
                # ATR (14-period)
                high_low = df['high'] - df['low']
                high_close = (df['high'] - df['close'].shift()).abs()
                low_close = (df['low'] - df['close'].shift()).abs()
                ranges = pd.concat([high_low, high_close, low_close], axis=1)
                true_range = np.max(ranges, axis=1)
                df['atr'] = true_range.rolling(14).mean()
                
                # Volume Average (e.g., 20-period)
                df['vol_avg'] = df['volume'].rolling(20).mean()
                         
            elif self.strategy_type == 'DONCHIAN':
                # Donchian Channels (20 High, 10 Low)
                # Shift by 1 so we compare Close vs Previous Highs
                df['high_20'] = df['high'].rolling(20).max().shift(1)
                df['low_10'] = df['low'].rolling(10).min().shift(1)
                
            elif self.strategy_type == 'RSI2':
                # SMA 200, SMA 5
                df['sma200'] = df['close'].rolling(200).mean()
                df['sma5'] = df['close'].rolling(5).mean()
                
                # RSI 2
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(2).mean() # Simple RSI for 2 period approximation
                loss = (-delta.where(delta < 0, 0)).rolling(2).mean()
                rs = gain / loss
                df['rsi2'] = 100 - (100 / (1 + rs))
                # Fix NaNs or Inf
                df['rsi2'] = df['rsi2'].fillna(50)

            elif self.strategy_type == 'RSI_BANDS':
                # Bollinger Bands (20, 2)
                df['sma20'] = df['close'].rolling(window=20).mean()
                std20 = df['close'].rolling(window=20).std()
                df['upper_bb'] = df['sma20'] + (std20 * 2)
                df['lower_bb'] = df['sma20'] - (std20 * 2)
                
                # SMA 50
                df['sma50'] = df['close'].rolling(window=50).mean()
                
                # RSI 14
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                df['rsi'] = 100 - (100 / (1 + rs))
                df['rsi'] = df['rsi'].fillna(50)
            
            elif self.strategy_type == 'ELITE' or self.strategy_type == 'OPTIONS_SIM' or self.strategy_type == 'OPTIONS_INVERSE':
                # Need ADX(14) and RSI(14)
                
                # RSI 14
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                df['rsi'] = 100 - (100 / (1 + rs))
                df['rsi'] = df['rsi'].fillna(50)
                
                # ADX 14 (Vectorized approximation)
                high = df['high']
                low = df['low']
                close = df['close']
                
                # TR
                tr1 = high - low
                tr2 = (high - close.shift()).abs()
                tr3 = (low - close.shift()).abs()
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                
                # DM
                up_move = high - high.shift()
                down_move = low.shift() - low
                
                plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
                minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
                
                # Convert to Series for rolling
                tr_s = pd.Series(tr, index=df.index)
                plus_dm_s = pd.Series(plus_dm, index=df.index)
                minus_dm_s = pd.Series(minus_dm, index=df.index)
                
                # Wilder's Smoothing (Approx via rolling mean for speed, or ewm)
                # ADX usually uses Wilder which is alpha=1/14. ewm(alpha=1/14)
                atr14 = tr_s.ewm(alpha=1/14, adjust=False).mean()
                plus_di = 100 * (plus_dm_s.ewm(alpha=1/14, adjust=False).mean() / atr14)
                minus_di = 100 * (minus_dm_s.ewm(alpha=1/14, adjust=False).mean() / atr14)
                
                dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
                df['adx'] = dx.ewm(alpha=1/14, adjust=False).mean()
                
                # Base Swing Indicators as well
                df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
                df['sma50'] = df['close'].rolling(window=50).mean()
                df['atr'] = atr14 # Re-use

            results[sym] = df
            
            # CACHE DATA
            os.makedirs(f"data_cache_{self.strategy_type}", exist_ok=True)
            df.to_csv(f"data_cache_{self.strategy_type}/{sym}.csv")
            
        print(f"BACKTEST: Data processed for {len(results)} symbols.")
        return results

    def run(self, symbols: List[str], days=252):
        print(f"\n--- 🦅 HARMONIC EAGLE BACKTESTER ---\nStrategy: {self.strategy_type}\nPeriod: Last {days} Days\nCapital: ${self.initial_capital:,.2f}\n")
        # Select Timeframe
        tf_str = '1Day'
        if self.strategy_type == 'DAY' or self.strategy_type == 'SNIPER_OPTIONS' or self.strategy_type == 'KELLOG' or self.strategy_type == 'WARRIOR':
             tf_str = '5Min'
        
        # CONGRESS and BUFFETT use 1Day default
             
        data_map = self.fetch_backtest_data(symbols, days, timeframe_str=tf_str)

        if not data_map:
            print("No data availability.")
            return

        # Get all unique timestamps
        # For Swing: Dates. For Day: Timestamps.
        all_timestamps = sorted(list(set().union(*(df.index for df in data_map.values()))))
        
        try:
            from tqdm import tqdm
            pbar = tqdm(all_timestamps, unit="bar")
        except ImportError:
            pbar = all_timestamps

        for current_time in pbar:
            # 1. PROCESS EXITS
            self._process_exits(current_time, data_map)
            
            # 2. PROCESS ENTRIES
            # For Day Trading: We enter during the day (Intraday checks).
            # For Swing: We enter at Close.
            self._process_entries(current_time, data_map)
            
            # 3. EQUITY SNAPSHOT (Daily only, or every bar?)
            # Doing every bar is heavy. Let's do every bar for Day Trade accuracy.
            self._update_equity(current_time, data_map)

        self._generate_report()

    def _update_equity(self, current_time, data_map):
         # Skip equity calc every minute to save logs, maybe purely end of day?
         # For MVP, calculate every step.
         open_value = 0
         for p in self.positions:
            sym = p['symbol']
            try:
                if current_time in data_map[sym].index:
                    curr_price = data_map[sym].loc[current_time]['close']
                    # Handle Series vs Scalar
                    if isinstance(curr_price, pd.Series): curr_price = curr_price.iloc[0]
                    open_value += curr_price * p['qty']
                else:
                    open_value += p['entry_price'] * p['qty']
            except:
                 open_value += p['entry_price'] * p['qty']
         
         total_equity = self.cash + open_value
         # Record
         # For Swing: Use date. For Day: Use timestamp.
         self.equity_curve.append({"time": current_time, "equity": total_equity})

    def _process_exits(self, current_time, data_map):
        closed_indices = []
        for i, pos in enumerate(self.positions):
            sym = pos['symbol']
            try:
                row = data_map[sym].loc[current_time]
                if isinstance(row, pd.DataFrame): row = row.iloc[0] # Duplicate handling
            except KeyError: continue # No data for this bar

            low = float(row['low'])
            high = float(row['high'])
            close = float(row['close'])
            
            exit_price = None
            reason = ""
            
            # Generic logic
            is_long = pos['direction'] == Direction.LONG
            
            if is_long:
                 if low <= pos['stop_loss']: exit_price, reason = pos['stop_loss'], "STOP_LOSS"
                 elif high >= pos['take_profit']: exit_price, reason = pos['take_profit'], "TAKE_PROFIT"
            else:
                 if high >= pos['stop_loss']: exit_price, reason = pos['stop_loss'], "STOP_LOSS"
                 elif low <= pos['take_profit']: exit_price, reason = pos['take_profit'], "TAKE_PROFIT"
            
            # Time / EOD Stop / Strategy Specific Exits
            if self.strategy_type == 'SWING' or self.strategy_type == 'ELITE' or self.strategy_type == 'OPTIONS_SIM' or self.strategy_type == 'OPTIONS_INVERSE':
                 if (current_time - pos['entry_date']).days >= 7:
                     exit_price, reason = close, "TIME_STOP"
            elif self.strategy_type == 'CONGRESS':
                 if (current_time - pos['entry_date']).days >= 30:
                     exit_price, reason = close, "PELOSI_EXIT_30D"
            elif self.strategy_type == 'BUFFETT':
                 if (current_time - pos['entry_date']).days >= 365:
                     exit_price, reason = close, "VALUE_EXIT_1YR"
            elif self.strategy_type == 'DAY':
                 if current_time.time() >= time(15, 55):
                     exit_price, reason = close, "EOD_EXIT"
            elif self.strategy_type == 'SNIPER_OPTIONS':
                 # 1 Hour Time Stop
                 # Assuming 5Min bars, simplistic check
                 # Delta check preferred
                 time_held = current_time - pos['entry_date']
                 if time_held.total_seconds() >= 3600: # 1 Hour
                     exit_price, reason = close, "TIME_STOP_1HR"
                 
                 # Tight Targets (Override generic Stop/TP if needed, but usually pos['stop_loss'] handles price stops)
                 # We set generous stops in entry, but here we enforce Time strictly.
                 # Let's rely on pos['take_profit'] and pos['stop_loss'] for price, which we must set correctly in _process_entries.
                 
            elif self.strategy_type == 'DONCHIAN':
                # Trailing Stop: Low of last 10 days
                # We need 'low_10' from data.
                # 'low_10' in df is strictly 'Min of Previous 10'.
                low_10 = float(row.get('low_10', 0))
                if low <= low_10:
                    exit_price, reason = low_10, "TRAILING_STOP"
            elif self.strategy_type == 'RSI2':
                # Exit if Price > SMA5 OR RSI > 90
                # We check conditions at Close of day
                sma5 = float(row.get('sma5', 0))
                rsi2 = float(row.get('rsi2', 50))
                if close > sma5:
                    exit_price, reason = close, "SMA5_EXIT"
                elif rsi2 > 90:
                    exit_price, reason = close, "RSI_EXTREME"

            elif self.strategy_type == 'RSI_BANDS':
                # EXIT RULES
                # 1. RSI > 75 (Overbought)
                # 2. Price > Upper BB (Extension)
                # 3. PROFIT PROTECTION: If PnL > 0.5% and turning red (Close < Open or Close < PrevClose), SELL.
                
                rsi = float(row.get('rsi', 50))
                upper_bb = float(row.get('upper_bb', 99999))
                sma50 = float(row.get('sma50', 0))
                
                # Calculate current PnL %
                curr_pnl_pct = (close - pos['entry_price']) / pos['entry_price']
                
                if rsi > 75:
                    exit_price, reason = close, "RSI_EXIT_75"
                elif close > upper_bb:
                    exit_price, reason = close, "BB_EXTENSION_EXIT"
                elif curr_pnl_pct > 0.005: 
                    # > 0.5% Profit
                    # Check for Reversal (Bearish Candle or Close < Prev High)
                    # Simple: If Close < Open (Red Candle Day), take the profit.
                    is_red_candle = close < float(row.get('open', 0))
                    if is_red_candle:
                         exit_price, reason = close, "PROFIT_PROTECT_0.5%"
                
            if exit_price:
                # PnL Calculation
                stock_pnl_pct = 0
                if is_long:
                    stock_pnl_pct = (exit_price - pos['entry_price']) / pos['entry_price']
                else:
                    stock_pnl_pct = (pos['entry_price'] - exit_price) / pos['entry_price']
                
                # --- OPTIONS SIMULATION LOGIC ---
                if self.strategy_type == 'OPTIONS_SIM':
                    # Leverage Factor: 10x (Conservative Delta proxy)
                    days_held = (current_time - pos['entry_date']).days
                    theta_loss_pct = days_held * 0.03
                    option_pnl_pct = (stock_pnl_pct * 10.0) - theta_loss_pct
                    if option_pnl_pct < -1.0: option_pnl_pct = -1.0
                    
                    capital_allocated = pos['entry_price'] * pos['qty'] 
                    pnl = capital_allocated * option_pnl_pct
                    self.cash += (capital_allocated + pnl)

                elif self.strategy_type == 'OPTIONS_INVERSE':
                    # FADE THE TREND (Buy PUTS on Long Signal)
                    # Direction: SHORT (We are Shorting the Stock via Puts)
                    
                    # Stock PnL for Short
                    # If Stock +2%, Short PnL = -2%
                    # If Stock -2%, Short PnL = +2%
                    short_stock_pnl_pct = (pos['entry_price'] - exit_price) / pos['entry_price']
                    
                    # Option Leverage (10x)
                    days_held = (current_time - pos['entry_date']).days
                    theta_loss_pct = days_held * 0.03
                    
                    option_pnl_pct = (short_stock_pnl_pct * 10.0) - theta_loss_pct
                    if option_pnl_pct < -1.0: option_pnl_pct = -1.0
                    
                    capital_allocated = pos['entry_price'] * pos['qty']
                    pnl = capital_allocated * option_pnl_pct
                    self.cash += (capital_allocated + pnl)

                elif self.strategy_type == 'SNIPER_OPTIONS':
                    # INTRADAY HIGH LEVERAGE
                    # Proxy: 20x Leverage (Weekly Options on Expiry week)
                    # No Theta (Intraday is negligible for <1hr holds usually)
                    
                    # Stock move 0.5% -> Option move 10%
                    option_pnl_pct = stock_pnl_pct * 20.0
                    
                    # Cap Loss at -100%
                    if option_pnl_pct < -1.0: option_pnl_pct = -1.0
                    
                    capital_allocated = pos['entry_price'] * pos['qty']
                    pnl = capital_allocated * option_pnl_pct
                    self.cash += (capital_allocated + pnl)

                else:
                    # STANDARD STOCK SIMULATION
                    pnl = (exit_price - pos['entry_price']) * pos['qty'] if is_long else (pos['entry_price'] - exit_price) * pos['qty']
                    self.cash += (pos['entry_price'] * pos['qty'] + pnl)
                
                self.trade_log.append({
                    "date": current_time, "symbol": sym, "side": "LONG" if is_long else "SHORT",
                    "result": reason, "entry": pos['entry_price'], "exit": exit_price, "pnl": pnl
                })
                closed_indices.append(i)
                
        for i in sorted(closed_indices, reverse=True): del self.positions[i]

    def _process_entries(self, current_time, data_map):
        # Scan Logic
        for sym, df in data_map.items():
            try:
                if current_time not in df.index: continue
            except: continue
            
            if any(p['symbol'] == sym for p in self.positions): continue # Max 1 per symbol
            
            row = df.loc[current_time]
            if isinstance(row, pd.DataFrame): row = row.iloc[0]
            
            # Universal Feature Dict (Pass everything available)
            feature_dict = row.to_dict()
            feature_dict['row'] = row # Pass full row access
            feature_dict['df'] = df
            feature_dict['current_date'] = current_time
            
            # Map index/special fields if needed
            # (row.to_dict handles close, high, low, ema20, rsi2, etc automatically)
            
            if self.strategy_type == 'DAY' or self.strategy_type == 'SNIPER_OPTIONS' or self.strategy_type == 'KELLOG' or self.strategy_type == 'WARRIOR':
                 idx_pos = df.index.get_loc(current_time)
                 if isinstance(idx_pos, slice): idx_pos = idx_pos.start
                 if idx_pos < 50: continue
                 subset = df.iloc[idx_pos-50 : idx_pos+1]
                 feature_dict['intraday_df'] = subset

            # Analyze
            candidate = self.setup.analyze(sym, feature_dict)
            
            if candidate:
                 # Entry!
                 price = candidate.trade_plan.entry
                 stop = candidate.trade_plan.stop_loss
                 take_profit = candidate.trade_plan.take_profit
                 
                 # SNIPER OVERRIDE
                 if self.strategy_type == 'SNIPER_OPTIONS':
                     # Force 1% Target (-0.5% Stop)
                     # Option proxy: +20% / -10%
                     if candidate.direction == Direction.LONG:
                         take_profit = price * 1.01
                         stop = price * 0.995
                     else:
                         take_profit = price * 0.99
                         stop = price * 1.005 # Short Stop is higher

                 risk_per = abs(price - stop)
                 if risk_per == 0: continue
                 
                 risk_amt = self.initial_capital * 0.0075 
                 # For SNIPER, we risk less per trade because volatility is insane? 
                 # Or we risk normal amount.
                 
                 qty = int(risk_amt / risk_per)
                 max_cost = self.initial_capital * 0.20
                 if (qty * price) > max_cost: qty = int(max_cost / price)
                 if qty < 1 or self.cash < (qty * price): continue
                 
                 self.cash -= (qty * price)
                 self.positions.append({
                     "symbol": sym, "entry_date": current_time, "entry_price": price,
                     "qty": qty, "stop_loss": stop, "take_profit": take_profit,
                     "direction": candidate.direction
                 })

    def _generate_report(self):
        print("\n--- 📊 BACKTEST RESULTS ---")
        if not self.trade_log:
            print("No trades executed.")
            return

        df = pd.DataFrame(self.trade_log)
        total_pnl = df['pnl'].sum()
        final_equity = self.equity_curve[-1]['equity']
        roi = ((final_equity - self.initial_capital) / self.initial_capital) * 100
        print(f"Total Trades: {len(df)}")
        print(f"Total PFnL:   ${total_pnl:,.2f}")
        print(f"Final Equity: ${final_equity:,.2f} ({roi:+.2f}%)")
        print("\nLast 5 Trades:")
        print(df.tail(5)[['date', 'symbol', 'side', 'result', 'pnl']].to_string(index=False))
