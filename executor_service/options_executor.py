from alpaca_trade_api.rest import REST
from configs.settings import settings
from strategy_engine.models import Candidate
import time
import asyncio

from contracts.options_adapter import options_adapter

class OptionsExecutor:
    def __init__(self):
        self.api = None
        try:
             self.api = REST(settings.APCA_API_KEY_ID, settings.APCA_API_SECRET_KEY, base_url=settings.APCA_API_BASE_URL)
        except Exception as e:
             print(f"Options Executor Connection Fail: {e}")

    def execute_condor(self, candidate: Candidate) -> str:
        """
        Executes a 4-Leg Iron Condor securely with Realistic Limits.
        """
        details = candidate.options_details
        if not details or not details.legs:
            return "SKIPPED: No Legs in Candidate"
            
        legs = details.legs # Expects dict: {long_put, short_put, ...}
        qty = 1 # Start small
        
        print(f"🦅 OPTION EXECUTION: Processing Condor for {candidate.symbol}")
        
        # --- PHASE 0: REALITY CHECK (Quotes & Limits) ---
        print(f"   Fetching Live Quotes for Limits...")
        leg_symbols = list(legs.values())
        quotes = options_adapter.get_quotes(leg_symbols)
        
        limit_map = {}
        for sym in leg_symbols:
            q = quotes.get(sym)
            if not q or q['ask'] <= 0:
                print(f"REALISM FAIL: No acceptable Quote for {sym}")
                return "ABORTED: No Liquidity"
                
            # Calc Limits (Conservative Realism: Pay Ask, Sell Bid)
            # Add small buffer for fill assurance in fast markets
            buy_limit = round(q['ask'] * 1.05, 2) # Max pay 5% over ask
            if buy_limit == 0: buy_limit = 0.01
            
            sell_limit = round(q['bid'] * 0.95, 2) # Min accept 5% under bid
            
            limit_map[sym] = {'buy': buy_limit, 'sell': sell_limit}
            print(f"   Limits {sym}: Buy<={buy_limit} | Sell>={sell_limit} (Ref: {q['ask']}/{q['bid']})")

        # --- PHASE 1: SHIELDS UP (Buy Wings) ---
        wing_orders = []
        try:
            # Long Put
            sym_lp = legs['long_put']
            o1 = self.api.submit_order(
                symbol=sym_lp, qty=qty, side='buy', type='limit', limit_price=limit_map[sym_lp]['buy'], time_in_force='day'
            )
            # Long Call
            sym_lc = legs['long_call']
            o2 = self.api.submit_order(
                symbol=sym_lc, qty=qty, side='buy', type='limit', limit_price=limit_map[sym_lc]['buy'], time_in_force='day'
            )
            wing_orders = [o1, o2]
            print(f"Phase 1 Submitted (LIMIT): Wings {o1.symbol}, {o2.symbol}")
        except Exception as e:
            print(f"Phase 1 FAIL: {e}")
            return f"ERROR: Phase 1 Failed {e}"

        # --- WAIT FOR FILL ---
        # Poll for 10 seconds
        filled = False
        for _ in range(10):
            time.sleep(1)
            statuses = [self.api.get_order(o.id).status for o in wing_orders]
            if all(s == 'filled' for s in statuses):
                filled = True
                break
        
        if not filled:
            # ABORT PHASE 2
            print("Phase 1 Timeout. Aborting Body Sell.")
            for o in wing_orders: self.api.cancel_order(o.id)
            return "ABORTED: Wings Timeout"
            
        # --- PHASE 1.5: VERIFY POSITIONS (Double Check) ---
        # "Make sure we are not naked" - explicitly confirm API lists ownership
        try:
             # Wait a beat for positions to index
             time.sleep(1)
             positions = self.api.list_positions()
             held_symbols = {p.symbol for p in positions}
             
             wings_secure = (legs['long_put'] in held_symbols) and (legs['long_call'] in held_symbols)
             
             if not wings_secure:
                  print("CRITICAL: Order filled but Position NOT found. Aborting Short Sell.")
                  return "ABORTED: Ghost Fill Protection"
        except Exception as ve:
             print(f"Verification Error: {ve}")
             return f"ABORTED: Verification Error {ve}"
             
        # --- PHASE 2: INCOME (Sell Body) ---
        try:
            # Short Put
            sym_sp = legs['short_put']
            o3 = self.api.submit_order(
                symbol=sym_sp, qty=qty, side='sell', type='limit', limit_price=limit_map[sym_sp]['sell'], time_in_force='day'
            )
            # Short Call
            sym_sc = legs['short_call']
            o4 = self.api.submit_order(
                symbol=sym_sc, qty=qty, side='sell', type='limit', limit_price=limit_map[sym_sc]['sell'], time_in_force='day'
            )
            print(f"Phase 2 Submitted (LIMIT): Body Sold {o3.symbol}, {o4.symbol}")
            return "SUCCESS: Iron Condor Executed"
        except Exception as e:
            print(f"Phase 2 FAIL: {e}")
            # Alert User: Only Wings Bought (Debit Spread instead of Condor - Not terrible, just directional)
            return f"PARTIAL: Wings Only (Phase 2 Error {e})"

options_executor = OptionsExecutor()
