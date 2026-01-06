import asyncio
from executor_service.order_executor import executor
from strategy_engine.scanner_service import scanner
from strategy_engine.scanner_service import scanner
from strategy_engine.data_loader import DataLoader
import pandas as pd

data_loader = DataLoader()

async def audit_holdings():
    print("🦅 AUDITING ACTIVE PORTFOLIO STRENGTH...")
    
    if not executor.api:
        print("❌ Alpaca API Not Connected.")
        return

    # 1. Get Positions
    positions = executor.api.list_positions()
    if not positions:
        print("No active positions.")
        return

    audit_data = []

    print(f"Analyzing {len(positions)} symbols...")
    
    for p in positions:
        symbol = p.symbol
        pnl_pct = float(p.unrealized_plpc) * 100
        qty = float(p.qty)
        side = "LONG" if qty > 0 else "SHORT"
        
        # 2. Run Technical Analysis
        # Fetch Data
        data_map = data_loader.fetch_snapshot([symbol])
        
        score = 0
        setup = "No Data"

        if symbol in data_map and 'df' in data_map[symbol]:
            df = data_map[symbol]['df']
            
            # We can use the Ranker or check specific Setups
            # Let's verify if it passes any Swing Setup
            from strategy_engine.swing_setups import SwingStrategyEngine
            
            engine = SwingStrategyEngine()
            cands = engine.scan([symbol], data_map)
            
            if cands:
                # Use the best candidate
                best = cands[0]
                score = best.scores.overall_rank_score
                setup = best.setup_name
            else:
                score = 0
                setup = "No Setup (Weak)"
                
            # Fallback simple trend check for display
            if score == 0:
                  last_price = df['close'].iloc[-1]
                  ema_20 = df['close'].ewm(span=20).mean().iloc[-1]
                  if last_price > ema_20: setup += " (Above EMA)"
                  else: setup += " (Below EMA)"

        audit_data.append({
            "Symbol": symbol,
            "Side": side,
            "PnL %": round(pnl_pct, 2),
            "Tech Score": score,
            "Trend State": setup,
            "Action": "HOLD" if score > 50 else "WEAK"
        })

    # 3. Display
    df_res = pd.DataFrame(audit_data)
    df_res = df_res.sort_values("PnL %", ascending=False)
    
    print("\n🦅 PORTFOLIO SCORECARD:")
    print(df_res.to_markdown(index=False))
    
    # Correlation Check
    # Do high scores correlate with high PnL?
    # (In this context, Score is 'Current Strength', PnL is 'Past Performance')
    print("\n💡 INSIGHT: Symbols with High PnL but Low Score = 'Momentum Fading' (Consider TP)")
    print("💡 INSIGHT: Symbols with Neg PnL and Low Score = 'Broken Thesis' (Consider Cut)")

if __name__ == "__main__":
    asyncio.run(audit_holdings())
