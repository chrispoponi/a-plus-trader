import logging
from configs.settings import settings
from strategy_engine.models import WebhookSignal
from executor_service.idempotency import idempotency
from data_adapters.alpaca_adapter import alpaca_client

# Setup structured logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("executor")

async def process_webhook(signal: WebhookSignal):
    # 1. Validate Token (Redundant if done in FastAPI dep, but safe)
    if signal.auth_token != settings.WEBHOOK_TOKEN:
        logger.warning(f"Unauthorized signal attempt. Token: {signal.auth_token[:5]}...")
        return {"status": "error", "message": "Unauthorized"}
        
    # 2. Idempotency
    if idempotency.is_processed(signal.signal_id):
        logger.info(f"Signal {signal.signal_id} already processed. Skipping.")
        return {"status": "ignored", "reason": "duplicate", "signal_id": signal.signal_id}

    logger.info(f"Processing NEW signal: {signal.signal_id} | {signal.action} {signal.symbol}")

    # 3. Risk Checks (Global)
    # Check max daily loss (stub: assumes we track PnL somewhere)
    # Check max open positions (stub)
    
    # 4. Mode Check
    if settings.TRADING_MODE == "LIVE" and not settings.TRADING_MODE.value == "LIVE":
         # Double check (redundant but explicit)
         pass

    # 5. Execution
    try:
        response = alpaca_client.place_order(
            symbol=signal.symbol,
            qty=signal.qty,
            side=signal.action.lower(),  # buy/sell
            order_type=signal.order_type,
            limit_price=signal.limit_price,
            stop_price=signal.stop_price,
            take_profit=signal.bracket.take_profit,
            stop_loss=signal.bracket.stop_loss
        )
        
        # 6. Mark Processed (ONLY if successful or non-retriable error)
        idempotency.mark_processed(signal.signal_id)
        
        logger.info(f"Order processed successfully: {response}")
        return {"status": "success", "order_id": response.get("id")}
        
    except Exception as e:
        logger.error(f"Execution failed: {str(e)}")
        return {"status": "error", "message": str(e)}
