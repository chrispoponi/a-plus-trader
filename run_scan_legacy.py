import asyncio
import requests
from strategy_engine.swing_setups import SwingStrategyEngine
from strategy_engine.breakout_setup import BreakoutEngine
from scoring.ranker import ranker
from signal_router.webhook_generator import generate_webhook_payload
from configs.settings import settings
from strategy_engine.models import Section

async def main():
    print(f"=== A+ TRADER AGENT SCAN ({settings.TRADING_MODE.value}) ===\n")
    
    # 1. Initialize Engines
    swing_engine = SwingStrategyEngine()
    breakout_engine = BreakoutEngine()
    
    # 2. Define Watchlist (In prod, this comes from a data provider or DB)
    symbols = ["AAPL", "TSLA", "NVDA", "SPY", "AMD", "META", "MSFT", "GOOGL"] 
    
    raw_candidates = []
    
    # 3. Run Swing Scan
    print(f"Scanning {len(symbols)} symbols for Swing Setups...")
    swing_results = swing_engine.scan(symbols)
    raw_candidates.extend(swing_results)
    print(f" -> Found {len(swing_results)} candidates.")

    # 4. Run Breakout Scan (Stub)
    # breakout_results = breakout_engine.scan(symbols)
    # raw_candidates.extend(breakout_results)
    
    # 5. Score & Filter
    final_candidates = []
    for cand in raw_candidates:
        # Apply Scoring Engine
        cand.scores = ranker.calculate_scores(cand)
        
        # Filter by Min Win Probability
        if cand.scores.win_probability_estimate >= settings.MIN_WIN_PROBABILITY_ESTIMATE:
            final_candidates.append(cand)
        else:
            print(f"Discarding {cand.symbol}: Score {cand.scores.win_probability_estimate:.1f}% < {settings.MIN_WIN_PROBABILITY_ESTIMATE}%")

    # 6. Sort by Overall Rank
    final_candidates.sort(key=lambda c: c.scores.overall_rank_score, reverse=True)
    
    # 7. Select Top 3
    top_signals = final_candidates[:3]
    
    # 8. Output Report
    for section in [Section.SWING, Section.BREAKOUT, Section.OPTIONS]:
        section_cands = [c for c in final_candidates if c.section == section]
        if not section_cands:
            continue
            
        print(f"\n--- {section.value} ---")
        for c in section_cands:
            print(f"Symbol:   {c.symbol} ({c.direction})")
            print(f"Setup:    {c.setup_name}")
            print(f"Plan:     Entry ${c.trade_plan.entry} | Stop ${c.trade_plan.stop_loss} | Target ${c.trade_plan.take_profit}")
            print(f"Scores:   Win {c.scores.win_probability_estimate:.1f}% | Rank {c.scores.overall_rank_score:.1f}")
            print(f"Thesis:   {c.thesis}")
            print("-" * 40)
    
    print("\n=== TOP 3 SIGNALS TO TRANSMIT ===")
    if not top_signals:
        print("No signals met the criteria.")
    else:
        for sig in top_signals:
            payload = generate_webhook_payload(sig)
            print(f"Broadcasting: {payload.signal_id} ({payload.symbol})")
            
            # Transmit to Local Execution Service
            try:
                # payload.model_dump() is pydantic v2, .dict() is v1. Using safe check.
                json_data = payload.model_dump() if hasattr(payload, 'model_dump') else payload.dict()
                
                # In a real run, we post to the service. 
                # For this CLI tool, we print the curl or just fire it if the service is up.
                # await post_to_service(json_data)
                print(f"Payload ready for {settings.WEBHOOK_TOKEN[:5]}...")
            except Exception as e:
                print(f"Error generating payload: {e}")

if __name__ == "__main__":
    asyncio.run(main())
