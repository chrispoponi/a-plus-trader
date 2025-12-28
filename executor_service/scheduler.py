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
    
    core_swings = [c for c in swings if c.trade_plan.is_core_trade]
    
    msg_lines = [f"**{scan_name} Report**"]
    
    if core_swings:
        msg_lines.append(f"🟢 **CORE SWINGS DETECTED**: {len(core_swings)}")
        for c in core_swings:
            # AUTO EXECUTE TRADES
            # Rules: Must be Core (>80) AND have Positive AI Analysis
            ai_pass = c.ai_analysis and "Bearish" not in c.ai_analysis and "Error" not in c.ai_analysis
            
            # TODO: Uncomment strict AI gate if desired. For now, execute all Core.
            status = executor.execute_trade(c)
            
            emoji = "🚀" if "SUCCESS" in status else "⚠️"
            msg_lines.append(f"- {c.symbol}: Score {c.scores.overall_rank_score} | Exec: {emoji} ({status})")
    else:
        msg_lines.append("No Core Swings.")
        
    msg_lines.append(f"Day Trades: {len(days)} | Options: {len(options)}")
    
    # Send
    color = 0x00ff00 if core_swings else 0xcccccc
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
