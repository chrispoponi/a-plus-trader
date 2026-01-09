from alpaca_trade_api.rest import REST, TimeFrame
from configs.settings import settings, TradingMode
from strategy_engine.models import Candidate, Direction
import math

class OrderExecutor:
    def __init__(self):
        # Initialize Alpaca Client
        if settings.APCA_API_KEY_ID and settings.APCA_API_SECRET_KEY:
            self.api = REST(
                settings.APCA_API_KEY_ID,
                settings.APCA_API_SECRET_KEY,
                base_url=settings.APCA_API_BASE_URL
            )
            print(f"EXECUTOR: Alpaca Connected ({settings.TRADING_MODE})")
        else:
            self.api = None
            print("EXECUTOR: Alpaca Keys Missing. Execution Disabled.")

    def get_account_buying_power(self) -> float:
        if not self.api: return 0.0
        try:
            acct = self.api.get_account()
            return float(acct.buying_power)
        except Exception as e:
            print(f"Error fetching account: {e}")
            return 0.0

    def calculate_position_size(self, candidate: Candidate, account_equity: float = 100000.0) -> int:
        """
        Calculates position size using Dynamic Conviction Sizing.
        Formula: Base Risk * (Score / Baseline)^2
        """
        plan = candidate.trade_plan
        price = plan.entry
        if price <= 0: return 0
        
        # 1. Base Parameters
        base_risk_pct = settings.MAX_RISK_PER_TRADE_PERCENT # e.g. 0.75
        
        # 2. Conviction Scaling (The Quantitative Edge)
        score = candidate.scores.overall_rank_score
        baseline = 70.0
        
        # Squared Multiplier
        multiplier = (score / baseline) ** 2
        
        # 3. Calculate Dynamic Risk Pct
        scaled_risk_pct = base_risk_pct * multiplier
        
        # 4. Safety Caps (Floor 0.5%, Ceiling 2.0%)
        final_risk_pct = max(0.50, min(scaled_risk_pct, 2.0))
        
        # 5. Calculate Shares
        stop_dist = abs(price - plan.stop_loss)
        if stop_dist <= 0: stop_dist = price * 0.01
        
        risk_dollars = account_equity * (final_risk_pct / 100.0)
        shares_risk = math.floor(risk_dollars / stop_dist)
        
        # Max Alloc Cap (e.g. Max 25% of Portfolio in one stock)
        max_alloc_pct = settings.MAX_PORTFOLIO_RISK_PERCENT / 100.0 # Using as Position Cap proxy? 
        # Actually MAX_PORTFOLIO_RISK implies total risk. 
        # Let's start with a hard 20% position cap rule to avoid concentration.
        cap_dollars = account_equity * 0.20
        shares_cap = math.floor(cap_dollars / price)
        
        final_shares = min(shares_risk, shares_cap)
        
        if final_shares > 0:
            print(f"⚖️ SIZING [{candidate.symbol}]: Score {score:.0f} -> Risk {final_risk_pct:.2f}% (Base {base_risk_pct}%). Qty: {final_shares}")
            
        return max(final_shares, 1)

    def check_risk_compliance(self, symbol: str) -> str:
        """
        Returns "OK" if safe to trade. 
        Returns error string if risk limits hit.
        """
        if not self.api: return "NO_API"
        
        try:
            # 1. Check Max Positions
            positions = self.api.list_positions()
            # Dynamic Cap from Settings
            max_pos = settings.MAX_OPEN_SWING_POSITIONS + settings.MAX_OPEN_DAY_POSITIONS
            if len(positions) >= max_pos:
                return f"MAX_POSITIONS_REACHED ({len(positions)}/{max_pos})"
            
            # 2. Check Duplicates
            for pos in positions:
                if pos.symbol == symbol:
                    return f"ALREADY_HOLDING_{symbol}"
                    
            return "OK"
        except Exception as e:
            print(f"Risk Check Error: {e}")
            return "RISK_CHECK_ERROR"

    def execute_trade(self, candidate: Candidate):
        if not self.api:
            print(f"SKIP EXECUTION: {candidate.symbol} (No API)")
            return "FAILED_NO_API"

        if settings.TRADING_MODE == TradingMode.RESEARCH:
            print(f"SKIP EXECUTION: {candidate.symbol} (Research Mode)")
            return "RESEARCH_ONLY"

        symbol = candidate.symbol
        
        # --- RISK GATE ---
        risk_status = self.check_risk_compliance(symbol)
        if risk_status != "OK":
            print(f"SKIP EXECUTION: {symbol} Risk Rejection: {risk_status}")
            return risk_status

        # --- OPTIONS ROUTING ---
        if candidate.section == "OPTIONS SETUP":
             if not settings.OPTIONS_ENABLED:
                 print(f"SKIP EXECUTION: {symbol} (Options Disabled)")
                 return "SKIPPED_OPTIONS_DISABLED"

             try:
                 from executor_service.options_executor import options_executor
                 return options_executor.execute_condor(candidate)
             except Exception as oe:
                 print(f"Options Routing Error: {oe}")
                 return f"OPT_FAIL: {oe}"
        # -----------------------

        side = "buy" if candidate.direction == Direction.LONG else "sell"
        plan = candidate.trade_plan
        
        # 1. Get Equity
        try:
            acct = self.api.get_account()
            equity = float(acct.equity)
        except:
            equity = 100000.0
            
        qty = self.calculate_position_size(candidate, equity)
        
        if qty <= 0:
            print(f"SKIP EXECUTION: {symbol} (Calculated Qty 0)")
            return "QTY_ZERO"

        print(f"EXECUTING {side.upper()} {qty} {symbol} @ {plan.entry} (Risk: ${equity * 0.015:.2f} - Aggressive)")

        # 2. Submit Bracket Order
        try:
            type_order = 'market'
            tif = 'day'
            limit_price = None
            
            # Specific Logic for Day vs Swing
            if candidate.section == "SWING":
                type_order = 'limit'
                tif = 'gtc'
                limit_price = plan.entry # Use Entry as Limit
            else:
                # Day Trade: Market Entry
                type_order = 'market'
                tif = 'day'
            
            # --- SAFETY SEAL: VALIDATE BRACKET ---
            sl = plan.stop_loss
            tp = plan.take_profit
            en = plan.entry
            
            if not sl or not tp:
                return f"REJECTED_SAFETY: Missing Legs (Stop: {sl}, Target: {tp})"
                
            # Logical Validation
            if side == 'buy':
                if sl >= en: return f"REJECTED_SAFETY: Long Stop ({sl}) >= Entry ({en})"
                if tp <= en: return f"REJECTED_SAFETY: Long Target ({tp}) <= Entry ({en})"
            else: # sell (short)
                if sl <= en: return f"REJECTED_SAFETY: Short Stop ({sl}) <= Entry ({en})"
                if tp >= en: return f"REJECTED_SAFETY: Short Target ({tp}) >= Entry ({en})"
            # -------------------------------------

            # Construct Args
            order_args = {
                "symbol": symbol,
                "qty": qty,
                "side": side,
                "type": type_order,
                "time_in_force": tif,
                "order_class": 'bracket',
                "take_profit": {'limit_price': tp},
                "stop_loss": {'stop_price': sl}
            }
            
            if limit_price:
                order_args["limit_price"] = limit_price
            
            order = self.api.submit_order(**order_args)
            print(f"ORDER SUBMITTED: {order.id}") # Critical Log

            # --- DISCORD NOTIFICATION (PRIORITY) ---
            try:
                from utils.notifications import notifier
                
                # Determine Bot Name
                bot_name = "🦅 SWING BOT"
                if candidate.section == "SCALP": bot_name = "⚔️ WARRIOR BOT"
                elif candidate.section == "OPTIONS": bot_name = "🎯 OPTIONS BOT"
                elif candidate.section == "DAY_TRADE": bot_name = "⚡ DAY BOT"
                
                # Calculate R-Risk/Reward
                risk = abs(en - sl) if sl else 1
                reward = abs(tp - en) if tp else 1
                rr = reward / risk if risk > 0 else 0
                
                msg = (
                    f"**Action:** {side.upper()} {qty} shares\n"
                    f"**Entry:** ${plan.entry:.2f}\n"
                    f"**Stop:** ${plan.stop_loss:.2f}\n"
                    f"**Target:** ${plan.take_profit:.2f} ({rr:.1f}R)\n"
                    f"**Score:** {candidate.scores.overall_rank_score}/100\n"
                    f"**Setup:** {candidate.setup_name}"
                )
                
                notifier.send_message(f"🚨 {bot_name}: {symbol}", msg, color=0x00ff00)
            except Exception as note_err:
                print(f"DISCORD FAIL: {note_err}")
            # ----------------------------

            # --- JOURNAL LOGGING ---
            try:
                from executor_service.trade_logger import trade_logger
                trade_logger.log_trade_entry(
                    symbol=symbol,
                    bucket=candidate.section,
                    qty=qty,
                    entry_price=plan.entry,
                    stop=plan.stop_loss,
                    target=plan.take_profit,
                    score=candidate.scores.overall_rank_score,
                    setup_name=candidate.setup_name
                )
            except Exception as log_err:
                print(f"LOGGER FAIL: {log_err}")
            # -----------------------
            
            return f"SUCCESS_{order.id}"
            
        except Exception as e:
            print(f"EXECUTION FAILED: {symbol} - {e}")
            return f"ERROR_{str(e)}"

    def ensure_protective_stops(self) -> list:
        """
        Safety Net: Scans for open positions without active Stop Loss orders.
        If found, places an emergency Stop Loss at 2.0% risk from CURRENT price.
        Returns list of actions taken.
        """
        if not self.api: return []
        
        actions = []
        try:
            positions = self.api.list_positions()
            open_orders = self.api.list_orders(status='open')
            
            # Build map of covered symbols (Checking for Stop types)
            covered = set()
            for o in open_orders:
                if o.type in ['stop', 'stop_limit', 'trailing_stop']:
                    covered.add(o.symbol)
                    
            for p in positions:
                if p.symbol not in covered:
                    # NAKED POSITION FOUND
                    sym = p.symbol
                    qty_val = float(p.qty)
                    qty_int = abs(int(qty_val))
                    curr = float(p.current_price)
                    side = 'sell' if qty_val > 0 else 'buy'
                    
                    # Emergency Logic: 2.0% distance (Wide enough to avoid noise, tight enough to save account)
                    dist = curr * 0.02
                    stop_price = round(curr - dist, 2) if side == 'sell' else round(curr + dist, 2)
                    
                    try:
                        self.api.submit_order(
                            symbol=sym,
                            qty=qty_int,
                            side=side,
                            type='stop',
                            time_in_force='gtc',
                            stop_price=stop_price
                        )
                        msg = f"🛡️ AUTO-HEALED: {sym} (Added Safety Stop @ {stop_price})"
                        actions.append(msg)
                        print(msg)
                    except Exception as e:
                        err = f"❌ FAILED TO HEAL {sym}: {e}"
                        actions.append(err)
                        print(err)
        except Exception as cx:
            print(f"Watchdog Error: {cx}")
            
        return actions

    async def manage_peak_exits(self):
        """
        PROFIT PROTECTOR:
        Loops through active LONG positions.
        Checks for 'Peak Exhaustion' (Price rising, Volume falling).
        If detected, TIGHTENS the Stop Loss (aggregates to a Trailing Stop).
        """
        if not self.api: return
        
        from strategy_engine.data_loader import DataLoader
        dl = DataLoader()
        
        print("🦅 CHECKING FOR PEAK EXHAUSTION...")
        
        try:
            positions = self.api.list_positions()
            for p in positions:
                if p.side != 'long': continue # Only managing Longs for now
                
                symbol = p.symbol
                qty = float(p.qty)
                current_price = float(p.current_price)
                
                # 1. Fetch Data (5min candles for sensitivity)
                data_map = dl.fetch_intraday_snapshot([symbol], timeframe='5Min')
                if symbol not in data_map: continue
                
                df = data_map[symbol].get('intraday_df')
                if df is None or df.empty: continue
                
                # 2. Calc Exhaustion Logic
                # (Replicating backtest logic)
                df['avg_vol'] = df['volume'].rolling(20).mean()
                df['vol_ratio'] = df['volume'] / df['avg_vol']
                df['high_low'] = df['high'] - df['low']
                df['atr'] = df['high_low'].rolling(14).mean()
                
                curr = df.iloc[-1]
                prev = df.iloc[-2]
                
                # Signal: Price Up, Volume Weak (< 90% avg)
                price_up = curr['close'] > prev['close']
                vol_weak = curr['vol_ratio'] < 0.9
                is_exhausted = price_up and vol_weak
                
                # 3. Determine 'Tight Stop' Price
                atr = curr['atr'] if curr['atr'] > 0 else (current_price * 0.01)
                
                if is_exhausted:
                    # TIGHTEN: 0.5 ATR Trail
                    proposed_stop = current_price - (0.5 * atr)
                    mode = "EXHAUSTION (Tight)"
                else:
                    # STANDARD TRAIL: 2.0 ATR (Standard Wave Ride)
                    proposed_stop = current_price - (2.0 * atr)
                    mode = "STANDARD (Wide)"
                    
                proposed_stop = round(proposed_stop, 2)
                
                # 4. Update Existing Stop Order
                # Find the open stop order
                orders = self.api.list_orders(status='open', symbol=symbol)
                stop_order = None
                for o in orders:
                    if o.type in ['stop', 'stop_limit', 'trailing_stop']:
                        stop_order = o
                        break
                
                if stop_order:
                    current_stop_price = float(stop_order.stop_price) if stop_order.stop_price else 0
                    
                    # RATCHET LOGIC: Only move UP
                    if proposed_stop > current_stop_price:
                        # Safety Check: Don't move stop ABOVE current price
                        if proposed_stop < current_price:
                            print(f"🌊 RATCHET: {symbol} [{mode}] | Moving Stop {current_stop_price} -> {proposed_stop}")
                            try:
                                self.api.replace_order(
                                    order_id=stop_order.id,
                                    stop_price=proposed_stop
                                )
                                from utils.notifications import notifier
                                notifier.send_message(
                                    f"🌊 PEAK MANAGER: {symbol}",
                                    f"Locked Profit. Stop moved to ${proposed_stop} ({mode}).\nPrice: ${current_price}",
                                    color=0x00ff00
                                )
                            except Exception as replace_err:
                                print(f"Generic Replace Error: {replace_err}")

        except Exception as e:
            print(f"Peak Manager Error: {e}")
            
# Global Instance
executor = OrderExecutor()
