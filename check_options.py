
from alpaca_trade_api.rest import REST
from configs.settings import settings
import os

def check_options():
    print("Checking Options Capabilities...")
    try:
        api = REST(settings.APCA_API_KEY_ID, settings.APCA_API_SECRET_KEY, base_url=settings.APCA_API_BASE_URL)
        
        # 1. Check if we can list optionable assets
        # assets = api.list_assets(asset_class='us_option') 
        # Note: Alpaca usually treats options as separate assets or requires flexible query
        
        # 2. Try to get an Option Chain for SPY
        # The endpoint varies by SDK version.
        try:
            # Attempt raw request if method unknown
            # GET /v1beta1/options/contracts?underlying_symbols=SPY
            pass
        except:
             pass
             
        # Just checking attributes
        has_option_stream = hasattr(api, 'get_option_contracts')
        print(f"Has 'get_option_contracts': {has_option_stream}")
        
        has_snapshot = hasattr(api, 'get_option_snapshot') 
        print(f"Has 'get_option_snapshot': {has_snapshot}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_options()
