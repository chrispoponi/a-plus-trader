
from typing import Dict, Optional, List
from strategy_engine.models import Candidate, Section, TradePlan, Direction, Scores, Compliance
import pandas as pd
from datetime import datetime, timedelta

# SIMULATED CONGRESS DATABASE
# In a real app, this would be an API call to QuiverQuant or similar.
# Format: Ticker -> List of (Date, Type)
PELOSI_TRADES = {
    "NVDA": [("2024-11-20", "BUY"), ("2023-11-22", "BUY"), ("2023-01-05", "BUY")],
    "MSFT": [("2024-10-15", "BUY"), ("2024-02-12", "BUY")],
    "PANW": [("2024-02-12", "BUY")],
    "AMZN": [("2024-01-15", "BUY")],
    "AAPL": [("2024-05-15", "BUY")],
    "PLTR": [("2024-08-01", "BUY")] # Hypothetical or actual
}

class CongressStrategy:
    """
    STRATEGY: The 'Nancy Pelosi' / Congressional Copy-Trade
    SOURCE: Public Disclosures (Simulated via Hardcoded List for Backtest)
    LOGIC:
    - DISCLOSURE: If House/Senate member files BUY.
    - LAG: We assume we trade on the Disclosure Date (or 1 day later).
    - ENTRY: Market Buy.
    - EXIT: Hold 30 Days OR -10% Stop.
    - SIZING: Equal Weight.
    """

    def analyze(self, symbol: str, features: Dict[str, any]) -> Optional[Candidate]:
        # Current Date in Simulation
        # features['df'] contains daily data.
        # But BacktestEngine iteration gives us 'row' or 'current_time'.
        # We need check if current_time matches a file date.
        
        current_date_ts = features.get('current_date') # Need to ensure Backtest passes this
        if not current_date_ts: return None
        
        current_date_str = current_date_ts.strftime("%Y-%m-%d")
        
        trades = PELOSI_TRADES.get(symbol, [])
        for t_date, t_type in trades:
            # Check if Today matched the Trade Date (or close proximity)
            # In backtest loop, exact match is easiest.
            if t_date == current_date_str and t_type == "BUY":
                row = features.get('row')
                price = row['close']
                stop = price * 0.90 # 10% Trailing/Fixed Stop
                target = price * 1.50 # Open upside
                
                return Candidate(
                    section=Section.SWING,
                    symbol=symbol,
                    setup_name="Congress Disclosure",
                    direction=Direction.LONG,
                    thesis=f"Congressional Trading Disclosure: {t_type} on {t_date}.",
                    features={"filer": "Pelosi", "lag": 0},
                    trade_plan=TradePlan(
                        entry=price,
                        stop_loss=stop,
                        take_profit=target,
                        risk_percent=0.02,
                        stop_type="Diff: 10%"
                    ),
                    scores=Scores(overall_rank_score=95, win_probability_estimate=80, quality_score=95, risk_score=10, baseline_win_rate=60, adjustments=0),
                    compliance=Compliance(passed_thresholds=True),
                    signal_id=f"CONGRESS_{symbol}_{t_date}"
                )
                
        return None
