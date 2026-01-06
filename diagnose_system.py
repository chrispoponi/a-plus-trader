from configs.settings import settings
from utils.notifications import notifier
import os

def diagnose():
    print("🦅 SYSTEM DIAGNOSIS...")
    
    # 1. Check Env
    webhook = settings.DISCORD_WEBHOOK_URL
    print(f"🔹 DISCORD_WEBHOOK_URL: {'[SET]' if webhook else '[MISSING/EMPTY]'}")
    if webhook:
         print(f"   (Length: {len(webhook)} chars)")
         
    # 2. Test Send
    print("🔹 Attempting to send Test Message...")
    try:
        notifier.send_message("🛠️ DIAGNOSTIC TEST", "Verifying Discord Connectivity from active instance.", color=0x00ffff)
        print("   ✅ Send call executed (Check Discord channel).")
    except Exception as e:
        print(f"   ❌ Send Failed: {e}")
        
    # 3. Check Scheduler
    # We can't check the running scheduler from here easily if it's in another process,
    # but we can check if dependencies load.
    try:
        from apscheduler.triggers.interval import IntervalTrigger
        print("   ✅ APScheduler IntervalTrigger importable.")
    except Exception as e:
         print(f"   ❌ APScheduler Import Fail: {e}")

if __name__ == "__main__":
    diagnose()
