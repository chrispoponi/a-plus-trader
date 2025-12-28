from datetime import datetime, time
import pytz

# Define Eastern Time Zone
NY_TZ = pytz.timezone('America/New_York')

class MarketClock:
    @staticmethod
    def get_ny_time():
        """Returns current time in New York."""
        return datetime.now(NY_TZ)

    @staticmethod
    def is_market_open():
        """Checks if current time is between 9:30 AM and 4:00 PM ET on a weekday."""
        now = MarketClock.get_ny_time()
        # 0=Monday, 4=Friday
        if now.weekday() > 4:
            return False
            
        current_time = now.time()
        market_open = time(9, 30)
        market_close = time(16, 0)
        
        return market_open <= current_time <= market_close

    @staticmethod
    def get_market_segment():
        """
        Returns the current market segment based on User's automated rules.
        Segments:
        - PRE_MARKET: Before 9:30
        - NO_TRADE_ZONE: 9:30 - 9:40
        - OBSERVATION_ZONE: 9:40 - 10:00
        - MONEY_WINDOW: 10:00 - 10:30 (Day Trade Auto Only)
        - STABILIZATION: 10:30 - 11:00 (Swing/Options begin to validate)
        - OPEN_SESSION: 11:00 - 15:55
        - CLOSING_BELL: 15:55 - 16:00
        - POST_MARKET: After 16:00
        """
        now = MarketClock.get_ny_time()
        t = now.time()
        
        if t < time(9, 30): return "PRE_MARKET"
        if t < time(9, 40): return "NO_TRADE_ZONE"
        if t < time(10, 0): return "OBSERVATION_ZONE"
        if t < time(10, 30): return "MONEY_WINDOW"
        if t < time(11, 0): return "STABILIZATION"
        if t < time(15, 55): return "OPEN_SESSION"
        if t <= time(16, 0): return "CLOSING_BELL"
        return "POST_MARKET"
