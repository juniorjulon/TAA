# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**TAA Dashboard** is an institutional-grade Tactical Asset Allocation (TAA) signal generation system for insurance portfolios. It scores 12 asset classes across four signal pillars — **Fundamentals (F), Momentum (M), Sentiment (S), Valuation (V)** — then maps composite z-scores to conviction-based tilts around strategic benchmarks.

For insurance portfolios (Solvency II / NAIC RBC), tilts are capped at **±5%** per asset class with a tracking error budget of **50–150bp**. A +3% equity tilt consumes ~1.2% incremental SCR.

The authoritative signal specification is **`TAA_Signal_Reference.html`** (open in browser). This CLAUDE.md is the implementation guide derived from it.

**Single source of truth for configuration**: `config/taa_config.xlsx` -- edit this file to add/modify signals, asset classes, or pillar weights, then run `python src/build_dashboard.py` to propagate changes into `index.html` and `src/config.py`.

---

## Complete Run Guide

### Script inventory

| Script | What it does | Key output(s) |
|---|---|---|
| `src/seed_taa_config.py` | One-time seed -- creates `config/taa_config.xlsx` from scratch | `config/taa_config.xlsx` |
| `src/build_dashboard.py` | Reads Excel, regenerates 5 JS blocks in `index.html` and 3 Python blocks in `src/config.py` | `index.html`, `src/config.py` |
| `src/main.py` | Full TAA signal pipeline (data -> z-scores -> tilts) | `results/RUN_*/taa_scorecard.csv`, `taa_composite_series.csv`, `pillars_{ac}.csv` |
| `src/chartbook_data.py` | Extracts signal-level time series from pipeline results | `results/chartbook_data.json` (~4.6 MB) |
| `src/generate_dashboard.py` | Embeds CSVs + JSON into a standalone HTML dashboard | `dashboard.html` |
| `src/generate_methodology_doc.py` | Generates the consolidated Word methodology reference | `docs/TAA_Methodology.docx` |
| `src/test_build_layer.py` | 29-check health test for the config/build/doc layer | Exit 0 = all pass |

### Full pipeline from scratch

```
Step 1 -- Edit config (if needed)
    config/taa_config.xlsx
    Sheets: AssetClasses, DataSeries, PillarWeights, PillarNotes, SignalMapping

Step 2 -- Propagate config changes to code
    python src/build_dashboard.py
    -> index.html      5 JS blocks updated (SIG_MATRIX, AC_META, FI/EQ blueprints, PW)
    -> src/config.py   3 Python blocks updated (ASSET_CLASSES, PILLAR_WEIGHTS, MAX_TILT_PCT)

Step 3 -- Run TAA signal pipeline
    python src/main.py
    -> results/RUN_YYYYMMDD_HHMM/taa_scorecard.csv       latest z-scores + tilt per AC
    -> results/RUN_YYYYMMDD_HHMM/taa_composite_series.csv full composite history
    -> results/RUN_YYYYMMDD_HHMM/pillars_{ac}.csv         per-AC pillar history (x12)

Step 4 -- Extract chartbook series
    python src/chartbook_data.py
    -> results/chartbook_data.json   5Y of every signal, used by dashboard charts

Step 5 -- Regenerate dashboard HTML
    python src/generate_dashboard.py
    -> dashboard.html   standalone file, open in any browser on file://

Step 6 -- Regenerate methodology Word doc (when methodology changes)
    python src/generate_methodology_doc.py
    -> docs/TAA_Methodology.docx

Step 7 -- Health check (always run last)
    python src/test_build_layer.py
    Exit 0 = 29/29 checks passed
    Exit 1 = list of failed checks printed
```

### Minimal weekly refresh (no config change)

```bash
python src/main.py                      # re-run signals on new market data
python src/chartbook_data.py            # rebuild chartbook series
python src/generate_dashboard.py        # refresh dashboard.html
python src/test_build_layer.py          # confirm integrity
```

### When only config/taa_config.xlsx changes

```bash
python src/build_dashboard.py           # Excel -> index.html + src/config.py
python src/generate_methodology_doc.py  # refresh Word doc
python src/test_build_layer.py          # verify all 29 checks pass
# Then re-run Steps 3-5 above to pick up new weights/signals in the pipeline
```

### First-time setup (empty repo)

```bash
python src/seed_taa_config.py           # creates config/taa_config.xlsx (run once)
# Edit config/taa_config.xlsx as needed
python src/build_dashboard.py           # push config into index.html + config.py
python src/test_build_layer.py          # verify
```

## System Architecture

### Data Flow

```
1. data_loader.py    →  loads Dashboard_TAA_Inputs.xlsx (6 sheets)
2. proxies.py        →  derives sentiment proxies from price data (VIX, MOVE, TED)
3. main.py           →  merges Bloomberg/FRED overrides with proxies (Bloomberg wins)
4. signals.py        →  atomic z-score functions (rolling, EWMA, percentile)
5. pillars.py        →  four pillars per asset class (F, M, S, V)
6. scoring.py        →  composite → conviction → absolute+relative view → tilt
7. main.py           →  exports taa_scorecard.csv, taa_composite_series.csv
```

### Module Responsibilities

| File | Responsibility |
|---|---|
| `config.py` | All tickers, column maps, windows, pillar weights, conviction thresholds — **change here only** |
| `data_loader.py` | Loads 6 Excel sheets; forward-fills max 5 days; clips daily returns >±5σ |
| `signals.py` | Atomic z-score primitives — all return `pd.Series` with DatetimeIndex |
| `pillars.py` | Builds F, M, S, V pillar scores per asset class; handles sign inversions |
| `proxies.py` | Derives VIX/MOVE/TED proxies from price data when live data is absent |
| `scoring.py` | Composite → pillar agreement multiplier → absolute+relative views → tilt |
| `main.py` | Pipeline entry point; Bloomberg/FRED override placeholders |

---

## Running the System

```bash
# Full pipeline (verbose)
python main.py

# Outputs (in /mnt/user-data/outputs/):
#   taa_scorecard.csv          one row per asset class, latest snapshot
#   taa_composite_series.csv   full time series of composites
#   pillars_{ac}.csv           per-asset-class pillar time series

# Unit tests
python test_system.py

# Debug a single asset class
python -c "
from main import run_pipeline
r = run_pipeline(verbose=False)
print(r['composites']['us_equity'].tail(10))
print(r['scorecard'])
"
```

**Connect live data** (Bloomberg/FRED) by editing `build_bloomberg_series()` in `main.py`. Non-empty Series automatically override proxies:
```python
from fredapi import Fred
fred = Fred(api_key=os.getenv('FRED_API_KEY'))
ext['vix'] = fred.get_series('VIXCLS')
ext['ted'] = fred.get_series('TEDRATE')
```

---

## Excel Input: `Dashboard_TAA_Inputs.xlsx`

Sheet structure updated April 2026: sheets renamed H1–H6, histories extended to 2010, new series added.

| Sheet | Rows | Period | Content |
|---|---|---|---|
| `OAS` | ~6,937 | 1999–2026 | ICE BofA credit spreads: BBB, HY, EM BBB, LatAm |
| `H4` | 3,991 | 2010–2026 | Forward P/E, EY, TR price levels (12 equity/FI indices) |
| `H5` | 4,044 | 2010–2026 | VIX, MOVE, VSTOXX, CDX, Treasury yields, TIPS, DXY, BFCIUS (FCI), SOFRRATE, PCE YoY, Breakevens |
| `H6` | 3,991 | 2010–2026 | MSCI World + S&P 11 sectors — Forward PE, EY, TR (36 cols) |
| `H1` | 4,003 | 2010–2026 | ISM PMI (mfg/svcs/employment), CESI (US/EZ/China/Global), GDP (US/DM/EM/EU/World) |
| `H2` | 3,960 | 2010–2026 | PMI (Japan/UK/Global), CESI (UK/Japan/EM), GDP (Japan/China/LatAm) |
| `H3` | 3,991 | 2010–2026 | Forward EPS: US, World, EM, China, Japan, EAFE, LatAm |
| `AAII` | 10,105 | 1987–2026 | AAII Bull/Bear weekly (resampled to daily via ffill) |

**Key new series (April 2026):**
- `DXY` (H5): USD Index from 2011 — wired into EM sentiment (strong USD = EM headwind)
- `BFCIUS` (H5): Bloomberg US FCI from 2011 — wired into US equity/credit sentiment (tight = headwind)
- `SOFRRATE` (H5): SOFR rate from 2018 — `modern_ted = tbill_3m − SOFR` (replaces defunct BASPTDSP)
- `PCE CYOY` (H5): Core PCE monthly — `real_ff = FDTR − PCE` wired into money_market fundamentals
- `Breakevens 5Y/10Y` (H5): moved from H3; wired into FI/equity fundamentals

**Critical**: Always use **H4 TR columns** for equity/FI momentum — 15Y history from 2010.
`config.py:EXCEL_PATH` resolves to `data/Dashboard_TAA_Inputs.xlsx` relative to the project root.

---

## Asset Class Universe

12 asset classes defined in `config.py:ASSET_CLASSES`:

| Key | Label | Group |
|---|---|---|
| `money_market` | Money Market | FI |
| `short_term_fi` | Short-Term FI | FI |
| `lt_treasuries` | LT Treasuries | FI |
| `lt_us_corp` | LT US Corporate | FI |
| `lt_em_fi` | LT EM Fixed Income | FI |
| `us_equity` | US Equity | EQ |
| `us_growth` | US Growth | EQ |
| `us_value` | US Value | EQ |
| `dm_equity` | DM ex-US Equity | EQ |
| `em_equity` | EM Equity | EQ |
| `em_xchina` | EM ex-China | EQ |
| `china_equity` | China Equity | EQ |

---

## Signal Universe & Tickers

Full specification in `TAA_Signal_Reference.html`. Key series by pillar:

### Pillar I — Fundamentals

**PMI Series (Bloomberg, monthly, 60-month z-score)**

| Signal | Ticker | Asset classes |
|---|---|---|
| ISM Manufacturing PMI | `NAPMPMI Index` | US Eq `++`, UST `−`, STFI `−` |
| ISM Services PMI | `NAPMNMI Index` | US Eq `+`, LT Tsy `−` |
| ISM New Orders / Inventories | `.ISM G Index` | US Eq `++`, Corp `+` (ratio > 1.0 = demand expanding) |
| ISM Mfg Employment | `NAPMEMPL Index` | US Eq `+` |
| ISM Mfg New Export Orders | `NAPMNEWO Index` | US Eq `+`, EM Eq `+` |
| Eurozone Mfg PMI | `MPMIEZMA Index` | DM Eq `+`, EZ Eq `++` |
| Eurozone Services PMI | `MPMIEZSA Index` | EZ Eq `+` |
| China Mfg PMI (Caixin) | `CPMINDX Index` | China Eq `++`, EM Eq `+`, LT EM FI `+` |
| China Services PMI | `MPMICNSA Index` | China Eq `+` |
| Japan Mfg PMI | `MPMIJPMA Index` | DM Eq `+` |
| Global Mfg PMI | `MPMIGLMA Index` | All Eq `+`, LT EM FI `+` |

Compute for each: level z-score (60M), Δ3M direction, and for US/China/EZ: 4-quadrant regime score.

**Economic Surprise (CESI — Bloomberg, daily, 252-day z-score)**

⚠️ **CESI mean-reverts toward zero.** At extremes (percentile > 85% or < 15%): use **contrarian** signal (flip sign). In mid-range: use directional.

| Signal | Ticker |
|---|---|
| CESI United States | `CESIUSD Index` |
| CESI Eurozone | `CESIEUR Index` |
| CESI China | `CESICNY Index` |
| CESI Global | `CESIGL Index` (background/context only) |
| CESI Emerging Markets | `CESIEM Index` |
| CESI UK | `CESIGBP Index` |
| CESI Japan | `CESIJPY Index` |

Compute: level z-score + Δ20d direction. US CESI inverted for FI pillars.

**GDP Forecasts (Bloomberg ECGD series, daily)**

Blend current-year and next-year with time-varying weights: `w_current = month/12` (January: 8% current / 92% next; December: 100% current). **Month-over-month revision** (Δ1M in consensus) is more predictive than level.

| Region | Tickers |
|---|---|
| United States | `ECGDUS 26`, `ECGDUS 27` |
| Eurozone | `ECGDEU 26`, `ECGDEU 27` |
| Developed Markets | `ECGDD1 26`, `ECGDD1 27` |
| Emerging Markets | `ECGDM1 26`, `ECGDM1 27` |
| China | `ECGDCN 26`, `ECGDCN 27` |
| Japan | `ECGDJP 26`, `ECGDJP 27` |
| LatAm | `ECGDR4 26`, `ECGDR4 27` |

**Earnings (Bloomberg BEST fields)**

| Signal | Index | Field |
|---|---|---|
| US Fwd EPS Growth | `SPX Index` | `BEST_EPS_GRO` |
| EM Fwd EPS Growth | `MXEF Index` | `BEST_EPS_GRO` |
| Eurozone Fwd EPS Growth | `MXEMU Index` | `BEST_EPS_GRO` |
| China Fwd EPS Growth | `MXCN Index` | `BEST_EPS_GRO` |
| US Earnings Beat % | Computed | >65%: +2 · 55-65%: +1 · <50%: −1 |

Earnings Revision Ratio: `ERR = (upgrades − downgrades) / total` (z-score 60M).

**Inflation & Policy (FRED, daily/monthly)**

| Signal | Ticker | Note |
|---|---|---|
| 5Y Breakeven Inflation | `T5YIE` | z-score 252×5 days; vs 2% target |
| 10Y Breakeven Inflation | `T10YIE` | amplified signal for LT Tsy |
| US Core PCE YoY | `PCEPILFE` | monthly; vs 2% target; bearish duration when above |
| Fed Funds Rate | `FDTR` (BBG) / Hoja2 col 16 | FF vs neutral r* ~2.5%; real FF = FF − CPI |

---

### Pillar II — Momentum

**Compute these 7 metrics for every equity TR index:**
```python
ret_1M       = price.pct_change(21)
ret_3M       = price.pct_change(63)
ret_6M       = price.pct_change(126)
ret_12_1M    = price.shift(21).pct_change(231)      # 12-1M skip-month
ma_dist      = (price.rolling(50).mean() / price.rolling(200).mean()) - 1
rsi_14       = rsi(price, period=14)                 # signals.py: rsi()
range_pos    = (price - price.rolling(252).min()) / (price.rolling(252).max() - price.rolling(252).min())
```

**Composite momentum weight**: `12-1M (40%) + 3M (25%) + MA50/200 (20%) + RSI (15%)`

**Equity TR Indices (Sheet: TR — use Hoja2 for 12-1M)**

| Ticker | Asset Class |
|---|---|
| `SPXT Index TR` | US Equity |
| `SPTRSGX Index TR` | US Growth |
| `SPTRSVX Index TR` | US Value |
| `SPXQUT Index TR` | US Quality |
| `M0EFHUSD Index TR` | DM ex-US |
| `NDDUWI Index TR` | MSCI World |
| `NDUEEGF Index TR` | EM Equity |
| `M1CXBRV Index TR` | EM ex-China |
| `NDEUCHF Index TR` | China Equity |
| `S5INFT, S5ENRS, S5UTIL, S5INDU, S5HLTH, S5MATR` | US Sectors |
| `S5CONS, S5TELS, S5RLST, S5COND, S5FINL` | US Sectors |

**Fixed Income TR Indices (Sheet: Hoja2)**

| Ticker | Asset Class | Key metrics |
|---|---|---|
| `BFU5TRUU Index` | Short-Term FI | ret_1M, ret_3M, ret_12_1M, MA50/200, RSI |
| `LT03TRUU Index` | MM / STFI | ret_1M, ret_3M, MA50/200 |
| `I13282US Index` | Short-Term FI | Same as above |
| `LBUSTRUU Index` (Bloomberg US Agg) | LT US Corp proxy | full 7 metrics |
| `BSGVTRUU Index` | LT Treasuries | ret_1M, ret_3M, ret_12_1M, MA50/200, RSI |

**OAS Spread Momentum — sign inversion rule:**
Spread tightening = positive for credit. Apply: `z_spread_mom = −1 × zscore(OAS_change_1M)`.

| Ticker | Series | Asset classes |
|---|---|---|
| `BAMLC0A4CBBB` (FRED) | ICE BofA BBB OAS | STFI `+`, LT US Corp `++` |
| `BAMLH0A0HYM2` (FRED) | ICE BofA HY OAS | LT US Corp `++`, US Eq proxy |
| `BAMLEM2BRRBBBCRPIOAS` (FRED) | EM BBB Corp OAS | LT EM FI `++`, EM Eq |
| `BAMLEMRLCRPILAOAS` (FRED) | LatAm Corp OAS | LT EM FI |
| `IBOXUMAE Index` (BBG) | CDX IG spread | LT US Corp, STFI |
| `IBOXHYAE Index` (BBG) | CDX HY price | US Equity (risk appetite) |

**Yield Momentum (Sheet: TSY) — sign inversion:**
Falling yields = bond prices rising. Apply: `z_yield_mom = −1 × zscore(yield_change_1M, 252*5)`.

| Ticker | Series |
|---|---|
| `GT10 @BGN Govt` | US 10Y Yield — LT Tsy `++`, LT Corp `+` |
| `GT02 @BGN Govt` | US 2Y Yield — STFI `+` |
| `10Y − 2Y` (computed) | Term Spread: steepening direction — regime context |

---

### Pillar III — Sentiment

⚠️ **Operational status**: VIX, MOVE, TED spread, PCR, and DXY are **not yet loaded from Excel or FRED**. `proxies.py` estimates them from price data. **Until live data is connected, treat the Sentiment pillar as degraded and reduce its weight toward 0%, redistributing to other pillars.**

All sentiment signals are **contrarian at extremes** (high fear = buy signal for equity).

**Volatility Regime**

Use **percentile rank** (5Y window), not z-score — VIX is non-normal.

```python
vix_pctile = VIX.rolling(252*5).rank(pct=True)
# Score mapping:
#   pctile > 90% → +2.0 (extreme fear = contrarian buy equity)
#   pctile > 75% → +1.0
#   25% to 75%   →  0.0
#   pctile < 25% → −1.0 (complacency)
#   pctile < 10% → −2.0
```

| Signal | Ticker | Source | Note |
|---|---|---|---|
| CBOE VIX | `VIXCLS` | FRED (free) | Contrarian for equity; bullish for UST/STFI |
| ICE BofA MOVE | `MOVE Index` | Bloomberg | High = bad for FI carry; MOVE > 120 reduce carry; > 150 neutral all |
| VSTOXX | `V2X Index` | Bloomberg | EZ equity contrarian |
| VIX Term Structure | `VIX/VIX3M` (computed) | FRED | ratio > 1.0 = backwardation (panic) = +1 |

**Funding & Liquidity**

| Signal | Ticker | Sign |
|---|---|---|
| TED Spread (LIBOR 3M − T-Bill 3M) | `TEDRATE` (FRED) | Equity `−`; MM/STFI `+` (safe haven) |
| USD Strength (DXY) | `DXY Index` / `DTWEXBGS` (FRED) | EM Equity/FI: `−1 × z` (strong USD = EM headwind) |
| EMBI Spread | `BAMLHE00EHY2Y` (FRED) | EM Equity/FI `−` (high spread = EM stress) |
| GS Financial Conditions Index | `GSFCI Index` (BBG) | US Equity `−`, LT Corp `−` (tighter = negative) |

**Positioning & Options (all contrarian)**

| Signal | Source | Threshold |
|---|---|---|
| CBOE Equity PCR (10d MA) | `CPCE` (FRED) | >1.1: contrarian buy; <0.7: contrarian sell |
| AAII Bull-Bear Spread | AAII.com weekly | z-score 104w; extreme bullish (>+30%) → sell signal |
| CFTC COT S&P Net Spec | CFTC / Quandl | extreme net long = crowded = sell signal |
| CFTC COT UST 10Y Net Spec | CFTC / Quandl | extreme net short = potential squeeze = buy UST |
| SKEW Index | `SKEWX` (FRED) | high SKEW = institutional tail hedging = mild equity bearish |

---

### Pillar IV — Valuation

**Equity P/E — Use percentile rank (10Y window), not z-score**

P/E is right-skewed and non-stationary. Scoring formula:
```python
pe_pctile = forward_pe.rolling(252*10).rank(pct=True)
pe_score  = -2 + 4 * (1 - pe_pctile)   # maps [0,1] → [+2, −2] (cheap=positive)
```

| Index | Ticker | Cheap / Fair / Expensive |
|---|---|---|
| S&P 500 | `SPXT Index PE` (Hoja2) | <15x / 15–20x / >22x |
| MSCI EAFE | `M0EFHUSD Index PE` | <13x / 13–17x / >19x |
| MSCI EM | `NDUEEGF Index PE` | <10x / 10–13x / >15x |
| MSCI China | `NDEUCHF Index PE` | <9x / 9–12x / >14x |
| MSCI EM ex China | `M1CXBRV Index PE` | <10x / 10–13x / — |
| S&P 500 Growth | `SPTRSGX Index PE` | Relative: P/E Growth / P/E Value z-score |
| S&P 500 Value | `SPTRSVX Index PE` | Relative: P/E Value / P/E Market z-score |

**Equity Risk Premium (ERP) — Most important cross-asset signal**
```python
earnings_yield  = 1 / forward_pe * 100              # percent
real_yield_10y  = DFII10                             # TIPS 10Y (FRED)
erp             = earnings_yield - real_yield_10y
z_erp           = rolling_zscore(erp, window=252*10) # 10Y window

# Absolute thresholds:
# ERP > 4%:  +2 (equities very attractive vs bonds)
# ERP 2–4%:  +1 to 0 (proportional)
# ERP 1–2%:  −1
# ERP < 1%:  −2 (expensive)
# ERP < 0:   extreme caution
```

**Fixed Income Valuation (Sheet: TSY + FRED)**

| Signal | Ticker | Key threshold |
|---|---|---|
| US 10Y Yield (pctile 10Y) | `GT10 @BGN Govt` | High yield = attractive carry for LT Tsy |
| US 2Y Yield (pctile 10Y) | `GT02 @BGN Govt` | High 2Y = attractive for STFI |
| Term Spread 10Y−2Y | Computed | Inverted (<0) = bullish duration (rate cuts ahead) |
| TIPS 10Y Real Yield | `DFII10` (FRED) | >2.0% = very attractive; negative real yield = unattractive |
| TIPS 5Y Real Yield | `DFII5` (FRED) | STFI real yield attractiveness |

**OAS Valuation (Sheet: OAS, ~26Y of data)**

Use percentile rank over 5Y and 10Y rolling windows:

| Ticker | Cheap / Fair / Expensive |
|---|---|
| `BAMLC0A4CBBB` (BBB OAS) | >180bp cheap / 100–180bp fair / <100bp expensive |
| `BAMLH0A0HYM2` (HY OAS) | >500bp cheap / 300–500bp fair / <300bp expensive |
| `BAMLEM2BRRBBBCRPIOAS` (EM BBB) | >250bp cheap / 150–250bp fair / <150bp expensive |

**Money Market Valuation (dominant pillar: 50% weight)**

| Signal | Ticker | Key metric |
|---|---|---|
| Real 3M T-bill rate | `DTB3 − PCEPILFE` (FRED) | Positive and high = MM very attractive |
| 3M T-bill yield pctile (10Y) | `DTB3` (FRED) | Is nominal yield high vs history? |
| Fed Funds vs neutral r* | `FEDFUNDS` (FRED) | FF > 2.5% = restrictive = MM attractive vs duration |

---

## Aggregation Pipeline (5 steps)

### Step 1 — Normalize each raw series → z-score

```python
# EWMA is the production default (λ=0.95, handles regime breaks)
def ewma_zscore(s, span=EWMA_SPAN):
    mu    = s.ewm(span=span).mean()
    sigma = s.ewm(span=span).std()
    return (s - mu).div(sigma).clip(-3, 3)

# Rolling z-score for valuation (slower-moving signals)
def rolling_zscore(s, window):
    return (s - s.rolling(window).mean()).div(s.rolling(window).std()).clip(-3, 3)

# Percentile rank for non-normal distributions (VIX, OAS, P/E)
pctile = s.rolling(window).rank(pct=True)
```

**Window selection by signal type:**
- PMI monthly signals: 60 months
- Daily price/spread signals: 252×5 days (5Y)
- Valuation (P/E, ERP, real yield): 252×10 days (10Y)
- EWMA default span: `EWMA_SPAN = 252*3` (~3Y half-life)

### Step 2 — Apply sign conventions before aggregating

```python
# FIXED INCOME (duration): macro signals INVERTED
z_pmi_fi   = -1 * z_pmi_ism          # PMI up → rates rise → bond prices fall
z_gdp_fi   = -1 * z_gdp_revision_us
z_cesi_fi  = -1 * z_cesi_us

# CREDIT: spread tightening is positive
z_oas_mom  = -1 * rolling_zscore(oas.diff(21), 252*5)

# SENTIMENT: VIX at extremes → contrarian (non-linear scoring)
vix_pctile = VIX.rolling(252*5).rank(pct=True)
z_vix_eq   = np.where(vix_pctile > 0.85,  +1.5,
             np.where(vix_pctile < 0.15,  -1.5,
                      -1 * rolling_zscore(VIX, 252*5)))

# CESI: at extremes (pctile > 85% or < 15%), flip sign (contrarian)
cesi_pctile = CESI.rolling(252).rank(pct=True)
z_cesi      = np.where(cesi_pctile > 0.85, -1 * z_cesi_raw,
              np.where(cesi_pctile < 0.15, -1 * z_cesi_raw, z_cesi_raw))
```

**Sign convention summary:**

| Signal type | Equity sign | FI duration sign | Credit sign |
|---|---|---|---|
| PMI / GDP / CESI (growth) | `+` | `−1 ×` (inverted) | `+` (growth = tighter spreads) |
| OAS/spread change | n/a | `+` (widening = flight to quality for UST) | `−1 ×` (tightening = positive) |
| VIX / MOVE (stress) | contrarian `C` | flight-to-quality `+` | `−` |
| P/E level | `−1 ×` via `pe_score` | n/a | n/a |

### Step 3 — Aggregate within each pillar

```python
# Example: Fundamentals pillar for US Equity
pillar_F_us = (
    0.35 * z_pmi_composite_us   +   # ISM Mfg + Services average
    0.25 * z_cesi_us            +   # Citi Surprise (with contrarian at extremes)
    0.20 * z_gdp_revision_us    +   # GDP forecast revision
    0.15 * z_eps_growth_us      +   # Forward EPS growth
    0.05 * z_eps_beat_us            # Earnings beat %
)
# Re-normalize after combining (prevents variance collapse)
Z_F_us = rolling_zscore(pillar_F_us, window=252).clip(-3, 3)
```

`pillars.py:_wavg()` handles this: skips absent/None signals and renormalizes weights automatically.

### Step 4 — Combine pillars → composite z-score

```python
# Pillar weights by asset class (from config.py: PILLAR_WEIGHTS)
weights = {
    'money_market':  {'F':0.10,'M':0.15,'S':0.25,'V':0.50},  # dominated by carry/valuation
    'short_term_fi': {'F':0.20,'M':0.25,'S':0.20,'V':0.35},
    'lt_treasuries': {'F':0.25,'M':0.25,'S':0.20,'V':0.30},
    'lt_us_corp':    {'F':0.20,'M':0.30,'S':0.20,'V':0.30},
    'lt_em_fi':      {'F':0.25,'M':0.30,'S':0.20,'V':0.25},
    'us_equity':     {'F':0.25,'M':0.30,'S':0.20,'V':0.25},
    'us_growth':     {'F':0.20,'M':0.35,'S':0.15,'V':0.30},
    'us_value':      {'F':0.30,'M':0.25,'S':0.20,'V':0.25},
    # DM and EM equity: same as us_equity
}
Z_composite = sum(weights[ac][p] * Z_pillar[p] for p in 'FMSV')
```

### Step 5 — Pillar agreement multiplier (conviction quality filter)

```python
directions   = [np.sign(Z_pillar[p]) for p in 'FMSV' if abs(Z_pillar[p]) > 0.25]
majority_dir = max(set(directions), key=directions.count)
n_agree      = sum(1 for d in directions if d == majority_dir)

# Multipliers (config.py: PILLAR_AGREEMENT_MULTIPLIERS):
# 4/4 agree → 1.00×  |  3/4 → 0.80×  |  2/4 → 0.50×  |  1/4 or 0 → 0.00×
conviction_mult = {4: 1.0, 3: 0.8, 2: 0.5, 1: 0.0, 0: 0.0}[n_agree]
```

---

## Absolute vs. Relative Views

The composite feeds into **two view types** that are blended before sizing tilts.

### Absolute view (35% weight)
"Is this asset class attractive vs. its own history?"
Z_composite > 0 → above-average quality. Simultaneous OW across multiple ACs is valid.

| Z-composite | Conviction | Max tilt vs SAA |
|---|---|---|
| > +1.50 | HIGH OVERWEIGHT | +3.0% to +5.0% |
| +0.75 to +1.50 | MEDIUM OVERWEIGHT | +1.5% to +3.0% |
| −0.75 to +0.75 | NEUTRAL | 0% |
| −1.50 to −0.75 | MEDIUM UNDERWEIGHT | −1.5% to −3.0% |
| < −1.50 | HIGH UNDERWEIGHT | −3.0% to −5.0% |

### Relative view (65% weight)
"Which asset class do I prefer over the others?"

```python
composites  = {ac: Z_composite[ac] for ac in universe}
mu_cs       = np.mean(list(composites.values()))
std_cs      = np.std(list(composites.values()))
Z_rel       = {ac: (composites[ac] - mu_cs) / std_cs for ac in composites}

# Blend: 35% absolute, 65% relative
ALPHA_ABS   = 0.35   # config.py
Z_final     = {ac: ALPHA_ABS * composites[ac] + (1 - ALPHA_ABS) * Z_rel[ac]
               for ac in composites}

# Tilt (clipped to max_tilt per asset class)
tilt = {ac: np.clip(Z_final[ac] * max_tilt[ac] * conviction_mult[ac],
                    -max_tilt[ac], max_tilt[ac]) for ac in composites}
```

**Practical result**: An asset class with positive absolute z but below-universe-average composite gets a relative underweight — this is how "OW equity / UW FI" calls emerge naturally even when both have positive absolute scores.

### Crisis Override (hard rule)
```python
# Activates when BOTH VIX AND MOVE exceed their 80th percentile simultaneously
crisis_flag  = (vix_pctile > 0.80) & (move_pctile > 0.80)
final_tilt   = raw_tilt * (~crisis_flag).astype(int)  # all tilts → 0
# Override lifts when both return below 70th percentile
```

---

## Configuration Reference (`config.py`)

All tunable parameters — no business logic lives here:

```
EXCEL_PATH                     path to Dashboard_TAA_Inputs.xlsx
ASSET_CLASSES                  ordered list of 12 asset class keys
PILLAR_WEIGHTS                 {ac: {F,M,S,V weights summing to 1.0}}
MAX_TILT_PCT                   hard cap per asset class (MM=2%, US Eq=5%, etc.)
CONVICTION_THRESHOLDS          z-score thresholds: 1.50, 0.75, −0.75, −1.50
ALPHA_ABS                      0.35 (absolute view weight; relative = 0.65)
PILLAR_AGREEMENT_MULTIPLIERS   {4:1.0, 3:0.8, 2:0.5, 1:0.0}
PILLAR_AGREEMENT_THRESHOLD     0.25 (min |z| for pillar to count as having signal)
WINDOWS                        {short:63, medium:252, long:756, xlarge:1260, vlong:2520, pmi:60}
EWMA_SPAN                      756 (252*3, ~3Y)
MIN_HISTORY_DAYS               63 (guard against signal computation with insufficient data)
MAX_FFILL_DAYS                 5 (max consecutive NaN forward-fill for price gaps)
OUTLIER_CLIP_Z                 3.0 (winsorization bound for all z-scores)
RETURN_OUTLIER_ZSCORE          5.0 (daily return flagged as data error)
MOM_HORIZONS                   {1m:21, 3m:63, 6m:126, 12m:252, skip:21}
```

---

## Extending the System

### Add a signal

1. Define atomic function in `signals.py` (returns `pd.Series` with DatetimeIndex):
```python
def my_signal(series: pd.Series, window: int = WINDOWS['xlarge']) -> pd.Series:
    raw = series.diff(21)           # some transformation
    return ewma_zscore(raw)         # normalize
```

2. Import and wire into the appropriate pillar in `pillars.py`:
```python
from signals import my_signal
# In pillar_fundamentals() for the relevant asset class:
signals['my_sig'] = my_signal(data['my_field'])
weights['my_sig'] = 0.10            # renormalization handles this automatically
```

3. Run `python main.py` to verify output.

### Add an asset class

1. Add to `config.py`: `ASSET_CLASSES`, `ASSET_CLASS_LABELS`, `ASSET_CLASS_GROUPS`, `PILLAR_WEIGHTS`, `MAX_TILT_PCT`
2. Add pillar logic branches in `pillars.py` (all four pillar functions)
3. Verify in `main.py` output

### Connect live Bloomberg/FRED data

Edit `build_bloomberg_series()` in `main.py`. Any non-empty `pd.Series` overrides the corresponding proxy:
```python
ext['vix']      = fred.get_series('VIXCLS')
ext['move']     = bbg.bdh('MOVE Index', 'PX_LAST', '2000-01-01')['PX_LAST']
ext['pmi_us']   = bbg.bdh('NAPMPMI Index', 'PX_LAST', '2000-01-01')['PX_LAST']
ext['cesi_us']  = bbg.bdh('CESIUSD Index', 'PX_LAST', '2000-01-01')['PX_LAST']
```

---

## Key Design Rules (Non-Obvious)

- **Adaptive windows**: All normalization functions use `min(target_window, available_observations)`, so short series (PE sheet: 261 rows) produce valid signals. Never break this.
- **Graceful degradation**: Missing signals (empty `pd.Series`) are silently skipped; weights renormalize. System runs with partial data.
- **Signal sign lives in `pillars.py`**: `signals.py` computes z-scores unsigned where possible. `pillars.py` applies `−1 ×` inversions for FI. Never apply inversions in `signals.py` — it makes the function non-reusable.
- **CESI contrarian at extremes**: Not a simple z-score. Must check percentile before applying direction.
- **EWMA vs rolling**: EWMA is default for daily signals. Rolling is only used for slow-moving valuation signals (P/E, ERP, real yield) where the 10Y window is intentional.
- **Re-standardize after pillar aggregation**: `standardise_pillar()` is called after `_wavg()` in `pillars.py` to restore unit variance — do not remove this step.
- **TR sheet is for sectors only**: The 261-row TR sheet is used for sector PE/TR analysis. For any momentum signal requiring 12-1M history (>261 rows), use Hoja2 Block B.

---


---

## Configuration Management Layer (Added April 2026)

A build layer was added to make the system **self-updating from a single Excel file**.
The Excel is the only file a non-developer needs to edit to change signals, weights, or asset classes.

### Files

| File | Type | Purpose |
|---|---|---|
| `config/taa_config.xlsx` | **User-owned** | Single source of truth. 6 sheets: Instructions, AssetClasses, DataSeries, PillarWeights, PillarNotes, SignalMapping |
| `src/seed_taa_config.py` | One-time seeder | Creates `taa_config.xlsx` from scratch. Run once on a new machine. |
| `src/build_dashboard.py` | Build script | Reads Excel, regenerates machine-managed blocks in `index.html` and `src/config.py` |
| `src/generate_methodology_doc.py` | Doc generator | Reads Excel, produces `docs/TAA_Methodology.docx` |
| `src/test_build_layer.py` | Health check | 29 automated checks across all layer components |
| `docs/TAA_Methodology.docx` | **Generated** | Consolidated methodology reference (do not edit manually) |

### Excel sheet schema

| Sheet | Columns | Purpose |
|---|---|---|
| `AssetClasses` | ac_id, full_label, short_label, group, benchmark, sub_description, color, max_tilt_pct | 12 ACs |
| `DataSeries` | series_id, signal_name, ticker, source, frequency, pillar, transformation, window, notes | 89 signals |
| `PillarWeights` | ac_id, F, M, S, V (each row sums to 1.0) | Pillar weights per AC |
| `PillarNotes` | ac_id, pillar, note | Italic methodology note per (AC, pillar) card |
| `SignalMapping` | ac_id, series_id, pillar, sign, weight_in_pillar, description_override | 180 signal-to-AC wires |

### Build markers in index.html and src/config.py

Machine-managed blocks are wrapped in `<<<BUILD:...>>>` comment markers. The build script
replaces content between these markers; all code outside them is preserved.

**index.html markers** (JS comment prefix `//`):
```
<<<BUILD:SIG_MATRIX_START>>>   ...  <<<BUILD:SIG_MATRIX_END>>>
<<<BUILD:AC_META_START>>>      ...  <<<BUILD:AC_META_END>>>
<<<BUILD:FI_BLUEPRINT_START>>> ...  <<<BUILD:FI_BLUEPRINT_END>>>
<<<BUILD:EQ_BLUEPRINT_START>>> ...  <<<BUILD:EQ_BLUEPRINT_END>>>
<<<BUILD:AC_LABEL_PW_START>>>  ...  <<<BUILD:AC_LABEL_PW_END>>>
```

**src/config.py markers** (Python comment prefix `#`):
```
<<<BUILD:PY_AC_UNIVERSE_START>>>    ...  <<<BUILD:PY_AC_UNIVERSE_END>>>
<<<BUILD:PY_PILLAR_WEIGHTS_START>>> ...  <<<BUILD:PY_PILLAR_WEIGHTS_END>>>
<<<BUILD:PY_MAX_TILT_START>>>       ...  <<<BUILD:PY_MAX_TILT_END>>>
```

### How to extend via Excel (preferred workflow)

**Add a new signal:**
1. Add a row in `DataSeries` with a unique `series_id`, ticker, source, pillar.
2. Add rows in `SignalMapping` for each AC the signal applies to (set sign and weight).
3. Run `python src/build_dashboard.py` and `python src/generate_methodology_doc.py`.
4. Wire the signal into `src/pillars.py` for live computation (see "Extending the System" below).
5. Run `python src/test_build_layer.py` to confirm all checks pass.

**Add a new asset class:**
1. Add a row in `AssetClasses` with a unique `ac_id` (snake_case).
2. Add a row in `PillarWeights` with F+M+S+V = 1.0.
3. Add `SignalMapping` rows so the AC has at least one signal per pillar.
4. Run `python src/build_dashboard.py`.
5. Add pillar logic branches for the new AC in `src/pillars.py`.
6. Run `python src/test_build_layer.py`.

**Change pillar weights:**
1. Edit the relevant row in the `PillarWeights` sheet (keep F+M+S+V = 1.0).
2. Run `python src/build_dashboard.py`.
3. Re-run `python src/main.py` to recompute composites with new weights.

---

## Dashboard Layer (Added April 2026)

Two new files were added on top of the signal pipeline to produce an interactive HTML dashboard.

### New Files

| File | Purpose |
|---|---|
| `src/chartbook_data.py` | Extracts signal-level time series from the pipeline and exports `results/chartbook_data.json` (~4.6 MB, ~5Y of history per series) |
| `src/generate_dashboard.py` | Reads CSVs + chartbook JSON, embeds last 252 days of data inline, generates `dashboard.html` (~1.1 MB standalone file) |
| `dashboard.html` | **Generated output** — open directly in any browser, no server required |

### How to Regenerate the Dashboard

```bash
# Step 1: Run the signal pipeline (produces CSVs in results/RUN_YYYYMMDD_HHMM/)
python src/main.py

# Step 2: Extract chartbook-level series
python src/chartbook_data.py
# → results/chartbook_data.json

# Step 3: Generate the standalone HTML dashboard
python src/generate_dashboard.py
# → dashboard.html  (open in browser)
```

If only `main.py` has been re-run, you must also re-run Steps 2 and 3 to refresh the dashboard.
Update the `LATEST_RUN` constant in `src/generate_dashboard.py` if using a newer run directory.

### Dashboard Structure (9 navigation items)

```
1. CHARTBOOK
   I.  Fundamentals  — PMI levels, CESI, GDP revisions, EPS, breakevens
                        grouped by region: US | Eurozone | China | Japan | EM
   II. Momentum      — price momentum components per asset class
                        metric checkboxes: Ret 1M / Ret 3M / Ret 6M / 12-1M / MA dist / RSI
                        groups: US Equity | DM Equity | EM Equity | Fixed Income | Spreads
   III. Sentiment    — VIX, MOVE, VSTOXX, TED, AAII Bull-Bear, PCR
   IV. Valuation     — P/E absolute (6 indices) + Relative P/E (interactive A/B selector)
                        ERP, OAS levels, yield curve, TIPS real yields

2. TAA METHODOLOGY
   Full Signal Matrix — pivot: signals × 12 asset classes with +/−/C/— sign badges
   Fixed Income       — pillar weight bars + current Z-scores per FI AC
   Equity             — same for 7 equity ACs

3. TAA SIGNALS
   Composite Scorecard — KPI row + full scorecard table + pillar bar chart + ranking chart
                          + FI/EQ composite time series (1Y)
   Signal Heatmap      — Z-score heatmap + F vs V scatter + M vs S scatter
```

### chartbook_data.json Schema

```
{
  "meta":         { run_date, max_rows, description },
  "fundamentals": { pmi, cesi, gdp_revision, earnings, inflation }
                  each series: { dates[], values[], z[], pctile[] (where applicable) }
  "momentum":     { equity: {ac: {ret_1m,ret_3m,ret_6m,ret_12_1m,ma_dist,rsi}},
                    fi:     {ac: {..., yield_mom_1m, yield_mom_3m}},
                    spreads:{oas_bbb,oas_hy,oas_em,oas_latam: {spread_mom_1m, spread_mom_3m}} }
  "sentiment":    { volatility: {vix,move,vstoxx}, funding: {ted,embi},
                    positioning: {aaii_bull_bear, pcr} }
  "valuation":    { pe_absolute: {sp500,msci_acwi,msci_eafe,msci_em,...},
                    pe_relative: {growth_vs_value,us_vs_em,dm_vs_us,...: {dates,ratio,z}},
                    erp:         {us_equity,acwi,em_equity,china: {dates,values,z}},
                    oas:         {bbb,hy,em,latam: {dates,values,z,pctile}},
                    yields:      {usy_10y,usy_2y,tips_10y,tips_5y,term_spread,...} }
}
```

### Key Implementation Notes

- **All data embedded inline**: `dashboard.html` contains all data as `const` JS objects — no server or fetch calls needed. Works on `file://` protocol.
- **Relative P/E**: `relative_pe()` in `signals.py:314` is already implemented and reused. The chartbook computes 8 pairs: growth_vs_value, value_vs_growth, us_vs_em, em_vs_us, dm_vs_us, china_vs_em, china_vs_us, em_vs_dm.
- **Timeframe toggles**: Each chart card has 1M / 3M / 1Y buttons that slice the embedded series using `sliceTF(arr, n)` and call `chart.update()`. The full 252-day dataset is always in memory.
- **Metric toggles (Momentum)**: Checkbox buttons per momentum component hide/show individual Chart.js datasets via `dataset.hidden`.
- **OAS displayed in bps**: The OAS sheet stores spreads as decimal percent (1.53 = 153 bps). The dashboard multiplies by 100 before display.
- **Design tokens**: `--brand:#C41230` (Rimac red), pillar colors: F=`#14B8A6`, M=`#F59E0B`, S=`#A855F7`, V=`#3A7BD5`. Dark theme `#0B1220` bg. Chart.js 4.4.1 + Space Grotesk font.
