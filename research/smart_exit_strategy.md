# Research: Smart Exit Strategy ("The Harmonic Wave")

## Core Concept
Markets move in waves. A "Tsunami" (Parabolic Move) is rare; most moves are standard oscillations. To maximize profit, we want to sell when the wave is at its crest (Peak) rather than waiting for the Stop Loss to hit on the way down.

## The Signal: "Exhaustion"
A peak is mathematically defined by **Divergence**:
- **Price** makes a New High.
- **Volume** makes a Lower High (Dries Up).
- **RSI** makes a Lower High (Momentum Wanes).

## Python Implementation

We can program a `check_peak_exhaustion(symbol, data)` function that returns a `Confidence Score (0-100)` for exiting.

### 1. The Code Logic
```python
def detect_peak_exhaustion(df):
    """
    Analyzes the last few candles to detect a 'Peak Exhaustion' pattern.
    Returns: exhaustion_score (0-100)
    """
    # Get latest data
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    
    score = 0
    
    # --- FACTOR 1: EXTENSION (The Wave Height) ---
    # Is price significantly above the mean (20 EMA)?
    # A standard 'Extension' is > 5-10% above EMA20 for swing stocks.
    dist_from_mean = (curr['close'] - curr['ema20']) / curr['ema20']
    
    if dist_from_mean > 0.10: score += 30  # +10% Extended
    elif dist_from_mean > 0.05: score += 10
    
    # Check Bollinger Bands (Upper Band = 2 Std Devs)
    if curr['close'] > curr['upper_band']:
        score += 20  # Piercing the envelope
        
    # --- FACTOR 2: MOMENTUM SATURATION ---
    # RSI > 70 is Overbought. RSI > 80 is Extreme.
    if curr['rsi'] > 80: score += 30
    elif curr['rsi'] > 70: score += 15
    
    # --- FACTOR 3: VOLUME DRY UP (The Tell) ---
    # Logic: Price is UP, but Volume is DOWN compared to average.
    # We use Relative Volume (RVOL).
    vol_avg = curr['vol_avg_20']
    rvol = curr['volume'] / vol_avg
    
    # If Price is making a new high...
    if curr['close'] > prev['high']:
        # But Volume is weak (< 80% of average)
        if rvol < 0.8:
            score += 20  # Buyers are tired
            print("Volume Divergence Detected")
            
    return score

# USAGE IN TRADING BOT
def manage_position(position):
    df = data_loader.fetch_data(position.symbol)
    exhaustion = detect_peak_exhaustion(df)
    
    current_pnl_pct = position.unrealized_pnl_pct * 100
    
    # EXECUTION LOGIC
    # Only sell if we are actually in profit (> 5%)
    if current_pnl_pct > 5.0:
        if exhaustion >= 80:
            return "SELL_ALL (Peak Reached)"
        elif exhaustion >= 50:
            return "SELL_HALF (Scale Out)"
            
    return "HOLD"
```

## Integration Plan (Future)
We can add a `ProfitProtector` job to the `Scheduler` (running every 15 mins).
1.  **Loop** active positions.
2.  **Calculate** Exhaustion Score.
3.  **Execute** Trim or Sell if Score > Threshold.

This allows us to "Scoop" the 19% gains automatically without waiting for the trend to reverse and stop us out at 10% or break-even.
