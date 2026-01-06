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
        Calculates position size using Aggressive Allocation Model.
        Shares = Min( Risk_Shares, Cap_Shares )
        """
        plan = candidate.trade_plan
        price = plan.entry
        if price <= 0: return 0
        
        # 1. Determine Parameters based on Section
        if candidate.section == "DAY_TRADE":
            alloc_pct = 0.20 # 20% of Account
            risk_pct = 0.015 # 1.5% Risk
        else: # SWING
            alloc_pct = 0.14 # 14% of Account
            risk_pct = 0.025 # 2.5% Risk
            
        # 2. Risk-Based Sizing (How many shares can I buy without losing > Risk%?)
        stop_dist = abs(price - plan.stop_loss)
        if stop_dist <= 0: stop_dist = price * 0.01 # Fallback to prevent divide by zero
        
        risk_dollars = account_equity * risk_pct
        shares_risk = math.floor(risk_dollars / stop_dist)
        
        # 3. Capital-Cap Sizing (How many shares until I hit Max Allocation?)
        cap_dollars = account_equity * alloc_pct
        shares_cap = math.floor(cap_dollars / price)
        
        # 4. Final Sizing (Conservative of the two)
        final_shares = min(shares_risk, shares_cap)
        
        return max(final_shares, 1) # Min 1

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
        # -----------------

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
            
            # --- JOURNAL LOGGING ---
            try:
                from executor_service.trade_logger import trade_logger
                trade_logger.log_trade_entry(
                    symbol=symbol,
                    bucket=candidate.section,
                    qty=qty,
                    entry_price=plan.entry,
                    stop=plan.stop_loss,
                    target=plan.take_profit
                )
            except Exception as log_err:
                print(f"LOGGER FAIL: {log_err}")
            # -----------------------

            # --- DISCORD NOTIFICATION ---
            try:
                from utils.notifications import notifier
                
                # Determine Bot Name
                bot_name = "🦅 SWING BOT"
                if candidate.section == "SCALP": bot_name = "⚔️ WARRIOR BOT"
                elif candidate.section == "OPTIONS": bot_name = "🎯 OPTIONS BOT"
                elif candidate.section == "DAY_TRADE": bot_name = "⚡ DAY BOT"
                
                msg = (
                    f"**Action:** {side.upper()} {qty} shares\n"
                    f"**Entry:** ${plan.entry:.2f}\n"
                    f"**Stop:** ${plan.stop_loss:.2f}\n"
                    f"**Target:** ${plan.take_profit:.2f}\n"
                    f"**Setup:** {candidate.setup_name}"
                )
                
                notifier.send_message(f"{bot_name}: {symbol}", msg, color=0x00ff00)
            except Exception as note_err:
                print(f"DISCORD FAIL: {note_err}")
            # ----------------------------

            print(f"ORDER SUBMITTED: {order.id}")
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

# Global Instance
executor = OrderExecutor()
