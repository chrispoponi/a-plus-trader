
import asyncio
import sys
import os
import time
from datetime import datetime

# Ensure project root is in path
sys.path.append(os.getcwd())

from strategy_engine.scanner_service import scanner
from utils.notifications import notifier
from utils.market_clock import MarketClock

async def run_sniper_bot():
    print("🔫 SNIPER BOT: ONLINE. Scanning for Intraday Volatility Options Setups...")
    notifier.send_message("SNIPER BOT ACTIVE", "Scanning 18 Tickers every 5 minutes for Volatility Surges.", color=0xffff00)
    
    universe = [
        "NVDA", "TSLA", "AMD", "META", "AMZN", "AAPL", "MSFT", "PLTR", "COIN", "MARA",
        "NFLX", "GOOGL", "IWM", "QQQ", "SPY", "MSTR", "SMCI", "ARM"
    ]
    
    last_alerts = {} # symbol -> timestamp (deduplicate alerts)

    while True:
        try:
            # 1. Market Check
            if not MarketClock.is_market_open():
                print("Market Closed. Sleeping...")
                await asyncio.sleep(300)
                continue
                
            now_ts = datetime.now()
            print(f"\n--- SCANNING @ {now_ts.strftime('%H:%M:%S')} ---")
            
            # 2. Run Scan
            candidates = scanner.run_sniper_scan(universe)
            
            # 3. Process Alerts
            for c in candidates:
                # Deduplicate: Don't alert same symbol within 30 mins
                last_time = last_alerts.get(c.symbol)
                if last_time and (now_ts - last_time).total_seconds() < 1800:
                    print(f"Skipping duplicate alert for {c.symbol}")
                    continue
                
                # Construct Options Call
                # Logic: Buy Closest Strike ATM. Expiry: Current Week.
                price = c.trade_plan.entry
                strike = int(round(price))
                contract_type = "CALL" if c.direction.value == "LONG" else "PUT"
                
                msg = (
                    f"🚨 **SNIPER SIGNAL DETECTED** 🚨\n"
                    f"Symbol: **{c.symbol}** (${price:.2f})\n"
                    f"Setup: {c.setup_name}\n"
                    f"Thesis: {c.thesis}\n\n"
                    f"🎯 **ACTION REQUIRED**:\n"
                    f"Buy Weekly **{contract_type}** Strike **${strike}**\n"
                    f"Logic: Momentum Breakout. Hold < 1 Hour."
                )
                
                print(msg)
                notifier.send_message(f"SNIPER ALERT: {c.symbol} {contract_type}", msg, color=0xff0000)
                
                last_alerts[c.symbol] = now_ts
            
            if not candidates:
                print("No targets found.")
                
            # Sleep 5 Minutes (Match Bar Size)
            await asyncio.sleep(300)
            
        except KeyboardInterrupt:
            print("Sniper Bot stopping...")
            break
        except Exception as e:
            print(f"Sniper Bot Loop Error: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(run_sniper_bot())
    except KeyboardInterrupt:
        pass
