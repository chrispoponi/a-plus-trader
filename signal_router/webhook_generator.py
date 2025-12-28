from strategy_engine.models import Candidate, WebhookSignal, WebhookBracket, Action, OrderType
from configs.settings import settings

def generate_webhook_payload(candidate: Candidate) -> WebhookSignal:
    """
    Converts a qualified Candidate into the JSON structure expected by the Execution Layer.
    """
    
    # Determine Action from Direction
    action = Action.BUY if candidate.direction == "LONG" else Action.SELL
    # Note: Options logic would differ (BUY_TO_OPEN vs SELL_TO_OPEN)
    
    # Calculate Qty based on Risk Management
    # (Simplified logic here)
    qty = 10 
    if candidate.trade_plan.position_size_shares:
        qty = candidate.trade_plan.position_size_shares
        
    return WebhookSignal(
        auth_token=settings.WEBHOOK_TOKEN,
        signal_id=candidate.signal_id,
        section=candidate.section,
        symbol=candidate.symbol,
        action=action,
        order_type=OrderType.LIMIT, # Default to limit
        qty=qty,
        limit_price=candidate.trade_plan.entry,
        stop_price=None, # Only for stop orders
        time_in_force="gtc",
        bracket=WebhookBracket(
            take_profit=candidate.trade_plan.take_profit,
            stop_loss=candidate.trade_plan.stop_loss
        ),
        win_probability_estimate=candidate.scores.win_probability_estimate,
        validity_window_minutes=60, # 1 hour default
        notes=candidate.thesis
    )
