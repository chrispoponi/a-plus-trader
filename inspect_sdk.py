from alpaca.data.historical import StockHistoricalDataClient
try:
    print(StockHistoricalDataClient.get_stock_most_actives.__annotations__)
except AttributeError:
    print("Method get_stock_most_actives not found on client.")
