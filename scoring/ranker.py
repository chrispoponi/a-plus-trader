from strategy_engine.models import Scores, Candidate

class ScoringEngine:
    def calculate_scores(self, candidate: Candidate) -> Scores:
        # 1. Baseline Win Rate
        baseline = self._get_baseline(candidate.setup_name)
        
        # 2. Adjustments (Regime, Volatility, Sentiment)
        adjustments = 0.0
        features = candidate.features or {}
        
        # Bonus for Strong Trend Alignment
        if features.get("trend_strength", 0) > 0.8:
            adjustments += 5.0
            
        win_prob = min(max(baseline + adjustments, 0), 100)
        
        # 3. Quality Score (Dynamic)
        # 20 EMA Pullback: Closer to 20EMA = Higher Score
        quality = 70.0 # Base
        dist_pct = features.get("dist_to_20ema", 0.02)
        if dist_pct < 0.01: quality += 15 # Tight pullback
        if features.get("volume_rvol", 1.0) > 1.5: quality += 10 # Volume conviction
        quality = min(quality, 100)
        
        # 4. Risk Score (Dynamic)
        # Lower volatility (ATR) relative to price usually safer for tight stops
        risk_score = 70.0
        if features.get("is_market_leader"): risk_score += 10
        if features.get("sector_strength"): risk_score += 10
        # Check Stop distance? 
        risk_score = min(risk_score, 100)
        
        # 5. Overall Rank
        overall = (win_prob * 0.5) + (quality * 0.3) + (risk_score * 0.2)
        
        return Scores(
            win_probability_estimate=win_prob,
            quality_score=quality,
            risk_score=risk_score,
            overall_rank_score=overall,
            baseline_win_rate=baseline,
            adjustments=adjustments
        )

    def _get_baseline(self, setup_name: str) -> float:
        # High probability baselines
        defaults = {
            "EMA 20 Pullback": 62.0,
            "EMA 20 Trend Pullback": 68.0, 
            "Breakout": 60.0,
            "VWAP Reclaim": 58.0
        }
        return defaults.get(setup_name, 50.0)

ranker = ScoringEngine()
