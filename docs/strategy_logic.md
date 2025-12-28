# A+ Trader Engine: Systems Logic

This document defines the exact logic used by the A+ Trader Architect for automated decision making.

## 0. Global Market Filter (SPY/QQQ)
**Tool**: `Auto Trendlines Pro` (Pine Script Port)
**Goal**: Ensure we are swimming with the current.
- **Context**: The bot specifically analyzes **SPY** and **QQQ** daily charts first.
- **Bullish**: Price > Support Trendline AND Price > 50 SMA.
- **Bearish**: Price < Resistance Trendline OR Price < 50 SMA.
- **Impact**:
  - If Market is **Bearish**, `Swing Longs` are blocked or size-reduced.
  - If Market is **Neutral/Choppy**, `Iron Condors` are preferred.

## 1. Swing Trade Engine
**Strategy**: `20/50 MA Trend Pullback`
**Goal**: Catch the primary trend wave after a consolidation.
- **Trend Filter**: 20EMA must be ABOVE 50SMA (for Long).
- **Entry**: Price pulls back to within 2% of the 20 EMA ("The Value Zone").
- **Scoring**:
  - Trend Alignment (is slope positive?): 25 pts
  - Pullback Quality (hammer, doji support): 20 pts
  - Volume (increasing on up days): 15 pts
- **Sizing**:
  - **Standard**: 0.75% Risk
  - **CORE (A+)**: 1.25% Risk (Only top 2 candidates with Score > 80)

## 2. Options Engine
**Strategy**: `High Probability Credit Spreads`
**Goal**: Generate income with defined risk outcomes (POP > 70%).
- **Selection**:
  - If Trend is Bullish (Price > 50SMA) -> **Bull Put Spread** (Sell Puts)
  - If Market is Choppy/Range -> **Iron Condor**
- **Criteria**:
  - Probability of Profit (POP) must be > 70%.
  - Max Loss is defined upfront.
  - Takes profit at 50% of max credit.

## 3. Day Trade Engine
**Strategy**: `VWAP Momentum Reclaim`
**Goal**: Capture intraday explosive moves.
- **Trigger**: Price crosses ABOVE VWAP with strong volume.
- **Validation**: Relative Volume (RVOL) must be > 1.5x (High demand).
- **Risk**: Tight stop below VWAP line. 
- **Target**: 2R (Risk 1 to make 2).
