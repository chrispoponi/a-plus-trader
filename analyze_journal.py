import pandas as pd
import os
from datetime import datetime

JOURNAL_FILE = "uploads/trade_journal.csv"

def analyze():
    if not os.path.exists(JOURNAL_FILE):
        print("No Journal File Found.")
        return

    try:
        df = pd.read_csv(JOURNAL_FILE)
        print(f"Total Records: {len(df)}")
        
        # Filter Jan 5th 2026 onwards
        # exit_time format usually "2026-01-..."
        # We need to parse dates. Try checking 'entry_time' or 'exit_time'
        df['exit_time'] = pd.to_datetime(df['exit_time'], errors='coerce')
        # Check if tz aware
        if df['exit_time'].dt.tz is None:
             df['exit_time'] = df['exit_time'].dt.tz_localize('UTC')
        else:
             df['exit_time'] = df['exit_time'].dt.tz_convert('UTC')
             
        start_date = pd.Timestamp("2026-01-05").tz_localize("UTC")
        
        recent = df[df['exit_time'] >= start_date].copy()
        print(f"Trades since Jan 5: {len(recent)}")
        
        if recent.empty:
            print("No recent trades found.")
            return

        # Ensure numeric
        recent['pnl_dollars'] = pd.to_numeric(recent['pnl_dollars'], errors='coerce').fillna(0)
        
        # Metrics
        wins = recent[recent['pnl_dollars'] > 0]
        losses = recent[recent['pnl_dollars'] <= 0]
        
        win_rate = len(wins) / len(recent)
        avg_win = wins['pnl_dollars'].mean() if not wins.empty else 0
        avg_loss = abs(losses['pnl_dollars'].mean()) if not losses.empty else 0
        
        print("\n--- PERFORMANCE (Jan 5 - Now) ---")
        print(f"Win Rate: {win_rate:.1%}")
        print(f"Avg Win:  ${avg_win:.2f}")
        print(f"Avg Loss: ${avg_loss:.2f}")
        
        if avg_loss > 0:
            reward_risk = avg_win / avg_loss
            print(f"Risk/Reward Ratio: {reward_risk:.2f}")
            
            # Kelly Criterion
            # f = p - q/b
            # p = win_rate
            # q = 1 - p
            # b = reward_risk
            p = win_rate
            q = 1.0 - p
            b = reward_risk
            kelly = p - (q / b)
            print(f"Kelly Criterion (Full): {kelly:.2%}")
            print(f"Kelly Criterion (Half): {kelly/2:.2%}")
        else:
            print("Risk/Reward: Undefined (No Losses)")
            
        print(f"Total PnL: ${recent['pnl_dollars'].sum():.2f}")
        
    except Exception as e:
        print(f"Analysis Failed: {e}")

if __name__ == "__main__":
    analyze()
