from typing import Optional
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import APIError
from configs.settings import settings

class AlpacaAdapter:
    def __init__(self):
        self.key_id = settings.APCA_API_KEY_ID
        self.secret = settings.APCA_API_SECRET_KEY
        self.base_url = settings.APCA_API_BASE_URL
        self.mode = settings.TRADING_MODE
        
        # Initialize the official API client
        if self.key_id and self.secret:
            self.api = tradeapi.REST(
                self.key_id, 
                self.secret, 
                self.base_url, 
                api_version='v2'
            )
        else:
            print("WARNING: Alpaca credentials missing. Adapter in stub mode.")
            self.api = None

    def get_account(self):
        if not self.api:
            return None
        return self.api.get_account()

    def place_order(self, symbol: str, qty: float, side: str, order_type: str, 
                   limit_price: Optional[float] = None, stop_price: Optional[float] = None,
                   take_profit: Optional[float] = None, stop_loss: Optional[float] = None):
        
        if not self.api:
            return {"status": "error", "message": "Alpaca API not initialized"}

        try:
            # Construct Bracket Order args if provided
            order_args = {
                "symbol": symbol,
                "qty": qty,
                "side": side,
                "type": order_type,
                "time_in_force": "gtc"
            }
            
            if order_type == "limit" and limit_price:
                order_args["limit_price"] = limit_price
            if order_type == "stop" and stop_price:
                order_args["stop_price"] = stop_price
            
            # Advanced Bracket Logic (OTO)
            if take_profit or stop_loss:
                # Alpaca expects bracket parameters usually within order_class='bracket'
                # or simplified params if using simple OTO
                # For simplicity/robustness, we'll try the take_profit / stop_loss dicts if supported
                order_args["order_class"] = "bracket"
                if take_profit:
                    order_args["take_profit"] = {"limit_price": take_profit}
                if stop_loss:
                    order_args["stop_loss"] = {"stop_price": stop_loss}
            
            # Log intent
            print(f"[{self.mode}] Submitting to Alpaca: {order_args}")
            
            if self.mode == "RESEARCH":
                return {"status": "simulated", "order_args": order_args}
                
            # Execute
            order = self.api.submit_order(**order_args)
            return {"status": "success", "id": order.id, "client_order_id": order.client_order_id}

        except APIError as e:
            print(f"Alpaca API Error: {e}")
            raise e

    def get_account_equity(self) -> float:
        if not self.api:
            return 100000.0 # Stub
        try:
            acct = self.api.get_account()
            return float(acct.equity)
        except Exception as e:
            print(f"Error fetching equity: {e}")
            return 0.0

    def check_market_open(self) -> bool:
        if not self.api: 
            return True
        try:
            clock = self.api.get_clock()
            return clock.is_open
        except:
            return False

alpaca_client = AlpacaAdapter()
