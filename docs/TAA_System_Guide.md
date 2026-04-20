# TAA Signal System — Technical Guide

**Version 2.0 · April 2026**

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Repository Structure](#2-repository-structure)
3. [Data Architecture](#3-data-architecture)
4. [The Four Pillars](#4-the-four-pillars)
5. [Signal Computation (`signals.py`)](#5-signal-computation)
6. [Proxy Signals (`proxies.py`)](#6-proxy-signals)
7. [Pillar Aggregation (`pillars.py`)](#7-pillar-aggregation)
8. [Scoring & Views (`scoring.py`)](#8-scoring--views)
9. [Absolute vs Relative Views](#9-absolute-vs-relative-views)
10. [How to Run](#10-how-to-run)
11. [Current Data Status](#11-current-data-status)
12. [Test Suite](#12-test-suite)
13. [Current Results — April 2026](#13-current-results--april-2026)
14. [Challenges & Known Limitations](#14-challenges--known-limitations)
15. [Roadmap to an Exceptional TAA System](#15-roadmap-to-an-exceptional-taa-system)

---

## 1. System Overview

The TAA Signal System generates **tactical asset allocation signals** for 12 asset classes across Fixed Income and Equity. Given a set of inputs (macro, momentum, sentiment, valuation), it produces:

- A **z-score composite** per asset class (how attractive is this AC vs its own history?)
- An **absolute view** (OW / neutral / UW in isolation)
- A **relative view** (which ACs do I prefer over others?)
- A **final tilt** (% deviation from the SAA benchmark), capped at ±2–5% per asset class

Designed for insurance portfolios (Solvency II / NAIC RBC). Total tracking error budget: **50–150bp**.

### Asset Classes Covered

| Group | Asset Class | Key Benchmark |
|-------|-------------|---------------|
| FI | Money Market | T-bills / FDTR |
| FI | Short-Term FI | Bloomberg Treasury 1-5Y (BFU5TRUU) |
| FI | LT Treasuries | Bloomberg Global Govt (BSGVTRUU) |
| FI | LT US Corporate | Bloomberg US Aggregate (I26729US) |
| FI | LT EM Fixed Income | ICE BofA EM BBB Corp (BAMLEM2BRRBBB) |
| EQ | US Equity | S&P 500 TR (SPXT) |
| EQ | US Growth | S&P 500 Growth (SPTRSGX) |
| EQ | US Value | S&P 500 Value (SPTRSVX) |
| EQ | DM ex-US Equity | MSCI EAFE (NDDUEAFE) |
| EQ | EM Equity | MSCI EM (NDUEEGF) |
| EQ | EM ex-China | MSCI EM ex-China (M1CXBRV) |
| EQ | China Equity | MSCI China (NDEUCHF) |

### Signal Flow (Pipeline)

```
data/Dashboard_TAA_Inputs.xlsx
           |
    data_loader.py          proxies.py
    (10 data dicts)    (internal proxies from price data)
           |                    |
           +-----> main.py <----+
                   |
           build_bloomberg_series()   <-- non-empty overrides proxy
                   |
              ext dict (all signals)
                   |
             pillars.py
          F pillar   M pillar   S pillar   V pillar
                   |
             scoring.py
          composite z-score
                   |
         absolute view + relative view
                   |
           final tilt (35% abs + 65% rel)
                   |
          results/RUN_YYYYMMDD_HHMM/
```

---

## 2. Repository Structure

```
9_TAA Dashboard/
|
+-- src/                     <- all production Python code
|   +-- config.py            <- parameters, tickers, weights, thresholds (change here only)
|   +-- data_loader.py       <- loads all 10 Excel sheets; cleans and type-checks
|   +-- signals.py           <- atomic signal functions (z-scores, momentum, valuation)
|   +-- proxies.py           <- derives proxy signals from price data when live data absent
|   +-- pillars.py           <- builds F/M/S/V pillar scores for each of 12 asset classes
|   +-- scoring.py           <- composite -> conviction -> absolute/relative views -> tilt
|   +-- main.py              <- pipeline entry point; Bloomberg/FRED override hooks
|
+-- tests/
|   +-- test_system.py       <- 38 automated tests (must all pass before any deployment)
|
+-- data/
|   +-- Dashboard_TAA_Inputs.xlsx   <- primary data source (10 sheets)
|
+-- docs/
|   +-- TAA_System_Guide.md         <- this file
|   +-- TAA_Signal_Reference.html   <- authoritative signal specification (open in browser)
|   +-- TAA Signal Generation v1.0.md
|   +-- Dashboard TAA - Guidelines.docx
|
+-- results/
|   +-- RUN_YYYYMMDD_HHMM/   <- auto-created each run
|       +-- taa_scorecard.csv
|       +-- taa_composite_series.csv
|       +-- pillars_{ac}.csv (x12)
|
+-- research/                <- academic references
+-- CLAUDE.md                <- AI assistant instructions
+-- requirements.txt
```

**Module dependency chain (no circular imports):**
```
config -> data_loader -> signals -> proxies -> pillars -> scoring -> main
```

---

## 3. Data Architecture

### Excel Workbook: `data/Dashboard_TAA_Inputs.xlsx`

| Sheet | Rows | Period | Content |
|-------|------|--------|---------|
| `OAS` | 6,937 | 1999-2026 | ICE BofA credit spreads: BBB, HY, EM BBB, LatAm |
| `4` | 2,686 | 2015-2026 | Forward P/E, Earnings Yields, TR price levels |
| `5` | 2,669 | 2015-2026 | VIX, MOVE, VSTOXX, CDX, Treasury yields, PCR |
| `F1` | 2,692 | 2015-2026 | ISM PMI, CESI (US/EZ/China/Global), GDP forecasts |
| `F2` | 2,692 | 2015-2026 | PMI (Japan/UK/Global), CESI (UK/Japan/EM), GDP cont. |
| `F3` | 2,721 | 2015-2026 | Forward EPS (US/World/EM/China/EAFE), Breakevens, CPI |
| `AAII` | 10,105 | 1987-2026 | AAII Bull/Bear weekly sentiment (resampled daily) |

**Data loaded as** (`data_loader.py`): `oas`, `pe`, `yields`, `fi_px`, `tsy`, `cds`, `mkt`, `f1`, `f3`, `aaii`.

### Key Data Rule: Use `fi_px` (Sheet 4 TR columns) for All Momentum

The TR-based columns in Sheet 4 have only 2,686 rows (from 2015). For 12-1M momentum (which requires 252 trading days look-back), this limits signal history to ~2018 onwards.

For **OAS spread momentum**, the OAS sheet provides 26 years of history — the credit spread signals are therefore the best-anchored signals in the system.

### Adaptive Windows

All normalization functions use `min(target_window, available_observations)`. This prevents errors on short series (e.g., forward P/E available from 2015 uses ~10 years, close to the 10-year target). Interpretation adjusts accordingly: "cheap/expensive vs. 10-year history" for OAS, "cheap/expensive vs. available history" for P/E.

---

## 4. The Four Pillars

### Pillar I — Fundamentals (Leading Macro Indicators)

**Role:** Signals that lead markets 1–6 months. Tell you where the economy is going.

**Current status (as of April 2026): FULLY LIVE from Excel.**

| Signal | Source | Series | Notes |
|--------|--------|--------|-------|
| ISM Mfg PMI | Sheet F1 | `pmi_ism_mfg` | Blended with ISM Services |
| ISM Services PMI | Sheet F1 | `pmi_ism_svcs` | Blended with Manufacturing |
| Eurozone PMI | Sheet F1/F2 | `pmi_ez_mfg` + `pmi_ez_svcs` | Blended |
| China PMI (Caixin) | Sheet F1/F2 | `pmi_china_mfg` + `pmi_china_svcs` | Blended |
| CESI US | Sheet F1 | `cesi_us` | Contrarian at extremes |
| CESI Eurozone | Sheet F1 | `cesi_ez` | Contrarian at extremes |
| CESI China | Sheet F2 | `cesi_china` | Contrarian at extremes |
| CESI EM | Sheet F2 | `cesi_em` | Contrarian at extremes |
| GDP US | Sheet F1 | `gdp_us_cur` + `gdp_us_nxt` | Time-weighted blend |
| GDP EM/DM/EU/China | Sheet F1/F2 | region-specific | Time-weighted blend |
| Forward EPS revision | Sheet F3 | `eps_fwd_us` / `eps_fwd_em` / etc. | 1M pct_change -> ewma_z |
| Breakeven inflation | Sheet F3 | `breakeven_5y`, `breakeven_10y` | EWMA z-score 10Y window |

**Sign convention:**
- Equity: **direct** (+PMI = +signal)
- FI Duration: **inverted** (+PMI -> rates rise -> bonds fall -> x-1)
- Credit/EM FI: **direct** (growth = tighter spreads = positive)

---

### Pillar II — Momentum (Trend Following)

**Role:** Price persistence and spread dynamics. Highest information coefficient signal in multi-asset TAA.

**Current status: FULLY OPERATIONAL from Sheet 4 TR + OAS sheet.**

| Signal type | Weights | Source |
|-------------|---------|--------|
| 12-1M skip momentum | 40% | Sheet 4 TR prices |
| 3M price return | 25% | Sheet 4 TR prices |
| MA50/MA200 distance | 25% | Sheet 4 TR prices |
| RSI(14) mapped [-1,+1] | 10% | Sheet 4 TR prices |
| OAS 1M tightening | -- | OAS sheet (26Y history) |
| OAS 3M tightening | -- | OAS sheet (26Y history) |
| CDX IG/HY momentum | -- | Sheet 5 |

---

### Pillar III — Sentiment (Contrarian)

**Role:** Volatility regime, positioning, liquidity stress. Most signals are **contrarian**.

**Current status: PARTIALLY LIVE. Two critical gaps remain.**

| Signal | Status | Source | Notes |
|--------|--------|--------|-------|
| VIX percentile | LIVE | Sheet 5 | Non-linear contrarian scoring |
| MOVE Index | LIVE | Sheet 5 | FI volatility regime |
| VSTOXX | LIVE | Sheet 5 | EZ equity contrarian |
| PCR (Put/Call Ratio) | LIVE | Sheet 5 | Contrarian at extremes |
| AAII Bull-Bear | LIVE | AAII sheet | z-score 5Y, contrarian |
| EM BBB OAS (EMBI proxy) | LIVE | OAS sheet | Proxy for EMBI sovereign |
| TED Spread | **DEGRADED** | Sheet 5 | Data cuts off 2019-02-07 |
| DXY (USD Index) | **MISSING** | -- | No proxy available; EM signals incomplete |

---

### Pillar IV — Valuation (Long-term Anchor)

**Role:** Long-run mean-reversion anchor. Low predictive power short-term but powerful over 3–5 years.

**Current status: FULLY OPERATIONAL.**

| Signal | Source | Window |
|--------|--------|--------|
| Forward P/E percentile | Sheet 4 PE | Adaptive (available history) |
| Earnings yield | Sheet 4 EY | 10Y target |
| ERP (EY - TIPS 10Y real yield) | Sheet 4 EY + Sheet 5 TIPS | 10Y EWMA |
| OAS level percentile (BBB, HY, EM) | OAS sheet | 5Y and 10Y |
| Treasury yield level | Sheet 5 TSY | 10Y |
| Term spread 10Y-2Y | Sheet 5 TSY | 5Y |
| Relative P/E (Growth vs Value, US vs EM) | Sheet 4 PE | Adaptive |
| TIPS 5Y real yield | Sheet 5 | 10Y |

---

## 5. Signal Computation

All functions in `signals.py` follow these conventions:

### Normalisation Functions

```python
rolling_zscore(s, window, min_periods=None)
```
- Rolling mean/std z-score with adaptive window
- Always winsorised at +/-3sigma
- Use for: monthly PMI, slow structural series

```python
ewma_zscore(s, span=None)
```
- Exponentially weighted z-score (default span = 756 days = 3 years)
- **Preferred for all daily signals** — handles regime breaks by downweighting stale data
- Always winsorised at +/-3sigma
- Use for: price momentum, spread changes, CESI, EPS revisions

```python
pctile_rank(s, window)
```
- Rolling percentile [0,1]
- Use for: P/E (skewed), OAS levels, VIX (non-normal)

### Price Momentum Composite

```python
composite_price_momentum(price)
```
Combines five sub-signals:
- **12-1M skip momentum** (40%): return from 12M to 1M ago — highest IC empirically
- **3M return** (25%): medium-term trend
- **MA50/MA200 distance** (25%): trend-following confirmation
- **RSI(14)** (10%): overbought/oversold
- Missing sub-signals: weights redistributed automatically

### Valuation Signals

```python
pe_score(pe, window=None)          # score = -2 + 4 * (1 - pctile); cheap = +2
equity_risk_premium(ey, ry)        # ERP = Earnings Yield - Real Yield; EWMA z-score
oas_level_score(oas, window)       # wide spreads = +2; tight spreads = -2
yield_level_score(yield, window)   # high yield = attractive carry = positive
```

---

## 6. Proxy Signals

When live data is absent, `proxies.py` derives approximations from available Excel data. Each proxy is active only when the corresponding Bloomberg/FRED series returns an empty result.

| Proxy key | What it approximates | Derived from | Quality |
|-----------|---------------------|-------------|---------|
| `growth_proxy` | PMI / CESI | Cyclical/defensive sector return + OAS tightening speed | 3/5 |
| `credit_cycle` | Credit momentum | OAS tightening speed (BBB + HY) | 4/5 |
| `ts_regime` | GDP revision proxy | Term spread direction | 3/5 |
| `inflation` | Inflation regime | Fed Funds level + 10Y yield trend | 3/5 |
| `eps_us` / `eps_em` | EPS revision | Earnings yield direction + price direction | 3/5 |
| `hy_stress` | VIX proxy | HY OAS rapid widening + level stress | 3/5 |
| `ig_appetite` | TED spread proxy | CDX IG spread level and direction | 3/5 |
| `em_stress` | EMBI proxy | EM BBB + LatAm OAS level | 4/5 |
| `dxy` | **No proxy** | DXY requires FX rate data | 0/5 |
| `move` | **No proxy** | MOVE requires SIFMA bond vol data | 0/5 |

**Override logic:** in `main.py`, `build_bloomberg_series()` returns a dict of real signals from the Excel. Any non-empty Series automatically replaces the corresponding proxy. Connect live Bloomberg/FRED by populating that function.

---

## 7. Pillar Aggregation

The `_wavg()` function in `pillars.py` combines signals using a **DataFrame-based weighted average that handles NaN gracefully per row**:

```python
df  = pd.DataFrame(cols)       # one column per active signal
w_s = pd.Series(wts)           # weights
num = df.mul(w_s).sum(axis=1, min_count=1)
den = df.notna().mul(w_s).sum(axis=1).replace(0, np.nan)
composite = (num / den)        # weights renormalize per date automatically
```

This means a signal with a shorter history (e.g., TED spread truncated at 2019) naturally drops out of the combination for post-2019 dates, and the remaining signals carry proportionally more weight. No NaN contamination.

After combining, `standardise_pillar()` re-applies EWMA z-score to restore unit variance (correlated signals compress variance when summed; this corrects it).

### Sign Conventions

| Signal | Equity | FI Duration | FI Credit |
|--------|--------|-------------|-----------|
| PMI / GDP / CESI (growth) | + | x-1 | + |
| OAS tightening | n/a | + (flight-to-quality) | + |
| VIX / MOVE (stress) | contrarian | + (FTQ) | - |
| P/E level | x-1 via pe_score | n/a | n/a |
| ERP high | + | n/a | n/a |
| USD strong | - (via DXY) | n/a | EM: - |

---

## 8. Scoring & Views

### Step 1: Composite Z-score

Uses same DataFrame-based per-row weighted average as `_wavg()`. Pillars with no data on a given date are skipped; weights renormalize.

Pillar weights (from `config.py`):
- Money Market: V=50%, S=25%, M=15%, F=10% — dominated by carry/valuation
- LT Treasuries: V=30%, F=25%, M=25%, S=20%
- US Equity: M=30%, F=25%, V=25%, S=20%

### Step 2: Conviction Map

| Z composite | Label | Tilt fraction |
|:-----------:|-------|:-------------:|
| > +1.50 | HIGH OW | +1.0 |
| > +0.75 | MEDIUM OW | +0.5 |
| > -0.75 | NEUTRAL | 0.0 |
| > -1.50 | MEDIUM UW | -0.5 |
| <= -1.50 | HIGH UW | -1.0 |

### Step 3: Pillar Agreement Multiplier

| n pillars agree | Multiplier |
|:--------------:|:----------:|
| 4/4 | 1.00 |
| 3/4 | 0.80 |
| 2/4 | 0.50 |
| 1/4 or 0 | 0.00 |

### Step 4 - 6: Absolute + Relative Tilt

```python
abs_tilt   = tilt_fraction * conviction_mult * MAX_TILT_PCT[ac]
Z_rel      = (Z_comp - mean(universe)) / std(universe)
rel_tilt   = Z_rel * MAX_TILT_PCT[ac] * conviction_mult
final_tilt = 0.35 * abs_tilt + 0.65 * rel_tilt     # ALPHA_ABS = 0.35
final_tilt = clip(final_tilt, -MAX_TILT_PCT[ac], +MAX_TILT_PCT[ac])
```

### Crisis Override (Hard Rule)

When **both** VIX and MOVE exceed their 80th percentile simultaneously, all tilts are forced to zero. The override lifts only when both return below the 70th percentile.

---

## 9. Absolute vs Relative Views

**Absolute view:** "Is this asset class attractive vs its own history?"
- Z > 0 -> above-average attractiveness
- Multiple ACs can simultaneously score positive
- Drives: should I deviate from SAA at all?

**Relative view:** "Which AC do I prefer over the others?"
- Cross-sectional normalisation always produces winners and losers
- EM Equity with Z_abs = +1.8 and US Equity with Z_abs = +0.6 -> EM OW, US UW relative
- Drives: *where* to put the tilt

**Why 35/65 blend?** The relative view dominates because for a benchmark-constrained insurance portfolio, having a coherent ranking across ACs (OW equity, UW FI) matters more than magnitude. The absolute view prevents the model from tilting at all when every signal is near zero.

---

## 10. How to Run

### Prerequisites

```bash
cd "9_TAA Dashboard"
.venv\Scripts\pip install pandas numpy scipy openpyxl
```

### Run the Pipeline

```bash
python src/main.py
```

Produces a timestamped results folder:
```
results/RUN_20260416_1430/
    taa_scorecard.csv          one row per AC, latest snapshot
    taa_composite_series.csv   full composite z-score time series
    pillars_us_equity.csv      per-pillar z-scores (12 files)
    ...
```

### Run Tests

```bash
python tests/test_system.py
# Expected: 38/38 tests passed  ALL PASSED
```

### Debug a Single Asset Class

```python
from sys import path; path.insert(0, "src")
from main import run_pipeline
r = run_pipeline(verbose=False)
print(r["composites"]["us_equity"].tail(10))
print(r["scorecard"])
```

### Connect Live Bloomberg/FRED Data

Edit `build_bloomberg_series()` in `src/main.py`. Any non-empty `pd.Series` automatically overrides the corresponding proxy:

```python
# FRED (free, no key required)
def _fred(series_id):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    return pd.read_csv(url, index_col=0, parse_dates=True).squeeze().dropna()

ext["ted"]    = _fred("TEDRATE")     # TED spread -- fills the 2019 gap immediately
ext["dxy"]    = _fred("DTWEXBGS")    # DXY -- unlocks EM FI sentiment signals
ext["embi"]   = _fred("BAMLHE00EHY2Y")

# Bloomberg (via xbbg)
from xbbg import blp
ext["move"]   = blp.bdh("MOVE Index", "PX_LAST", "2000-01-01")["PX_LAST"]
```

---

## 11. Current Data Status

| Category | Series | Status | Gap / Action |
|----------|--------|--------|-------------|
| PMI (ISM, EZ, China, Japan) | Blended mfg + svcs | LIVE from F1/F2 | -- |
| CESI (US, EZ, China, EM) | Daily surprise index | LIVE from F1/F2 | Contrarian extremes partially implemented |
| GDP forecasts (US, DM, EM, EU, China) | Current + next year blend | LIVE from F1/F2 | -- |
| Forward EPS (US, World, EM, China, EAFE) | 1M revision | LIVE from F3 | -- |
| Breakeven inflation (5Y, 10Y) | Level z-score | LIVE from F3 | -- |
| VIX, MOVE, VSTOXX, PCR | Daily levels | LIVE from Sheet 5 | -- |
| CDX IG/HY | Spread / price levels | LIVE from Sheet 5 | -- |
| US yields (2Y, 10Y, TIPS 5Y, 10Y) | Level + term spread | LIVE from Sheet 5 | -- |
| AAII Bull-Bear | Weekly, resampled daily | LIVE from AAII | -- |
| EM BBB OAS (EMBI proxy) | Level z-score | LIVE from OAS | Proxy only; real EMBI better |
| **TED Spread** | BASPTDSP | **DEGRADED** | Cuts off 2019-02-07; FRED TEDRATE fills gap |
| **DXY (USD Index)** | DTWEXBGS | **MISSING** | EM signals incomplete without this |
| **MOVE Index** | MOVE Index BBG | LIVE | -- |
| CAPE (Shiller P/E) | -- | **NOT IMPLEMENTED** | Long-run US equity valuation |
| Real 3M T-bill | DTB3 | **NOT IMPLEMENTED** | Money market real carry signal |
| CFTC positioning | COT data | **NOT IMPLEMENTED** | Institutional positioning signals |

---

## 12. Test Suite

```
tests/test_system.py: 38 tests across 6 categories
----------------------------------------------------
IMPORTS          (6 tests)  -- all modules import without error
DATA LOADING    (10 tests)  -- sheet presence, date ordering, OAS history length,
                               fi_px/yields/tsy/mkt/f1/f3 present, no zero prices
SIGNALS          (8 tests)  -- normalisation correctness, sign conventions,
                               pe_score, erp, oas_level, composite_mom
PROXIES          (2 tests)  -- key completeness, winsorisation
BLOOMBERG        (3 tests)  -- pmi_us / vix / eps_us populated from Excel
PILLARS          (3 tests)  -- all 12 ACs compute, outputs bounded, 12/12 active
SCORING          (6 tests)  -- composite, conviction thresholds, pillar agreement,
                               scorecard shape, tilts within max, relative z mean=0
```

**Run before every deployment:** `python tests/test_system.py && python src/main.py`

---

## 13. Current Results — April 2026

### Latest Scorecard (2026-04-16)

```
Asset Class        Z_F     Z_M     Z_S     Z_V    Z_Comp  Agree   Conviction    FinalTilt%
------------------------------------------------------------------------------------------
Fixed Income
  Money Market    +1.53   -0.01   +2.51   -0.02    +0.77    2/4   MEDIUM OW       +0.2%
  Short-Term FI   -0.50   +0.06   +2.19   +1.23    +0.78    2/4   MEDIUM OW       +0.3%
  LT Treasuries   -0.50   -0.21   +2.33   +0.60    +0.47    2/4   NEUTRAL          0.0%
  LT US Corp      +0.11   +0.25   +0.19   +2.64    +0.93    2/4   MEDIUM OW       +0.3%
  LT EM FI        +0.02   +1.36   -3.00   +3.00    +0.56    2/4   NEUTRAL          0.0%

Equity
  US Equity       +0.27   +0.66   +1.58   +0.54    +0.72    4/4   NEUTRAL          0.0%
  US Growth       +0.27   +0.54   +1.58   +1.85    +1.04    4/4   MEDIUM OW       +0.5%
  US Value        +0.27   +0.79   +1.58   -0.33    +0.51    3/4   NEUTRAL          0.0%
  DM ex-US Eq     -1.31   -0.04   +1.55   -1.52    -0.41    2/4   NEUTRAL         -1.3%
  EM Equity       +0.02   +1.18   +3.00   +2.55    +1.60    3/4   HIGH OW         +2.2%
  EM ex-China     +0.02   +1.18   +3.00   +3.00    +1.71    3/4   HIGH OW         +2.4%
  China Equity    +1.61   -0.80   +2.99   +1.59    +1.16    3/4   MEDIUM OW       +0.4%
------------------------------------------------------------------------------------------
FI net tilt: +0.7%    Equity net tilt: +4.2%    Total |tilts|: 7.5%
```

### Key Observations

**EM ex-China is the strongest signal (+2.007 composite):** Valuation at +3.0 (P/E historically cheap), Sentiment at +3.0 (VIX elevated = contrarian buy), Momentum at +1.18 (positive trend). Three of four pillars clearly bullish.

**China Equity has a split signal:** Fundamentals strong (+1.61, driven by PMI and EPS revision), Sentiment near max (+2.99), but Momentum negative (-0.80). Classic "cheap and still falling" dynamic — justified MEDIUM OW but not HIGH OW.

**DM ex-US is the only relative underweight:** Fundamentals at -1.31 (Eurozone PMI weak) combined with Valuation at -1.52 (P/E not cheap relative to own history). Even with sentiment tailwind, the composite is negative.

**Sentiment pillar uniformly elevated (+1.5 to +3.0 across all equity):** High VIX percentile and elevated OAS levels are generating broad contrarian buy signals for equity. This is structurally consistent with the April 2026 volatility environment but should be cross-checked against the DXY (currently missing) which would differentiate US vs. EM.

**Pillar Agreement at 2/4 for most FI classes:** The conviction multiplier is 0.50x for FI, capping absolute tilts at half of MAX_TILT_PCT. This is correct behavior — FI signals are genuinely mixed (valuation positive, momentum negative, sentiment elevated due to flight-to-quality).

---

## 14. Challenges & Known Limitations

### 14.1 Data Gaps

**TED Spread truncates at 2019-02-07.** The BASPTDSP Index in Sheet 5 ends there. In the current build, the TED signal participates in the Sentiment pillar for 2015–2019 but is absent thereafter. The DataFrame-based `_wavg()` handles this gracefully (weights redistribute), but the Sentiment pillar is less informative for funding stress signals post-2019. **Fix: pull FRED TEDRATE, which runs to present.**

**DXY (USD Index) is completely absent.** This is a critical gap for EM equity and EM FI. USD strength is the dominant driver of EM asset returns across regimes (Koijen et al. 2018 show DXY explains ~35% of EM return variance). Without it, the Sentiment and Fundamentals pillars for `em_equity`, `em_xchina`, `lt_em_fi`, and `china_equity` are missing their most powerful driver. **Fix: FRED DTWEXBGS (free, daily, from 1973).**

**EMBI sovereign spread replaced by EM BBB corporate OAS.** The EM BBB OAS captures credit risk in EM corporates, not EM sovereign stress. During sovereign-specific episodes (e.g., Argentina, Turkey), these diverge significantly. **Fix: FRED BAMLHE00EHY2Y (EM HY sovereign OAS).**

**No CAPE (Shiller P/E) for US equity.** The forward P/E in Sheet 4 covers only from 2015. For long-run valuation context — detecting whether US equity is in a decade-long expensive regime vs. short-term dislocation — the Shiller CAPE over 130+ years is irreplaceable. **Fix: FRED CAPE10 (free, monthly from 1880).**

**No real 3M T-bill rate for Money Market.** The Money Market valuation pillar is missing its most important signal: whether cash is genuinely attractive on a real yield basis. Nominal yield is high but CPI context is needed. **Fix: FRED DTB3 (T-bill 3M) minus CPIAUCSL (CPI) = real cash yield.**

### 14.2 Methodology Limitations

**No empirical validation of signal weights.** All pillar weights within `_wavg()` and all pillar-to-composite weights in `PILLAR_WEIGHTS` are prior beliefs derived from the literature and framework design. They have never been tested against actual forward returns from this system. Until a walk-forward backtest measures IC (Information Coefficient) per signal, there is no evidence that the chosen weights are optimal vs. equal-weighting.

**Short sample history (2015 start).** Most signals have only ~10 years of data. The 10-year valuation windows are therefore operating at or near their minimum effective length. Regime diversity is limited: 2015-2026 includes one full tightening cycle, one COVID shock, and one post-COVID inflationary regime — but no 2008-style credit crisis or 2000-style equity bubble cycle. Signal behavior in those regimes is untested.

**CESI contrarian-at-extremes not fully wired.** The CLAUDE.md specification requires: when CESI is above 85th percentile or below 15th percentile, flip the sign (contrarian). The current implementation uses CESI directionally for all percentile levels. This is a known divergence from the methodology spec.

**Pillar Agreement Multiplier of 0.50x at 2/4 agreement is generous.** When only 2 of 4 pillars agree (which currently describes most FI signals), the system still assigns half the maximum tilt. Academic evidence (MSCI, AQR) suggests that when signals conflict, the tilt should be close to zero, not 50% of full conviction. Tightening this to 0.25x at 2/4 would be more conservative.

**No transaction cost or turnover constraint.** The system computes optimal tilts without regard to the bid-ask cost of rebalancing. For insurance portfolios with large notional exposures, tilt changes of 1-2% can represent hundreds of millions in trades. The system needs a turnover dampener (e.g., only rebalance if tilt change > 0.5% absolute).

**Tracking error estimate is a simple approximation.** The console displays `total_tilts * 0.16 = TE bps` which uses a flat 16% volatility assumption. Actual tracking error depends on the covariance matrix of all tilted asset classes — correlated tilts (e.g., OW EM equity AND EM FI simultaneously) can produce much higher or lower TE than the simple sum suggests.

### 14.3 Architectural Limitations

**No time-series export of the composite score history.** While `taa_composite_series.csv` is exported, there is no way to visualise signal evolution, detect drift, or compare today's scorecard to 6 months ago without loading CSVs manually.

**No alert/monitoring layer.** Large signal moves (e.g., composite z-score crosses +1.5 threshold, triggering a conviction change) produce no notification. In production, this should trigger an investment committee alert.

**Backtesting is absent.** The system has never been run in a simulated forward-looking mode where signals from date T predict returns from T to T+N. Without this, IC, IR, and optimal weight calculations are impossible.

---

## 15. Roadmap to an Exceptional TAA System

### Tier 1 — Near-term Improvements (1–4 weeks)
*Fix the remaining data gaps. These are all free data sources requiring < 1 day to connect each.*

---

**T1.1 — Connect FRED Free Data Series**

All of these can be pulled with a single function and zero cost:

```python
def _fred(series_id):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    return pd.read_csv(url, index_col=0, parse_dates=True).squeeze().dropna()
```

| Priority | FRED Series | Key | Impact |
|----------|-------------|-----|--------|
| Critical | `TEDRATE` | `ted` | Fills Sentiment gap post-2019 immediately |
| Critical | `DTWEXBGS` | `dxy` | Unlocks EM signals (currently missing driver) |
| High | `BAMLHE00EHY2Y` | `embi` | True EM sovereign spread vs. EM corp proxy |
| High | `CAPE10` | `cape_us` | 130Y US valuation context for LT signals |
| High | `DTB3` | `tbill_3m` | Real money market yield (DTB3 - CPI) |
| Medium | `VIXCLS` | `vix` | Independent cross-check vs. Sheet 5 VIX |
| Medium | `T5YIE` | `breakeven_5y` | Independent cross-check vs. Sheet F3 |
| Medium | `DFII10` | `tips_10y` | Real yield for ERP (more authoritative than Sheet 5) |
| Medium | `CPCE` | `pcr` | CBOE equity-only PCR (more precise than PCR from Sheet 5) |

**T1.2 — Fix TED Spread Gap Specifically**

The Sheet 5 BASPTDSP data ends 2019-02-07. The simplest fix is a hybrid loader:
```python
# In data_loader.py -> load_mkt():
if "ted" in out.columns:
    ted_fred = _fred("TEDRATE")     # LIBOR-based, ends 2023
    sofr_ted = _fred("SOFR")        # SOFR-based proxy for 2023+
    out["ted"] = out["ted"].combine_first(ted_fred).combine_first(sofr_ted)
```
Note: LIBOR was discontinued in June 2023. For 2023+, use SOFR spread over T-bills or ICE SONIA spread as a successor TED proxy.

**T1.3 — Implement CESI Contrarian at Extremes**

Add percentile check to `pillar_fundamentals()` in `pillars.py`:

```python
def _cesi_with_flip(raw_cesi, window=WINDOWS["medium"]):
    pctile = pctile_rank(raw_cesi, window)
    z = ewma_zscore(raw_cesi)
    # At extremes: flip sign (contrarian mean-reversion logic)
    z_adj = z.copy()
    z_adj[pctile > 0.85] = -z[pctile > 0.85]
    z_adj[pctile < 0.15] = -z[pctile < 0.15]
    return z_adj
```

**T1.4 — Wire ISM New Orders / Inventories Ratio**

The `.ISM G Index` column (`ism_new_ord_inv`) is loaded in Sheet F1 but not yet used in the US equity Fundamentals pillar. This ratio (ratio > 1.0 = demand expanding faster than inventories) has one of the highest ICs of all ISM sub-components for US equity returns.

```python
# In pillar_fundamentals() for us_equity:
ism_ratio = _get(f1, "ism_new_ord_inv")
if ism_ratio is not None:
    ism_ratio_z = ewma_zscore(ism_ratio - 1.0)  # centered at 1.0
    signals["ism_noi"] = ism_ratio_z
    weights["ism_noi"] = 0.10  # add 10%, reduce others proportionally
```

**T1.5 — Add Real 3M T-bill Signal to Money Market Valuation**

```python
# In pillar_valuation() for money_market:
tbill = _get(tsy_df, "tbill_3m")     # already in Sheet 5 as "H15X5YR Index" -- but check
cpi   = _get(f1, "cpi_us")           # CPI YoY from Sheet F3
if tbill is not None and cpi is not None:
    real_cash = tbill.sub(cpi, fill_value=np.nan)
    real_cash_z = rolling_zscore(real_cash, WINDOWS["vlong"])
    signals["real_cash"] = real_cash_z
    weights["real_cash"] = 0.20
```

---

### Tier 2 — Medium-term Improvements (1–3 months)
*Add new signals, build a backtesting framework, improve scoring robustness.*

---

**T2.1 — Walk-Forward Backtesting Framework**

This is the most important medium-term priority. Without it, you cannot answer: "Does this system actually predict returns?"

Build `src/backtest.py`:

```python
def walk_forward_ic(signals_df, returns_df, horizons=[21, 63, 126]):
    """
    For each signal column, compute rolling IC = corr(signal_t, return_{t+h}).
    Returns IC time series, mean IC, ICIR (IC / std(IC)).
    Walk-forward: re-estimate using only data available at time t.
    """
    results = {}
    for horizon in horizons:
        fwd_returns = returns_df.shift(-horizon)
        ic_series = signals_df.corrwith(fwd_returns, axis=1)  # rolling 252d
        results[f"IC_{horizon}d"] = ic_series
    return pd.DataFrame(results)
```

Target ICs for a well-calibrated system:
- Momentum signals: IC 0.05–0.10 at 3M horizon (well-documented)
- Valuation signals: IC 0.02–0.05 at 12M horizon
- Fundamental signals: IC 0.03–0.08 at 1–3M horizon

**T2.2 — IC-Weighted Signal Aggregation (Replace Fixed Weights)**

Once you have IC estimates, replace hardcoded `weights` dicts in `pillars.py` with IC-proportional weights:

```python
def ic_weights(ic_dict, shrinkage=0.5):
    """Shrink toward equal weight to avoid overfitting."""
    n = len(ic_dict)
    eq = {k: 1/n for k in ic_dict}
    icir = {k: v / ic_dict[k].std() for k, v in ic_dict.items()}
    w_raw = {k: max(v, 0) for k, v in icir.items()}  # floor at 0
    total = sum(w_raw.values()) or 1
    w_norm = {k: v/total for k, v in w_raw.items()}
    return {k: (1-shrinkage)*w_norm[k] + shrinkage*eq[k] for k in ic_dict}
```

**T2.3 — Add CAPE as Long-Run US Equity Valuation Signal**

Shiller CAPE from FRED (`CAPE10`) goes back to 1880. It is the most robust long-run equity valuation measure available. At current levels (~33x), it signals historically expensive US equities.

Integration:
```python
cape = _fred("CAPE10")
cape_pctile = pctile_rank(cape, window=252*40)  # 40Y window captures multiple regimes
cape_score  = -2 + 4 * (1 - cape_pctile)        # same formula as pe_score
```

Use as a 20% weight within the US equity Valuation pillar alongside the existing forward P/E. The two are complementary: forward P/E is short-run, CAPE is long-run.

**T2.4 — US Sector Rotation Model (Within US Equity)**

Add a sub-module `src/sectors.py` that computes momentum and fundamentals signals for the 11 GICS sectors using tickers already in Sheet 4 (S5INFT, S5ENRS, S5UTIL, S5INDU, S5HLTH, S5MATR, S5CONS, S5TELS, S5RLST, S5COND, S5FINL). Sectors that score best get a tilt within the US equity allocation — a second layer of active management.

**T2.5 — Macro Regime Overlay (Fed Cycle)**

Replace the simple crisis override with a richer 4-phase Fed cycle regime:

| Phase | Fed Funds direction | Yield curve | Impact on signals |
|-------|--------------------|-----------|--------------------|
| Hiking | Rising | Flattening | Cut equity momentum weight; raise FI valuation weight |
| Peak | Flat / near top | Inverted | Maximum recession risk; raise FI duration weight |
| Cutting | Falling | Steepening | Raise equity momentum; raise credit weight |
| Trough | Flat / near bottom | Steep | Growth signals most predictive |

Regime detection from `fedrate` + `term_spread` (both already in data):
```python
def fed_regime(fedrate, term_spread):
    rate_delta = fedrate.diff(63)     # 3M change in Fed Funds
    hiking  = rate_delta > 0.25
    cutting = rate_delta < -0.25
    inverted = term_spread < 0
    # Return 4-state regime: 0=hiking, 1=peak, 2=cutting, 3=trough
```

Use regime to dynamically adjust `PILLAR_WEIGHTS` in `config.py` instead of fixed weights.

**T2.6 — Solvency II SCR Impact Calculator**

Insurance portfolios must estimate SCR (Solvency Capital Requirement) changes from any tilt. Add a module `src/scr.py`:

```python
SCR_CHARGES = {
    "us_equity":     0.39,  # 39% equity shock (SII Type 1)
    "dm_equity":     0.39,
    "em_equity":     0.49,  # 49% equity shock (SII Type 2)
    "china_equity":  0.49,
    "lt_us_corp":    0.08,  # spread shock at BBB duration ~7Y
    "lt_em_fi":      0.12,
    "lt_treasuries": 0.04,  # interest rate shock
}

def scr_impact(scorecard_df, portfolio_nav):
    """Returns SCR delta (EUR/USD) for each proposed tilt."""
    return {ac: row["final_tilt_%"]/100 * portfolio_nav * SCR_CHARGES.get(ac, 0)
            for ac, row in scorecard_df.iterrows()}
```

**T2.7 — Turnover / Transaction Cost Dampener**

Prevent excessive rebalancing by only updating tilts when the signal has moved materially:

```python
MIN_TILT_CHANGE = 0.50   # only rebalance if tilt changes by >= 50bp
prev_tilts = load_last_scorecard()
new_tilts  = score_snapshot(pillar_scores)
for ac in ASSET_CLASSES:
    if abs(new_tilts.loc[ac, "final_tilt_%"] - prev_tilts.loc[ac, "final_tilt_%"]) < MIN_TILT_CHANGE:
        new_tilts.loc[ac, "final_tilt_%"] = prev_tilts.loc[ac, "final_tilt_%"]  # hold
```

---

### Tier 3 — Exceptional System Improvements (3–12 months)
*These would make this system genuinely institutional-grade and differentiated.*

---

**T3.1 — Interactive HTML/Plotly Dashboard**

Replace the console scorecard with a Plotly Dash web app showing:
- Real-time scorecard heatmap (color: conviction level)
- Time series of composite z-scores per AC (12 panels)
- Pillar breakdown drilldown per AC
- Historical tilt evolution chart
- Signal-level transparency table
- Regime indicator (Fed cycle, VIX regime, credit cycle phase)

Launch with `python src/dashboard.py` -> opens at `localhost:8050`.

**T3.2 — 2-State Hidden Markov Model Regime Detection**

Rather than the binary VIX/MOVE crisis override, implement a probabilistic 2-state HMM on daily returns:

- State 0 (Risk-on): low vol, tight spreads, upward-sloping curve
- State 1 (Risk-off): elevated vol, wide spreads, inverted curve or flight-to-quality

Signal weights shift continuously based on P(State=1):
```python
from hmmlearn.hmm import GaussianHMM
# Fit on: VIX, HY OAS, term spread, US equity return vol
# Output: regime probability per day
# Use as weight adjuster: if P(risk-off) > 0.70, reduce equity weights by 30%
```

**T3.3 — Add Commodity Asset Class**

The current universe is pure FI + equity. Commodities (Gold, Oil, Diversified Commodity Index) offer genuine diversification during inflationary regimes and are relevant for insurance portfolios with inflation-linked liabilities.

New asset classes to add:
- `gold` — Gold TR: signal from real yields (inverted), USD (inverted), VIX (positive)
- `oil_commods` — Bloomberg Commodity Index: signal from PMI (positive), inventory levels
- `inflation_linked` — TIPS / IL bonds: signal from breakeven direction, real yield level

**T3.4 — DM Country Breakdown (Eurozone vs Japan vs UK vs Australia)**

Currently `dm_equity` is a single asset class. For meaningful tilts within DM, split into:
- `ez_equity` (Eurozone): driven by ECB cycle, EZ PMI, EUR strength
- `japan_equity`: driven by BoJ, JPY weakness, export PMI
- `uk_equity`: driven by BoE, GBP, UK CESI
- `dm_other` (Canada, Australia, Switzerland): residual

All PMI and CESI series for these regions are already loaded in F1/F2 — only `pillars.py` additions required.

**T3.5 — Machine Learning Signal Combination**

Replace the linear weighted average within each pillar with a gradient-boosted tree trained to predict 3M forward returns:

```python
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler

# Features: all z-scored signals for an asset class
# Target: 63-day forward return (winsorised at +-3 std)
# Train: expanding window, minimum 3Y in-sample
# Predict: next period's expected return (becomes the pillar score)
```

Key constraint: use expanding (not rolling) windows to avoid look-ahead bias. Evaluate OOS IR vs. the linear baseline — if IR improves significantly, adopt; if not, the linear model is more robust.

**T3.6 — Factor Timing Overlay (AQR-inspired)**

In addition to the cross-asset TAA signals, implement a within-equity **factor timing** layer:

- Value factor: P/B spread between cheap/expensive deciles -> tilt toward value when spread is historically wide
- Momentum factor: cross-sectional momentum across 12 equity ACs -> weight toward winner ACs
- Low vol factor: VIX regime -> in high-VIX regimes, tilt toward low-vol / quality stocks
- Growth factor: EPS revisions -> tilt toward high-revision regions

This creates a 3-layer system: SAA benchmark -> TAA tilt (this system) -> factor tilt (new layer).

**T3.7 — Alternative Data Integration**

Signals with genuinely orthogonal information to traditional macro:

| Data source | Signal | Access |
|-------------|--------|--------|
| Google Trends | "recession" search queries -> consumer fear | `pytrends` library, free |
| EPFR Fund Flows | Weekly ETF flows by asset class -> positioning | Bloomberg / Refinitiv |
| Satellite shipping | Global trade volume (ships at sea) -> real PMI cross-check | Quandl, paid |
| ESG sentiment | Carbon risk scores per region -> regulatory headwinds | MSCI ESG, Bloomberg ESG |
| Credit card data | Consumer spending velocity -> earnings beat prediction | Bloomberg, Yodlee |

**T3.8 — FX Overlay for Currency-Hedging Decisions**

For a EUR-based insurance investor, currency exposure carries both P&L and SCR implications. Add a `src/fx_overlay.py` module:

- For each non-EUR asset class: compute hedge cost (forward premium/discount)
- Signal: hedge when carry cost < expected FX return; unhedge when carry favorable
- Key pairs: EUR/USD (S&P 500 hedging), EUR/JPY, EUR/GBP, EUR/CNY (EM)

**T3.9 — Automated Investment Committee Report (PDF)**

Weekly auto-generated PDF with:
- Executive summary: top 3 changes from last week
- Scorecard heatmap + conviction changes
- Key signal alerts (threshold crossings)
- Backtest performance attribution (if backtesting framework is built)
- Risk dashboard: SCR impact of current tilts, TE budget utilization

Generate with `reportlab` or `weasyprint` (HTML to PDF).

---

### Summary Priority Matrix

| Priority | Item | Effort | Impact | Data cost |
|----------|------|--------|--------|-----------|
| **Must do first** | T1.1 FRED free data (TED, DXY, EMBI, CAPE) | 1 day | Very high | Free |
| **Must do first** | T1.3 CESI contrarian at extremes | 2 hours | Medium | Already have data |
| **Must do first** | T1.4 ISM New Orders/Inventories ratio | 1 hour | Medium | Already have data |
| **High value** | T2.1 Walk-forward backtesting | 2–3 weeks | Critical | None |
| **High value** | T2.5 Fed cycle regime overlay | 1 week | High | Free (FRED) |
| **High value** | T2.6 SCR impact calculator | 3 days | High for insurance | None |
| **Medium value** | T2.3 CAPE for US equity | 1 hour | High | Free (FRED) |
| **Medium value** | T2.4 Sector rotation | 2 weeks | Medium | Data in Excel |
| **Differentiator** | T3.1 Plotly dashboard | 2 weeks | High (usability) | None |
| **Differentiator** | T3.3 Commodities AC | 2 weeks | High (diversification) | Bloomberg |
| **Long-term** | T3.5 ML signal combination | 4–8 weeks | High if ICs confirm | None |
| **Long-term** | T3.4 DM country breakdown | 1 week | Medium | Data in F1/F2 |

---

*TAA Signal System — Technical Guide v2.0 · April 2026*
