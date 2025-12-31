
import asyncio
import os
import time
import sys
import subprocess

# Ensure project root is in path
sys.path.append(os.getcwd())

from utils.notifications import notifier

PROCESS_NAMES = {
    "SWING BOT": "executor_service/main.py",
    "SNIPER BOT": "run_sniper_bot.py"
}

from datetime import datetime

async def monitor():
    print("👀 WATCHDOG: Monitoring Bot Processes...")
    notifier.send_message("👀 WATCHDOG ONLINE", "Monitoring Swing & Sniper Bots.", color=0x999999)
    
    # Store last status to avoid spamming
    last_status = {name: True for name in PROCESS_NAMES} # Assume up initially
    
    while True:
        try:
            current_pids = {}
            
            # CHECK VIA PGREP
            for human_name, script_name in PROCESS_NAMES.items():
                try:
                    # pgrep -f matches full command line
                    result = subprocess.run(['pgrep', '-f', script_name], capture_output=True, text=True)
                    if result.returncode == 0:
                        # Process exists
                        pids = result.stdout.strip().split('\n')
                        # Exclude self (watchdog) if needed, but script_name is specific
                        current_pids[human_name] = pids[0]
                except Exception:
                    pass
            
            # Check Status
            for name, script_name in PROCESS_NAMES.items():
                is_running = name in current_pids
                was_running = last_status[name]
                
                if not is_running and was_running:
                     # DOWN DETECTED
                     msg = f"⚠️ CRITICAL: {name} IS DOWN! Process not found."
                     print(msg)
                     notifier.send_message("🔴 BOT DOWN ALERT", msg, color=0xff0000)
                     last_status[name] = False
                
                elif is_running and not was_running:
                     # RECOVERY DETECTED
                     msg = f"✅ {name} RECOVERED. PID: {current_pids[name]}"
                     print(msg)
                     notifier.send_message("🟢 BOT RECOVERED", msg, color=0x00ff00)
                     last_status[name] = True
                     
            # Heartbeat every hour
            if datetime.now().minute == 0 and datetime.now().second < 10:
                # Basic check
                 notifier.send_message("💓 SYSTEM HEARTBEAT", f"Watchdog Active. {len(current_pids)}/2 Bots Running.", color=0x333333)
                 await asyncio.sleep(60) # Don't spam

            await asyncio.sleep(10) # Check every 10s
            
        except Exception as e:
            print(f"Watchdog Error: {e}")
            await asyncio.sleep(30)

if __name__ == "__main__":
    try:
        # Install psutil if missing? Standard env usually has it or we rely on shell grep.
        # But psutil is better.
        asyncio.run(monitor())
    except KeyboardInterrupt:
        pass
