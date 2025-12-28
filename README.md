# A+ Trader Builder Agent

A production-grade, auditable trading signal platform operating in Google Antigravity.

## Mission
1. Generate trade candidates (Swing, Breakout, Options).
2. Score and rank signals (Min 65% Win Probability).
3. Transmit TOP 3 signals to Execution Layer via Webhooks.
4. Auto-trade via Alpaca (Paper/Live).

## Quick Start

### 1. Configuration
Copy the template and fill in your keys:
```bash
cp .env.template .env
# Edit .env: Add Alpaca Keys, Adjust Risk Settings
```

### 2. Install Dependencies
```bash
python3 -m pip install -r requirements.txt
```

### 3. Run Execution Service (Listener)
Start the webhook receiver that connects to Alpaca:
```bash
uvicorn executor_service.main:app --reload
```

### 4. Run Strategy Scan (Generator)
Run the daily scan to generate and transmit signals:
```bash
python3 run_scan.py
```

## Architecture
- **strategy_engine/**: Logic for 24 Swing Setups, Breakouts, Options.
- **scoring/**: Win probability estimation engine.
- **executor_service/**: FastAPI webhook receiver with idempotency & risk checks.
- **configs/**: Settings and Risk Controls (Non-negotiable).

## Risk Management (Non-Negotiable)
- Defaults: 50% max risk per trade, 10% max daily loss.
- Mode: PAPER defaults. Live requires explicit confirmation.

## Documentation
See `docs/` for TradingView setup instructions.
