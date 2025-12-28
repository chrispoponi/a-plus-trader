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

@app.get("/")
def health_check():
    return {
        "status": "system_active", 
        "mode": settings.TRADING_MODE, 
        "risk_limit": settings.MAX_RISK_PER_TRADE_PERCENT
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

@app.on_event("startup")
def on_startup():
    start_scheduler()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
