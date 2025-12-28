# TradingView Webhook Setup

This guide explains how to connect TradingView alerts to the **A+ Trader Builder Agent** execution service.

## 1. Webhook URL
Your execution service endpoint is:
```
http://<YOUR_SERVER_IP>:8000/webhook
```
*If running locally, you must use a tunneling service like ngrok.*

## 2. Authentication
Your secure token is: defined in `.env` (Default: `3a61436ddbf04bb796b1ede8b65d9490`)

## 3. JSON Payload Template
Paste the following into your TradingView Alert "Message" field.
**IMPORTANT**: Replace `{{values}}` with actual static values or use TradingView placeholders if you are advanced.

```json
{
  "auth_token": "3a61436ddbf04bb796b1ede8b65d9490",
  "signal_id": "{{ticker}}_{{timenow}}",
  "section": "SWING GRADE SETUP",
  "symbol": "{{ticker}}",
  "action": "BUY",
  "order_type": "limit",
  "qty": 100,
  "limit_price": {{close}},
  "stop_price": null,
  "time_in_force": "gtc",
  "bracket": {
    "take_profit": 150.00,
    "stop_loss": 90.00
  },
  "win_probability_estimate": 75.0,
  "validity_window_minutes": 60,
  "notes": "Manual TradingView Alert"
}
```

## 4. Testing
1. Set the service to `TRADING_MODE=PAPER` in `.env`.
2. Fire the alert from TradingView.
3. Check application logs for "Processing NEW signal".
