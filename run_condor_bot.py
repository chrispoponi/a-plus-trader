from __future__ import annotations

import os
import json
import math
import time
import sqlite3
import logging
import asyncio
from dataclasses import dataclass
from datetime import datetime, date, timedelta
import pytz
from typing import Optional, List, Tuple, Dict, Any

from utils.notifications import notifier
from utils.market_clock import MarketClock

# =========================
# Config
# =========================
TZ = pytz.timezone("America/Los_Angeles")

SYMBOL = "SPX"
WING_WIDTH_POINTS = 10
TARGET_DELTA_CALL = 0.10
TARGET_DELTA_PUT = -0.10

ENTRY_HOUR = 9
ENTRY_MINUTE = 0

MONITOR_INTERVAL_SECONDS = 300  # 5 minutes
MAX_ACCOUNT_RISK_PCT = 0.02     # 2% per trade

BLACKOUT_FILE = "events_blackout.json"
DB_FILE = "trades.sqlite"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# =========================
# Logging
# =========================
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("spx_condor_bot")

# =========================
# Data structures
# =========================
@dataclass
class OptionContract:
    symbol: str
    expiry: str            # YYYYMMDD
    strike: float
    right: str             # "C" or "P"

@dataclass
class IronCondorLegs:
    short_put: OptionContract
    long_put: OptionContract
    short_call: OptionContract
    long_call: OptionContract

@dataclass
class EntryResult:
    trade_id: str
    credit_received: float     # dollars per 1-lot spread
    contracts: int
    legs: IronCondorLegs
    expiry: str

@dataclass
class OpenTrade:
    trade_id: str
    entry_time: str
    expiry: str
    credit_received: float
    contracts: int
    status: str               # OPEN/CLOSED/SKIPPED
    close_time: Optional[str] = None
    close_reason: Optional[str] = None
    close_debit: Optional[float] = None

# =========================
# Blackout calendar
# =========================
def load_blackout_dates(path: str) -> Dict[str, List[str]]:
    if not os.path.exists(path):
        log.warning("Blackout file not found (%s). No blackout days will be applied.", path)
        return {"NFP": [], "CPI": [], "FOMC": []}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for k in ("NFP", "CPI", "FOMC"):
        data.setdefault(k, [])
    return data

def is_blackout_day(d: date, blackout: Dict[str, List[str]]) -> Tuple[bool, str]:
    d_str = d.isoformat()
    d_minus_1_str = (d + timedelta(days=1)).isoformat()
    
    if d_minus_1_str in blackout.get("NFP", []):
        return True, "Pre-NFP"
    if d_minus_1_str in blackout.get("CPI", []):
        return True, "Pre-CPI"
    if d_str in blackout.get("FOMC", []):
        return True, "FOMC Day"
    return False, ""

# =========================
# Journal (SQLite)
# =========================
def init_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        trade_id TEXT PRIMARY KEY,
        entry_time TEXT,
        expiry TEXT,
        credit_received REAL,
        contracts INTEGER,
        status TEXT,
        close_time TEXT,
        close_reason TEXT,
        close_debit REAL
    )
    """)
    conn.commit()
    conn.close()

def upsert_trade(db_path: str, t: OpenTrade) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO trades (trade_id, entry_time, expiry, credit_received, contracts, status, close_time, close_reason, close_debit)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(trade_id) DO UPDATE SET
        entry_time=excluded.entry_time,
        expiry=excluded.expiry,
        credit_received=excluded.credit_received,
        contracts=excluded.contracts,
        status=excluded.status,
        close_time=excluded.close_time,
        close_reason=excluded.close_reason,
        close_debit=excluded.close_debit
    """, (t.trade_id, t.entry_time, t.expiry, t.credit_received, t.contracts, t.status, t.close_time, t.close_reason, t.close_debit))
    conn.commit()
    conn.close()

def get_open_trade(db_path: str) -> Optional[OpenTrade]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT trade_id, entry_time, expiry, credit_received, contracts, status, close_time, close_reason, close_debit FROM trades WHERE status='OPEN' LIMIT 1")
    row = cur.fetchone()
    conn.close()
    if not row: return None
    return OpenTrade(*row)

# =========================
# SIGNAL ADAPTER (Mock Broker for Signal Only)
# =========================
class SignalBroker:
    """
    Since we are "Signal Only" for now, this adapter:
    1. Uses Polygon/Alpaca data to find the strikes (simulated).
    2. Sends Discord Alert for you to execute manually.
    3. Journals it as if it happened.
    """
    def __init__(self):
        # We need data to find strikes. Using Alpaca for SPY as proxy for SPX?
        # SPX data is paid/complex on Alpaca.
        # Approximation: SPX ~ 10x SPY (roughly) or use SPY options.
        # User explicitly asked for SPX.
        # Without IBKR connection, we cannot get true SPX Chains easily.
        # FALLBACK: We will calculate the Strikes based on Spot Price % logic
        # and ask User to find the exact delta.
        # Or we use Alpaca to get SPY price then mult by 10 for estimation.
        from alpaca_trade_api.rest import REST
        from configs.settings import settings
        self.api = REST(settings.APCA_API_KEY_ID, settings.APCA_API_SECRET_KEY, base_url=settings.APCA_API_BASE_URL)

    def get_account_equity(self) -> float:
        try:
            acct = self.api.get_account()
            return float(acct.equity)
        except:
            return 100000.0 # Default if fail

    def get_next_trading_day_expiry(self, now: datetime) -> str:
        d = now.date()
        next_day = d + timedelta(days=1)
        while next_day.weekday() >= 5: next_day += timedelta(days=1)
        return next_day.strftime("%Y%m%d")

    def get_spx_spot(self) -> float:
        # Use SPY * ratio or just ask API if it has SPX (usually no)
        # Check SPY
        bar = self.api.get_latest_bar("SPY")
        spy_price = bar.c
        # SPX is roughly SPY * 10 (approx). 
        # Actually SPX is an index, SPY is ETF. The ratio varies slightly but ~10x.
        # Better: use 'SPX' symbol if available? Alpaca Basic data doesn't have indices usually.
        # Let's use SPY price and explicitly tell user "Based on SPY".
        # Or better: Just fetch SPY Price and multiply by 10.02 (current basis).
        return spy_price * 10.02 

    def estimate_strikes(self, spot: float) -> IronCondorLegs:
        # 10 Delta is usually ~ 1.5% OTM for 1DTE (rough rule of thumb for VIX 15)
        # We will just estimate Strikes for the signal.
        
        # 1.5% OTM Short Call/Put
        call_strike = round(spot * 1.015 / 5) * 5
        put_strike = round(spot * 0.985 / 5) * 5
        
        wing = 10 
        
        return IronCondorLegs(
            short_put=OptionContract("SPX", "", put_strike, "P"),
            long_put=OptionContract("SPX", "", put_strike - wing, "P"),
            short_call=OptionContract("SPX", "", call_strike, "C"),
            long_call=OptionContract("SPX", "", call_strike + wing, "C")
        )

# =========================
# LOGIC
# =========================
def run_condor_check():
    # 1. Check Blackout
    blackout = load_blackout_dates(BLACKOUT_FILE)
    now_la = datetime.now(TZ)
    today = now_la.date()
    
    is_black, reason = is_blackout_day(today, blackout)
    
    if is_black:
        notifier.send_message("🛑 CONDOR BLACKOUT", f"Skipping trade today: {reason}", color=0xff0000)
        return

    # 2. Check Database for Open Trade
    if get_open_trade(DB_FILE):
        # We already entered?
        # Actually in Signal Mode, we just alert once.
        return

    # 3. Generate Signal
    broker = SignalBroker()
    equity = broker.get_account_equity()
    
    try:
        spot = broker.get_spx_spot()
        legs = broker.estimate_strikes(spot)
        
        # Estimating Credit (Roughly $0.60 - $0.80 for 10 wide 10 delta?)
        est_credit = 0.75 * 100 # $75
        
        # Contracts
        # 2% Risk. Risk per trade = 10 width - credit = $9.25 loss max? 
        # Actually User said close at 2x credit. 
        # Stop Loss Risk = Credit * 2. 
        # If Credit is $75. Stop loss is -$150.
        risk_budget = equity * 0.02
        contracts = max(1, int(risk_budget / 150.0))
        
        # ALERT
        expiry = broker.get_next_trading_day_expiry(now_la)
        
        msg = (
            f"🦅 **IRON CONDOR SIGNAL** (1DTE)\n"
            f"**Underlying**: SPX (Spot ~{spot:.0f})\n"
            f"**Expiry**: {expiry}\n\n"
            f"**SHORT CALL**: {legs.short_call.strike}\n"
            f"**SHORT PUT**: {legs.short_put.strike}\n"
            f"**Wings**: 10pt Wide\n\n"
            f"**Qty**: {contracts} Contracts\n"
            f"**Est Credit**: $0.75\n"
            f"**Stop Loss**: 2.0x Credit (Hard Stop)\n\n"
            f"⚠️ *Signal Estimated from SPY Proxy. Verify Delta 10 on IBKR.*"
        )
        
        notifier.send_message("🦅 CONDOR BOT FIRE", msg, color=0xff00ff)
        
        # Log to DB
        t = OpenTrade(
            trade_id=f"CONDOR_{today.isoformat()}",
            entry_time=now_la.isoformat(),
            expiry=expiry,
            credit_received=est_credit,
            contracts=contracts,
            status="OPEN"
        )
        upsert_trade(DB_FILE, t)
        
    except Exception as e:
        notifier.send_message("Condor Error", f"Failed to gen signal: {e}", color=0xff0000)

async def condor_loop():
    print("🦅 CONDOR BOT: ONLINE (Signal Only Mode)")
    # Loop to check time
    while True:
        now = datetime.now(TZ)
        # Run at 9:00 AM PT
        if now.hour == 9 and now.minute == 0:
            run_condor_check()
            await asyncio.sleep(65) # Sleep past the minute
        else:
            await asyncio.sleep(10)

if __name__ == "__main__":
    init_db(DB_FILE)
    asyncio.run(condor_loop())
