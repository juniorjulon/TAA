# TAA Dashboard — Complete Methodology

**System:** Tactical Asset Allocation (TAA) Signal Engine  
**Client:** Rimac Group — Insurance Portfolios  
**Last updated:** May 2026 (v5)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Data Architecture](#2-data-architecture)
3. [Derived / Custom Series](#3-derived--custom-series)
4. [Signal Engine](#4-signal-engine)
5. [Pillar Construction (F / M / S / V)](#5-pillar-construction-f--m--s--v)
6. [Composite Scoring](#6-composite-scoring)
7. [Conviction Mapping](#7-conviction-mapping)
8. [Absolute vs. Relative Views](#8-absolute-vs-relative-views)
9. [Hierarchical Architecture (L1 / L2)](#9-hierarchical-architecture-l1--l2)
10. [Portfolio Construction](#10-portfolio-construction)
11. [Dashboard Generation](#11-dashboard-generation)
12. [Data Quality & Governance](#12-data-quality--governance)
13. [Configuration Reference](#13-configuration-reference)
14. [Weekly Pipeline](#14-weekly-pipeline)
15. [Academic Foundations](#15-academic-foundations)
16. [Data Quality Detail — Per-Signal Reference](#16-data-quality-detail--per-signal-reference)
17. [Excluded Signals & Phase 2 Roadmap](#17-excluded-signals--phase-2-roadmap)

---

## 1. System Overview

The TAA Dashboard generates weekly tactical tilts around Strategic Asset Allocation (SAA) benchmarks for Rimac Group's insurance portfolios. It scores **6 active asset classes** across **4 signal pillars** and maps composite z-scores to conviction-based tilts.

### Design principles

| Principle | Implementation |
|---|---|
| Single source of truth | `config/taa_config.xlsx` for all signals, weights, and mappings |
| Plain-vanilla signals | No exotic data; every signal has a verifiable data source and clear economic rationale |
| Sign lives in mapping | Direction (bullish/bearish) is set exclusively in `SignalMapping`; raw series are never inverted in Python |
| No short positions | Solvency II / insurance mandate: `force_zero_sum = True`, `portfolio_weight.clip(lower=0)` |
| Reproducibility | All outputs time-stamped (`RUN_YYYYMMDD_HHMMSS`); inputs + config version-controlled |

### Active asset class universe (6 ACs)

| Key | Label | Group | Hierarchy |
|---|---|---|---|
| `lt_treasuries` | LT US Treasuries | FI | Child of `lt_fi_aggregate` |
| `lt_us_corp` | LT US Corporate | FI | Child of `lt_fi_aggregate` |
| `lt_em_fi` | LT EM Fixed Income | FI | Child of `lt_fi_aggregate` |
| `us_equity` | US Equity (Broad) | EQ | Standalone L1 |
| `dm_equity` | DM ex-US Equity | EQ | Standalone L1 |
| `em_equity` | Emerging Markets Equity | EQ | Standalone L1 |

> **Note:** Money Market, Short-Term FI, US Growth, and US Value are **not active TAA ACs**. Their underlying data series remain in the system and are used as signals for the 6 active ACs. MM and STFI absorb net tilts from the zero-sum constraint at the portfolio level.

---

## 2. Data Architecture

### 2.1 Primary input file

**`data/Dashboard_TAA_Inputs.xlsx`** — 9 sheets, weekly refresh, all series daily unless noted.

| Sheet | Internal key | Period | Key content |
|---|---|---|---|
| OAS | `oas` | 1999–2026 | oas_bbb, oas_hy, oas_em, oas_latam (ICE BofA, FRED) |
| H4 | `pe`, `yields`, `fi_px` | 2010–2026 | PE ratios, earnings yields, TR price indices (14 indices) |
| H5 | `mkt`, `tsy`, `cds` | 2010–2026 | VIX, MOVE, VSTOXX, SKEW, PCR, DXY, FCI, breakevens, SOFR, Treasury yields, CDX |
| H6 | `sectors` | 2010–2026 | S&P 11 sector PE / EY / TR (12 cols each) |
| H1 | `f1` (part) | 2010–2026 | PMI (ISM, EZ, China mfg+svcs), CESI (US/EZ/CN/Global), GDP forecasts (US/EM/DM/EU 26+27) |
| H2 | `f1` (part) | 2010–2026 | PMI (Japan, UK), CESI (EM, Japan), GDP (Japan, China, LatAm 26+27) |
| H3 | `f3` | 2010–2026 | Forward EPS (US/World/EM/China/Japan/EAFE/LatAm) |
| H7 | `h7` | 2010–2026 | Breakeven 1Y, GDPNow, NFCI, FCI EZ, FCI UK |
| AAII | `aaii` | 1987–2026 | AAII Bull-Bear spread (weekly → daily forward-fill) |

### 2.2 Forward-fill rules

| Series type | Max ffill | Reason |
|---|---|---|
| Daily price/rate | 5 days | Weekends + 1 holiday |
| Monthly (PMI, CESI, GDP) | 31 days | One monthly release cycle |

### 2.3 GDP column naming convention

All GDP forecast columns use a **year-suffix**: `gdp_forecast_{region}_{26|27}` where `26` = current year, `27` = next year. At each calendar date, a blend weight `w = month/12` determines the forward-looking composite:

```
gdp_{region} = w_cur × gdp_forecast_{region}_26 + (1 − w_cur) × gdp_forecast_{region}_27
```

---

## 3. Derived / Custom Series

**`data/custom_series.xlsx`** — 41 derived series; regenerated weekly by `src/build_custom_series.py`. **Never edit manually.**

| Group | Series | Formula |
|---|---|---|
| PMI composites | `pmi_us`, `pmi_ez`, `pmi_china` | (mfg + svcs) / 2 |
| GDP blends | `gdp_us/dm/em/eu/jp/cn` | w_cur × 26 + (1−w) × 27, w = month/12 |
| Rate environment | `modern_ted` | 3M T-bill − SOFR (gated 2018-04-01); `real_ff` = FDTR − PCE; `term_spread` = 10Y − 2Y |
| Equity risk premia | `erp_us/acwi/em/em_xchina/china` | Earnings Yield % − TIPS 10Y % |
| PE scores | `pe_score_sp500/eafe/em/emx/china/gro/val` | `signals.pe_score()` — percentile-based rating |
| Relative PE | `rel_pe_gro_val`, `rel_pe_dm_us`, etc. | log(PE_b / PE_a) |
| OAS stress proxies | `hy_stress`, `hy_safe_haven`, `em_stress`, `embi` | OAS.diff(21d) — raw momentum; sign set in SignalMapping |
| OAS ratio | `hy_ig_ratio` | oas_hy / oas_bbb |
| CDX momentum | `cdx_ig_mom`, `cdx_hy_mom` | Composite multi-horizon momentum on CDX spreads |
| EPS revision | `eps_rev_us/em/eafe/china` | 0.4 × pct_change(63d) + 0.6 × pct_change(126d) |

---

## 4. Signal Engine

**`src/signal_engine.py`** — reads `DataSeries` sheet in `taa_config.xlsx` and produces `{series_id: pd.Series (z-score)}` for every active row.

### 4.1 Signal flow

```
taa_config.xlsx → DataSeries sheet (170 rows)
  For each active row:
    1. Load raw series from correct sheet (original or custom)
    2. Apply transform_code
    3. Clip to dates ≥ MIN_DATE_FOR_SIGNALS (2013-02-01)
    4. Clip values to ±OUTLIER_CLIP_Z (3.0σ)
  Output: {series_id: pd.Series}
```

### 4.2 Transform codes — Summary

| Code | Output | Formula | Use cases |
|---|---|---|---|
| `ewma_z` | EWMA z-score | `(x − EWMA_mean) / EWMA_std`, span = 756d | VIX, DXY, FCI, PMI composites, sentiment |
| `rolling_z` | Rolling z-score | `(x − rolling_mean) / rolling_std`, window per row | Breakevens, ERP, term spread (slow valuation signals) |
| `pctile` | Percentile rank | `rank(x) / n` → rescaled `(p − 0.5) × 4` | OAS levels, yield levels (absolute cheapness) |
| `mom_z` | Momentum z-score | `ewma_z(pct_change(window))` | Forward EPS revisions |
| `price_mom` | Composite price momentum | 40% × 12-1M skip + 25% × 3M + 25% × MA(50/200) + 10% × RSI(14) | TR price indices (equity and FI) |
| `diff_z` | Direction-neutral diff z-score | `ewma_z(diff(window))` — use `sign = −1` in SignalMapping where falling = positive | OAS spread momentum, Treasury yield momentum |

> **`inv_mom_z` is deprecated (May 2026).** It was replaced by `diff_z` + `sign = −1` in SignalMapping. The two are mathematically identical: `+1 × inv_mom_z = −1 × diff_z`. The change moves direction control out of Python and into Excel, consistent with the system's design principle.

---

### 4.2a Why Z-Scores Differ Between Series — Rigorous Analysis

> **Core principle:** A z-score always measures "how far is today's value from some reference, in units of historical variability." The *reference* (mean) and the *unit* (standard deviation) are defined differently for each transform — and appropriately so, because different financial series have fundamentally different statistical properties, different information horizons, and different economic interpretations.

#### 4.2a.1 The Mathematical Decomposition

Every transform in this system computes a variant of:

```
z_t = (x_t − μ_t) / σ_t
```

What differs is:
1. **What `x_t` represents** — the raw level, the rate of change, or a composite
2. **How `μ_t` is estimated** — EWMA (recent-weighted), rolling (equal-weight), or rank-based (empirical)
3. **How `σ_t` is estimated** — same options above
4. **Over what time window** — from 21 days (1M return) to 2,520 days (10Y valuation cycle)

This means **two series both showing "z = +1.5" are not interchangeable in scale or meaning**. One may be 1.5 standard deviations above its recent 3-year EWMA trend; the other may be at the 87th percentile of its 5-year rank history.

---

#### 4.2a.2 Why The Same Raw Value Produces Different Z-Scores at Different Times (EWMA Regime Adaptation)

For `ewma_z`, both μ_t and σ_t are exponentially weighted moving averages that update continuously:

```
μ_t = λ × μ_{t-1} + (1 − λ) × x_t         where λ = 1 − 2/(span+1) ≈ 0.9974
σ_t = EWMA_std(x, span=756d)
z_t = (x_t − μ_t) / σ_t
```

**Consequence:** VIX = 20 in 2016 and VIX = 20 in 2023 give completely different z-scores:

| Date | VIX Level | EWMA Mean | EWMA Std | Z-score |
|---|---|---|---|---|
| 2016 (quiet regime) | 20 | ~14 | ~4 | **+1.5** (elevated) |
| 2023 (post-COVID regime) | 20 | ~19 | ~5 | **+0.2** (near neutral) |

This is **intentional and desirable**: the system measures signal relative to the *current volatility regime*, not an unconditional historical mean. A VIX of 20 is genuinely unremarkable in 2023's environment; it was genuinely elevated in 2016's calm.

**Academic support:** Lo (2001) shows that asset return distributions are non-stationary and regime-dependent. Perez-Quiros & Timmermann (2000) demonstrate that macro signals must be evaluated regime-conditionally to have predictive power in multi-asset allocation.

---

#### 4.2a.3 EWMA vs Rolling Z-Score — When Each Is Appropriate

**`ewma_z` (span = 756d):** Used for signals where *recent regime* is the relevant comparison:
- PMI, CESI: today's PMI should be compared to the recent 3-year trend (a 52 PMI is strong in a weak-trend environment, weak in a strong-trend environment)
- VIX, FCI: volatility regimes shift; EWMA adapts faster than a fixed rolling window
- Mathematical property: exponential decay means a shock from 756 days ago receives weight ≈ e^{-1} ≈ 37% of a current observation

**`rolling_z` (window = 1–10Y):** Used for signals where *secular cycles* are the relevant comparison:
- ERP (Earnings Yield minus TIPS): the spread between equities and bonds must be evaluated against 5–10Y history because valuation cycles operate at decade-long frequencies
- Breakevens: inflation expectations are anchored by long-run monetary regimes (e.g., 2% Fed target)
- Term spread: the yield curve has a structural "normal" slope that changes only with major regime shifts
- Mathematical property: equal weight over the window gives a stable mean — suitable when the series is a slow long-cycle oscillator

**Key difference at a concrete example:**
```
Series: US 10Y-2Y term spread, t=2023-01-05 (value = -0.70%, inverted curve)

rolling_z over 10Y window:
  rolling_mean(2520d) = +0.87%, rolling_std = 0.93%
  z = (-0.70 - 0.87) / 0.93 = -1.69  (deeply inverted vs 10Y history)

ewma_z (span=756d):
  ewma_mean (adapts to 2022 inversion) ≈ +0.40%, ewma_std ≈ 0.91%
  z = (-0.70 - 0.40) / 0.91 = -1.21  (less extreme, regime-adjusted)
```

The rolling_z correctly captures how anomalous the inversion is relative to a full rate cycle; the ewma_z partially adjusts for the 2022 regime shift (the EWMA mean has already moved toward inversion). For term spread — a secular/regime signal — the rolling_z is preferred.

---

#### 4.2a.4 Why Percentile Rank Differs from Both (Distribution-Free Scoring)

**`pctile`** makes zero assumptions about the shape of the distribution. It computes the fraction of historical observations that are at or below today's value:

```
p_t = rank(x_t, within window) / n_window
z_t = (p_t − 0.5) × 4         → maps [0,1] to [-2, +2]
```

**When this matters — OAS spread example:**

OAS (High Yield option-adjusted spread) is heavily **right-skewed**: it spends 80% of its time below 500 bps, but spikes to 1,500–2,000 bps during crises (GFC 2008, COVID 2020). A distribution-based z-score would assign z ≈ +8 during the GFC peak — mathematically valid, economically useless (the system clips to ±3σ anyway, and the signal would max out for trivial widening).

```
OAS HY spread example:

Normal period: OAS = 350 bps
  rolling_mean (5Y) = 440 bps, rolling_std = 220 bps  →  z = -0.41
  pctile (5Y rank) = 35th pctile  →  z = (0.35-0.5)×4 = -0.6

Crisis: OAS = 1,200 bps (COVID March 2020)
  rolling_z → z = (1200-440)/220 = +3.45 → CLIPPED to +3.0
  pctile → 98th pctile → z = (0.98-0.5)×4 = +1.92 (proportional, not clipped)
```

The percentile-based score at crisis reads **+1.92** (extreme, but proportionally calibrated), while rolling_z maxes out at +3.0 (top of clip range) even for moderate widening. This means OAS at 700 bps and 1,200 bps would both read z = +3.0 under rolling_z — losing differentiation exactly when it matters most.

**Rescaling choice:** `(p − 0.5) × 4` is not arbitrary. A unit-normal distribution has roughly 68% of observations within ±1σ. The percentile-to-z mapping needs to match this scale so pctile signals can be combined with ewma_z/rolling_z signals in pillar aggregation without one dominating. At p=0.84 (84th pctile, 1σ equivalent for normal): z = (0.84-0.5)×4 = +1.36 — reasonably close to +1σ.

---

#### 4.2a.5 Why Momentum Transforms Differ from Level Transforms

**`mom_z` — Acceleration in EPS Revisions:**

For forward EPS revisions, the *level* of EPS carries no useful information — equity markets price in the current level continuously. What matters is *how quickly EPS estimates are being revised upward or downward* relative to the historical pace of revisions.

```
eps_fwd_us = 265 (dollars, arbitrary level)
→ ewma_z(level) ≈ +2.5  (EPS is high in absolute terms, always has been post-growth)
→ This gives a perpetually bullish signal because EPS grows secularly

mom_z = ewma_z(pct_change(63d)):
  today's 3M EPS change = +2.1%
  EWMA_mean of 3M EPS changes ≈ +0.8%
  EWMA_std ≈ 1.4%
  z = (2.1 - 0.8) / 1.4 = +0.93  (above-average acceleration, moderate signal)
```

This correctly captures whether analysts are upgrading or downgrading faster than usual — **the information is in the revision velocity, not the level**.

Academic support: Chan, Jegadeesh & Lakonishok (1996) show that earnings revision momentum (change in analyst consensus) has the highest information coefficient for cross-sectional equity selection at 3–6 month horizons — precisely the window used here (`pct_change(63d)` = 3M and `pct_change(126d)` = 6M).

**`diff_z` — Credit and Yield Momentum Signals (replaces deprecated `inv_mom_z`):**

For OAS spreads and Treasury yields, the economically meaningful signal is the **absolute change** (in basis points, not % change). A 50 bps tightening in OAS at 300 bps and at 600 bps both mean the same thing — credit is improving — but `pct_change` would give different values. `diff_z` uses the raw absolute change:

```
diff_z = ewma_z(diff(window))
       = ewma_z(x_t − x_{t-window})
```

This is **direction-neutral**: a positive diff (series rising) gives a positive z-score; a negative diff (series falling) gives a negative z-score. The direction is then controlled exclusively by `sign` in SignalMapping:

- `sign = −1` for credit and duration assets (tightening/falling = bullish → negative diff → negative diff_z → sign × diff_z = positive contribution ✓)
- `sign = +1` would apply where rising spreads are positive (e.g., flight-to-quality proxies)

**Affected series (updated May 2026):**

| Series | Window | SignalMapping sign | Economic logic |
|---|---|---|---|
| `oas_bbb_mom` | 21d | −1 | IG spread tightening = bullish for credit |
| `oas_hy_mom` | 21d | −1 | HY spread tightening = risk appetite |
| `oas_em_mom` | 21d | −1 | EM spread tightening = bullish for EM debt |
| `gt02_mom` | 21d | −1 | 2Y yield falling = positive for short duration |
| `gt10_mom` | 21d | −1 | 10Y yield falling = positive for long duration |

**Design principle enforced:** Before this change, `inv_mom_z` baked the direction into Python (`−ewma_z(diff)`). All five series had `sign = +1` in SignalMapping — the sign column was doing nothing. Now `diff_z` is neutral and `sign = −1` is meaningful. The result is identical: `+1 × (−ewma_z(diff)) = −1 × (ewma_z(diff))` — but direction now lives where it belongs: in Excel.

---

#### 4.2a.6 Price Momentum Composite — Why Four Horizons?

`price_mom` combines four signals:

| Component | Weight | Window | Economic Logic |
|---|---|---|---|
| 12-1M skip momentum | 40% | 252d less 21d | Cross-sectional momentum peak IC at 12M; skip 1M avoids short-term reversal (Jegadeesh-Titman 1993) |
| 3M return | 25% | 63d | Medium-term trend; captures macro inflection points |
| MA(50)/MA(200) distance | 25% | 50/200d | Technical trend filter; MA cross historically most reliable trend indicator |
| RSI(14) | 10% | 14d | Short-term overbought/oversold; dampens position when already extended |

**Why not a single horizon?** Multi-horizon momentum composites have substantially better out-of-sample Sharpe ratios than single-horizon signals (Novy-Marx 2012; Asness, Moskowitz & Pedersen 2013). The 40%/25%/25%/10% weighting reflects empirical information content: 12-1M has the strongest cross-sectional predictor in multi-asset contexts, but 3M adds incremental value especially at regime turns when the 12M signal is stale.

Each sub-component is individually `ewma_z` normalized before combination:
```python
signals["12_1m"] = ewma_zscore(price.shift(skip_days).pct_change(252 - skip))
signals["3m"]    = ewma_zscore(price.pct_change(63))
signals["ma"]    = ewma_zscore((MA50 - MA200) / MA200)
signals["rsi"]   = ewma_zscore((RSI - 50) / 50)
```

This ensures each component contributes with unit variance before weighting — preventing any single horizon from dominating.

---

#### 4.2a.7 Window Selection Logic

The window for each transform is set in the `DataSeries` sheet of `taa_config.xlsx`. The choices follow this decision tree:

```
Is the series stationary (oscillates around a long-run mean)?
  → Yes, and it responds to current economic cycle:  ewma_z (span=756d)
  → Yes, but it's anchored to a structural level:    rolling_z (window=1260–2520d)
  
Is the series heavily skewed or fat-tailed?
  → Yes:  pctile (window=1260d for 5Y history)

Does the signal require measuring the rate of change?
  → For %change of a slow series:  mom_z (window=63d or 126d)
  → For diff of spread/yield:       diff_z (window=21d or 63d) + sign=−1 in SignalMapping

Is the series a price/TR index (non-stationary, trending)?
  → price_mom (4-horizon composite)
```

**EWMA span choice (756d ≈ 3 years):** The half-life of an EWMA with span `s` is approximately `s × ln(2)/2 ≈ 0.35s`. For span=756d, half-life ≈ 265 calendar days (~9 months). This means the EWMA mean "half-forgets" any level after 9 months and "fully forgets" within ~3 years. This matches business cycle duration (NBER average expansion = 58 months; the 3Y EWMA allows 2-3 full cycle captures in the look-back).

---

#### 4.2a.8 Winsorisation and its Effect on Z-Score Scale

**All transforms clip to ±3σ before pillar aggregation:**

```python
return z.clip(-OUTLIER_CLIP_Z, OUTLIER_CLIP_Z)  # OUTLIER_CLIP_Z = 3.0
```

This is applied at TWO stages:
1. **After transform**: individual signal z-scores clipped to ±3σ
2. **After pillar aggregation**: the pillar composite re-standardised and clipped again

Consequence: **The effective range of any signal in the system is [-3, +3]**, regardless of which transform was used or what the raw series value is. A VIX spike to 80 and PMI drop to 40 both max out at z = +3.0 or -3.0. This prevents crisis extremes from generating unrealistic tilts.

**Why clip at 3σ rather than 2σ or 4σ?** At ±3σ, 99.7% of normal observations are kept (only tail observations are clipped). This preserves signal fidelity in normal regimes while bounding extreme crisis values. Clipping at ±2σ would discard 4.6% of observations — too aggressive for real-time signals. Clipping at ±4σ would let through observations that could destabilize the scoring system (a +4σ z-score would overwhelm all other pillar signals in a composite).

---

#### 4.2a.9 Practical Decision Matrix: Which Transform for Which Series?

| Series characteristic | Best transform | Example series |
|---|---|---|
| Bounded oscillator (35–65), stationary | `ewma_z` | PMI (all regions), CESI |
| Financial conditions index (stationary, fast) | `ewma_z` | FCI_US, FCI_EZ, DXY |
| Sentiment index (stationary, contrarian) | `ewma_z` | VIX, VSTOXX, AAII, PCR |
| Valuation level (slow, secular cycle) | `rolling_z` | ERP, breakeven inflation, term spread |
| Spread level (fat-tailed, skewed) | `pctile` | OAS BBB, OAS HY, OAS EM, yield levels |
| Revision flow (acceleration in slow series) | `mom_z` | Forward EPS 3M and 6M revisions |
| Price/TR index (non-stationary, trending) | `price_mom` | SP500 TR, EAFE TR, CEMBI TR |
| Spread/yield direction (sign=−1 in SignalMapping) | `diff_z` | OAS BBB/HY/EM mom, GT10/GT02 mom |

### 4.3 Signal reliability floor

```
MIN_DATE_FOR_SIGNALS = 2013-02-01
```

EWMA span is 756 days; all input data starts 2010-12-31. Signals before 2013-02-01 use incomplete EWMA windows and are excluded.

**Per-signal `reliable_from` date** is computed as:
```
reliable_from = max(first_valid_date + warm_up_days, MIN_DATE_FOR_SIGNALS)
```

Key exceptions:
- **`modern_ted`**: gated at 2018-04-01 (SOFR inception); NaN before that date
- **`pmi_china`**: reliable from ~2025 (short history)
- **GDP 27-series**: only available from 2025

### 4.4 Sign convention (critical)

> **The sign (+1 or −1) lives exclusively in `SignalMapping` in `taa_config.xlsx`.**  
> Raw series and transforms are **never inverted** in Python code.

| Sign | Meaning |
|---|---|
| `+1` | Series value ↑ → bullish for this AC in this pillar |
| `−1` | Series value ↑ → bearish for this AC in this pillar |

Example: PMI US is `+1` for US Equity (expansion = bullish) but `−1` for LT Treasuries (expansion → rates rise → bond prices fall).

---

## 5. Pillar Construction (F / M / S / V)

**`src/pillars.py`** — builds 4 pillar z-scores per AC from the signal dict.

### 5.1 Signal aggregation within a pillar

For each (AC, pillar) combination, the engine:

1. **Selects** the signals listed in `SignalMapping` for that (AC, pillar) pair
2. **Applies sign** (from SignalMapping): `signed_z = sign × raw_z`
3. **Computes weighted average**:

```
composite_t = Σᵢ (sign_i × weight_i × raw_z_i(t)) / Σᵢ weight_i
```

4. **Re-standardises** against the composite's own history via `standardise_pillar()`:

```python
mu_t    = EWMA(composite, span=756)
sigma_t = EWMA_std(composite, span=756)
pillar_z_t = (composite_t − mu_t) / sigma_t
```

> **Why re-standardise?** The weighted average of individually z-scored signals can still have non-unit variance (due to correlations and partial data). Re-standardising via `standardise_pillar()` ensures every pillar has unit variance before being combined into the composite. This means the **Pillar Z-Score displayed in the dashboard is not a simple weighted sum of the signal z-scores** — it is the historical z-score of that weighted sum.

### 5.2 Displayed signal z-scores

In the Fixed Income / Equity pages, each signal shows a **signed z-score**:

```
displayed_z = sign × raw_z
```

- **Green** = bullish contribution to the pillar
- **Red** = bearish contribution to the pillar
- The weighted sum of displayed z-scores ≈ pre-standardisation pillar composite
- The actual Pillar Z-Score (footer) = EWMA z-score of that composite vs its history

### 5.3 Signal categories by pillar

#### Pillar F — Fundamentals (macro regime signals)

| Series | Transform | Direction logic |
|---|---|---|
| PMI US/EZ/China composite | `ewma_z` | Expansion = bullish EQ/credit; bearish duration |
| CESI (Surprise indices) | `ewma_z` | Positive surprise = bullish EQ; bearish duration |
| GDP blend (consensus) | `ewma_z` | Growth upgrade = bullish EQ/credit; bearish duration |
| GDPNow (real-time) | `ewma_z` | US short-term growth proxy |
| Forward EPS (growth, revision) | `mom_z`, `ewma_z` | EPS acceleration = bullish EQ and credit |
| ISM N.O./Inventories ratio | `ewma_z` | >1.0 = demand > inventory = bullish |
| Breakeven inflation (1Y, 5Y, 10Y) | `rolling_z` | Higher BEI = tighter Fed = bearish duration; mixed for credit |
| Real Fed Funds Rate | `rolling_z` | Restrictive policy = bearish duration, bearish EQ at extremes |
| Core PCE YoY | `ewma_z` | Above target = Fed stays restrictive |

#### Pillar M — Momentum (price and spread trends)

| Series | Transform | Direction logic |
|---|---|---|
| TR price indices (SP500, EAFE, MSCI EM, etc.) | `price_mom` | Composite: 12-1M (40%) + 3M (25%) + MA cross (25%) + RSI (10%) |
| FI TR indices (BSGV, BFU5, LT03, I132) | `price_mom` | Same composite; falling yield = rising price |
| OAS momentum (BBB, HY, EM) | `diff_z` + sign=−1 | Spread tightening (negative diff) × sign=−1 = positive momentum |
| Treasury yield momentum (2Y, 10Y) | `diff_z` + sign=−1 | Yield falling (negative diff) × sign=−1 = positive for duration |
| CDX IG / HY momentum | `ewma_z` | CDS tightening = positive credit signal |

#### Pillar S — Sentiment (risk appetite and positioning)

| Series | Transform | Direction logic |
|---|---|---|
| CBOE VIX | `ewma_z` | High VIX = contrarian buy EQ; bullish safe-haven FI |
| MOVE Index (bond vol) | `ewma_z` | High MOVE = flight to UST quality |
| VSTOXX | `ewma_z` | EZ-specific fear; contrarian for DM equity |
| SKEW Index | `ewma_z` | Tail risk indicator |
| Modern TED (T-bill − SOFR) | `ewma_z` | Funding stress = bullish MM/STFI, bearish credit/EQ; gated 2018+ |
| OAS stress proxies (diff 21d) | `ewma_z` | HY/EM widening = risk-off |
| AAII Bull-Bear spread | `ewma_z` | Contrarian: extreme bullish = sell signal (sign = −1 for EQ) |
| CBOE PCR (Put/Call ratio) | `ewma_z` | High PCR = fear = contrarian buy EQ (sign = +1) |
| Bloomberg US/EZ FCI | `ewma_z` | Tight conditions = headwind for EQ/credit (sign = −1) |
| DXY USD Index | `ewma_z` | Strong USD = EM headwind (sign = −1 for EM FI/EQ) |

#### Pillar V — Valuation (absolute and relative cheapness)

| Series | Transform | Direction logic |
|---|---|---|
| PE scores (SP500, EAFE, EM, etc.) | `ewma_z` | Low P/E = cheap = bullish |
| Equity Risk Premium (EY − TIPS 10Y) | `rolling_z` | High ERP = equity cheap vs bonds = bullish |
| Relative PE (Growth vs Value, DM vs US, etc.) | `ewma_z` | Relative cheapness signal |
| OAS levels (BBB, HY, EM, LatAm) | `pctile` | High percentile = cheap credit = bullish spread |
| HY/IG ratio | `ewma_z` | High ratio = HY expensive vs IG |
| Yield levels (2Y, 10Y, TIPS 5Y, 10Y) | `pctile` | High yield = attractive carry = bullish for duration |
| Term spread (10Y − 2Y) | `ewma_z` | Inverted curve = recession signal = bullish long duration |

---

## 6. Composite Scoring

**`src/scoring.py`** — combines 4 pillar z-scores into a single composite.

### 6.1 Pillar weights

Pillar weights are AC-specific and sum to 1.0 per row. They are stored in the `PillarWeights` sheet of `taa_config.xlsx` and auto-generated into `src/config.py`.

| AC | F | M | S | V | Logic |
|---|---|---|---|---|---|
| lt_treasuries | 25% | 25% | 20% | 30% | Balanced; valuation via yield level |
| lt_us_corp | 20% | 30% | 20% | 30% | Momentum and valuation dominant (OAS) |
| lt_em_fi | 25% | 30% | 20% | 25% | Balanced across pillars |
| us_equity | 25% | 30% | 20% | 25% | Momentum slightly dominant |
| dm_equity | 25% | 30% | 20% | 25% | Same as US equity |
| em_equity | 25% | 30% | 20% | 25% | Same; EM-specific signals in each pillar |

### 6.2 Composite z-score formula

```
Z_composite = Σₚ (w_p × Z_pillar_p) / Σₚ w_p
```

Missing pillars are skipped gracefully — weights renormalize to available pillars. Final composite is clipped to ±3σ.

### 6.3 Pillar agreement multiplier

The **conviction multiplier** adjusts the tilt magnitude based on how many pillars agree on direction:

| Pillars in agreement | Multiplier |
|---|---|
| 4 / 4 | 1.00 (full conviction) |
| 3 / 4 | 0.80 |
| 2 / 4 | 0.50 |
| 1 / 4 | 0.00 (no tilt even if composite is large) |
| 0 | 0.00 |

A pillar "agrees" if its z-score has the same sign as the composite AND `|z_pillar| > 0.25`.

---

## 7. Conviction Mapping

### 7.1 Conviction thresholds

```
Z_composite → conviction label → tilt fraction
```

| Z threshold | Label | Tilt fraction |
|---|---|---|
| z ≥ +1.50 | HIGH OW | +1.0 |
| z ≥ +0.75 | MEDIUM OW | +0.5 |
| −0.75 ≤ z < +0.75 | NEUTRAL | 0.0 |
| −1.50 ≤ z < −0.75 | MEDIUM UW | −0.5 |
| z < −1.50 | HIGH UW | −1.0 |

### 7.2 Absolute tilt

```
abs_tilt = tilt_fraction × conviction_multiplier × MAX_TILT_PCT[ac]
```

`MAX_TILT_PCT` is the maximum tilt for each AC at a reference TE budget of 100 bps, regenerated from `taa_config.xlsx`.

### 7.3 Crisis override

When **both** VIX and MOVE exceed their 80th percentile simultaneously, all tilts are forced to zero. The override lifts when both return below 70th percentile.

---

## 8. Absolute vs. Relative Views

Wang & Kochard (2012) validate blending absolute and relative z-scores:

### 8.1 Absolute view

> "Is this AC attractive vs its own history?"

```
Z_absolute = Z_composite (from above)
abs_tilt   = f(Z_absolute) × conviction_mult × MAX_TILT
```

### 8.2 Relative view

> "Which AC do I prefer over the others (cross-sectional ranking)?"

```
Z_relative = (Z_composite − mean_cs) / std_cs
rel_tilt   = f(Z_relative) × conviction_mult × MAX_TILT
```

Where `mean_cs` and `std_cs` are the cross-sectional mean and std across all 6 active ACs at that date.

### 8.3 Final tilt blend

```
final_tilt = ALPHA_ABS × abs_tilt + (1 − ALPHA_ABS) × rel_tilt
           = 0.35 × abs_tilt + 0.65 × rel_tilt
```

The 35/65 split weights relative performance more heavily, consistent with the insurance portfolio context where tactical deviations are driven primarily by cross-asset attractiveness rather than absolute macro timing.

---

## 9. Hierarchical Architecture (L1 / L2)

**`src/hierarchical_scoring.py`** — two-level view system.

### 9.1 Rationale

Maillard/Roncalli/Teïletche (2010): L1 and L2 views are orthogonal — the aggregate direction and the within-bucket rotation are independently managed.

### 9.2 Level 1 — Aggregate directional view

```
Standalone ACs:     Z_L1 = Z_composite  (own signal)
Synthetic aggregate: Z_L1 = Σ (model_weight_child × Z_composite_child)
```

Current L1 buckets:

| L1 Bucket | Type | Children | Model weights |
|---|---|---|---|
| `lt_fi_aggregate` | Synthetic | lt_treasuries, lt_us_corp, lt_em_fi | 40% / 35% / 25% |
| `us_equity` | Real AC | Standalone | — |
| `dm_equity` | Real AC | Standalone | — |
| `em_equity` | Real AC | Standalone | — |

### 9.3 Level 2 — Within-bucket relative rotation

```
Z_L2 = Z_composite_child − Z_L1_parent
```

This is a zero-sum view within each bucket — an OW one child must be offset by UW another.

For `lt_fi_aggregate`:
- `z_L2(lt_treasuries) = z_composite(lt_treasuries) − z_L1(lt_fi_aggregate)`
- `z_L2(lt_us_corp)    = z_composite(lt_us_corp)    − z_L1(lt_fi_aggregate)`
- `z_L2(lt_em_fi)      = z_composite(lt_em_fi)      − z_L1(lt_fi_aggregate)`

### 9.4 L2 tilt sizing

L2 tilts are sized proportionally within the L1 tilt budget, constrained by `max_tilt_l2` from `AC_HIERARCHY`.

---

## 10. Portfolio Construction

**`src/portfolio.py`** — applies the central house view to 4 institutional portfolios.

### 10.1 Four Rimac portfolios

| Portfolio | TE Budget | Risk Profile | Key SAA (FI / US Eq / DM / EM) |
|---|---|---|---|
| IGCON_USD | 50 bps | Conservative | Heavy FI |
| IGMOD_USD | 75 bps | Moderate | Balanced |
| IGDIN_USD | 100 bps | Aggressive | More equity |
| IGEQUS_USD | 125 bps | Aggressive | ~95% US equity |

All portfolios have `force_zero_sum = True`.

### 10.2 TE-scaled tilt

```
te_scale   = portfolio_te_budget_bps / 100
max_tilt_p = MAX_TILT_PCT[ac] × te_scale
tilt_p     = tilt_fraction × conviction_mult × max_tilt_p
```

A 50 bps portfolio gets tilts half the size of the reference (100 bps) portfolio.

### 10.3 No-short constraint (Solvency II)

```python
portfolio_weight = (saa_weight + tilt).clip(lower=0)
portfolio_tilt   = portfolio_weight − saa_weight
```

If a tilt would push a weight below zero, it is clipped and the tilt is reduced accordingly.

### 10.4 Zero-sum enforcement

After clipping, the net tilt across all ACs in the portfolio may not sum to zero. The excess is redistributed proportionally across all ACs with positive SAA weight:

```
excess = Σ portfolio_tilt
adj_per_ac = excess / len(eligible_acs)
portfolio_tilt[eligible] -= adj_per_ac
```

Any remaining residual is absorbed by the AC with the **largest SAA weight** (most liquid, most natural absorber).

> **Key insight:** Money Market and Short-Term FI are present in `portfolios.xlsx` with their SAA weights but receive **no TAA signal tilt** (they are not active ACs). This means they naturally absorb the net excess of tilts generated by the 6 active ACs. An OW in Emerging Markets Equity, for example, is effectively financed by a relative UW in Money Market/Short-Term FI.

---

## 11. Dashboard Generation

### 11.1 Single-file architecture (updated May 2026)

```
index.html  ←  source AND output — contains CSS, JS, layout and live data
         ↑↓
src/generate_dashboard.py  ←  reads index.html, replaces data constants, writes back
```

`index.html` is both the template and the output. `generate_dashboard.py` replaces the JS data constants (`SCORECARD`, `COMPOSITES`, `CB`, etc.) in-place on every run.

> **`docs/model_design.html` is a design reference only** — it was used to define the visual format but is not read by any pipeline script. Edit `index.html` directly when changing the dashboard layout or JS logic.

### 11.2 Data injection points

| JS constant | Source | Content |
|---|---|---|
| `SCORECARD` | `results/RUN_*/taa_scorecard.csv` | Latest z-scores + tilts per AC |
| `COMPOSITES` | `results/RUN_*/taa_composite_series.csv` | 252-day composite z-score history |
| `CB` | `results/chartbook_data.json` | All signal time series + PMI heatmap |
| `SIG_Z` | `results/signal_z_snapshot.json` | Current z-score per `series_id` (95 signals) |
| `SIG_MATRIX` | `taa_config.xlsx` via `build_dashboard.py` | Signal × AC coverage matrix |
| `FI_BLUEPRINT` | `taa_config.xlsx` via `build_dashboard.py` | FI pillar signal details |
| `EQ_BLUEPRINT` | `taa_config.xlsx` via `build_dashboard.py` | EQ pillar signal details |
| `AC_LABEL_FULL`, `PW` | `taa_config.xlsx` via `build_dashboard.py` | AC labels + pillar weights |

### 11.2a Dynamic AC grouping (updated May 2026)

`fiAC` and `eqAC` — the lists of FI and EQ asset classes shown in the composite time-series charts — are now derived at runtime from `SCORECARD.group` rather than hardcoded:

```javascript
const fiAC = AC_ORDER.filter(ac => SCORECARD.find(r=>r.ac===ac)?.group==='FI');
const eqAC = AC_ORDER.filter(ac => SCORECARD.find(r=>r.ac===ac)?.group==='EQ');
```

Adding or removing an AC from `AssetClasses` in `taa_config.xlsx` automatically updates these lists without any manual edits to `index.html`.

### 11.3 Methodology page (Fixed Income / Equity)

The blueprint pages show:
- Each signal in each pillar with its **signed z-score** (`sign × raw_z`)
- Green bar = bullish contribution; Red bar = bearish contribution
- The **Pillar Z-Score** (footer) is the EWMA-standardised composite — not a simple weighted sum of the signal z-scores
- Hovering over a z-score shows a tooltip: "Signed z-score (sign × raw z). Pillar Z is EWMA-standardised against history."

### 11.4 Portfolio views — current gap

The pipeline generates `results/RUN_*/multi_portfolio_views.xlsx` with per-portfolio tilts and weights for all 4 Rimac portfolios. This file is **not yet injected into `index.html`**. The dashboard currently shows only the house-view scorecard (reference 100 bps TE), not the IGCON / IGMOD / IGDIN / IGEQUS specific views.

**Planned addition:** A `PORTFOLIOS` JS constant injected by `generate_dashboard.py` from `multi_portfolio_views.xlsx`, rendered as a tab-switched portfolio view in the dashboard. See `docs/portfolio_dashboard_analysis.md` for the full specification.

### 11.5 Signal Matrix (Full Signal Matrix page)

- One row per signal series, columns = 6 active ACs
- Signs shown as `+` (bullish) or `−` (bearish) or `—` (not mapped to this AC)
- Source column: `CALC` for derived custom series; Bloomberg ticker / FRED code for original series
- Pillar grouping (F / M / S / V) with color coding

---

## 12. Data Quality & Governance

### 12.1 Key rules

| Rule | Value | Reason |
|---|---|---|
| Signal floor | `MIN_DATE_FOR_SIGNALS = 2013-02-01` | EWMA 756d warm-up from 2010-12-31 |
| modern_ted gate | 2018-04-01 | SOFR inception; series is NaN before that date |
| OAS staleness | Warning if lag > 7 days | OAS sheet typically lags H5 by ~17 business days |
| Daily ffill | 5 days | Weekend + 1 holiday max |
| Monthly ffill | 31 days | PMI/CESI/GDP releases |
| Outlier clip | ±3σ per series and per composite | Winsorisation at all stages |
| Holiday/month-end spikes | `SMOOTH_COMPOSITE` toggle | 10-day rolling median; off by default |

### 12.2 OAS staleness warning

At runtime, `main.py` compares the latest date in the OAS sheet against the latest date in H5. If OAS lags by more than 7 business days, a warning is printed. OAS typically lags by ~17 business days (settlement cycle).

### 12.3 Series source classification

| `series_type` | Source | Dashboard SRC |
|---|---|---|
| `original` | `Dashboard_TAA_Inputs.xlsx` | Bloomberg ticker or FRED code |
| `custom` | `data/custom_series.xlsx` | `CALC` |

### 12.4 Run ID format

```
RUN_YYYYMMDD_HHMMSS
```

Seconds included to prevent collision if two runs start in the same minute.

---

## 13. Configuration Reference

### 13.1 File hierarchy

```
config/taa_config.xlsx          ← SINGLE SOURCE OF TRUTH
  Sheet: AssetClasses           Active/inactive flag, labels, colors, groups
  Sheet: DataSeries             170 rows: series_id, source, transform, window
  Sheet: PillarWeights          F/M/S/V weights per AC
  Sheet: PillarNotes            Methodology notes per (AC, pillar) — reference only
  Sheet: SignalMapping          130 rows: series_id × AC × pillar × sign × weight
  Sheet: TransformCodes         Code descriptions
  Sheet: MomentumConfig         Per-series price_mom customisation
config/portfolios.xlsx          4 real portfolios: SAA weights, TE budgets
```

### 13.2 How to activate/deactivate an AC

1. In `taa_config.xlsx` → `AssetClasses` sheet, set `active = False` for the AC
2. Run `python src/build_dashboard.py` (updates `src/config.py` BUILD blocks)
3. Remove the AC from any hardcoded display arrays in `docs/model_design.html`:
   - `fiAC` / `eqAC` lists
   - `AC_LABEL2`, `AC_ORDER`, `AC_SHORT`, `AC_ID_TO_KEY`
   - FI/EQ blueprint blocks
4. Run the full pipeline

### 13.3 How to add a new signal

```bash
# If derived: add computation in build_custom_series.py, then:
python src/build_custom_series.py

# Add to taa_config.xlsx:
#   DataSeries: new row with series_id, source, transform, window
#   SignalMapping: new rows with series_id × AC × pillar × sign × weight

python src/main.py               # look for "OK  series_id" in verbose output
python src/test_build_layer.py   # verify health checks pass
```

### 13.4 Key Python constants (auto-generated from Excel)

```python
ASSET_CLASSES        # list of active AC keys (currently 6)
ASSET_CLASS_LABELS   # {ac_key: display_label}
ASSET_CLASS_GROUPS   # {ac_key: 'FI' or 'EQ'}
PILLAR_WEIGHTS       # {ac_key: {F, M, S, V} summing to 1.0}
MAX_TILT_PCT         # {ac_key: float}  — at 100 bps TE reference
```

---

## 14. Weekly Pipeline

Standard refresh sequence (every Monday, after data update):

```bash
# Step 1 — Rebuild derived series
python src/build_custom_series.py
# → data/custom_series.xlsx  (41 series)

# Step 2 — Run TAA signal pipeline
python src/main.py
# → results/RUN_YYYYMMDD_HHMMSS/taa_scorecard.csv
# → results/RUN_YYYYMMDD_HHMMSS/taa_composite_series.csv
# → results/RUN_YYYYMMDD_HHMMSS/pillars_{ac}.csv  (× 6 ACs)
# → results/RUN_YYYYMMDD_HHMMSS/taa_hierarchy_scorecard.csv
# → results/RUN_YYYYMMDD_HHMMSS/taa_bucket_summary.csv
# → results/RUN_YYYYMMDD_HHMMSS/multi_portfolio_views.xlsx
# → results/signal_z_snapshot.json  (95 signal z-scores for dashboard)

# Step 3 — Health check
python src/test_build_layer.py   # Expected: 29/29 PASS

# Step 4 — Regenerate dashboard
python src/chartbook_data.py     # → results/chartbook_data.json
python src/generate_dashboard.py # → index.html  (open in browser)

# Step 5 — Only when taa_config.xlsx changes
python src/build_dashboard.py    # → src/config.py BUILD blocks updated
```

### Output files per run

| File | Content |
|---|---|
| `taa_scorecard.csv` | Scorecard snapshot: Z_F/M/S/V, Z_composite, conviction, tilts per AC |
| `taa_composite_series.csv` | Full composite z-score history per AC |
| `pillars_{ac}.csv` | Per-AC pillar z-score time series (F/M/S/V) |
| `taa_hierarchy_scorecard.csv` | L1/L2 z-scores and tilts |
| `taa_bucket_summary.csv` | Compact bucket summary |
| `multi_portfolio_views.xlsx` | Per-portfolio tilt application (4 sheets + summary) |
| `signal_z_snapshot.json` | Current z-score per series_id (dashboard injection) |

---

## 15. Academic Foundations

| Reference | Application in this system |
|---|---|
| Brinson, Hood & Beebower (1986) | Asset allocation explains 80–90% of return variance; validates TAA as primary lever |
| Grinold & Kahn (2000) | Fundamental Law of Active Management; TE-budget framework |
| Wang & Kochard (2012) | **35/65 absolute/relative z-score blend** — directly implemented in `ALPHA_ABS = 0.35` |
| Asness, Moskowitz & Pedersen (2013) | Value + momentum everywhere; validates dual use across asset classes |
| Koijen et al. (2018) | Carry is universal; OAS / ERP / yield carry validates our Valuation pillar signals |
| Maillard, Roncalli & Teïletche (2010) | Hierarchical risk parity; **validates L1/L2 orthogonal view structure** |
| Chan, Jegadeesh & Lakonishok (1996) | Earnings revision momentum strongest at 3–6M; validates `eps_rev` 40%×3M + 60%×6M blend |
| Lee (2000) | Multi-portfolio TAA; **validates TE-scaled tilt sizing across portfolios** |

---

*Document generated from codebase state as of May 2026 (v5). Last updated May 2026 — reflects diff_z refactor (inv_mom_z deprecated), index.html single-file architecture, dynamic fiAC/eqAC grouping, and portfolio dashboard gap documentation.*

---

## 16. Data Quality Detail — Per-Signal Reference

### 16.1 Signal reliability floor

All EWMA z-scores use `EWMA_SPAN = 756 trading days` (~3 years). Data starts 2010-12-31. The EWMA needs a full span before its mean and standard deviation stabilize. Signals before 2013-02-01 are excluded globally.

**Warm-up period by transform:**

| Transform | Warm-up |
|---|---|
| `ewma_z` | 756 days |
| `rolling_z` | window per DataSeries row |
| `pctile` | window per DataSeries row |
| `mom_z` | pct_change_window + 756 days |
| `price_mom` | ~263 days (12M horizon + skip month) |
| `diff_z` | diff_window + 756 days (replaces deprecated `inv_mom_z`) |

**Composite `reliable_from` per AC** = max(pillar reliable_from) across all 4 pillars. Exported as informational column in `taa_scorecard.csv`.

### 16.2 Key dates per signal

| Signal | First valid date | reliable_from | Notes |
|---|---|---|---|
| OAS series | 1999-12-31 | 2003-01 (pctile 1260d) | Longest history in system |
| AAII | 1987-07-24 | 1990-07 (ewma span) | 36-year sentiment history |
| VIX, MOVE, VSTOXX | 2010-12-31 | 2013-10 | ewma_z(756) |
| PMI US | 2010-12-31 | 2013-10 | ewma_z(756) |
| PCR (CBOE Put/Call) | 2010-12-31 | 2013-10 | ewma_z(756); wired in S pillar May 2026 |
| modern_ted | **2018-04-01** | **2020-12** | SOFR inception; gated in build_custom_series.py |
| pmi_china | 2023-04 | 2026-03 | Short history — EM F pillar limited before 2026 |
| gdp_forecast_*_27 | 2025-01 | 2026-01 | Bloomberg next-year series only from 2025 |

### 16.3 Input sheet summary

| Sheet | Rows | Period | Freq | NaN% | Critical notes |
|---|---|---|---|---|---|
| OAS | ~6,937 | 1999–2026 | Daily | 0% | ~17 days behind H5; update weekly |
| H4 (PE/EY/TR) | 3,991 | 2010–2026 | Business | 8.1% | msci_em_xchina 41% NaN (2010–2015 gap) |
| H5 (MKT) | 4,044 | 2010–2026 | Business | 6.6% | SOFR 47% NaN (pre-2018) |
| H6 (Sectors) | 3,991 | 2010–2026 | Business | 2.2% | sp500_re 37% NaN (inception ~2016) |
| H1 (PMI/CESI/GDP) | 4,003 | 2010–2026 | Mixed | 54.3% | GDP daily; PMI/CESI monthly |
| H2 (Regional) | 3,960 | 2010–2026 | Mixed | ~50% | Japan/China GDP; monthly PMI |
| H3 (EPS) | 3,991 | 2010–2026 | Business | 0% | Clean; daily forward EPS |
| H7 (New macro) | 3,991 | 2010–2026 | Business | 1.5% | GDPNow, NFCI, FCI_EZ, breakeven_1y |
| AAII | 10,105 | 1987–2026 | Weekly→daily | 0.1% | Resampled to business days; ffill 7d |

### 16.4 Forward-fill rules by series type

| Series type | Max ffill | Rationale |
|---|---|---|
| Daily prices (H4, H5, OAS) | 5 days | Covers weekends + 1 holiday |
| Monthly PMI/CESI (H1) | 31 days | One monthly release cycle |
| Daily GDP forecasts (H1/H2) | 31 days | Daily updates; 31d covers occasional gaps |
| AAII (weekly) | 7 days | Spread to business days |
| SOFR / modern_ted | Gated 2018-04-01 | Inception date; NaN before, not filled |
| PCE YoY (monthly, H5) | 5 days | Monthly gaps remain as NaN |

### 16.5 Known data gaps

**Critical:**

| Gap | Impact | Handling |
|---|---|---|
| modern_ted (2010–2018) | S pillar contributes zero for these dates | Gated to 2018-04-01 in build_custom_series.py |
| gdp_forecast_*_27 (pre-2025) | GDP blend falls back to current-year only | NaN → blend uses 100% current-year |
| pmi_china (pre-2023) | EM F pillar uses proxy signals only | Short history; reliable_from ≈ 2026-03 |

**Medium (expected inception gaps):**

| Series | NaN% | Period | Cause |
|---|---|---|---|
| msci_em_xchina PE/EY | 41% | 2010–2015 | Data provider gap |
| sp500_quality PE/EY | 32% | 2010–2016 | Index inception |
| sp500_re PE/EY | 37% | 2010–2016 | REIT sub-index inception |
| sofr | 47% | 2010–2018 | Inception April 2018 |
| pce_yoy | 73% | Always | Monthly Federal Reserve release |

### 16.6 OAS staleness

OAS sheet typically lags H5 by ~17 business days. `main.py` prints a warning if lag > 7 days:

```
WARNING: OAS data is 17 days behind H5 (2026-03-31 vs 2026-04-17).
Credit signals (oas_bbb, oas_em, hy_stress) may be stale.
```

### 16.7 Holiday / month-end z-score spikes

Price momentum signals (`price_mom` via `pct_change(21)`) can spike ±1.5–2.9 z-units on Dec 29–Jan 2 and last 2 trading days of each quarter due to year-end rebalancing flows.

- Toggle: `SMOOTH_COMPOSITE = True` in `config.py` → applies 10-day rolling median to composites
- Default: `False` (raw z-scores)
- Exclude Dec 29–Jan 2 from backtests / performance attribution

### 16.8 GDP series naming convention (updated May 2026)

All GDP forecast series use the **year-suffix** convention: `gdp_forecast_{region}_{26|27}`

| Internal name | Bloomberg ticker | Description |
|---|---|---|
| `gdp_forecast_us_26` | ECGDUS 26 Index | US current-year consensus (daily) |
| `gdp_forecast_us_27` | ECGDUS 27 Index | US next-year consensus (from 2025) |
| `gdp_forecast_em_26/27` | ECGDM1 26/27 Index | EM current/next year |
| `gdp_forecast_dm_26/27` | ECGDD1 26/27 Index | DM current/next year |
| `gdp_forecast_eu_26/27` | ECGDEU 26/27 Index | Eurozone current/next year |
| `gdp_forecast_jp_26/27` | ECGDJP 26/27 Index | Japan current/next year |
| `gdp_forecast_cn_26/27` | ECGDCN 26/27 Index | China current/next year |
| `gdp_forecast_latam_26/27` | ECGDR4 26/27 Index | LatAm current/next year |

**Blend formula:**
```
gdp_blend = (month/12) × gdp_cur + (1 − month/12) × gdp_nxt
```
January: 8% current / 92% next. December: 92% current / 8% next.

### 16.9 Data quality scorecard

| Issue | Severity | Status |
|---|---|---|
| EWMA warm-up 2010–2013 | HIGH | Fixed — MIN_DATE_FOR_SIGNALS = 2013-02-01 |
| SOFR gap 2010–2018 (modern_ted) | HIGH | Fixed — gated to 2018-04-01 |
| GDP 27-series missing pre-2025 | MEDIUM | Documented — falls back to current-year |
| F1 ffill too long (125 days) | MEDIUM | Fixed — reduced to MAX_FFILL_MONTHLY = 31 |
| OAS lags H5 by ~17 days | MEDIUM | Warning added in main.py |
| PE/YIELDS missing 32–41% (new indices) | MEDIUM | Documented — expected inception gaps |
| Holiday z-score spikes | MEDIUM | Documented — SMOOTH_COMPOSITE toggle available |
| PCR had no data wired | LOW | Fixed — wired in H5 → DataSeries → SignalMapping (May 2026) |
| Same-minute run collision | LOW | Fixed — RUN timestamp now includes seconds |
| GDP columns wrong naming | LOW | Fixed — renamed to gdp_forecast_*_26/27 |
| Breakeven 5Y reading from wrong sheet | LOW | Fixed — from f3 (H3) → mkt (H5) |
| modern_ted reading defunct column | LOW | Fixed — from mkt["ted"] → tsy["modern_ted"] |

---

## 17. Excluded Signals & Phase 2 Roadmap

Signals evaluated but excluded from the current plain-vanilla baseline. Candidates for Phase 2 once the system is validated with the Investment Committee.

**Design rule:** Every active signal must have (1) verifiable data in the Excel inputs, (2) a clear, directly explainable economic rationale, (3) no double-counting with existing signals in the same pillar.

### 17.1 Priority summary

| Priority | Signal | Ease | Pillar | ACs | Status |
|---|---|---|---|---|---|
| ✅ Done | PCR (Put/Call Ratio) | — | S | US Equity | **ACTIVE** since May 2026 |
| 1 | Shiller CAPE | Medium | V | US Equity | Pending — data exists, needs validation |
| 2 | DXY for EM Equity S | Easy | S | EM Equity | Pending — data exists |
| 3 | CDX HY Momentum overlays | Easy | M | LT US Corp | Pending — data exists |
| 4 | GDP Revision composite | Easy | F | All EQ/credit | Pending — computable from existing data |
| 5 | CFTC COT positioning | Hard | S | US Equity, LT Tsy | Pending — requires external data source |

### 17.2 Shiller CAPE

**Pillar:** V | **ACs:** US Equity

P/E ratio using 10-year real inflation-adjusted earnings (Shiller 1981). CAPE > 30 historically predicts below-average 10Y returns. Useful as a long-horizon anchor alongside ERP.

**Why excluded:** Requires manually computing 10Y rolling real EPS. Data exists (H3 trailing EPS + H5 CPI) but computation needs validation against published Shiller series.

**To activate:**
```python
# build_custom_series.py
real_eps = spx_eps / (1 + cpi/100).cumprod()
cape = spx_price / real_eps.rolling(252*10).mean()
series["shiller_cape"] = cape
```
Then add `series_type="custom"` DataSeries row and wire with `rolling_z` or `pctile`.

### 17.3 CDX HY Momentum in US Corporate (M pillar)

**Pillar:** M | **ACs:** LT US Corp

CDX HY 5Y price momentum as risk-appetite proxy. HY credit prices lead equity by 1-2 weeks historically.

**Why excluded:** CDX momentum adds alongside price momentum in the same pillar → double-counting risk. For plain-vanilla, pure price momentum is the cleaner anchor.

**To activate:** Re-add `cdx_hy_mom` (+1, 0.15-0.20) to LT US Corp M, verify no overlap with `oas_hy_mom` (different instruments: CDX = synthetic index; OAS = cash market).

### 17.4 DXY Momentum for EM Equity (M pillar)

**Pillar:** M | **AC:** EM Equity

DXY trending stronger over 3-6 months leads to EM capital outflows. Momentum in DXY is bearish for EM.

**Why excluded:** Static DXY level z-score (`dxy_z`) already in S pillar. Adding momentum would double-count.

**To activate:** `dxy_mom = ewma_z(dxy.pct_change(63))`, add to EM Equity M at (-1, 0.10). Only if static DXY is removed from S pillar to avoid overlap.

### 17.5 GDP Revision composite (F pillar)

**Pillar:** F | **All EQ / credit ACs**

Monthly change in consensus GDP forecast is more predictive than the level. Currently `gdp_us` uses the blended level; adding explicit revision would capture turning points faster.

**Why excluded:** `ewma_z` applied to the GDP level already captures deviation from its moving average. Adding an explicit revision series would require a new custom series but adds minimal marginal information.

**To activate:**
```python
# build_custom_series.py
series["gdp_rev_us"] = series["gdp_us"].pct_change(21)
```
Then add as `ewma_z` signal in DataSeries, alongside existing `gdp_us`.

### 17.6 CFTC COT Positioning

**Pillar:** S | **ACs:** US Equity (sign -1), LT Treasuries (sign +1)

Extreme net speculator longs in S&P futures = crowded → contrarian sell. Extreme UST shorts = contrarian UST buy.

**Why excluded:** `cot_spx` and `cot_ust10` appear in legacy DataSeries but have no data in the current Excel. Requires CFTC Commitment of Traders (available free via CFTC website or FRED).

**To activate:**
1. Download COT data from FRED (`CFTCSP500` or equivalent)
2. Compute net speculator position as `pctile`
3. Wire: US Equity S (-1, 0.15); LT Treasuries S (+1, 0.15)

### 17.7 Signals evaluated and definitively excluded

| Signal | Reason for permanent exclusion |
|---|---|
| Bloomberg NFCI (Chicago Fed) | Highly correlated with `fci_z` (Bloomberg US FCI, already wired); adding both double-weights the same info |
| EM BBB OAS in EM Equity V | Cleaner for EM credit (already in LT EM FI V); adds confusion in equity valuation context |
| Breakeven 10Y in LT EM FI | Neither F nor V clearly for USD-denominated CEMBI; primary drivers are spread levels and EM growth |
| HY OAS Momentum in US Growth M | Plain-vanilla: US Growth M is cleanest with just growth TR momentum |
| DXY for LT EM FI S | CEMBI is USD-denominated; DXY doesn't directly affect instrument yield |
| EZ FCI for Short-Term FI S | Too indirect; STFI sentiment already covered by modern_ted + move_z |
| BBB/CDX IG in US Value M | Plain-vanilla first delivery; US Value M is just sp500_val_tr |

### 17.8 PCR (Put/Call Ratio) — ACTIVE since May 2026

**Pillar:** S | **ACs:** US Equity

`PCRTEQTY Index` — 3,844 clean daily values (2010–2026, range 0.38–2.46). High PCR = elevated put buying = fear = contrarian buy signal.

**Current configuration:**
- `series_type = "original"`, `input_sheet = "H5"`, `input_column = "PCRTEQTY Index"`
- `transform_code = "ewma_z"`, `window = 756`
- Wired to: us_equity S (+1, weight from SignalMapping)
