import pandas as pd
import numpy as np

try:
    df = pd.read_csv("uploads/trade_journal.csv")
    closed = df[df["status"] == "CLOSED"]
    
    if closed.empty:
        print("No closed trades found.")
    else:
        # Metrics
        count = len(closed)
        pnl = pd.to_numeric(closed["pnl_dollars"], errors='coerce').sum()
        wins = closed[pd.to_numeric(closed["pnl_dollars"], errors='coerce') > 0]
        win_rate = len(wins) / count
        
        # Time span
        dates = pd.to_datetime(closed["entry_time"], format="mixed", utc=True)
        days = (dates.max() - dates.min()).days
        if days < 1: days = 1
        
        avg_per_trade = pnl / count
        trades_per_day = count / days
        daily_avg = pnl / days
        
        print(f"Total Trades: {count}")
        print(f"Total PnL: ${pnl:.2f}")
        print(f"Win Rate: {win_rate:.2%}")
        print(f"Days Active: {days}")
        print(f"Avg PnL/Trade: ${avg_per_trade:.2f}")
        print(f"Trades/Day: {trades_per_day:.2f}")
        print(f"Daily Avg PnL: ${daily_avg:.2f}")
        
        # Projection
        curr_equity = 100000 + pnl # Assumption or fetch from file
        
        projected_annual = daily_avg * 252 # Trading days
        
        print(f"Projected Annual PnL: ${projected_annual:.2f}")

except Exception as e:
    print(f"Error: {e}")
