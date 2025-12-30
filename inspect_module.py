from alpaca.data.historical import StockHistoricalDataClient
print([m for m in dir(StockHistoricalDataClient) if 'active' in m or 'mover' in m])
