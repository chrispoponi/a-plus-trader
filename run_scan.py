import asyncio
from configs.settings import settings
from strategy_engine.scanner_service import scanner
from strategy_engine.models import Section

async def main():
    print(f"=== A+ TRADE SYSTEM ARCHITECT ({settings.TRADING_MODE.value}) ===\n")
    print(f"Risk Config: Max Risk {settings.MAX_RISK_PER_TRADE_PERCENT}% (Core {settings.CORE_RISK_PER_TRADE_PERCENT}%)")
    print(f"Max Daily Loss: {settings.MAX_DAILY_LOSS_PERCENT}%")
    
    # Run Scanner Service (orchestrates all 3 engines)
    results = await scanner.run_scan()
    
    # Output Report
    for section_name, candidates in results.items():
        if not candidates:
            continue
            
        print(f"\n>>> {section_name} <<<")
        for c in candidates:
            # Swing Specifics (Core vs Standard)
            sizing_tag = ""
            if section_name == Section.SWING.value:
                if c.trade_plan.is_core_trade:
                    sizing_tag = "[CORE POSITION - 1.25% RISK]"
                else:
                    sizing_tag = "[Standard - 0.75% Risk]"
            
            print(f"SYMBOL: {c.symbol} ({c.direction}) {sizing_tag}")
            print(f"Setup: {c.setup_name} | Score: {c.scores.overall_rank_score:.0f}/100")
            print(f"Thesis: {c.thesis}")
            
            # Trade Plan
            tp = c.trade_plan
            print(f"PLAN: Entry ${tp.entry} | Stop ${tp.stop_loss} ({tp.stop_type}) | Target ${tp.take_profit}")
            
            # Options Specifics
            if c.options_details:
                opt = c.options_details
                print(f"OPTIONS: {opt.strategy_type} | POP: {opt.pop_estimate}% | Max Loss: ${opt.max_loss:.0f}")
                print(f"Strikes: {opt.strikes} | Exp: {opt.expiration_date}")
            
            print("-" * 50)

    # Check for empty run
    total_cands = sum(len(x) for x in results.values())
    if total_cands == 0:
        print("\nNO TRADES TODAY. No candidates met the A+ criteria.")

if __name__ == "__main__":
    asyncio.run(main())
