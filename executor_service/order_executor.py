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
        Calculates number of shares based on Risk Percent vs Stop Loss Distance.
        Classic Risk Formula: 
        Risk Amount = Equity * Risk%
        Shares = Risk Amount / (Entry - Stop)
        """
        plan = candidate.trade_plan
        if not plan or plan.entry == plan.stop_loss: return 0

        risk_amount = account_equity * (plan.risk_percent / 100.0)
        risk_per_share = abs(plan.entry - plan.stop_loss)
        
        if risk_per_share <= 0: return 0
        
        shares = math.floor(risk_amount / risk_per_share)
        return max(shares, 1) # Minimum 1 share if valid

    def check_risk_compliance(self, symbol: str) -> str:
        """
        Returns "OK" if safe to trade. 
        Returns error string if risk limits hit.
        """
        if not self.api: return "NO_API"
        
        try:
            # 1. Check Max Positions
            positions = self.api.list_positions()
            if len(positions) >= settings.MAX_OPEN_SWING_POSITIONS:
                return f"MAX_POSITIONS_REACHED ({len(positions)}/{settings.MAX_OPEN_SWING_POSITIONS})"
            
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
        
        # 1. Calculate Size
        # (Ideally fetch real equity, but fallback to 100k for mock if fails)
        try:
            acct = self.api.get_account()
            equity = float(acct.equity)
        except:
            equity = 100000.0
            
        qty = self.calculate_position_size(candidate, equity)
        
        if qty <= 0:
            print(f"SKIP EXECUTION: {symbol} (Calculated Qty 0)")
            return "QTY_ZERO"

        print(f"EXECUTING {side.upper()} {qty} {symbol} @ {plan.entry} (Risk: ${equity * (plan.risk_percent/100.0):.2f})")

        # 2. Submit Bracket Order
        try:
            # We use MARKET for entry to ensure fill in this autonomous bot version
            # But we attach Take Profit and Stop Loss immediately
            
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type='market',
                time_in_force='gtc',
                order_class='bracket',
                take_profit={'limit_price': plan.take_profit},
                stop_loss={'stop_price': plan.stop_loss}
            )
            print(f"ORDER SUBMITTED: {order.id}")
            return f"SUCCESS_{order.id}"
            
        except Exception as e:
            print(f"EXECUTION FAILED: {symbol} - {e}")
            return f"ERROR_{str(e)}"

# Global Instance
executor = OrderExecutor()
