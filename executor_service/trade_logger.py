import uuid
from datetime import datetime
import pandas as pd
import os
from configs.settings import settings
import alpaca_trade_api as tradeapi

# Path to the persistent journal
JOURNAL_FILE = "uploads/trade_journal.csv"
EQUITY_FILE = "uploads/equity_curve.csv"

# Ensure uploads dir
os.makedirs("uploads", exist_ok=True)
print(f"📂 JOURNAL PATH: {os.path.abspath(JOURNAL_FILE)}")

class TradeLogger:
    def __init__(self):
        self.api = None
        try:
            self.api = tradeapi.REST(
                settings.APCA_API_KEY_ID,
                settings.APCA_API_SECRET_KEY,
                settings.APCA_API_BASE_URL,
                api_version='v2'
            )
            # Rehydrate from broker on cold start (for ephemeral cloud storage)
            self.hydrate_history()
        except Exception as e:
            print(f"Logger Init Error: {e}")

    def hydrate_history(self):
        """
        Rebuilds Journal from Alpaca Closed Orders.
        """
        if not self.api: return
        print("🦅 HYDRATING HISTORY FROM ALPACA...")
        
        try:
            # 1. Fetch recent closed orders (Exit candidates)
            # Increase limit to 500 to skip over "Cancelled" noise (Safety Seal rejects)
            orders = self.api.list_orders(status='closed', limit=500, direction='desc')
            if not orders: 
                print("Hydration: No closed orders found.")
                return "No Orders Found at Broker."
            
            print(f"Hydration: Scanned {len(orders)} closed orders.")

            # Load (empty) Journal
            if os.path.exists(JOURNAL_FILE):
                try: journal = pd.read_csv(JOURNAL_FILE)
                except: journal = pd.DataFrame()
            else:
                journal = pd.DataFrame()
                
            new_rows = []
            
            # 2. Iterate and Match Trades (LIFO Approximation)
            processed_order_ids = set()
            
            for i, out_order in enumerate(orders):
                if out_order.id in processed_order_ids: continue
                if not out_order.filled_at: continue # Skip Cancelled
                
                # We care about CLOSING trades (Exits) to log PnL
                if out_order.side == 'sell':
                    symbol = out_order.symbol
                    
                    # Check if already entering in Journal (Avoid Dupes)
                    ts_str = str(out_order.filled_at)[:19] 
                    if not journal.empty and "exit_time" in journal.columns:
                        # Improved Dupe Check with Repair Logic
                        mask = journal["exit_time"].astype(str).str.contains(ts_str)
                        if mask.any():
                             # Check if existing record has PnL (valid) or is a 'Ghost' (0 PnL)
                             existing = journal.loc[mask]
                             has_pnl = False
                             if "pnl_dollars" in existing.columns:
                                 vals = pd.to_numeric(existing["pnl_dollars"], errors='coerce').fillna(0)
                                 # If any matching row has abs(pnl) > 0.01, we consider it valid
                                 if (vals.abs() > 0.01).any():
                                     has_pnl = True
                             
                             if has_pnl:
                                 continue
                             else:
                                 # It's a Ghost Record (0 PnL). Remove it to allow overwrite.
                                 journal = journal.loc[~mask]
                                 # print(f"Repairing record for {symbol}")
                    
                    exit_price = float(out_order.filled_avg_price)
                    qty = float(out_order.qty)
                    exit_time = out_order.filled_at
                    
                    entry_price = exit_price # Default (Break Even)
                    entry_time = exit_time
                    matched = False
                    
                    # Look ahead (back in time) for the Buyer
                    for j in range(i + 1, len(orders)):
                        in_order = orders[j]
                        if in_order.symbol == symbol and in_order.side == 'buy':
                            # Found a potential entry match (Naive LIFO)
                            entry_price = float(in_order.filled_avg_price)
                            entry_time = in_order.filled_at
                            matched = True
                            break
                            
                    pnl_dollars = (exit_price - entry_price) * qty
                    cost_basis = entry_price * qty
                    pnl_percent = (pnl_dollars / cost_basis) if cost_basis > 0 else 0.0
                    
                    row = {
                        "trade_id": str(uuid.uuid4()),
                        "symbol": symbol,
                        "bucket": "RECOVERED",
                        "side": "LONG",
                        "entry_time": entry_time,
                        "entry_price": entry_price, 
                        "exit_time": exit_time,
                        "exit_price": exit_price,
                        "qty": qty,
                        "stop_price": None,
                        "target_price": None,
                        "risk_dollars": 0,
                        "pnl_dollars": pnl_dollars,
                        "pnl_percent": pnl_percent,
                        "r_multiple": 0,
                        "holding_minutes": 0,
                        "status": "CLOSED",
                        "notes": "Recovered" if matched else "Recovered (Unmatched Entry)"
                    }
                    new_rows.append(row)
                    processed_order_ids.add(out_order.id)
                
            msg = f"Hydration Complete. Scanned {len(orders)} orders."
            if new_rows:
                df = pd.DataFrame(new_rows)
                if not journal.empty:
                    journal = pd.concat([journal, df], ignore_index=True)
                else:
                    journal = df
                journal.to_csv(JOURNAL_FILE, index=False)
                print(f"✅ HYDRATED {len(new_rows)} historical records.")
                self.generate_analytics()
                msg += f" Added {len(new_rows)} trades."
            else:
                msg += " No new trades added."
                
            return msg
                
        except Exception as e:
            print(f"Hydration Failed: {e}")
            return f"Hydration Error: {str(e)}"

    def log_trade_entry(self, symbol, bucket, qty, entry_price, stop, target, score=0, setup_name="Unknown"):
        """
        Logs a new trade immediately upon execution, including Score and Setup.
        """
        risk_per_share = abs(entry_price - stop) if stop else 0
        risk_dollars = risk_per_share * qty

        trade = {
            "trade_id": str(uuid.uuid4()),
            "symbol": symbol,
            "bucket": bucket,
            "setup": setup_name,
            "score": score,
            "side": "LONG" if qty > 0 else "SHORT",
            "entry_time": datetime.utcnow(),
            "entry_price": entry_price,
            "exit_time": None,
            "exit_price": None,
            "qty": qty,
            "stop_price": stop,
            "target_price": target,
            "risk_dollars": risk_dollars,
            "pnl_dollars": None,
            "pnl_percent": None,
            "r_multiple": None,
            "holding_minutes": None,
            "status": "OPEN",
            "notes": ""
        }
        
        df = pd.DataFrame([trade])
        # Append to CSV
        header = not os.path.exists(JOURNAL_FILE)
        df.to_csv(JOURNAL_FILE, mode='a', header=header, index=False)
        print(f"📝 LOGGED ENTRY: {symbol} ({bucket}) - Score: {score}")


    def sync_open_positions(self):
        """
        SELF-HEAL: Fetches live Alpaca positions and ensures they are in the journal.
        If a position exists in Alpaca but not the Journal (e.g. after restart), it 'seeds' it.
        """
        if not self.api: return
        try:
            positions = self.api.list_positions()
        except: return

        # Load or Create Journal
        journal = pd.DataFrame()
        if os.path.exists(JOURNAL_FILE):
            journal = pd.read_csv(JOURNAL_FILE)
            
        # Get set of currently logged OPEN symbols
        logged_open_symbols = set()
        if not journal.empty:
             logged_open_symbols = set(journal[journal["status"] == "OPEN"]["symbol"].values)

        new_trades = []
        for p in positions:
            if p.symbol not in logged_open_symbols:
                # Discovered an Orphan Position. Seed it.
                print(f"⚠️ SEEDING ORPHAN POSITION: {p.symbol}")
                qty = float(p.qty)
                entry = float(p.avg_entry_price)
                side = "LONG" if qty > 0 else "SHORT"
                
                # Approximate risk (we don't know original stop)
                # Assume 2% risk for logging purposes
                stop = entry * 0.98 if side == "LONG" else entry * 1.02 
                risk = abs(entry - stop) * abs(qty)
                
                trade = {
                    "trade_id": str(uuid.uuid4()),
                    "symbol": p.symbol,
                    "bucket": "SEEDED",
                    "side": side,
                    "entry_time": datetime.utcnow().isoformat(), # Use specific format for consistency
                    "entry_price": entry,
                    "exit_time": None,
                    "exit_price": None,
                    "qty": qty,
                    "stop_price": stop,
                    "target_price": None,
                    "risk_dollars": risk,
                    "pnl_dollars": None,
                    "pnl_percent": None,
                    "r_multiple": None,
                    "holding_minutes": None,
                    "status": "OPEN",
                    "notes": "Recovered from Alpaca Api"
                }
                new_trades.append(trade)

        if new_trades:
            df_new = pd.DataFrame(new_trades)
            # Append safely
            if not journal.empty:
                journal = pd.concat([journal, df_new], ignore_index=True)
            else:
                journal = df_new
                
            journal.to_csv(JOURNAL_FILE, index=False)
            print(f"✅ SYNC: Recovered {len(new_trades)} positions into Journal.")

    def update_closed_trades(self):
        """
        Reconciles OPEN trades with Alpaca Order History to enable PnL tracking.
        Also triggers Sync to catch orphans.
        """
        # First, ensure we track everything we hold
        self.sync_open_positions()

        if not os.path.exists(JOURNAL_FILE): return
        if not self.api: return
        
        # Reload after sync
        journal = pd.read_csv(JOURNAL_FILE)
        # Handle 'entry_time' parsing carefully
        # ... (Rest of logic)
        journal["entry_time"] = pd.to_datetime(journal["entry_time"]) 
        open_trades = journal[journal["status"] == "OPEN"]
        
        if open_trades.empty: return

        # Get All Open Positions to quickly check what's still alive
        try:
            positions = {p.symbol: p for p in self.api.list_positions()}
        except: return

        updated_count = 0
        for idx, trade in open_trades.iterrows():
            symbol = trade["symbol"]
            qty = float(trade["qty"])

            # If symbol is still in active positions, skip (it's still open)
            if symbol in positions:
                continue

            # Trade is NOT in positions -> It must have closed.
            # Fetch latest CLOSED orders for this symbol
            try:
                # We fetch limit=5 to be safe
                closed_orders = self.api.list_orders(status="closed", symbols=[symbol], limit=5)
            except: continue
            
            if not closed_orders: continue
            
            # Find the sell order that happened AFTER entry
            # (Simplification: Just grab the most recent filled sell)
            fill = None
            for order in closed_orders:
                if order.side == 'sell' and order.filled_at:
                    filled_at = order.filled_at.replace(tzinfo=None) # Naive compare
                    if filled_at > trade["entry_time"]:
                        fill = order
                        break
            
            if not fill: continue

            # Found the exit!
            exit_price = float(fill.filled_avg_price)
            exit_time = fill.filled_at.replace(tzinfo=None) # Make naive for CSV
            
            entry_price = float(trade["entry_price"])
            pnl = (exit_price - entry_price) * qty
            pnl_pct = pnl / (entry_price * qty)
            risk = float(trade["risk_dollars"])
            r_mult = pnl / risk if risk > 0 else 0
            hold_min = (exit_time - trade["entry_time"]).total_seconds() / 60

            journal.loc[idx, "exit_price"] = exit_price
            journal.loc[idx, "exit_time"] = exit_time
            journal.loc[idx, "pnl_dollars"] = pnl
            journal.loc[idx, "pnl_percent"] = pnl_pct
            journal.loc[idx, "r_multiple"] = r_mult
            journal.loc[idx, "holding_minutes"] = hold_min
            journal.loc[idx, "status"] = "CLOSED"
            updated_count += 1

        if updated_count > 0:
            journal.to_csv(JOURNAL_FILE, index=False)
            print(f"📝 UPDATED {updated_count} CLOSED TRADES.")
            # Trigger Stats Re-Calc
            self.generate_analytics()
            
            # Return list for notifications
            closed_list = []
            # We iterate the indices we processed (which were in open_trades)
            # and check if they are now CLOSED in the master journal
            for idx in open_trades.index:
                if journal.loc[idx, "status"] == "CLOSED":
                    closed_list.append(journal.loc[idx].to_dict())
            return closed_list
            
        return []

    def generate_analytics(self) -> dict:
        """
        Calculates Win Rate, R-Multiple, and Equity Curve.
        """
        if not os.path.exists(JOURNAL_FILE): return {}
        
        df = pd.read_csv(JOURNAL_FILE)
        closed = df[df["status"] == "CLOSED"].copy()
        
        if closed.empty: return {"msg": "No closed trades yet"}
        
        # Ensure Numeric Types
        cols = ["pnl_dollars", "r_multiple", "holding_minutes"]
        for c in cols:
             if c in closed.columns:
                 closed[c] = pd.to_numeric(closed[c], errors='coerce').fillna(0.0)
        
        summary = {
            "total_trades": len(closed),
            "win_rate": (closed["pnl_dollars"] > 0).mean(),
            "avg_R": closed["r_multiple"].mean(),
            "total_pnl": closed["pnl_dollars"].sum(),
            "avg_hold_minutes": closed["holding_minutes"].mean()
        }
        
        # Drawdown Calc
        closed["cum_pnl"] = closed["pnl_dollars"].cumsum()
        closed["peak"] = closed["cum_pnl"].cummax()
        closed["drawdown"] = closed["peak"] - closed["cum_pnl"]
        
        summary["max_drawdown"] = closed["drawdown"].max()
        
        # Save Curve
        closed[["cum_pnl", "drawdown"]].to_csv(EQUITY_FILE, index=False)
        
        return summary

    def get_trade_history(self) -> list:
        """
        Returns the raw list of trades for the frontend table.
        """
        if not os.path.exists(JOURNAL_FILE): return []
        df = pd.read_csv(JOURNAL_FILE)
        # Replace NaN with None for JSON compliance
        df = df.where(pd.notnull(df), None)
        return df.to_dict(orient="records")

trade_logger = TradeLogger()
