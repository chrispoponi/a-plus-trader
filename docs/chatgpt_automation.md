# ChatGPT Automation Integration

You can automate ChatGPT (via Custom GPT Actions or a local script) to drop stock picks directly into your A+ Trader Agent.

## Endpoint
**URL**: `http://<YOUR_IP>:8000/automation/chatgpt-drop`
**Method**: `POST`
**Content-Type**: `application/json`

## Payload Schema

```json
{
  "auth_token": "3a61436ddbf04bb796b1ede8b65d9490", 
  "batch_id": "morning_scan_2025_12_28",
  "notes": "Top growth picks for the week",
  "picks": [
    {
      "symbol": "NVDA",
      "reason": "Breaking out of cup and handle",
      "sentiment": "BULLISH",
      "confidence": 0.85,
      "source_list_name": "growth_leaders"
    },
    {
      "symbol": "AMD",
      "reason": "Sympathy play, strong volume",
      "sentiment": "BULLISH",
      "source_list_name": "semis_watch"
    }
    // ... add up to 200 picks
  ]
}
```

## How to use with Custom GPTs
1. **Expose your server** to the internet (e.g. ngrok).
2. **Add Action** to your Custom GPT:
   - Paste the schema above into the Action definition.
   - Instruct the GPT: *"When I ask for a market scan, generate a JSON payload with the top 50 stocks and send it to my API."*
