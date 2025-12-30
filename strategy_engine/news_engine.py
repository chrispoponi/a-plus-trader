from alpaca.data.historical.news import NewsClient
from alpaca.data.requests import NewsRequest
from configs.settings import settings
from datetime import datetime, timedelta

class NewsEngine:
    def __init__(self):
        try:
            self.client = NewsClient(
                api_key=settings.APCA_API_KEY_ID,
                secret_key=settings.APCA_API_SECRET_KEY
            )
            print("news_engine: Connected to Alpaca News Source.")
        except Exception as e:
            print(f"news_engine: Connection Failed: {e}")
            self.client = None

        # Keywords that immediately flag caution
        self.red_flags = [
            "bankruptcy", "fraud", "sec investigation", "subpoena", 
            "lawsuit", "delisting", "offering", "dilution", 
            "earnings miss", "rating downgrade"
        ]

    def get_market_sentiment(self, symbol: str) -> dict:
        """
        Fetches latest 5 news items.
        Returns: {
            "sentiment": "NEUTRAL" | "NEGATIVE", 
            "latest_headline": str,
            "url": str
        }
        """
        if not self.client:
            return {"sentiment": "UNKNOWN", "latest_headline": "News API Offline", "url": "#"}

        try:
            # Fetch last 24h news
            req = NewsRequest(
                symbols=symbol,
                limit=5,
                start=datetime.now() - timedelta(days=2) # 48h window
            )
            news_items = self.client.get_news(req)
            
            if not news_items or len(news_items.news) == 0:
                 return {"sentiment": "NEUTRAL", "latest_headline": "No Recent News", "url": "#"}

            latest = news_items.news[0]
            headline = latest.headline.lower()
            
            # Simple Sentiment Check
            sentiment = "NEUTRAL"
            for flag in self.red_flags:
                if flag in headline:
                    sentiment = "NEGATIVE"
                    break
            
            return {
                "sentiment": sentiment,
                "latest_headline": latest.headline,
                "url": latest.url
            }

        except Exception as e:
            print(f"News Fetch Error ({symbol}): {e}")
            return {"sentiment": "UNKNOWN", "latest_headline": "Fetch Error", "url": "#"}

news_engine = NewsEngine()
