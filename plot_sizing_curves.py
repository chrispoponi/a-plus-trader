import numpy as np
import matplotlib.pyplot as plt

# --- Conviction-Based Sizing Variants ---

def quadratic_risk(score, base=0.75, baseline=70, cap=2.0):
    # base is percent e.g. 0.75
    ratio = (score / baseline) ** 2
    risk = base * ratio
    return min(risk, cap) # returns percentage e.g. 1.35

def logistic_risk(score, rmin=0.3, rmax=1.5, baseline=70, k=0.1):
    return rmin + (rmax - rmin) / (1 + np.exp(-k * (score - baseline)))

def volatility_adjusted(score, atr_pct=2.5, vol_ref=2.0, confidence=0.9):
    base = quadratic_risk(score)
    vol_adj = vol_ref / atr_pct
    return base * vol_adj * confidence

# --- Generate Curves ---
scores = np.arange(40, 101, 1)
quad_curve = [quadratic_risk(s) for s in scores]
logi_curve = [logistic_risk(s) for s in scores]
vol_curve = [volatility_adjusted(s) for s in scores]

# --- Plot ---
plt.figure(figsize=(10,6))
plt.plot(scores, quad_curve, label='Quadratic (Active Impl)', linewidth=2, color='blue')
plt.plot(scores, logi_curve, label='Logistic (Smoothed)', linewidth=2, color='green')
plt.plot(scores, vol_curve, label='Volatility-Adjusted (Mock)', linestyle='--', linewidth=2, color='orange')

plt.axvline(70, color='gray', linestyle=':', label='Baseline = 70')
plt.axhline(0.75, color='red', linestyle='--', alpha=0.5, label='Base Risk (0.75%)')

plt.title('Conviction-Based Sizing Algorithms Comparison')
plt.xlabel('Trade Score (0-100)')
plt.ylabel('Risk % of Equity')
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig('sizing_curves.png')
print("Graph saved to sizing_curves.png")
