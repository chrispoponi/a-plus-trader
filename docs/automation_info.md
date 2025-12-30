# Automation Workflow: Feeding the Beast

## Goal
To provide the A+ Trader Bot with a daily "Fresh List" of Top 50 Trending Tickers automatically (or semi-automatically), bypassing the static hardcoded list.

## Method 1: TradingView Export (Semi-Auto)
**Best for:** High-precision lists from complex TradingView Screeners.

1.  Open your [TradingView Screener](https://www.tradingview.com/screener/GGiGnEFR/).
2.  Click the **Export CSV** icon (top right of results table).
3.  Go to the **A+ Trader Dashboard** -> **Data Ingest**.
4.  Drag & Drop the CSV into the "Upload TradingView CSV" box.
    *   *The Bot immediately parses this file and adds the symbols to its active target list for the next scan.*

## Method 2: ChatGPT Automation (Fully Auto via Make/Zapier)
**Best for:** Hands-off daily lists.

1.  Use a service like Zapier or Make.com.
2.  **Trigger:** Daily at 09:30 AM EST.
3.  **Action:** Ask ChatGPT: "Generate a JSON list of 50 high-volume (>1M), bullish trend stocks for today. Format: { 'picks': [ {'symbol': 'AAPL'}, ... ] }".
4.  **Action:** POST the JSON to:
    *   `https://a-plus-trader.onrender.com/automation/chatgpt-drop`
    *   Headers: `X-Webhook-Token: [YOUR_TOKEN]`
5.  *Bot automatically ingests this JSON.*

## Method 3: The "Local Bridge" Script (Power User)
**Best for:** Developers who want to run a scraping script on their Mac.

1.  Create a Python script on your local machine that scrapes Finviz or uses yfinance.
2.  The script gathers valid tickers.
3.  The script POSTs them to the bot:
    ```python
    requests.post("https://a-plus-trader.onrender.com/automation/chatgpt-drop", json={"picks": [...]})
    ```
4.  Schedule this script via `crontab` on your Mac.

## Current Bot Configuration
*   **Scanning Logic:** The Bot scans `Hardcoded List` + `Uploaded CSVs` + `ChatGPT Drops`.
*   **Priority:** Fresh drops take precedence.
