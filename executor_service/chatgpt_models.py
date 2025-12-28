from pydantic import BaseModel
from typing import List, Optional

class ChatGPTStockPick(BaseModel):
    symbol: str
    reason: Optional[str] = None
    sentiment: Optional[str] = None # BULLISH / BEARISH
    confidence: Optional[float] = None
    source_list_name: Optional[str] = None # e.g. "aggressive_growth", "value_plays"

class ChatGPTDropPayload(BaseModel):
    auth_token: str
    batch_id: str # Unique ID for this drop
    picks: List[ChatGPTStockPick]
    notes: Optional[str] = None
