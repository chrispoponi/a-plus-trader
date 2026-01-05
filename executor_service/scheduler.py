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
    
    # --- AUTO EXECUTION ---
    from configs.settings import settings
    if settings.AUTO_EXECUTION_ENABLED:
        print(f"SCHEDULER: Auto-Execution Enabled. Processing {len(all_candidates)} candidates...")
        for cand in all_candidates:
            try:
                # Check Compliance & Execute
                # executor handles risk checks internally
                res = executor.execute_trade(cand)
                print(f"EXECUTION RESULT ({cand.symbol}): {res}")
            except Exception as e:
                print(f"Failed to execute {cand.symbol}: {e}")
    else:
        print("SCHEDULER: Auto-Execution DISABLED. Signaling only.")
    # ----------------------
    
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

def check_trade_exits():
    """
    Polls the trade logger to see if any open trades have closed.
    If so, sends a notification.
    """
    try:
        from executor_service.trade_logger import trade_logger
        # Returns list of dicts
        closed_trades = trade_logger.update_closed_trades()
        
        if closed_trades:
            print(f"SCHEDULER: Found {len(closed_trades)} closed trades.")
            for t in closed_trades:
                # Format Message
                pnl = t.get('pnl_dollars', 0)
                pct = t.get('pnl_percent', 0) * 100
                symbol = t.get('symbol')
                
                emoji = "🟢" if pnl >= 0 else "🔴"
                title = f"{emoji} TRADE CLOSED: {symbol}"
                
                msg = (
                    f"**Result:** ${pnl:.2f} ({pct:.2f}%)\n"
                    f"**Exit Price:** ${t.get('exit_price', 0):.2f}\n"
                    f"**Hold Time:** {t.get('holding_minutes', 0):.1f} mins"
                )
                
                color = 0x00ff00 if pnl >= 0 else 0xff0000
                notifier.send_message(title, msg, color)
    except Exception as e:
        print(f"Error checking exits: {e}")

def start_scheduler():
    # New York Time
    ny_tz = pytz.timezone("America/New_York")
    from apscheduler.triggers.interval import IntervalTrigger
    
    # 0. Exit Poller (Every 5 mins)
    scheduler.add_job(
        check_trade_exits,
        IntervalTrigger(minutes=5),
        id="exit_poller"
    )
    
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
