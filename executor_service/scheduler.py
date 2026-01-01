from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from strategy_engine.scanner_service import scanner
from utils.market_clock import MarketClock
from utils.notifications import notifier
from executor_service.order_executor import executor
import pytz

# Initialize Scheduler
scheduler = AsyncIOScheduler()

async def scheduled_market_scan(scan_name: str):
    """
    Job that runs at specific times.
    Checks if market is open, runs scan, alerts results, EXECUTES TRADES.
    """
    print(f"SCHEDULER: Starting {scan_name}...")
    
    # 1. Market Status Check
    if not MarketClock.is_market_open():
        # Optional: check if pre/post market rules allow?
        # For now, strict:
        print("Market Closed. Use force override if needed.")
        # We might still run scan to get data, but not execute?
    
    # 2. Run Scan
    # The scan run checks MarketClock internally for "Can Trade" permissions
    # But filters candidates.
    results = await scanner.run_scan()
    


    # 3. Process Results for Notification
    # We want to know how many trades were found.
    swings = results.get("Swing", [])
    options = results.get("Options", [])
    days = results.get("Day Trade", [])
    
    all_candidates = swings + options + days
    
    # GROUP BY STRATEGY
    from collections import defaultdict
    strat_counts = defaultdict(list)
    
    for c in all_candidates:
        # Example setup_name: "FGD (First Green Day)" or "3EMA Trend Breakout"
        # We group by the first word or full name
        strat_counts[c.setup_name].append(c)
    
    msg_lines = [f"**{scan_name} Report**"]
    
    if not all_candidates:
        msg_lines.append("💤 No Signals Found.")
    else:
        for setup, c_list in strat_counts.items():
            # Icon mapping
            icon = "🔹"
            if "FGD" in setup: icon = "🚀"
            elif "Panic" in setup: icon = "🩸"
            elif "3EMA" in setup: icon = "🌊"
            elif "Trend" in setup: icon = "🦅"
            elif "Options" in setup: icon = "🎯"
            elif "Warrior" in setup: icon = "⚔️"
            
            msg_lines.append(f"{icon} **{setup}**: {len(c_list)}")
            
            # List Top 3 symbols
            for c in c_list[:3]:
                 msg_lines.append(f"   • {c.symbol} (${c.trade_plan.entry:.2f})")
            if len(c_list) > 3:
                 msg_lines.append(f"   • ... and {len(c_list)-3} more")

    # Send
    color = 0x00ff00 if all_candidates else 0xcccccc
    notifier.send_message(f"📡 Bot Scan: {scan_name}", "\n".join(msg_lines), color)

def start_scheduler():
    # New York Time
    ny_tz = pytz.timezone("America/New_York")
    
    # 1. Morning Prep (9:45 AM)
    scheduler.add_job(
        scheduled_market_scan, 
        CronTrigger(hour=9, minute=45, timezone=ny_tz),
        args=["Morning Prep"]
    )
    
    # 2. Money Window (10:00 AM)
    scheduler.add_job(
        scheduled_market_scan, 
        CronTrigger(hour=10, minute=0, timezone=ny_tz),
        args=["Money Window Open"]
    )
    
    # 3. Options Window (10:30 AM)
    scheduler.add_job(
        scheduled_market_scan, 
        CronTrigger(hour=10, minute=30, timezone=ny_tz),
        args=["Options/Stabilization"]
    )
    
    # 4. Midday Check (12:00 PM)
    scheduler.add_job(
        scheduled_market_scan, 
        CronTrigger(hour=12, minute=0, timezone=ny_tz),
        args=["Midday Check"]
    )
    
    # 5. Power Hour (3:00 PM)
    scheduler.add_job(
        scheduled_market_scan, 
        CronTrigger(hour=15, minute=0, timezone=ny_tz),
        args=["Power Hour"]
    )

    scheduler.start()
    print("SCHEDULER: Online and waiting for market triggers.")
