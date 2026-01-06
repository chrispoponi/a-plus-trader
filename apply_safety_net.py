from executor_service.order_executor import executor

def apply_safety_net():
    print("🚑 APPLYING EMERGENCY SAFETY NET V2 🚑")
    
    if not executor.api:
        print("❌ Alpaca API Fail.")
        return

    # 1. Get Naked Positions
    positions = executor.api.list_positions()
    orders = executor.api.list_orders(status='open')
    
    protected_symbols = {o.symbol for o in orders if o.type in ['stop', 'stop_limit', 'trailing_stop']}
    
    for p in positions:
        if p.symbol not in protected_symbols:
            print(f"⚠️  Securing {p.symbol} ({p.qty} shares)...")
            
            qty = abs(int(p.qty))
            side = 'sell' if float(p.qty) > 0 else 'buy'
            current_price = float(p.current_price)
            avg_entry = float(p.avg_entry_price)
            
            # Logic:
            # If in Profit (>1%): Protect Breakeven or Trail.
            # If in Loss: Cap at 2% from CURRENT price.
            
            stop_price = 0.0
            if side == 'sell': # Long
                 stop_price = round(current_price * 0.98, 2)
            else: # Short
                 stop_price = round(current_price * 1.02, 2)
                
            try:
                executor.api.submit_order(
                    symbol=p.symbol,
                    qty=qty,
                    side=side,
                    type='stop',
                    time_in_force='gtc',
                    stop_price=stop_price
                )
                print(f"   ✅ STOP LOSS SET: {p.symbol} @ {stop_price}")
            except Exception as e:
                print(f"   ❌ FAILED to secure {p.symbol}: {e}")
        else:
             print(f"   👍 {p.symbol} IS PROTECTED.")

if __name__ == "__main__":
    apply_safety_net()
