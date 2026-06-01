# TAA Backtesting & Calibration Framework
## Rimac Group — Institutional TAA Signal System

**Version 1.0 · June 2026**  
**Prepared for:** Investment Committee  
**Classification:** Internal / Confidential  

---

## Table of Contents

1. [Purpose & Guiding Principles](#1-purpose--guiding-principles)
2. [Scope](#2-scope)
3. [Data Architecture for Backtesting](#3-data-architecture-for-backtesting)
4. [Point-in-Time Signal Reconstruction](#4-point-in-time-signal-reconstruction)
5. [Backtesting Engine](#5-backtesting-engine)
6. [Performance Measurement Framework](#6-performance-measurement-framework)
7. [Calibration Framework](#7-calibration-framework)
8. [Robustness & Stress Testing](#8-robustness--stress-testing)
9. [IC Presentation Layer](#9-ic-presentation-layer)
10. [Implementation Roadmap](#10-implementation-roadmap)
11. [Literature References](#11-literature-references)

---

## 1. Purpose & Guiding Principles

### 1.1 Why a Formal Backtesting Framework?

A TAA system generates value only if its signals have statistically robust predictive power over the relevant investment horizon. However, the academic literature on systematic strategies consistently demonstrates that most backtests **overstate** future performance — not through fraud but through a well-documented set of structural biases (Harvey, Liu & Zhu, 2016; Bailey et al., 2014; López de Prado, 2018).

This framework is designed to produce a backtesting and calibration process that is:

- **Economically grounded**: every tested parameter has a prior rooted in finance theory, not data mining
- **Statistically rigorous**: multiple testing corrections, walk-forward validation, and out-of-sample holdout prevent p-hacking
- **Operationally realistic**: T+2 execution lag, monthly rebalancing, and explicit transaction costs reflect the insurance mandate
- **IC-credible**: results are presented at both the signal/pillar level and the portfolio P&L level, enabling the committee to interrogate value-add at every layer

### 1.2 Guiding Principles

| Principle | Operationalisation |
|---|---|
| **No look-ahead** | All signals computed only from data available at the decision date (T). Returns evaluated from T+2 onwards. |
| **Economic prior first** | Parameters are tested within ranges derived from the literature. No unconstrained grid search. |
| **Statistical conservatism** | Report Newey-West t-statistics (lag=12) for all IR estimates. Require t > 2.0 for individual signals, t > 1.5 for composite. |
| **Robustness over optimality** | Prefer parameter sets that perform stably across both expanding and rolling windows. A parameter that improves IS IR by 0.05 but halves OOS IR is rejected. |
| **Solvency II alignment** | All risk metrics (TE, VaR, drawdown) framed in terms that map to the insurance solvency capital requirement (SCR) framework. |

---

## 2. Scope

### 2.1 Asset Class Universe

| Key | Benchmark Return Index | Source in System |
|---|---|---|
| `lt_treasuries` | Bloomberg US Long Treasury TR (`LT03TRUU`) | `lt03_price` (H4) |
| `lt_us_corp` | Bloomberg US Long Corp TR (`I13282US`) | `i132_price` (H4) |
| `lt_em_fi` | Bloomberg EM Sovereign TR (`BSGVTRUU`) | `bsgv_price` (H4) |
| `us_equity` | S&P 500 Total Return (`SPXT`) | `sp500_tr` (H4) |
| `dm_equity` | MSCI EAFE Net TR (`NDDUEAFE`) | `eafe_tr` (H4) |
| `em_equity` | MSCI EM Net TR (`NDUEEGF`) | `msci_em_tr` (H4) |

> **Action required (pre-backtest):** Confirm all six TR series are populated in `Dashboard_TAA_Inputs.xlsx` from at least **2013-01-01**. For any index with gaps before 2013, construct a proxy return from the OAS/yield data already in the system (e.g., duration-weighted yield carry + capital gain for FI). Document any proxy in `docs/data_quality.md`.

### 2.2 Portfolio Universe

All four live portfolios are backtested simultaneously:

| Portfolio | TE Budget | SAA: LT-TSY / LT-CORP / LT-EM / US-EQ / DM / EM |
|---|---|---|
| IGCON_USD | 50 bps | 0% / 0% / 30% / 19.2% / 7.5% / 3.3% |
| IGMOD_USD | 75 bps | 0% / 0% / 25% / 32.0% / 12.5% / 5.5% |
| IGDIN_USD | 100 bps | 0% / 0% / 15% / 44.8% / 17.5% / 7.7% |
| IGEQUS_USD | 125 bps | 0% / 0% / 0% / 95.0% / 0% / 0% |

The SAA portfolio at each rebalance date serves as the **zero-tilt benchmark**. TAA alpha = (SAA + tilt) return minus SAA return.

### 2.3 Backtest Period

| Parameter | Value | Rationale |
|---|---|---|
| Signal start | 2013-02-01 (`MIN_DATE_FOR_SIGNALS`) | EWMA 756-day warm-up from 2010-12-31 |
| Backtest start | **2014-01-31** | Adds 12 months buffer after signal floor; first full year of signal history available |
| Backtest end | Current (rolling, live update) | |
| Effective history | ~12.3 years (Jan 2014 – May 2026) | Covers 3 distinct rate regimes |
| Minimum IS window | 3 years (36 months) | Required before first walk-forward step |
| Holdout (fixed OOS) | **2023-01-01 – present** | Last ~3.5 years reserved; never used for calibration |

### 2.4 Parameters In Scope for Calibration

| Parameter | Current Value | Calibration Range | Literature Prior |
|---|---|---|---|
| Pillar weights F/M/S/V | AC-specific | ±50% of current; sum-to-1 constrained | Equal weight is competitive (DeMiguel et al., 2009) |
| Conviction threshold — mid | ±0.75 | [0.50, 1.00] | No strong prior; sensitivity test |
| Conviction threshold — high | ±1.50 | [1.00, 2.00] | 1.5σ is conventional IC boundary |
| ALPHA_ABS (abs/rel blend) | 0.35 | [0.25, 0.50] | Wang & Kochard (2012) validate 0.35 |
| EWMA span (daily signals) | 756 days | [504, 1008] (2Y–4Y) | Momentum: 12M optimal (Jegadeesh & Titman, 1993) |
| Rolling window (valuation) | 2520 days | [1260, 3780] (5Y–15Y) | Slow mean-reversion in valuation (Asness et al., 2013) |
| Pillar agreement threshold | 0.25σ | [0.10, 0.50] | No prior; robustness test only |

> **Design rule:** No parameter is calibrated in isolation. The optimizer runs over the **joint** parameter space with the objective function defined in Section 7.3. Individual parameter grids are then used for sensitivity analysis around the optimal joint solution.

---

## 3. Data Architecture for Backtesting

### 3.1 Data Flow in Backtest Mode

```
Dashboard_TAA_Inputs.xlsx  (historical, point-in-time)
         |
   [Expand to full daily panel]
         |
   Point-in-time signal engine  (Section 4)
   — re-runs SignalEngine at each monthly decision date
   — no future data bleeds into z-score computation
         |
   Monthly decision dates  (last business day of each month)
         |
   Tilt computation (scoring.py logic, with candidate parameters)
         |
   Portfolio overlay  (SAA + tilt, force_zero_sum)
         |
   T+2 execution  (weights effective two business days later)
         |
   Monthly returns (from AC return indices)
         |
   Performance metrics, attribution, calibration objective
```

### 3.2 Look-Ahead Bias Prevention Checklist

| Risk | Mitigation |
|---|---|
| EWMA/rolling z-scores use future data | All z-scores computed using only data up to decision date T |
| Pillar weights from full-history optimisation | Walk-forward split: weights calibrated on IS, evaluated on OOS only |
| Cross-sectional z standardisation uses future ACs | Z_relative computed from same-date cross-section only |
| Conviction thresholds tuned on full sample | Grid search runs only on IS window; thresholds frozen for OOS |
| Return index availability | Confirm all indices are genuinely available (not revised) from inception |
| GDP/EPS revisions | Bloomberg consensus is as-of — confirm no backdating in provider delivery |

### 3.3 Regime Calendar

Pre-define the following macro regimes for conditional analysis (Section 8.3). These are fixed ex-ante and are **not** optimised:

| Regime | Period(s) | Definition |
|---|---|---|
| **Post-GFC expansion** | Jan 2014 – Dec 2019 | NBER expansion, low volatility, QE |
| **COVID shock** | Mar 2020 – May 2020 | VIX > 60; crisis override period |
| **COVID recovery** | Jun 2020 – Dec 2021 | Fiscal stimulus, risk-on |
| **Rate hike cycle** | Jan 2022 – Dec 2023 | Fed +525 bps; FI drawdown, equity stress |
| **Post-hike normalisation** | Jan 2024 – present | Rate plateau, soft landing debate |

---

## 4. Point-in-Time Signal Reconstruction

### 4.1 The Look-Ahead Problem in TAA Backtests

The most common source of inflated backtest performance in factor-based TAA is **in-sample z-score contamination**: when a z-score is computed over the full time series and then "evaluated" at historical dates, the score at time T implicitly contains information from T+1 to T_end. This is especially severe for EWMA transforms, where long tails in the weight function mean the latest observations have disproportionate influence.

**Our solution:** the signal engine is called at each monthly decision date T using only the slice `data[:T]` of every input series. This is the standard "expanding signal" approach (see López de Prado, 2018, Chapter 12).

### 4.2 Implementation Architecture

```python
# Pseudocode — point-in-time signal engine
decision_dates = monthly_business_end_dates(start="2014-01-31", end=TODAY)

for T in decision_dates:
    # Slice all inputs at T
    inputs_at_T = {sheet: df.loc[:T] for sheet, df in all_inputs.items()}
    
    # Re-run signal engine (EWMA, rolling z, percentile — all computed on slice)
    signals_at_T = SignalEngine(inputs_at_T).load_all()
    
    # Pillar scores
    pillar_scores_at_T = build_all_pillars(signals_at_T, signal_mapping)
    
    # Scoring (using candidate parameters θ)
    scorecard_at_T = score_snapshot(pillar_scores_at_T, params=θ)
    
    # Tilts (force_zero_sum)
    tilts_at_T = apply_portfolio_constraints(scorecard_at_T, portfolios)
    
    # Store
    backtest_tilts[T] = tilts_at_T
```

### 4.3 Computational Efficiency

Running the full signal engine 150+ times (one per monthly date over 12.3 years) is feasible but non-trivial. Optimisations:

- **Vectorised slice**: pass a view `df.iloc[:idx]` rather than copying — O(1) memory overhead
- **Parallelise across calibration candidates**: `joblib.Parallel` over the parameter grid, each calling the full PIT engine independently
- **Caching of raw series**: load `Dashboard_TAA_Inputs.xlsx` once; cache the DataFrame dict; only re-slice per date
- **Estimated runtime**: ~150 dates × ~0.5s per signal engine call = **~75s for one parameter set**. With a grid of ~500 parameter combinations × 2 (expanding/rolling) = ~21 hours total. Plan accordingly (overnight run, or restrict grid).

---

## 5. Backtesting Engine

### 5.1 Rebalancing Mechanics

| Parameter | Value |
|---|---|
| Decision date | Last business day of month T |
| Execution date | T + 2 business days |
| Return window | [T+2, T'+2) where T' = next decision date |
| Rebalancing | Full portfolio rebalance to SAA + tilt at each date |

### 5.2 Portfolio Return Computation

At each execution date t_exec:

```
w_taa(t)  = w_saa + tilt(T)          [force_zero_sum, no shorts]
w_saa(t)  = static SAA weights        [per portfolio]

R_portfolio_taa(t)  = Σ_ac  w_taa_ac(t) × r_ac(t)
R_portfolio_saa(t)  = Σ_ac  w_saa_ac(t) × r_ac(t)

α(t) = R_portfolio_taa(t) − R_portfolio_saa(t)   [active return, monthly]
```

where `r_ac(t)` = total return of the AC benchmark index in month t.

### 5.3 Transaction Cost Model

**Model:** Flat 5 bps per trade (one-way) on changed weights.

```
TC(t) = 5 bps × Σ_ac |w_taa_ac(t) − w_taa_ac(t−1)|
```

Transaction costs are deducted from the active return `α(t)` at execution. This is a conservative flat rate; the sensitivity to TC is tested explicitly in Section 8.1.

**Breakeven cost analysis:** Report the TC level at which TAA IR equals zero. This gives the IC a direct read on the cost tolerance of the strategy.

### 5.4 SAA Benchmark Construction

The SAA benchmark is held at **fixed weights** between rebalance dates (no drift correction). This is standard for TAA attribution because it isolates the value of active tilts from passive weight drift. At each month-end, the SAA is reset to target weights (as if a structural rebalance occurred), ensuring the active return reflects only the tactical overlay.

> **Important nuance for insurance:** Solvency II portfolios may have regulatory rebalancing requirements. The backtest assumes the SAA is the "approved internal model" benchmark. Any constraints specific to the SCR calculation are noted as adjustments to the reported IR rather than embedded in the backtest.

### 5.5 Handling the IGEQUS Portfolio

IGEQUS is 95% US Equity with 5% MM as absorber. Because one AC dominates, the TAA tilt space is essentially one-dimensional (US equity tilt). The backtest for IGEQUS should separately report:

- **Raw IC-level IR**: across all 6 ACs
- **Effective IR on IGEQUS**: dominated by the US equity signal quality

This is expected behaviour, not a failure mode.

---

## 6. Performance Measurement Framework

### 6.1 Primary Metric — Information Ratio vs SAA

```
IR = mean(α) / std(α) × √12         [annualised, monthly α series]
```

Standard error of IR (Newey-West, 12 lags):

```
SE(IR) = NW_HAC_std(α) / std(α) × √12
t-stat = IR / SE(IR)
```

**Acceptance criterion (full backtest period, net of TC):**
- IC presentation minimum: IR > 0.30, t-stat > 1.5
- Signal inclusion minimum: individual AC IR > 0.20, t-stat > 1.2
- Calibrated parameter set minimum: OOS IR > 0.25 (cannot be pre-specified; monitored live)

These thresholds are conservative relative to the literature. Harvey et al. (2016) recommend t > 3.0 for newly discovered factors, but for a model calibrated with economic priors (not data-mined), t > 1.5 is defensible for a 12-year backtest.

### 6.2 Full Metric Suite

#### 6.2.1 Return & Risk

| Metric | Definition | Frequency |
|---|---|---|
| Active return (net) | Mean monthly α after TC × 12 | Annual |
| Tracking error (ex-post) | Std(monthly α) × √12 | Annual |
| Information Ratio | Active return / ex-post TE | Annual |
| Hit rate | % months α > 0 | Monthly |
| Win/loss ratio | Mean(α | α>0) / |Mean(α | α<0)| | Annual |

#### 6.2.2 Drawdown & Risk Management

| Metric | Definition | IC Relevance |
|---|---|---|
| Max active drawdown | Peak-to-trough of cumulative α | Solvency II tail risk |
| Max consecutive monthly losses | Longest run of negative α | Mandate resilience |
| Active VaR (95%) | 5th percentile of monthly α | SCR boundary |
| Active CVaR (95%) | Mean of worst 5% monthly α | Tail loss beyond VaR |
| TE budget utilisation | Realised TE / target TE | Mandate monitoring |

#### 6.2.3 Directional Accuracy (Hit Rate by AC)

For each AC independently, compute:
- **Directional hit rate**: % months where sign(tilt) = sign(AC active return)
- **Conditional IR**: IR conditional on a non-zero tilt being in place
- **Tilt frequency**: % months with |tilt| > threshold (calibrated separately)

A signal that is directionally correct only 50% of the time has zero information content (Grinold & Kahn, 2000). We report 95% CI for hit rate using a binomial test.

### 6.3 Attribution — Where Does Alpha Come From?

**Layer 1 — Pillar attribution:**

```
α_pillar_k(t) = contribution of pillar k to α(t)
              = [tilt generated by pillar k alone] × r_active_ac(t)
```

This requires running the scoring engine with only one pillar active at a time. The four pillar-level IRS should roughly sum to the composite IR (with interaction terms).

**Layer 2 — AC attribution (standard Brinson-Hood-Beebower):**

```
α_ac(t) = tilt_ac(t) × r_active_ac(t)
```

Sum across ACs = total portfolio active return (zero-sum constraint guarantees this).

**Layer 3 — Signal attribution (diagnostic only, not calibration target):**

Individual signal contribution to pillar z-score, traced through the weighting chain. This layer is for internal use only — too granular for IC consumption.

### 6.4 The Fundamental Law Check

Per Grinold & Kahn (2000):

```
IR ≈ IC × √BR × TC_coeff
```

Where:
- **IC** = Information Coefficient = correlation between TAA signal and subsequent AC return
- **BR** = Breadth = number of independent bets per year ≈ 6 ACs × 12 months = 72
- **TC_coeff** = transfer coefficient (penalty for constraints; our force_zero_sum reduces this from 1.0)

For IR = 0.40 and BR = 72: implied IC = 0.40 / √72 ≈ 0.047. This is a **very modest** signal quality requirement — consistent with systematic macro signals over monthly horizons. Report the realised IC alongside the FL check to show the model operates in a plausible regime.

---

## 7. Calibration Framework

### 7.1 Design Philosophy

The calibration framework follows a **prior-then-data** approach:

1. Define the parameter space from economic theory and literature (priors)
2. Test within that constrained space using walk-forward validation
3. Select the **most robust** parameter set, not the one with highest IS IR
4. Validate on the held-out OOS period (Section 2.3)
5. Report IS and OOS metrics side by side — a large IS/OOS divergence is a red flag

This mirrors the approach recommended by López de Prado (2018, Chapter 11) for systematic strategies.

### 7.2 Walk-Forward Methodology

Both variants are implemented and results are compared for consistency:

#### Variant A — Expanding Window

```
IS window grows from 36M minimum; OOS = next 12M

Step 1: IS=[Jan2014, Dec2016], OOS=[Jan2017, Dec2017]  → optimal θ* → OOS performance
Step 2: IS=[Jan2014, Dec2017], OOS=[Jan2018, Dec2018]  → optimal θ* → OOS performance
...
Step N: IS=[Jan2014, Dec2024], OOS=[Jan2025, present]  → optimal θ* → OOS performance
```

**Advantage:** More stable estimates as history grows; reflects what the IC would have known at each point.

#### Variant B — Rolling Window (5-Year Fixed)

```
IS window = fixed 5 years (60 months); OOS = next 12M

Step 1: IS=[Jan2014, Dec2018], OOS=[Jan2019, Dec2019]  → optimal θ* → OOS performance
Step 2: IS=[Jan2015, Dec2019], OOS=[Jan2020, Dec2020]  → optimal θ* → OOS performance
...
```

**Advantage:** Adapts to regime shifts faster; more relevant for detecting whether the model has broken.

#### Stability Criterion

Parameters are considered **robust** if:
- The optimal θ* is the same (or within the top quartile) in ≥ 70% of expanding steps
- The OOS IR degradation (IS IR minus OOS IR) < 0.20 on average across steps
- The expanding and rolling windows select the same θ* in ≥ 60% of steps

Where expanding and rolling diverge materially, flag for IC discussion — it indicates a regime-sensitivity that requires qualitative judgment.

### 7.3 Objective Function

**Primary objective:** Net IR, annualised, Newey-West adjusted, over the IS window.

```
L(θ) = IR_NW(θ, IS_window)  [maximise]
```

Subject to:
1. All parameters within literature-prior ranges (Section 2.4)
2. Pillar weights sum to 1.0 per AC
3. Net active TE ≤ 1.25 × target TE budget (per portfolio) in IS period
4. No AC tilt > 2 × MAX_TILT_PCT at any point (constraint from portfolio mandate)

**Secondary constraint (robustness filter):** Retain only parameter sets where:
- IS IR degradation from IS to OOS < 0.20
- Hit rate (IS) > 52%

### 7.4 Parameter Grid — Recommended Structure

To manage the computational budget (Section 4.3), use a **two-stage grid**:

**Stage 1 — Coarse grid (full space, expanding window only):**

| Parameter | Grid points | Step |
|---|---|---|
| ALPHA_ABS | {0.25, 0.30, 0.35, 0.40, 0.45, 0.50} | 0.05 |
| Conviction mid threshold | {0.50, 0.65, 0.75, 0.90, 1.00} | 0.15 |
| Conviction high threshold | {1.00, 1.25, 1.50, 1.75, 2.00} | 0.25 |
| EWMA span | {504, 630, 756, 882, 1008} days | 126d |
| Pillar weights | Equal / Current / F-heavy / M-heavy / V-heavy | 5 sets |

Total Stage 1 combinations: 6 × 5 × 5 × 5 × 5 = **3,750** (feasible: ~78 hours → run on weekend)

**Stage 2 — Fine grid (top 5% of Stage 1 candidates, both window variants):**

Narrow each parameter to ±1 step around the Stage 1 optimum. Approximately 100–200 combinations. Run both expanding and rolling variants. Report stability.

### 7.5 Anti-Overfitting Guardrails

**Rule 1 — Deflated Sharpe Ratio (Bailey & López de Prado, 2012)**

Correct the IR for the number of trials tested:

```
DSR = SR × [1 - γ × log(N) / √T]
```

Where N = number of parameter combinations tested, T = number of months. Report DSR alongside raw IR. If DSR < 0.20, the result is statistically fragile.

**Rule 2 — Probability of Backtest Overfitting (Bailey et al., 2014)**

Compute PBO using the combinatorial cross-validation approach: split the backtest period into N_s sub-periods, compute relative rank of the optimal strategy in each sub-period OOS test. If the optimal IS strategy ranks below median OOS in > 50% of splits, overfitting is confirmed.

**Rule 3 — Minimum Description Length prior**

Prefer simpler parameter sets (fewer non-equal pillar weights, fewer active signals) where IR is within 0.05 of the complex optimum. This implements the parsimony principle recommended in Ilmanen (2011, Chapter 1).

**Rule 4 — Economic veto**

Any parameter set that is mathematically optimal but economically implausible (e.g., negative weight on Fundamentals for all ACs, or conviction threshold of 0.50σ implying near-continuous active positions) is rejected regardless of IR. The investment team retains veto rights.

---

## 8. Robustness & Stress Testing

### 8.1 Parameter Sensitivity Analysis

Around the calibrated optimum θ*, vary each parameter independently ±20% and report the impact on OOS IR. Present as a **tornado chart** for the IC:

```
          ΔIR from optimal (OOS, ±20% parameter perturbation)
ALPHA_ABS          ████████░░░░░░░░  [most sensitive]
EWMA span          ████░░░░░░░░░░░░
Conv. mid thresh   ███░░░░░░░░░░░░░
Conv. high thresh  ██░░░░░░░░░░░░░░
Pillar weights     █░░░░░░░░░░░░░░░  [least sensitive — good]
```

A strategy where IR is insensitive to moderate parameter perturbation is **more credible** than one that requires precise calibration. Report the coefficient of variation of IR across the top-10 parameter sets as a robustness score.

### 8.2 Transaction Cost Sensitivity

Report IR vs. TC assumption across: 0, 3, 5, 8, 10, 15, 20 bps. Identify the **breakeven TC** where IR → 0. Present as a sensitivity table for the IC. The insurance mandate implies TC ≤ 10 bps for liquid equity ETFs and ≤ 5 bps for government FI — confirm the strategy remains IR-positive at these levels.

### 8.3 Regime-Conditional Performance

Split the backtest into the pre-defined regime calendar (Section 3.3) and report the metric suite per regime. Frame results around three IC questions:

1. **"Does the model protect capital during crises?"** → Active return during COVID shock (Mar–May 2020) and rate hike onset (Q1 2022). The crisis override (VIX + MOVE > 80th pctile → zero tilts) should show its value here.

2. **"Does the model add value in normal environments?"** → IR during Post-GFC expansion and post-hike normalisation.

3. **"Does the model handle rate regimes?"** → FI-pillar IR in the rate hike cycle (2022–2023) is the hardest test for the LT Treasuries and LT Corp signals.

Regime-conditional IR table format for IC:

| Regime | Period | Months | IR (net) | Hit Rate | Max DD (α) |
|---|---|---|---|---|---|
| Post-GFC expansion | 2014–2019 | 72 | ? | ? | ? |
| COVID shock | Mar–May 2020 | 3 | ? | ? | ? |
| COVID recovery | Jun 2020 – Dec 2021 | 19 | ? | ? | ? |
| Rate hike cycle | 2022–2023 | 24 | ? | ? | ? |
| Post-hike normalisation | 2024–present | 17 | ? | ? | ? |
| **Full period** | 2014–present | **~148** | **?** | **?** | **?** |

### 8.4 Signal Decay Analysis

For each pillar, measure the predictive power of the TAA signal at different forward horizons:

```
IC(h) = corr(signal_t, r_active_ac(t:t+h))  for h = 1, 3, 6, 12 months
```

Plot IC(h) as a decay curve per pillar per AC. Signals with rapid decay (IC near zero by h=3M) should not be used on a 12M forward basis. This analysis validates that the **monthly rebalancing frequency** is appropriate for each pillar's information decay rate.

Expected findings from the literature:
- Momentum signals: fast decay (IC drops sharply after 1M for equity; 3M for FI)
- Fundamental signals: slow decay (IC meaningful at 6–12M horizon)
- Valuation signals: very slow decay (IC meaningful only at 12M+; noisy at 1M)
- Sentiment signals: mixed (VIX contrarian: fast; AAII: medium)

### 8.5 Signal Correlation & Independence Test

The Fundamental Law of Active Management requires **independent** bets. If signals across ACs are highly correlated, the effective breadth (BR) is lower than the nominal 72 bets/year. Compute:

```
Corr_matrix(tilts) = correlation of monthly tilt time series across all AC pairs
```

If pairwise correlations are systematically > 0.60, report effective breadth:

```
BR_eff = n / (1 + (n-1) × ρ_avg)   [Qian & Hua, 2004]
```

And adjust the FL check accordingly. A low BR_eff implies the model is essentially making one macro call, not six independent ones.

---

## 9. IC Presentation Layer

### 9.1 Required Exhibits

The following exhibits are mandatory for the IC presentation:

#### Exhibit 1 — Cumulative Active Return Chart
- Y-axis: cumulative TAA active return (gross and net of TC)
- Superimpose: SAA passive flat line at zero
- Mark crisis periods in grey (COVID, rate hike onset)
- Four separate lines for four portfolios (or one representative, e.g., IGMOD)

#### Exhibit 2 — IR Summary Table
| | Full Period | IS (2014–2022) | Holdout OOS (2023–present) |
|---|---|---|---|
| IR (gross) | | | |
| IR (net, 5 bps TC) | | | |
| Hit rate | | | |
| Max active drawdown | | | |
| TE utilisation (avg) | | | |

#### Exhibit 3 — Pillar Attribution Chart
- Stacked bar: annual active return decomposed by pillar (F, M, S, V)
- Shows which pillar drove value and in which year
- Expected: M and V should dominate; F is slower

#### Exhibit 4 — Regime Performance Table (Section 8.3)

#### Exhibit 5 — Parameter Stability Chart (Walk-Forward)
- X-axis: calibration date (each step of walk-forward)
- Y-axis: optimal parameter value
- Shows whether the calibrated parameters are stable over time or jump around
- Stable parameters = robust model; jumping parameters = model is fragile

#### Exhibit 6 — Transaction Cost Sensitivity Table

#### Exhibit 7 — Calibrated Parameter Set vs Intuitive Prior
| Parameter | Economic Prior | Calibrated Value | Change | Verdict |
|---|---|---|---|---|
| ALPHA_ABS | 0.35 (W&K 2012) | ? | ? | Confirm / adjust |
| Conv. mid threshold | 0.75 | ? | ? | Confirm / adjust |
| Conv. high threshold | 1.50 | ? | ? | Confirm / adjust |
| EWMA span | 756 days | ? | ? | Confirm / adjust |
| Pillar weights | AC-specific | ? | ? | Confirm / adjust |

### 9.2 Narrative Structure for IC

Frame the presentation in three acts:

**Act 1 — Validation ("Does the model work?")**
Lead with full-period IR and hit rate. State that the model adds meaningful active return with controlled TE. Reference Brinson et al. (1986) to frame why even modest IR on a TE-constrained strategy has significant portfolio impact.

**Act 2 — Calibration ("Are the parameters right?")**
Show that the walk-forward calibrated parameters are close to the economic priors. A result where the data largely confirms the intuitive parameter choices is the best outcome: it means the priors were good and the model is not being fit to noise.

**Act 3 — Robustness ("Will this hold going forward?")**
Show regime analysis, OOS holdout performance, and parameter stability. Emphasise that robustness — not maximum IS IR — is the design objective. The IC should feel that the model's behaviour is understandable and predictable.

### 9.3 Red Flags to Monitor Ongoing

| Flag | Threshold | Action |
|---|---|---|
| OOS IR deterioration | IR drops > 0.30 vs last calibration | Trigger re-calibration review |
| Hit rate below 50% for 12 consecutive months | 12M rolling hit rate < 50% | Pillar-by-pillar diagnostic |
| TE utilisation > 150% of target | Avg |tilt| > 1.5 × MAX_TILT_PCT | Review conviction mapping |
| Single pillar dominates > 80% of active return | | Check for data or signal error |
| IS/OOS divergence > 0.25 IR | | Overfitting risk; freeze parameters |

---

## 10. Implementation Roadmap

### Phase 1 — Data Infrastructure (Weeks 1–2)

| Task | Owner | Output |
|---|---|---|
| Confirm all 6 TR indices available from 2013 in input file | Quant | Data availability map |
| Construct proxies for any FI gaps | Quant | Updated `data_quality.md` |
| Build monthly decision date calendar (2014–present) | Quant | `backtest_dates.csv` |
| Verify no look-ahead in Bloomberg consensus GDP/EPS delivery | Quant/Data | Sign-off memo |

### Phase 2 — PIT Signal Engine (Weeks 2–4)

| Task | Owner | Output |
|---|---|---|
| Wrap `SignalEngine` for date-sliced call | Quant | `src/backtest_signal_engine.py` |
| Validate: PIT signal at T matches live run at T | Quant | Unit test (29-check extended) |
| Run full PIT signal loop (2014–present), cache results | Quant | `results/backtest_signals.pkl` |

### Phase 3 — Backtesting Engine (Weeks 3–5)

| Task | Owner | Output |
|---|---|---|
| Monthly rebalancing engine (T+2 lag, TC model) | Quant | `src/backtest_engine.py` |
| SAA benchmark return computation | Quant | `results/backtest_saa_returns.csv` |
| Active return series (gross and net) | Quant | `results/backtest_active_returns.csv` |
| All four portfolio views | Quant | `results/backtest_portfolios.xlsx` |

### Phase 4 — Calibration Engine (Weeks 5–8)

| Task | Owner | Output |
|---|---|---|
| Stage 1 coarse grid (expanding window) | Quant | `results/calibration_stage1.csv` |
| Stage 2 fine grid (both expanding + rolling) | Quant | `results/calibration_stage2.csv` |
| Stability analysis (parameter time series) | Quant | `results/calibration_stability.csv` |
| DSR and PBO computation | Quant | `results/overfitting_metrics.csv` |
| OOS holdout evaluation | Quant | Finalised in IC document |

### Phase 5 — IC Document (Weeks 8–10)

| Task | Owner | Output |
|---|---|---|
| All 7 exhibits (Section 9.1) | Quant + PM | `docs/IC_Backtest_Presentation.pptx` |
| Narrative write-up (3-act structure) | PM | |
| Risk committee sign-off | CRO | |
| IC presentation | PM | |

---

## 11. Literature References

All calibration choices, metric definitions, and design decisions in this framework are grounded in the following peer-reviewed and practitioner literature:

### Foundational Asset Allocation

- **Brinson, Hood & Beebower (1986)** — "Determinants of Portfolio Performance", *Financial Analysts Journal*. Asset allocation explains 80–90% of portfolio return variance. Justifies focusing on AC-level tilts rather than security selection.

- **Grinold & Kahn (2000)** — *Active Portfolio Management*, 2nd ed. McGraw-Hill. Source of the Fundamental Law of Active Management (IR = IC × √BR). Defines Information Coefficient and Breadth. Framework for transfer coefficient under constraints.

- **Wang & Kochard (2012)** — "Using a Z-Score Approach to Combine Value and Momentum in Tactical Asset Allocation", *Journal of Portfolio Management*. Direct empirical support for the 35/65 absolute/relative blend (ALPHA_ABS = 0.35) used in the current system.

### Factor Premia (Signal Validation)

- **Asness, Moskowitz & Pedersen (2013)** — "Value and Momentum Everywhere", *Journal of Finance*. Demonstrates that value (valuation pillar) and momentum (momentum pillar) premia are persistent across 8 asset classes and 4 decades. Primary academic backing for the M and V pillars.

- **Koijen, Moskowitz, Pedersen & Vrugt (2018)** — "Carry", *Journal of Financial Economics*. Validates the carry signals embedded in the Fundamentals pillar (OAS carry, yield carry, ERP carry).

- **Jegadeesh & Titman (1993)** — "Returns to Buying Winners and Selling Losers", *Journal of Finance*. Original momentum paper. Validates the 3–12M lookback in `price_mom` transform.

- **Chan, Jegadeesh & Lakonishok (1996)** — "Momentum Strategies", *Journal of Finance*. EPS revision momentum is strongest at 3–6M horizon. Validates `eps_rev_us` (40% × 3M + 60% × 6M) construction.

- **Maillard, Roncalli & Teïletche (2010)** — "The Properties of Equally Weighted Risk Contribution Portfolios", *Journal of Portfolio Management*. Hierarchical risk parity rationale; L1 and L2 views are orthogonal in risk space.

### Overfitting & Statistical Validation

- **Harvey, Liu & Zhu (2016)** — "...and the Cross-Section of Expected Returns", *Review of Financial Studies*. Argues that t > 3.0 is required for newly discovered factors due to multiple testing bias. Our framework uses t > 1.5 (lower, because parameters are chosen from economic priors, not data-mined).

- **Bailey, Borwein, López de Prado & Zhu (2014)** — "Pseudo-Mathematics and Financial Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance", *Notices of the AMS*. Source of the Probability of Backtest Overfitting (PBO) metric.

- **Bailey & López de Prado (2012)** — "The Sharpe Ratio Efficient Frontier", *Journal of Risk*. Source of the Deflated Sharpe Ratio (DSR) — corrects SR for number of trials and skewness.

- **López de Prado (2018)** — *Advances in Financial Machine Learning*, Wiley. Chapters 7–12: walk-forward methodology, combinatorial purged cross-validation (CPCV), feature importance for signal selection. Primary methodological reference for the calibration engine.

- **White (2000)** — "A Reality Check for Data Snooping", *Econometrica*. Bootstrapped p-value for the best strategy in a universe, controlling for selection bias. Supplement to DSR/PBO.

### Regime Analysis

- **Ilmanen & Kizer (2012)** — "The Death of Diversification Has Been Greatly Exaggerated", *Journal of Portfolio Management*. Stock-bond correlation across macro regimes (growth/inflation quadrant). Framework for the Section 3.3 regime calendar.

- **Ang & Bekaert (2002)** — "International Asset Allocation with Regime Shifts", *Review of Financial Studies*. Regime-switching in multi-asset allocation; motivates regime-conditional performance reporting.

- **Ilmanen (2011)** — *Expected Returns*, Wiley. Cross-sectional predictability and the parsimony principle. Advocates for fewer, more robust signals over a larger set of marginally significant ones.

### Portfolio Construction Under Constraints

- **Lee (2000)** — "The Mathematics of Excess Return", *Journal of Portfolio Management*. Multi-portfolio TAA: tilts should scale with portfolio risk capacity (TE budget). Validates the TE-proportional tilt scaling in `portfolio.py`.

- **DeMiguel, Garlappi & Uppal (2009)** — "Optimal Versus Naive Diversification", *Review of Financial Studies*. 1/N equal-weight portfolios are competitive with optimised ones in finite samples. Motivates keeping equal pillar weights as the default prior before calibration.

- **Qian & Hua (2004)** — "Active Risk and Information Ratio", *Journal of Investment Management*. Source of the effective breadth formula BR_eff = n / (1 + (n−1) × ρ), correcting FL for signal correlation.

---

*Document version: 1.0 | June 2026 | Rimac Group Investment Management*  
*Contact: juniorjulonventura@gmail.com*  
*Next scheduled review: Post-IC presentation (target August 2026)*
