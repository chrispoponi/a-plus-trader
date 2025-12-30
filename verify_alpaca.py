try:
    from alpaca.data.requests import StockMostActivesRequest
    print("SUCCESS: StockMostActivesRequest found.")
except ImportError:
    print("FAIL: StockMostActivesRequest NOT found via alpaca.data.requests")
    # Try finding it elsewhere
    try:
        import alpaca.data.requests
        print(f"Dir of requests: {dir(alpaca.data.requests)}")
    except:
        print("Could not import alpaca.data.requests")
