import pandas as pd
import numpy as np
from strategy_engine.data_loader import DataLoader
import asyncio

# --- STRATEGY LOGIC ---

def run_peak_exit_backtest(symbol: str, data: pd.DataFrame):
    """
    Backtests Standard vs Peak Exit strategies.
    Assumes LONG entries when Price > EMA20.
    """
    df = data.copy()
    
    # 1. Indicators
    df['avg_vol'] = df['volume'].rolling(10).mean()
    df['vol_ratio'] = df['volume'] / df['avg_vol']
    df['atr'] = (df['high'] - df['low']).rolling(14).mean()
    df['ema20'] = df['close'].ewm(span=20).mean()
    
    # 2. Peak Exit Signals
    # Exhaustion: Price Up + Volume Dry (< 90% avg)
    df['price_up'] = df['close'] > df['close'].shift(1)
    df['exhaustion'] = (df['price_up']) & (df['vol_ratio'] < 0.9)
    
    # Adaptive Trailing Stop (Tightens during exhaustion)
    # If exhausted, tight stop (0.5 ATR). Normal, wide stop (2.0 ATR).
    # We simulate this iteratively
    
    trades_std = []
    trades_peak = []
    
    position_std = None # {entry_price, stop, target}
    position_peak = None # {entry_price, stop}
    
    bank_std = 0.0
    bank_peak = 0.0
    
    # Iterative Simulation
    for i in range(20, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        date = curr.name
        price = curr['close']
        atr = curr['atr']
        
        # ENTRY SIGNAL (Common for Both): Crossover EMA20
        # Simple for testing exit mechanics: Enter if price cross above EMA20
        entry_signal = (prev['close'] < prev['ema20']) and (curr['close'] > curr['ema20'])
        
        # --- STANDARD STRATEGY ---
        if position_std is None:
            if entry_signal:
                stop = price - (1.5 * atr)
                target = price + (3.0 * atr)
                position_std = {'entry': price, 'stop': stop, 'target': target, 'date': date}
        else:
            # Check Stoppped Out or Target Hit
            if price <= position_std['stop']:
                pnl = position_std['stop'] - position_std['entry']
                trades_std.append(pnl)
                bank_std += pnl
                position_std = None
            elif price >= position_std['target']:
                pnl = position_std['target'] - position_std['entry']
                trades_std.append(pnl)
                bank_std += pnl
                position_std = None
                
        # --- PEAK EXIT STRATEGY ---
        if position_peak is None:
            if entry_signal:
                # Initial Stop is wide (2.0 ATR) to ride wave
                stop = price - (2.0 * atr)
                position_peak = {'entry': price, 'stop': stop, 'highest_price': price, 'date': date}
        else:
            # Update High Water Mark
            if price > position_peak['highest_price']:
                position_peak['highest_price'] = price
                
            # DYNAMIC TRAILING STOP LOGIC
            # If Exhausted (Vol Dry Up while Rising), Tighten Stop to 0.5 ATR from HIGH
            is_exhausted = curr['exhaustion']
            
            if is_exhausted:
                # Tighten!
                new_stop = price - (0.5 * atr)
            else:
                # Normal Trail (Loose) - e.g. 2.0 ATR from High
                new_stop = position_peak['highest_price'] - (2.0 * atr)
            
            # Ratchet: Stop can only move UP
            if new_stop > position_peak['stop']:
                position_peak['stop'] = new_stop
                
            # Check Exit
            # 1. Hit Stop?
            if price <= position_peak['stop']:
                pnl = position_peak['stop'] - position_peak['entry']
                trades_peak.append(pnl)
                bank_peak += pnl
                position_peak = None
            # 2. No Fixed Target (Ride the Wave)

    print(f"\n📢 RESULTS FOR {symbol}:")
    print(f"   🔹 STANDARD (Fixed Target): Total PnL ${bank_std:.2f} | Trades: {len(trades_std)}")
    print(f"   🔸 PEAK EXIT (Wave Ride):   Total PnL ${bank_peak:.2f} | Trades: {len(trades_peak)}")
    
    diff = bank_peak - bank_std
    winner = "PEAK" if diff > 0 else "STANDARD"
    print(f"   🏆 WINNER: {winner} (+${abs(diff):.2f})")
    
    return bank_peak, bank_std

async def main():
    print("🦅 BACKTESTING PEAK EXIT STRATEGY...")
    dl = DataLoader()
    
    # Test on Momentum Stocks
    symbols = ['AFRM', 'NVDA', 'TSLA', 'AMD', 'COIN'] 
    
    results = dl.fetch_snapshot(symbols)
    
    total_peak = 0
    total_std = 0
    
    for sym, pkg in results.items():
        if 'df' in pkg:
            p, s = run_peak_exit_backtest(sym, pkg['df'])
            total_peak += p
            total_std += s
            
    print("\n========================================")
    print(f"FINAL SCORECARD:")
    print(f"STANDARD: ${total_std:.2f}")
    print(f"PEAK EXIT: ${total_peak:.2f}")
    print("========================================")

if __name__ == "__main__":
    asyncio.run(main())
