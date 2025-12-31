from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Section(str, Enum):
    SWING = "SWING GRADE SETUP"
    BREAKOUT = "BREAKOUT SETUP"
    OPTIONS = "OPTIONS SETUP"
    DAY_TRADE = "DAY TRADE SETUP"
    SCALP = "SCALP SETUP"

class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    SELL_TO_OPEN = "SELL_TO_OPEN" 
    BUY_TO_CLOSE = "BUY_TO_CLOSE"
    BUY_TO_OPEN = "BUY_TO_OPEN" # For debit spreads
    SELL_TO_CLOSE = "SELL_TO_CLOSE"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class TradePlan(BaseModel):
    entry: float = Field(..., description="Target entry price")
    stop_loss: float
    take_profit: float
    time_stop_days: Optional[int] = 5
    position_size_shares: Optional[int] = None
    position_size_contracts: Optional[int] = None
    risk_percent: float
    is_core_trade: bool = False
    stop_type: str = "Structure" # Structure, Volatility, MA

class OptionsDetails(BaseModel):
    strategy_type: str # Bull Put Spread, Iron Condor, etc
    strikes: List[float]
    expiration_date: str
    dte: int
    pop_estimate: float
    max_loss: float
    max_gain: float
    breakeven: List[float]

class Scores(BaseModel):
    win_probability_estimate: float = Field(..., ge=0, le=100)
    quality_score: float = Field(..., ge=0, le=100)
    risk_score: float = Field(..., ge=0, le=100)
    overall_rank_score: float = Field(..., ge=0, le=100)
    baseline_win_rate: float
    adjustments: float
    # Sub-scores
    trend_score: Optional[float] = 0
    structure_score: Optional[float] = 0
    vol_score: Optional[float] = 0
    sector_score: Optional[float] = 0

class Compliance(BaseModel):
    passed_thresholds: bool
    reasons_failed: List[str] = []

class Candidate(BaseModel):
    section: Section
    symbol: str
    timeframe: str = "1D"
    setup_name: str
    direction: Direction
    thesis: str
    features: Dict[str, Any]
    trade_plan: TradePlan
    options_details: Optional[OptionsDetails] = None
    scores: Scores
    compliance: Compliance
    signal_id: str
    ai_analysis: Optional[str] = None

class WebhookBracket(BaseModel):
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None

class WebhookSignal(BaseModel):
    auth_token: str
    signal_id: str
    section: Section
    symbol: str
    action: Action
    order_type: OrderType
    qty: float
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "gtc"
    bracket: WebhookBracket
    win_probability_estimate: float
    validity_window_minutes: int
    notes: Optional[str] = None
