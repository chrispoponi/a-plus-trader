from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from strategy_engine.models import WebhookSignal
from executor_service.webhook_handler import process_webhook
from configs.settings import settings
from strategy_engine.scanner_service import scanner
from executor_service.upload_router import router as upload_router
from executor_service.automation_router import router as automation_router

app = FastAPI(title="A+ Trader Agent", version="1.0.0")

# Allow frontend to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In prod, lock this to localhost:5173
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(automation_router)

@app.api_route("/", methods=["GET", "HEAD"])
def health_check():
    from executor_service.order_executor import executor
    
    conn = "connected" if executor.api else "disconnected"
    if executor.api:
        try:
            executor.api.get_clock()
        except:
            conn = "error_connecting"
            
    return {
        "status": "system_active", 
        "mode": settings.TRADING_MODE, 
        "risk_limit": settings.MAX_RISK_PER_TRADE_PERCENT,
        "alpaca_status": conn
    }

@app.get("/scan")
async def trigger_scan():
    """
    Triggers a fresh market scan and returns candidates categorized by section.
    """
    results = await scanner.run_scan()
    return results

@app.post("/webhook")
async def receive_signal(signal: WebhookSignal, background_tasks: BackgroundTasks):
    """
    Endpoint for TradingView webhooks.
    """
    if signal.auth_token != settings.WEBHOOK_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Process immediately (await) or background? 
    # For trading execution, usually we wait to confirm receipt, but if execution is slow, background.
    # Alpaca API is usually fast enough to await.
    result = await process_webhook(signal)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))
        
    return result

from executor_service.scheduler import start_scheduler

@app.get("/api/debug/system")
def debug_system():
    import pkg_resources
    import os
    
    # Check Library Versions
    libs = ["alpaca-trade-api", "pandas", "numpy", "uvicorn", "fastapi"]
    versions = {}
    for lib in libs:
        try:
            versions[lib] = pkg_resources.get_distribution(lib).version
        except:
            versions[lib] = "NOT_INSTALLED"
            
    # Check Env Vars (Masked)
    return {
        "env": {
            "API_KEY_ID": "SET" if settings.APCA_API_KEY_ID else "MISSING",
            "SECRET_KEY": "SET" if settings.APCA_API_SECRET_KEY else "MISSING",
            "BASE_URL": settings.APCA_API_BASE_URL
        },
        "versions": versions
    }

@app.get("/api/debug/data")
async def debug_data_connection():
    """
    Test connectivity to Alpaca Data API specifically.
    """
    try:
        # Import here to avoid circular dependencies if any
        from alpaca_trade_api.rest import REST, TimeFrame
        from configs.settings import settings
        
        api = REST(
            settings.APCA_API_KEY_ID,
            settings.APCA_API_SECRET_KEY,
            base_url=settings.APCA_API_BASE_URL
        )
        
        # Try to fetch 1 day of AAPL
        # Using IEX as per fix
        bars = api.get_bars("AAPL", TimeFrame.Day, limit=1, feed='iex').df
        
        if bars.empty:
            return {"status": "ERROR", "message": "Connection OK, but returned empty DataFrame for AAPL (IEX)."}
        
        close_price = bars.iloc[-1]['close'] if not bars.empty else 0
        
        return {
            "status": "SUCCESS", 
            "rows": len(bars), 
            "latest_price": float(close_price),
            "feed used": "iex"
        }
    except Exception as e:
        import traceback
        return {
            "status": "ERROR", 
            "message": str(e),
            "trace": traceback.format_exc()
        }

@app.get("/api/debug/force_scan")
async def force_scan_debug():
    """
    Directly triggers the scanner and returns the RAW JSON results.
    Bypasses the Dashboard UI to confirm backend logic.
    """
    try:
        from strategy_engine.scanner_service import scanner
        print("DEBUG: Force Scan Triggered via API")
        results = await scanner.run_scan()
        return {
            "status": "SUCCESS",
            "count_swing": len(results.get("SWING", [])),
            "data": results
        }
    except Exception as e:
        import traceback
        return {
            "status": "ERROR", 
            "message": str(e),
            "trace": traceback.format_exc()
        }

@app.get("/api/journal/stats")
async def journal_stats():
    """Returns Win Rate, R-Multiple, and Equity Curve."""
    from executor_service.trade_logger import trade_logger
    return trade_logger.generate_analytics()

@app.get("/api/journal/history")
async def journal_history():
    """Returns list of all trades (Open and Closed)."""
    from executor_service.trade_logger import trade_logger
    return trade_logger.get_trade_history()

@app.post("/api/emergency/liquidate")
async def emergency_liquidate():
    """
    KILL SWITCH: Liquidates all positions (Market Sell) and Cancels all open orders.
    """
    try:
        from executor_service.order_executor import executor
        if not executor.api:
            return {"status": "error", "message": "Alpaca API not connected"}
        
        # Alpaca native 'close all'
        executor.api.close_all_positions(cancel_orders=True)
        print("🚨 EMERGENCY: LIQUIDATE ALL TRIGGERED")
        return {"status": "success", "message": "Liquidate All Signal Sent"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/data/clear")
async def clear_data():
    """
    Clears all CSV files from uploads directory.
    """
    try:
        files = glob.glob(os.path.join("uploads", "*.csv"))
        for f in files:
            os.remove(f)
        return {"status": "success", "message": f"Cleared {len(files)} files."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/journal/update")
async def update_journal(background_tasks: BackgroundTasks):
    """Triggers reconciliation of closed trades."""
    from executor_service.trade_logger import trade_logger
    background_tasks.add_task(trade_logger.update_closed_trades)
    return {"status": "reconciliation_started"}

@app.get("/api/alpaca/positions")
async def get_alpaca_positions():
    """Fetches LIVE positions directly from Alpaca."""
    try:
        from executor_service.order_executor import executor
        if not executor.api:
            return [{
                "symbol": "API_DISCONNECTED",
                "qty": 0,
                "side": "ERR",
                "market_value": 0,
                "cost_basis": 0,
                "unrealized_pl": 0,
                "unrealized_plpc": 0,
                "current_price": 0
            }]
        
        # FIX: 'REST' object has no attribute 'get_all_positions'. Use 'list_positions'.
        raw_positions = executor.api.list_positions()
        data = []
        for p in raw_positions:
            try:
                # Super Safe Extraction
                s = str(p.symbol)
                q = float(p.qty) if p.qty is not None else 0.0
                mv = float(p.market_value) if p.market_value is not None else 0.0
                cb = float(p.cost_basis) if p.cost_basis is not None else 0.0
                upl = float(p.unrealized_pl) if p.unrealized_pl is not None else 0.0
                uplpc = float(p.unrealized_plpc) if p.unrealized_plpc is not None else 0.0
                cp = float(p.current_price) if p.current_price is not None else 0.0
                
                # Side
                side_val = "long"
                if hasattr(p, 'side'):
                     if hasattr(p.side, 'value'): side_val = str(p.side.value)
                     else: side_val = str(p.side)

                data.append({
                    "symbol": s,
                    "qty": q,
                    "side": side_val,
                    "market_value": mv,
                    "cost_basis": cb,
                    "unrealized_pl": upl,
                    "unrealized_plpc": uplpc,
                    "current_price": cp
                })
            except Exception as ser_err:
                data.append({
                    "symbol": f"ERR: {str(ser_err)[:10]}",
                    "qty": 0,
                    "side": "ERR",
                    "market_value": 0,
                    "cost_basis": 0,
                    "unrealized_pl": 0,
                    "unrealized_plpc": 0,
                    "current_price": 0
                })
                continue 
                
        return data 
                
        return data
    except Exception as e:
        print(f"Error fetching positions: {e}")
        return [{
                "symbol": f"ERROR: {str(e)[:15]}",
                "qty": 0,
                "side": "ERR",
                "market_value": 0,
                "cost_basis": 0,
                "unrealized_pl": 0,
                "unrealized_plpc": 0,
                "current_price": 0
            }]

@app.on_event("startup")
def on_startup():
    start_scheduler()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
