from executor_service.order_executor import executor
from configs.settings import settings

def audit_orders():
    print("🦅 AUDITING ACTIVE ORDERS & POSITIONS...")
    
    if not executor.api:
        print("❌ Alpaca API Not Connected.")
        return

    # 1. Get Positions
    positions = executor.api.list_positions()
    pos_map = {p.symbol: p for p in positions}
    print(f"📊 Open Positions: {len(positions)}")
    for p in positions:
        print(f"   • {p.symbol}: {p.qty} shares (Unrealized P&L: ${float(p.unrealized_pl):.2f})")

    # 2. Get Open Orders
    orders = executor.api.list_orders(status='open')
    print(f"\n🛡️ Active Orders (Stops/Limits): {len(orders)}")
    
    stops_found = {}
    
    for o in orders:
        desc = f"{o.side} {o.qty} {o.symbol} @ {o.stop_price if o.stop_price else o.limit_price} ({o.type})"
        print(f"   • {desc}")
        if o.type in ['stop', 'stop_limit']:
            stops_found[o.symbol] = True

    # 3. Gap Analysis (Positions without Stops)
    print("\n🚨 RISK AUDIT (Positions missing Stop Loss):")
    safe = True
    for sym in pos_map:
        if sym not in stops_found:
            print(f"   ⚠️  CRITICAL: {sym} HAS NO ACTIVE STOP LOSS ORDER!")
            safe = False
            
    if safe:
        print("   ✅ All positions have active stop orders.")
    else:
        print("   ❌ IMMEDIATE ACTION REQUIRED: Manually close or add stops.")

if __name__ == "__main__":
    audit_orders()
