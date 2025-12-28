from data_adapters.alpaca_adapter import alpaca_client
from configs.settings import settings

print(f"Checking connection to Alpaca ({settings.TRADING_MODE} Mode)...")

try:
    acct = alpaca_client.get_account()
    if acct:
        print("SUCCESS: Connected to Alpaca!")
        print(f"Account Status: {acct.status}")
        print(f"Equity: ${acct.equity}")
        print(f"Buying Power: ${acct.buying_power}")
    else:
        print("FAILURE: client init failed in adapter.")
except Exception as e:
    print(f"FAILURE: Connection error: {e}")
