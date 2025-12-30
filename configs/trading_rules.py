from strategy_engine.models import Section

class TradingRules:
    """
    Centralized definition of Automation Rules per section.
    Enforces the User's strict time-based logic.
    """
    
    _RULES = {
        "first_hour_rules": {
            "no_trade_before": "09:40",
            "observation_only_until": "10:00",
            "day_trade_money_window": {"start": "10:00", "end": "10:30"},
            "swing_options_safe_start": "11:00" # User suggested 10:30-11:00 stabilization
        },
        "day_trade_filters": {
            "min_rvol": 2.0, # Strict RVOL for first hour
            "min_rvol_general": 1.5, # Later in day
            "max_trades_first_hour": 1
        }
    }

    @staticmethod
    def can_trade_section(section: Section, segment: str):
        """
        Determines if a specific Section is allowed to generate signals 
        during the current Market Segment.
        """
        # 1. NO TRADE ZONE (9:30-9:40)
        if segment == "NO_TRADE_ZONE":
            return False, "Market too volatile (9:30-9:40). No-Trade Zone."
            
        # 2. OBSERVATION ZONE (9:40-10:00)
        if segment == "OBSERVATION_ZONE":
            if section == Section.DAY_TRADE:
                return True, "Day Trading Allowed (Early Momentum)."
            return False, "Structure formation period (9:40-10:00). Swings Paused."

        # 3. MONEY WINDOW (10:00-10:30)
        if segment == "MONEY_WINDOW":
            if section == Section.DAY_TRADE:
                return True, "Day Trading Allowed (Money Window)."
            else:
                return False, "Swing/Options paused during opening volatility. Wait for stabilization (>10:30)."

        # 4. STABILIZATION (10:30-11:00)
        if segment == "STABILIZATION":
            if section == Section.OPTIONS:
                return True, "Options allowed (IV stabilizing)." # User said 10:30-11:00 ok
            if section == Section.SWING:
                return False, "Swing entries preferred midday/close." # Strict rule: "Swing system should ignore first hour entries"
            return True, "Day trading allowed."

        # 5. OPEN SESSION (11:00+)
        if segment == "OPEN_SESSION" or segment == "CLOSING_BELL":
            return True, "Open session."
            
        # 6. OFF HOURS
        return False, "Market closed."

    @staticmethod
    def get_rvol_threshold(segment: str):
        """Returns required RVOL based on time of day."""
        if segment == "MONEY_WINDOW":
            return 2.0 # Strict for Money Window
        return 1.5 # Standard for rest of day
