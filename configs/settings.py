import os
from enum import Enum
from dotenv import load_dotenv

# Load .env (local dev)
load_dotenv("secrets.env")

class TradingMode(str, Enum):
    RESEARCH = "RESEARCH"
    PAPER = "PAPER"
    LIVE = "LIVE"

class Settings:
    # Security
    WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN", "")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret")

    # Mode
    TRADING_MODE = TradingMode(os.getenv("TRADING_MODE", "PAPER").upper())
    
    # Auto-Execution (Default: True for Paper, False for Live unless forced)
    _default_auto = "true" if TRADING_MODE != "LIVE" else "false"
    AUTO_EXECUTION_ENABLED = os.getenv("AUTO_EXECUTION_ENABLED", _default_auto).lower() == "true"

    # Alpaca
    APCA_API_KEY_ID = os.getenv("APCA_API_KEY_ID", "")
    APCA_API_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY", "")
    APCA_API_BASE_URL = os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")

    # Risk (Non-negotiable defaults from code if env missing, but env overrides)
    # User specified: 0.75% risk per trade, 2% max daily loss
    MAX_RISK_PER_TRADE_PERCENT = float(os.getenv("MAX_RISK_PER_TRADE_PERCENT", "0.75"))
    CORE_RISK_PER_TRADE_PERCENT = float(os.getenv("CORE_RISK_PER_TRADE_PERCENT", "1.25"))
    MAX_DAILY_LOSS_PERCENT = float(os.getenv("MAX_DAILY_LOSS_PERCENT", "2.0"))
    MAX_OPEN_SWING_POSITIONS = int(os.getenv("MAX_OPEN_SWING_POSITIONS", "4"))
    MAX_OPEN_DAY_POSITIONS = int(os.getenv("MAX_OPEN_DAY_POSITIONS", "2"))
    MAX_PORTFOLIO_RISK_PERCENT = float(os.getenv("MAX_PORTFOLIO_RISK_PERCENT", "4.0"))

    # Signal
    MIN_WIN_PROBABILITY_ESTIMATE = float(os.getenv("MIN_WIN_PROBABILITY", "65.0"))
    MIN_SWING_SCORE = 10.0 # DEBUG: Was 70.0
    MIN_A_PLUS_SWING_SCORE = 80.0

    @classmethod
    def validate(cls):
        if cls.TRADING_MODE == TradingMode.LIVE:
            if not os.getenv("LIVE_TRADING_CONFIRMED") == "true":
                 raise ValueError("LIVE trading requires LIVE_TRADING_CONFIRMED=true env var.")
        
        if not cls.WEBHOOK_TOKEN:
            print("WARNING: WEBHOOK_TOKEN is not set. Security is compromised.")

settings = Settings()
settings.validate()
