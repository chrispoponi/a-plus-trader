import pandas as pd
import uuid

JOURNAL_FILE = "uploads/trade_journal.csv"

def consolidate_manual_trades():
    if not os.path.exists(JOURNAL_FILE):
        print("No journal found.")
        return

    df = pd.read_csv(JOURNAL_FILE)
    
    # Separate Manual Imports from others
    manual = df[df["bucket"] == "MANUAL_IMPORT"].copy()
    others = df[df["bucket"] != "MANUAL_IMPORT"].copy()
    
    if manual.empty:
        print("No manual imports to fix.")
        return

    print(f"Found {len(manual)} manual records. Consolidating...")
    
    # Group by Symbol
    symbols = manual["symbol"].unique()
    consolidated_rows = []
    
    for sym in symbols:
        subset = manual[manual["symbol"] == sym]
        
        # Calculate Net Quantities and Cash Flow
        # In the ingest, I saved "entry_price" as positive. 
        # But I need to know if it was a Buy or Sell.
        # "side" column: BUY, SELL, SELL_SHORT.
        
        # Logic:
        # Buy: Cash Outflow (Negative Cash)
        # Sell/Short: Cash Inflow (Positive Cash, initially) 
        # Wait, Short Entry is Cash Inflow? Yes. Short Exit is Outflow.
        # Long Entry is Outflow. Long Exit is Inflow.
        
        # Let's look at the amounts from the user paste again.
        # Buy 30 SOFI ... -$825.60
        # Sell_short 338 PYPL ... +$19,823.70
        
        # So "Buy" is negative cash. "Sell" is positive cash.
        # Net Cash = Sum of all transaction amounts.
        # If Net Qty is 0, then Net Cash is the PnL.
        
        net_qty = 0
        net_cash = 0
        total_buy_qty = 0
        total_sell_qty = 0
        
        # For average entry price calc
        weighted_entry_cash = 0
        
        # We need to re-parse the amounts because I didn't save the raw signed amount in the CSV,
        # I saved "entry_price" (abs) and "qty".
        # Re-deriving signed amount:
        # If Side == BUY: Amount = -1 * price * qty
        # If Side == SELL or SELL_SHORT: Amount = price * qty
        
        # Wait, "Sell_short" is an entry. "Buy" to cover is an exit.
        # But purely cash-flow wise:
        # Sell (Open Short) -> +Cash
        # Buy (Close Short) -> -Cash
        # Buy (Open Long) -> -Cash
        # Sell (Close Long) -> +Cash
        
        # So simply: BUY = Negative. SELL/SELL_SHORT = Positive.
        
        for _, row in subset.iterrows():
            qty = float(row["qty"])
            price = float(row["entry_price"])
            side = row["side"].upper()
            
            if "BUY" in side:
                amount = -1 * price * qty
                net_qty += qty # Longs add to inventory
                net_cash += amount
                total_buy_qty += qty
                weighted_entry_cash += (price * qty)
            else: # SELL / SELL_SHORT
                amount = price * qty
                net_qty -= qty # Shorts subtract from inventory (or reduce long)
                net_cash += amount
                total_sell_qty += qty
                # If this is a short entry, we track it? 
                # For consolidated PnL, we just sum cash.
        
        # Check completeness
        status = "OPEN"
        if abs(net_qty) < 0.01: # Floating point tolerance
            status = "CLOSED"
        
        entry_time = subset["entry_time"].min()
        exit_time = subset["entry_time"].max()
        
        # Construct summary row
        # If closed, PnL = net_cash.
        # If open, PnL = Unrealized (but we can't really calc without current price).
        # We will log it as is.
        
        row = {
            "trade_id": str(uuid.uuid4()),
            "symbol": sym,
            "bucket": "MANUAL_IMPORT",
            "side": "LONG" if total_buy_qty > 0 else "SHORT", # Simplified
            "entry_time": entry_time,
            "entry_price": 0, # Hard to say average if mixed
            "exit_time": exit_time,
            "exit_price": 0,
            "qty": max(total_buy_qty, total_sell_qty), # Volume
            "status": status,
            "pnl_dollars": net_cash if status == "CLOSED" else 0, # Only realized if closed
            "pnl_percent": 0,
            "r_multiple": 0,
            "holding_minutes": 0,
            "notes": f"Consolidated {len(subset)} fills."
        }
        
        # Calc ROI % if closed
        if status == "CLOSED" and total_buy_qty > 0:
             # Just roughly: PnL / Total Cost
             cost = weighted_entry_cash if weighted_entry_cash > 0 else 1
             row["pnl_percent"] = row["pnl_dollars"] / cost
             row["entry_price"] = cost / total_buy_qty
             row["exit_price"] = (cost + row["pnl_dollars"]) / total_buy_qty

        consolidated_rows.append(row)

    # Combine
    if consolidated_rows:
        new_df = pd.DataFrame(consolidated_rows)
        final_df = pd.concat([others, new_df], ignore_index=True)
        final_df.to_csv(JOURNAL_FILE, index=False)
        print(f"✅ Consolidated into {len(consolidated_rows)} trades.")
        
        # Print for verification
        print(new_df[["symbol", "status", "pnl_dollars"]])
    else:
        print("No rows generated.")

if __name__ == "__main__":
    import os
    consolidate_manual_trades()
