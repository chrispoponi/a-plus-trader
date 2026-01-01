from strategy_engine.backtest_engine import BacktestEngine

def run_backtest():
    # 1. FIRST GREEN DAY (Swing - Daily Data)
    print("==========================================")
    print("RUNNING STRATEGY A: FIRST GREEN DAY (FGD)")
    print("==========================================")
    engine_fgd = BacktestEngine(strategy_type='FGD')
    
    # Selection: Known volatile small/mid caps
    pennies = ['MARA', 'RIOT', 'SOFI', 'OPEN', 'CLSK', 'HUT', 'WULF', 'CIFR']
    engine_fgd.run(pennies, days=120)

    # 2. MORNING PANIC DIP BUY (Day - Intraday Data)
    print("\n==========================================")
    print("RUNNING STRATEGY B: MORNING PANIC (MPDB)")
    print("==========================================")
    engine_mpdb = BacktestEngine(strategy_type='MPDB')
    
    # Short duration for Intraday (Alpaca limits)
    engine_mpdb.run(pennies, days=10) 

if __name__ == "__main__":
    run_backtest()
