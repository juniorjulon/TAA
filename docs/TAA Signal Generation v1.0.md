# Institutional TAA signal generation for insurance portfolios

**A composite z-score framework combining carry, momentum, valuation, and regime signals—normalized across asset classes and mapped to conviction-based tilts around strategic benchmarks—forms the backbone of modern institutional TAA.** This report provides the complete analytical toolkit: formulas, thresholds, aggregation methods, regime overlays, and a modular Python architecture. The approach draws on Koijen et al. (2018) for carry, Moskowitz et al. (2012) for time-series momentum, Ang & Bekaert (2004) for regime switching, and practitioner frameworks from BlackRock, AQR, MSCI, and Bridgewater. For insurance portfolios specifically, position sizing must respect Solvency II SCR charges and NAIC RBC constraints, typically capping TAA tilts at **±3–5%** per asset class with total tracking error budgets of **50–150bp**.

---

## 1. Z-score normalization turns heterogeneous signals into comparable scores

The foundational operation in any multi-asset TAA system is converting raw signals (PMI levels, credit spreads, dividend yields) measured in incompatible units into standardized z-scores that can be aggregated. Three formulations dominate practice:

**Standard rolling z-score:**
```
z_t = (x_t − μ_rolling) / σ_rolling
```

**Exponentially weighted z-score (EWMA):**
```
μ_t = λ · μ_{t−1} + (1−λ) · x_t
σ²_t = λ · σ²_{t−1} + (1−λ) · (x_t − μ_t)²
z_t = (x_t − μ_t) / σ_t
```

**Robust median/MAD z-score** (for fat-tailed series like credit spreads):
```
z_t = (x_t − median) / (1.4826 × MAD)
```

### Window selection depends on signal type

The choice of lookback window is not one-size-fits-all. Wang & Kochard (2012) in the *Journal of Wealth Management* use long windows for valuation signals and shorter windows for momentum—a principle confirmed across practitioners. **5-year rolling** serves as the default for most signals, capturing roughly one business cycle. **10-year or expanding windows** suit valuation signals (CAPE, credit spread percentiles) that mean-revert slowly; MSCI's Adaptive Multi-Factor framework uses 40 years of factor history for valuation z-scores. **3-year rolling** works best for momentum and sentiment signals that require regime responsiveness.

| Window | Best for | Tradeoff |
|--------|----------|----------|
| 3Y (36 months) | Momentum, sentiment, positioning | More responsive; higher noise |
| 5Y (60 months) | Default for most signals | Balances responsiveness and stability |
| 10Y (120 months) | Valuation, structural indicators | Captures multiple regimes; slow to adapt |
| EWMA (λ = 0.94–0.97) | Production systems needing adaptivity | Smooth regime adaptation; BlackRock BGRI uses this |

**BlackRock's BGRI** explicitly "weighs recent readings more heavily in calculating the average," making it an EWMA z-score. This is arguably the best production choice: it naturally downweights stale regime data without requiring explicit structural break detection. For monthly TAA, **λ = 0.95** gives an effective half-life of ~14 months, meaning data older than 3 years carries less than 5% weight.

### Handling regime breaks and outliers

The post-2021 inflation regime exposed the fragility of fixed rolling windows that span structural breaks. Three approaches address this. First, **Bai-Perron structural break tests** can detect unknown break points in each indicator series; z-scores are then computed only over post-break data. Second, EWMA z-scores handle this naturally by downweighting pre-break observations. Third, a **blended approach** combines windows: `z_composite = 0.5 · z_3Y + 0.3 · z_EWMA + 0.2 · z_expanding`.

For outlier treatment, **winsorize at ±3σ** as default (±2.5σ for fat-tailed series like credit spreads and volatility measures). The Deutsche Bank "Seven Sins of Quantitative Investing" (Luo et al., 2014) recommends percentile-based winsorization at the 1st/99th percentile for non-normal data. The formula is simply: `z_final = clip(z_raw, −3.0, +3.0)`.

---

## 2. Signal aggregation: equal weighting wins, but hierarchical structure matters

The evidence strongly favors simplicity. Asness, Moskowitz & Pedersen (2013) in "Value and Momentum Everywhere" (*Journal of Finance*) use a **50/50 equal-weight blend** of value and momentum across all asset classes, finding the combination produces "a significantly higher Sharpe ratio than either standalone" due to their **negative correlation** (ρ ≈ −0.5 to −0.2). DeMiguel et al. (2009) demonstrated that 1/N equal weighting outperforms optimization-based approaches out-of-sample. AQR's subsequent work explicitly argues that "factor timing is deceptively difficult."

### Hierarchical two-level aggregation

The practical architecture aggregates within-pillar first, then across pillars—preventing a pillar with 10 signals from dominating one with 2:

**Step 1 — Within-pillar:** Average (or ICIR-weight) all signals within each pillar, then re-standardize:
```
S_p = (1/K_p) Σ z_{p,i}     then     Z_p = (S_p − μ(S_p)) / σ(S_p)
```

**Step 2 — Across-pillar:** Weighted average of pillar z-scores:
```
Z_final = Σ W_p · Z_p       then re-standardize
```

A typical insurance TAA pillar structure assigns: **Fundamentals/Macro 20–25%**, **Momentum/Trend 20–25%**, **Valuation 20–25%**, **Positioning/Sentiment 15–20%**, **Carry 15–20%**. MSCI's 2018 Adaptive Multi-Factor Allocation framework uses four pillars (Macro Cycle, Momentum, Valuation, Market Sentiment), equally weighted, and delivered **3.25–4.48% additional active return** over 1986–2018.

### IC-weighted aggregation with shrinkage

For practitioners wanting to go beyond equal weights, the **ICIR-weighted** approach proportions weights to each signal's Information Coefficient–to–Information Ratio:

```
w_i ∝ ICIR_i = mean(IC_i) / std(IC_i)
```

where IC_i = corr(signal_i, forward_returns) estimated over trailing 36–60 months. Typical good ICs range **0.02–0.08**; above 0.15 raises overfitting concerns. To combat estimation error, apply **Bayesian shrinkage** toward equal weights: `w_shrunk = (1−δ) · w_ICIR + δ · (1/K)`, with δ = 0.5 as a robust default. This connects to Grinold's Fundamental Law: **IR ≈ IC × √BR × TC**, where TC (transfer coefficient) typically runs 0.3–0.7 under portfolio constraints.

---

## 3. Carry signals capture the expected return from holding an asset

Koijen, Moskowitz, Pedersen & Vrugt (2018) in "Carry" (*Journal of Financial Economics*) define carry generically as **an asset's expected return assuming its price does not change**—observable ex-ante and model-free. For futures: **Carry = (S_t − F_t) / F_t**. The diversified carry portfolio across all asset classes delivered a Sharpe ratio of approximately **1.1**, uncorrelated with value, momentum, or TSMOM factors.

### Asset-class-specific carry formulas

**Fixed income carry** combines yield pickup and roll-down:
```
Carry_FI = (YTM − r_f) + (−ΔYield_rolldown × Duration)
```
For credit: `Carry_credit = OAS + roll-down along the credit spread curve`. FTSE Russell (2019) shows carry is maximized in the **3–7 year maturity sweet spot** where curve concavity is greatest.

**Equity carry:**
```
Carry_EQ = Dividend Yield − Real Risk-Free Rate
```
Koijen et al. define it as the expected dividend yield minus the risk-free rate for equity index futures.

**EM carry (hard currency):**
```
Carry_EM = EMBI Spread = YTM_EMBI − YTM_UST_matched_maturity
```
The **carry cushion** metric (yield-to-maturity / duration) measures how many basis points of spread widening an investor can absorb—currently around **114bp** for the EMBI at 7.55% yield and 6.6-year duration.

**FX carry:** `Carry_FX = r*_foreign − r_domestic` (the interest rate differential). **Commodity carry:** `Carry = (F_near − F_far) / F_far`, where backwardation signals positive carry. Gorton, Hayashi & Rouwenhorst (2013) show backwardated commodities return **12.2% annualized** versus −3.6% in contango.

All carry signals should be **z-scored within asset class** over a 3–5 year rolling window, then volatility-targeted: `Position = z_carry × (σ_target / σ_realized)`.

---

## 4. Regime detection structures the entire allocation framework

### The PMI 4-quadrant model

The ISM Manufacturing PMI, combined with its direction (3-month smoothed), creates four investable regimes:

| Quadrant | PMI level | Direction | Posture | Equity return (annualized) |
|----------|-----------|-----------|---------|----------------------------|
| Recovery | < 50 | Rising | Risk-on tilt | +15–20% |
| Expansion | > 50 | Rising | Full risk-on | +10–15% |
| Slowdown | > 50 | Falling | Reduce risk | +3–8% |
| Contraction | < 50 | Falling | Risk-off | −5 to −15% |

Direction is determined as `Rising = PMI_t > PMI_{t−3}` using a 3-month moving average to smooth noise.

### Bridgewater's Growth/Inflation 2×2 matrix

Bridgewater's All Weather identifies two primary drivers—**growth** and **inflation** relative to expectations—creating four environments. **Rising Growth + Falling Inflation** ("Goldilocks") favors equities and corporate bonds. **Rising Growth + Rising Inflation** favors commodities, TIPS, and energy. **Falling Growth + Falling Inflation** favors nominal Treasuries and IG credit. **Falling Growth + Rising Inflation** ("stagflation") favors gold and inflation-linked bonds—the worst environment for 60/40 portfolios. Their ALLW ETF (launched 2025 with SSGA) runs ~188% notional leverage across these four quadrants.

### Volatility regime overlays

VIX percentile ranking over a trailing 1–5 year window provides the equity volatility regime:

- **VIX < 25th percentile** (~12–14): Low vol, maintain full tilts, add tail hedges
- **VIX 25th–75th** (~14–20): Normal, standard tilt sizing
- **VIX > 75th** (~20–22): Elevated, reduce tilts by 30%
- **VIX > 90th** (~28+): Crisis, halve all tactical tilts

The **MOVE index** (ICE BofA, long-term average ~103) serves the same function for fixed income volatility. MOVE often leads VIX—the bond market prices systemic risk earlier. When **both VIX and MOVE exceed their 75th percentiles**, force a crisis overlay that halves all tilts regardless of other signals.

### Formal regime-switching models

Ang & Bekaert (2004) in the *Financial Analysts Journal* show that for mixed stock/bond portfolios, regime-switching models add substantial value—investors need **~2–3 cents per dollar** of initial wealth to compensate for ignoring regimes. Their 2-state Markov model identifies normal (moderate returns, low vol) and bear (negative returns, high vol, high correlation) regimes, with expected durations of ~10 quarters and ~4 quarters respectively. For production TAA, **2-state models** are preferred over 3-state for cleaner signals and fewer parameters. Hamilton (1989) Markov switching models, implemented via `statsmodels.tsa.regime_switching.MarkovRegression`, provide the econometric backbone.

---

## 5. Momentum signals exploit persistence across horizons and asset classes

### Time-series vs. cross-sectional momentum

**Jegadeesh & Titman (1993)** established cross-sectional momentum: rank assets by 12-month return skipping the most recent month (avoiding short-term reversal), long winners, short losers. The **12-1 month formula**:
```
Mom_{12-1} = (P_{t−1} / P_{t−12}) − 1
```

**Moskowitz, Ooi & Pedersen (2012)** introduced time-series momentum (TSMOM), where each asset's own past return predicts its future direction:
```
Position_i = sign(r_{i,t−12:t}) × (σ_target / σ_i,t)
```
Volatility is estimated from **60-day exponentially weighted squared daily returns**. The σ_target of 40% normalizes across assets. Diversified TSMOM earned **1.09% per month** (t-stat 5.40) across 58 liquid futures, unexplained by standard factors.

### Technical momentum signals

**RSI(14)** uses 14-period smoothed up/down moves: overbought > 70, oversold < 30. For TAA, convert to a continuous signal: `Signal = (RSI − 50) / 50`, bounded [−1, +1]. Best used as a **confirmation filter**, not primary signal—RSI can remain overbought for weeks in strong trends.

**Moving average crossovers:** The 50/200-day SMA crossover (golden cross/death cross) generates `Signal = sign(SMA_50 − SMA_200)`. Levine & Pedersen (2016) proved that TSMOM signals are mathematically equivalent to weighted moving average crossovers.

### Combining into a composite and mitigating crash risk

Equal-weight the z-scored components: **12-1 momentum (30%)**, **TSMOM (30%)**, **MA crossover (25%)**, **RSI (15%)**. The critical addition is **constant volatility scaling** (Barroso & Santa-Clara, 2015): `w_t = σ_target / σ_{WML,t−1}`, which scales momentum exposure by inverse lagged volatility. This substantially improves the Sharpe ratio by reducing exposure precisely when crash risk is highest. Daniel & Moskowitz (2016) show momentum crashes are forecastable—they occur in **panic states** following market declines when past losers surge during recoveries.

---

## 6. Conviction mapping and position sizing under insurance constraints

### From z-scores to conviction levels

The composite z-score maps to actionable tilts via threshold-based bucketing:

| Composite |z| | Conviction | Typical TAA tilt | Insurance portfolio tilt |
|-------------|------------|-------------------|--------------------------|
| < 0.5 | Low | ±0.5–1.0% | ±0.5% |
| 0.5–1.0 | Medium | ±1.5–3.0% | ±1.0–2.0% |
| > 1.0 | High | ±3.0–5.0% | ±2.0–3.0% |

The sign of z determines direction. An alternative cross-sectional approach ranks z-scores into quintiles, forcing a distribution of positions and avoiding "all overweight" scenarios.

### Position sizing frameworks

The **Kelly criterion** provides the theoretical maximum: `f* = (μ − r_f) / σ²`, or in matrix form `f* = Σ⁻¹(μ − r_f)`. Full Kelly is far too aggressive for institutional use—drawdowns can exceed 50%. **Half-Kelly** is standard practice, achieving ~75% of Kelly growth rate with substantially reduced drawdowns. For TAA: `Tilt_i = (0.5 × f*_i) × conviction_scalar`, where conviction_scalar = {0.25, 0.50, 1.0} for {Low, Medium, High}.

**Risk parity sizing** equalizes risk contribution: `w_i = (1/σ_i) / Σ(1/σ_j)`. Applied to tilts: `Adjusted_tilt_i = Base_tilt × (σ_avg / σ_i)`. This ensures a 1% equity tilt (vol ~16%) delivers similar risk as a 1% bond tilt (vol ~5%).

### Insurance-specific constraints are binding

**Solvency II** charges **39% SCR for Type 1 equities** (±10% symmetric adjustment) and duration-dependent spread charges (~20% for 10Y BBB). A +3% equity tilt adds ~1.2% to total portfolio SCR. **NAIC RBC** charges 15% for unaffiliated common stock. TAA tilts must be evaluated on a **return-on-capital basis**: expected excess return / incremental SCR. Typical bounds: **±5% maximum deviation per asset class**, **±0.5–1.0 year duration deviation**, **50–150bp total tracking error budget**, and annual transaction cost budget of **20–50bp**.

---

## 7. Relative signals identify cross-asset mispricing

### Equity risk premium drives the equity/bond decision

The ERP — `ERP = (1/Forward_PE) − TIPS_10Y` — is the single most important cross-asset relative signal. Historical average is ~4.0–4.5% (Damodaran). When ERP exceeds its long-term average by 1σ, equities are strongly favored; when ERP approaches zero, bonds are preferred. The **Fed Model** variant (`Fed_Gap = Earnings_Yield − 10Y Treasury`) is widely used but academically disputed—Asness (2003) in "Fight the Fed Model" showed r² of just 0.5% over 1871–2020. Best used as one signal among many.

### Credit relative value: the HY/IG spread ratio

The **HY-to-IG OAS ratio** (FRED: BAMLH0A0HYM2 / BAMLC0A0CM) has a 5-year average of ~3.3×, with a range of 1.67×–4.20×. Ratio > 4.0× signals HY relatively cheap (mean-reversion buy); < 2.5× favors IG. Adjust for duration differences via **OAS-per-unit-duration**: `OAS_per_dur = OAS / Effective_Duration`, which normalizes IG's longer duration (~7–8 years) versus HY's (~4 years).

### Regional rotation and EM vs. DM

**Relative CAPE**: `Z = zscore(CAPE_US / CAPE_EM, 120 months)`; positive z favors EM (US overvalued). **Relative PMI momentum**: `PMI_Mom_A − PMI_Mom_B` where momentum = current PMI minus 3-month trailing average. **Relative earnings revisions**: `ERR = (Upgrades − Downgrades) / Total_Estimates`, 3-month rolling, z-scored cross-sectionally. **Real yield differential** for DM vs. EM fixed income: `Real_Yield_EM − Real_Yield_DM`, risk-adjusted by subtracting sovereign CDS spreads.

---

## 8. Python implementation: a modular, class-based signal pipeline

### Core architecture

The signal system follows a **registry pattern** where each signal inherits from an abstract `BaseSignal` class with `compute_raw()` and `normalize()` methods. Signals self-register into a `SignalRegistry`, enabling `generate_all(data)` to produce every signal in a single pass:

```python
from abc import ABC, abstractmethod
import pandas as pd, numpy as np

def rolling_zscore(s: pd.Series, window: int = 252) -> pd.Series:
    return (s - s.rolling(window).mean()) / s.rolling(window).std()

def ewm_zscore(s: pd.Series, span: int = 252) -> pd.Series:
    return (s - s.ewm(span=span).mean()) / s.ewm(span=span).std()

class BaseSignal(ABC):
    def __init__(self, name: str, lookback: int = 252, z_window: int = 252):
        self.name, self.lookback, self.z_window = name, lookback, z_window

    @abstractmethod
    def compute_raw(self, data: dict) -> pd.Series: ...

    def normalize(self, raw: pd.Series) -> pd.Series:
        return rolling_zscore(raw, self.z_window).clip(-3, 3)

    def generate(self, data: dict) -> dict:
        raw = self.compute_raw(data)
        z = self.normalize(raw)
        return {'name': self.name, 'raw': raw.iloc[-1],
                'z_score': z.iloc[-1], 'series': z}
```

### Signal examples

```python
class ERPSignal(BaseSignal):
    """Equity Risk Premium: earnings yield minus real bond yield."""
    def __init__(self):
        super().__init__('ERP', z_window=120*21)
    def compute_raw(self, data):
        return (1.0 / data['sp500_fwd_pe']) * 100 - data['tips_10y']

class CarryFI(BaseSignal):
    """Fixed income carry: OAS as proxy for credit carry."""
    def __init__(self):
        super().__init__('Carry_FI', z_window=60*21)
    def compute_raw(self, data):
        return data['hy_oas']  # or OAS × spread_duration

class TSMOM(BaseSignal):
    """Time-series momentum: sign of 12-month return, vol-scaled."""
    def __init__(self):
        super().__init__('TSMOM_12M', lookback=252)
    def compute_raw(self, data):
        ret_12m = data['price'].pct_change(252)
        vol = data['price'].pct_change().rolling(60).std() * np.sqrt(252)
        return np.sign(ret_12m) * (0.10 / vol)  # 10% vol target
```

### Regime detection with HMM and Markov switching

```python
from hmmlearn import hmm
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

class HMMRegimeDetector:
    def __init__(self, n_regimes=2):
        self.model = hmm.GaussianHMM(n_components=n_regimes,
                     covariance_type='full', n_iter=100, random_state=42)

    def fit_predict(self, prices: pd.Series) -> pd.Series:
        log_ret = np.log(prices / prices.shift(1)).dropna()
        vol = log_ret.rolling(20).std().dropna()
        X = pd.concat([log_ret, vol], axis=1).dropna().values
        self.model.fit(X)
        states = self.model.predict(X)
        return pd.Series(states, index=prices.index[-len(states):])

# Markov switching via statsmodels
def markov_regime(returns, k_regimes=2):
    mod = MarkovRegression(returns.dropna(), k_regimes=k_regimes,
                           switching_variance=True)
    res = mod.fit()
    return res.smoothed_marginal_probabilities
```

### Hierarchical aggregation engine

```python
class TAACompositeEngine:
    def __init__(self, pillar_config: dict, pillar_weights: dict):
        self.pillar_config = pillar_config   # {'valuation': [sig1, sig2], ...}
        self.pillar_weights = pillar_weights  # {'valuation': 0.25, ...}

    def compute(self, signals: dict) -> float:
        pillar_scores = {}
        for pillar, sig_names in self.pillar_config.items():
            zs = [signals[n]['z_score'] for n in sig_names if n in signals]
            pillar_scores[pillar] = np.mean(zs) if zs else 0.0
        composite = sum(pillar_scores[p] * self.pillar_weights[p]
                        for p in pillar_scores)
        return composite / sum(self.pillar_weights.values())
```

### Key library stack

The production system relies on: **pandas/numpy** for data manipulation; **pandas-datareader** for FRED ingestion (`pdr.DataReader(['BAMLH0A0HYM2','DGS10'], 'fred', start)`); **blpapi/xbbg** for Bloomberg; **yfinance** as a free alternative; **scipy.stats** for z-scores and statistical tests; **statsmodels** for Markov regression and structural breaks; **hmmlearn** for HMM regime detection; **sklearn.mixture.GaussianMixture** for GMM clustering; **cvxpy** for convex portfolio optimization; and **quantstats/empyrical** for performance analytics. Store time series in **Parquet** (via pyarrow) for efficient columnar access, with SQLite for structured signal metadata.

### Backtesting discipline

Critical safeguards: always `.shift(1)` signals before computing portfolio returns to prevent look-ahead bias. Use **walk-forward validation** with expanding training windows, retrained quarterly. Model realistic transaction costs (**5–10bp** one-way for liquid assets, **10–20bp** for insurance portfolio assets). For insurance, additionally model SCR/RBC consumption of each tilt. The breakeven rule: only implement a TAA tilt if `Expected_alpha × holding_period > 2 × round_trip_cost`.

---

## Conclusion: a practical integration roadmap

The most robust institutional TAA system combines conceptual simplicity with disciplined execution. **Use EWMA z-scores** (λ ≈ 0.95 monthly) as the default normalization—they handle regime breaks gracefully and align with BlackRock's BGRI methodology. **Aggregate signals hierarchically** with equal weights across five pillars (Macro, Momentum, Valuation, Carry, Positioning), re-standardizing at each level. The academic evidence from AQR and DeMiguel et al. strongly discourages dynamic signal weighting; if pursued at all, apply heavy shrinkage (δ = 0.5) toward equal weights.

For insurance portfolios, the binding constraint is not signal quality but **position sizing under regulatory capital**. A +3% equity tilt consuming ~1.2% incremental SCR must clear a hurdle rate of roughly 2.4% annualized expected alpha after transaction costs. The practical path is **half-Kelly sizing with fixed-fraction caps**: ±0.5% for low conviction, ±1.5% for medium, ±2.5% for high, with a hard stop at ±5% per asset class and a volatility override that halves all tilts when VIX and MOVE simultaneously exceed their 75th percentiles. This architecture—modular signals, hierarchical aggregation, regime-aware sizing, and capital-constrained tilts—delivers a repeatable, auditable TAA process suitable for insurance investment committees.