# TAA Signal System — Technical Guide

**Version 3.0 · April 2026**

> **Signal methodology** (what each signal is, why it works, the economics behind each pillar, aggregation math) lives in **`docs/TAA_Methodology.docx`** — generated from `config/taa_config.xlsx`.
> This file covers only the **implementation layer**: repository structure, how to run, data architecture, configuration management, test suite, current data status, and roadmap.

---

## Table of Contents

1. [Repository Structure](#1-repository-structure)
2. [Configuration Management Layer](#2-configuration-management-layer)
3. [Data Architecture](#3-data-architecture)
4. [How to Run](#4-how-to-run)
5. [Proxy Signals](#5-proxy-signals)
6. [Test Suite](#6-test-suite)
7. [Current Data Status](#7-current-data-status)
8. [Current Results — Reference Snapshot](#8-current-results--reference-snapshot)
9. [Known Limitations](#9-known-limitations)
10. [Roadmap](#10-roadmap)

---

## 1. Repository Structure

```
TAA/
|
+-- config/
|   +-- taa_config.xlsx         <- SINGLE SOURCE OF TRUTH (user-owned)
|                                  Edit here to change signals, weights, ACs
|
+-- src/                        <- all Python code
|   |
|   +-- [Signal Pipeline]
|   |   +-- config.py           <- parameters regenerated from Excel; no business logic
|   |   +-- data_loader.py      <- loads all Excel sheets; cleans and type-checks
|   |   +-- signals.py          <- atomic signal functions (z-scores, momentum, valuation)
|   |   +-- proxies.py          <- derives proxy signals when live data is absent
|   |   +-- pillars.py          <- builds F/M/S/V pillar scores for all 12 asset classes
|   |   +-- scoring.py          <- composite -> conviction -> absolute/relative views -> tilt
|   |   +-- main.py             <- pipeline entry point; Bloomberg/FRED override hooks
|   |   +-- chartbook_data.py   <- extracts 5Y of signal history -> chartbook_data.json
|   |   +-- generate_dashboard.py <- embeds CSVs + JSON into standalone dashboard.html
|   |
|   +-- [Configuration Build Layer]
|   |   +-- seed_taa_config.py  <- one-time seeder: creates taa_config.xlsx from scratch
|   |   +-- build_dashboard.py  <- Excel -> index.html (5 JS blocks) + config.py (3 blocks)
|   |   +-- generate_methodology_doc.py <- Excel -> docs/TAA_Methodology.docx
|   |
|   +-- [Testing]
|       +-- test_system.py          <- 38-check signal pipeline test suite
|       +-- test_build_layer.py     <- 29-check build layer health test
|
+-- tests/
|   +-- test_system.py          <- symlink / copy of src/test_system.py
|
+-- data/
|   +-- Dashboard_TAA_Inputs.xlsx   <- primary market data source (multiple sheets)
|
+-- docs/
|   +-- TAA_System_Guide.md             <- this file (implementation reference)
|   +-- TAA_Methodology.docx            <- GENERATED - methodology reference (do not edit)
|   +-- TAA_Signal_Methodology.html     <- visual methodology reference (open in browser)
|   +-- TAA Signal Generation v1.0.md  <- legacy (superseded by TAA_Methodology.docx)
|   +-- Dashboard TAA - Guidelines.docx <- legacy guidelines
|
+-- results/
|   +-- RUN_YYYYMMDD_HHMM/     <- auto-created each run
|       +-- taa_scorecard.csv
|       +-- taa_composite_series.csv
|       +-- pillars_{ac}.csv   <- x12 files, one per asset class
|   +-- chartbook_data.json    <- extracted by chartbook_data.py
|
+-- index.html                 <- TAA methodology reference dashboard (static, file://)
+-- dashboard.html             <- GENERATED - live data dashboard (do not edit)
+-- CLAUDE.md                  <- AI assistant instructions
+-- requirements.txt
```

**Module dependency chain (no circular imports):**

```
config -> data_loader -> signals -> proxies -> pillars -> scoring -> main
```

---

## 2. Configuration Management Layer

The Excel workbook is the single source of truth. Editing it and running one command propagates all changes into the codebase.

### Workflow

```
config/taa_config.xlsx  (you edit this)
         |
         +-- python src/build_dashboard.py
         |       +-> index.html          (5 JS blocks replaced in-place)
         |       +-> src/config.py       (3 Python blocks replaced in-place)
         |
         +-- python src/generate_methodology_doc.py
                 +-> docs/TAA_Methodology.docx  (full Word doc regenerated)
```

### Excel sheet schema

| Sheet | Columns | Rows | Purpose |
|---|---|---|---|
| `Instructions` | — | — | User guide embedded in the workbook |
| `AssetClasses` | ac_id, full_label, short_label, group, benchmark, sub_description, color, max_tilt_pct | 12 | Asset class registry |
| `DataSeries` | series_id, signal_name, ticker, source, frequency, pillar, transformation, window, notes | 99 | Master signal catalogue |
| `PillarWeights` | ac_id, F, M, S, V (each row sums to 1.0) | 12 | Pillar weights per AC |
| `PillarNotes` | ac_id, pillar, note | 48 | Italic explanatory note per (AC, pillar) card |
| `SignalMapping` | ac_id, series_id, pillar, sign, weight_in_pillar, description_override | 206 | Signal-to-AC wiring table |

### Build markers

Machine-managed blocks are wrapped in `<<<BUILD:...>>>` comment markers. The build script replaces content between markers; everything outside is preserved.

**index.html** (comment prefix `//`):

```
<<<BUILD:SIG_MATRIX_START>>>    ...  <<<BUILD:SIG_MATRIX_END>>>
<<<BUILD:AC_META_START>>>       ...  <<<BUILD:AC_META_END>>>
<<<BUILD:FI_BLUEPRINT_START>>>  ...  <<<BUILD:FI_BLUEPRINT_END>>>
<<<BUILD:EQ_BLUEPRINT_START>>>  ...  <<<BUILD:EQ_BLUEPRINT_END>>>
<<<BUILD:AC_LABEL_PW_START>>>   ...  <<<BUILD:AC_LABEL_PW_END>>>
```

**src/config.py** (comment prefix `#`):

```
<<<BUILD:PY_AC_UNIVERSE_START>>>     ...  <<<BUILD:PY_AC_UNIVERSE_END>>>
<<<BUILD:PY_PILLAR_WEIGHTS_START>>>  ...  <<<BUILD:PY_PILLAR_WEIGHTS_END>>>
<<<BUILD:PY_MAX_TILT_START>>>        ...  <<<BUILD:PY_MAX_TILT_END>>>
```

### How to extend via Excel

**Add a signal:**
1. Add a row in `DataSeries` with unique `series_id`, ticker, source, pillar.
2. Add rows in `SignalMapping` for each AC the signal applies to (sign + weight).
3. Run `python src/build_dashboard.py` and `python src/generate_methodology_doc.py`.
4. Wire the signal computation into `src/pillars.py` (see signal pipeline code).
5. Verify: `python src/test_build_layer.py`.

**Add an asset class:**
1. Add a row in `AssetClasses` with unique `ac_id` (snake_case).
2. Add a row in `PillarWeights` with F+M+S+V = 1.0.
3. Add `SignalMapping` rows (at least one signal per pillar).
4. Run `python src/build_dashboard.py`.
5. Add pillar logic branches in `src/pillars.py`.
6. Verify: `python src/test_build_layer.py`.

**Change pillar weights:**
1. Edit the relevant row in `PillarWeights` (keep F+M+S+V = 1.0).
2. Run `python src/build_dashboard.py`.
3. Re-run `python src/main.py` to recompute composites with new weights.

---

## 3. Data Architecture

### Excel Workbook: `data/Dashboard_TAA_Inputs.xlsx`

Sheet names were updated from the legacy `F1/F2/F3/4/5` naming to `H1–H6` in April 2026. All histories extended to 2010.

| Sheet | Rows | Period | Content |
|---|---|---|---|
| `OAS` | 6,937 | 1999–2026 | ICE BofA credit spreads: BBB, HY, EM BBB, LatAm |
| `H4` | 3,991 | 2010–2026 | Forward P/E, Earnings Yields, TR price levels (12 indices) |
| `H5` | 4,044 | 2010–2026 | VIX, MOVE, VSTOXX, CDX, Treasury yields, TIPS, DXY, BFCIUS (FCI), SOFRRATE, PCE YoY, Breakevens 5Y/10Y, PCR, SKEW |
| `H6` | 3,991 | 2010–2026 | MSCI World + S&P 11 sectors — Forward PE, EY, TR (36 columns) |
| `H1` | 4,003 | 2010–2026 | ISM PMI (mfg/svcs), CESI (US/EZ/China/Global), GDP forecasts (US/DM/EM/EU/World) |
| `H2` | 3,960 | 2010–2026 | PMI (Japan/UK/Global), CESI (UK/Japan/EM), GDP (Japan/China/LatAm) |
| `H3` | 3,991 | 2010–2026 | Forward EPS (US/World/EM/China/Japan/EAFE/LatAm) |
| `AAII` | 10,105 | 1987–2026 | AAII Bull/Bear weekly sentiment (resampled daily) |

**Key new series added April 2026:**
- **DXY** (`H5`): Bloomberg USD Index from 2011 — now live in EM sentiment pillars
- **BFCIUS** (`H5`): Bloomberg US Financial Conditions Index from 2011 — wired into US equity/credit sentiment
- **SOFRRATE** (`H5`): SOFR rate from Apr 2018 — used to compute `modern_ted = tbill_3m − SOFR`
- **PCE YoY** (`H5`): Core PCE inflation monthly — used to compute `real_ff = FDTR − PCE` (MM carry)
- **Breakevens 5Y/10Y** (`H5`): moved from H3; inflation expectations wired into FI fundamentals

**Critical data rules:**
- Use **H4 TR columns** for all momentum signals — 15Y of history from 2010.
- Use **OAS sheet** for spread momentum and valuation — 26Y of history, best-anchored signals.
- For 12-1M momentum, signal history begins 2011 (need 12M of prices before computing).
- Modern TED replaces defunct BASPTDSP (last valid date: 2019-02-07).

### Column mappings

All sheet-to-internal-name mappings live in `src/config.py`:

| Config constant | Sheet | Purpose |
|---|---|---|
| `OAS_COLS` | OAS | Credit spreads |
| `SHEET4_PE_COLS`, `SHEET4_EY_COLS`, `SHEET4_TR_COLS` | H4 | PE, EY, TR levels |
| `SHEET_H6_PE_COLS`, `SHEET_H6_EY_COLS`, `SHEET_H6_TR_COLS` | H6 | Sector PE, EY, TR |
| `SHEET5_COLS` | H5 | All market/sentiment/inflation data |
| `SHEET_F1_COLS`, `SHEET_F2_COLS` | H1, H2 | PMI, CESI, GDP |
| `SHEET_F3_COLS` | H3 | Forward EPS |
| `SHEET_AAII_COLS` | AAII | Sentiment |

Change tickers in config.py, not in `data_loader.py`.

### Adaptive windows

All normalization functions use `min(target_window, available_observations)`. Short series (e.g., P/E from 2015) produce valid signals without errors; interpretive notes adjust accordingly.

---

## 4. How to Run

### Script inventory

| Script | What it does | Key output |
|---|---|---|
| `src/seed_taa_config.py` | Creates `config/taa_config.xlsx` from scratch | `config/taa_config.xlsx` |
| `src/build_dashboard.py` | Excel -> index.html + src/config.py | `index.html`, `src/config.py` |
| `src/main.py` | Full TAA signal pipeline | `results/RUN_*/` CSVs |
| `src/chartbook_data.py` | Extracts 5Y signal history | `results/chartbook_data.json` |
| `src/generate_dashboard.py` | Builds standalone HTML dashboard | `dashboard.html` |
| `src/generate_methodology_doc.py` | Builds Word methodology reference | `docs/TAA_Methodology.docx` |
| `src/test_build_layer.py` | 29-check build layer health test | Exit 0 = all pass |
| `src/test_system.py` | 38-check signal pipeline test | Exit 0 = all pass |

### Prerequisites

```bash
pip install pandas numpy scipy openpyxl python-docx
```

### Full pipeline from scratch

```bash
# Step 1 — Edit source of truth (if config has changed)
#   Open config/taa_config.xlsx and edit any sheet

# Step 2 — Propagate config changes into code
python src/build_dashboard.py
# -> index.html: SIG_MATRIX, AC_META, FI/EQ blueprints, PW blocks updated
# -> src/config.py: ASSET_CLASSES, PILLAR_WEIGHTS, MAX_TILT_PCT blocks updated

# Step 3 — Run TAA signal pipeline
python src/main.py
# -> results/RUN_YYYYMMDD_HHMM/taa_scorecard.csv       (12 rows, latest snapshot)
# -> results/RUN_YYYYMMDD_HHMM/taa_composite_series.csv (full composite history)
# -> results/RUN_YYYYMMDD_HHMM/pillars_{ac}.csv         (x12, per-AC pillar history)

# Step 4 — Extract chartbook series
python src/chartbook_data.py
# -> results/chartbook_data.json  (~4.6 MB, 5Y of every signal per series)

# Step 5 — Regenerate dashboard
python src/generate_dashboard.py
# -> dashboard.html  (standalone, works on file://, no server needed)

# Step 6 — Regenerate methodology Word doc (when methodology content changes)
python src/generate_methodology_doc.py
# -> docs/TAA_Methodology.docx

# Step 7 — Health check (always run last)
python src/test_build_layer.py  # 29 checks: build layer
python src/test_system.py       # 38 checks: signal pipeline
```

### Minimal weekly refresh (no config change)

```bash
python src/main.py
python src/chartbook_data.py
python src/generate_dashboard.py
python src/test_system.py
```

### When only `config/taa_config.xlsx` changes

```bash
python src/build_dashboard.py
python src/generate_methodology_doc.py
python src/test_build_layer.py
# Then re-run Steps 3-5 (main.py, chartbook_data.py, generate_dashboard.py)
```

### First-time setup on a new machine

```bash
# If config/taa_config.xlsx doesn't exist yet:
python src/seed_taa_config.py
# Then follow the full pipeline above from Step 2
```

### Debug a single asset class

```python
from sys import path; path.insert(0, "src")
from main import run_pipeline
r = run_pipeline(verbose=False)
print(r["composites"]["us_equity"].tail(10))
print(r["scorecard"])
```

### Connect live Bloomberg / FRED data

Edit `build_bloomberg_series()` in `src/main.py`. Any non-empty `pd.Series` automatically overrides the corresponding proxy:

```python
# FRED (free, no API key required for CSV endpoint)
def _fred(series_id):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    return pd.read_csv(url, index_col=0, parse_dates=True).squeeze().dropna()

ext["ted"]   = _fred("TEDRATE")      # fills the TED gap immediately
ext["dxy"]   = _fred("DTWEXBGS")     # unlocks EM sentiment signals
ext["embi"]  = _fred("BAMLHE00EHY2Y")
ext["cape"]  = _fred("CAPE10")       # 130Y US valuation context

# Bloomberg (via xbbg)
from xbbg import blp
ext["move"]  = blp.bdh("MOVE Index", "PX_LAST", "2000-01-01")["PX_LAST"]
ext["vix"]   = blp.bdh("VIX Index",  "PX_LAST", "2000-01-01")["PX_LAST"]
```

---

## 5. Proxy Signals

When live data is absent, `proxies.py` derives approximations from available Excel data. Each proxy is active only when the corresponding Bloomberg/FRED series is empty.

| Proxy key | What it approximates | Derived from | Quality |
|---|---|---|---|
| `growth_proxy` | PMI / CESI | Cyclical/defensive sector return + OAS tightening speed | 3/5 |
| `credit_cycle` | Credit momentum | OAS tightening speed (BBB + HY) | 4/5 |
| `ts_regime` | GDP revision proxy | Term spread direction | 3/5 |
| `inflation` | Inflation regime | Fed Funds level + 10Y yield trend | 3/5 |
| `eps_us` / `eps_em` | EPS revision | Earnings yield direction + price direction | 3/5 |
| `hy_stress` | VIX proxy | HY OAS rapid widening + level stress | 3/5 |
| `ig_appetite` | TED spread proxy | CDX IG spread level and direction | 3/5 |
| `em_stress` | EMBI proxy | EM BBB + LatAm OAS level | 4/5 |
| `dxy` | No proxy | DXY requires FX rate data | 0/5 |
| `move` | No proxy | MOVE requires SIFMA bond vol data | 0/5 |

---

## 6. Test Suite

### Signal pipeline: `src/test_system.py` (38 checks)

```
IMPORTS         (6)   all modules import without error
DATA LOADING   (10)   sheet presence, date ordering, OAS history length,
                       fi_px/yields/tsy/mkt/f1/f3 present, no zero prices
SIGNALS         (8)   normalisation correctness, sign conventions,
                       pe_score, erp, oas_level, composite_mom
PROXIES         (2)   key completeness, winsorisation
BLOOMBERG       (3)   pmi_us / vix / eps_us populated from Excel
PILLARS         (3)   all 12 ACs compute, outputs bounded, 12/12 active
SCORING         (6)   composite, conviction thresholds, pillar agreement,
                       scorecard shape, tilts within max, relative z mean=0
```

```bash
python src/test_system.py
# Expected: 38/38 ALL PASSED
```

### Build layer: `src/test_build_layer.py` (29 checks)

```
FILE EXISTENCE      (7)   all config/build/doc files present
EXCEL STRUCTURE     (8)   sheet names, row counts, pillar weights sum to 1.0
HTML MARKERS       (14)   all 10 BUILD markers present in index.html,
                            FI has 5 AC blocks, EQ has 7 AC blocks, AC_SHORT has 12 keys
CONFIG.PY MARKERS   (8)   all 6 BUILD markers present, ASSET_CLASSES=12, PILLAR_WEIGHTS=12
BUILD SCRIPT        (4)   importable, renders SIG_MATRIX/FI/EQ correctly
DOCX                (4)   readable, >= 30 paragraphs, key headings, all 12 AC names
```

```bash
python src/test_build_layer.py
# Expected: 29/29 ALL CHECKS PASSED
```

**Run both before every config change, after every code change.**

---

## 7. Current Data Status

### Live signals (all from Excel — no external API required)

| Category | Series | Sheet | Notes |
|---|---|---|---|
| PMI (ISM, EZ, China, Japan, Global) | Blended mfg + svcs | H1/H2 | Japan now wired into dm_equity |
| CESI (US, EZ, China, EM, Japan) | Daily surprise index | H1/H2 | Contrarian-at-extremes not yet wired |
| GDP forecasts (US, DM, EM, EU, China, Japan, LatAm) | Blended cur/nxt year | H1/H2 | Japan now wired into dm_equity |
| Forward EPS (US, World, EM, China, Japan, EAFE, LatAm) | 1M revision z-score | H3 | Japan now wired into dm_equity |
| Breakeven inflation (5Y, 10Y) | EWMA z-score | H5 | Moved from H3; wired into FI/equity |
| VIX, MOVE, VSTOXX, PCR, SKEW | Daily levels | H5 | VSTOXX now wired into dm_equity; MOVE into lt_treasuries |
| DXY (USD Index) | EWMA z-score | H5 | **Now live from 2011**; wired into all EM sentiment |
| BFCIUS (Financial Conditions Index) | EWMA z-score | H5 | **Now live from 2011**; tight FCI = equity headwind |
| SOFRRATE + tbill_3m → modern_ted | Funding stress spread | H5 | **Replaces defunct BASPTDSP**; from 2018 |
| PCE YoY → real_ff | Real Fed Funds = FDTR - PCE | H5 | **Now live**; wired into money_market fundamentals |
| CDX IG / HY | Spread / price levels | H5 | — |
| US yields (2Y, 10Y, TIPS 5Y, 10Y, 3M T-bill) | Level + term spread | H5 | — |
| AAII Bull-Bear | Weekly, resampled daily | AAII | **Now wired** into US equity/growth/value sentiment (contrarian) |
| ICE BofA OAS (BBB, HY, EM, LatAm) | Spread level + momentum | OAS | Also used as EMBI proxy |
| H4 TR / PE / EY | 15 equity/FI indices | H4 | Primary momentum and valuation source |
| H6 Sectors | MSCI World + 11 S&P sectors | H6 | Sector rotation (not yet used in scoring) |

### Still missing / degraded

| Category | Status | Recommended fix |
|---|---|---|
| **TED spread** | BASPTDSP cuts off 2019-02-07. **Modern TED (tbill_3m − SOFR) live from 2018.** Pre-2018 uses OAS proxy. | Gap covered 2018+; pre-2018 gap acceptable |
| **EMBI** | EM BBB OAS used as proxy. Diverges during sovereign episodes. | FRED BAMLHE00EHY2Y (free) |
| **CAPE (Shiller)** | Not implemented. Forward P/E only from 2010. | FRED CAPE10 (monthly from 1880) |
| **CFTC positioning** | Not implemented. | CFTC public data (free, weekly) |
| **CESI contrarian at extremes** | Used directionally for all percentiles. Known deviation from spec. | Wire percentile check in pillars.py |

---

## 8. Current Results — Reference Snapshot (22 April 2026)

Full suite of new signals active: DXY, modern TED, FCI, AAII, VSTOXX, MOVE, real_ff, Japan PMI/GDP/EPS.

```
Asset Class              Z_F    Z_M    Z_S    Z_V   Z_Comp  Agree  Conviction    FinalTilt%
-------------------------------------------------------------------------------------------
Fixed Income
  Money Market          -0.51  +0.17  +1.50  -0.27    +0.21    2/4  NEUTRAL          -0.3%
  Short-Term FI         -0.45  +0.22  +1.75  +1.32    +0.78    2/4  MEDIUM OW        +0.3%
  LT Treasuries         -0.45  +0.11  +0.50  +0.61    +0.20    2/4  NEUTRAL          -0.7%
  LT US Corp            +0.04  +0.36  +1.50  +2.25    +1.09    3/4  MEDIUM OW        +1.2%
  LT EM FI              +0.02  +1.37  -1.89  +2.73    +0.72    2/4  NEUTRAL           0.0%

Equity
  US Equity             +0.22  +0.91  +2.10  -0.08    +0.73    2/4  NEUTRAL           0.0%
  US Growth             +0.22  +0.78  +2.10  +0.95    +0.92    3/4  MEDIUM OW        +0.4%
  US Value              +0.22  +1.02  +2.10  -0.60    +0.59    2/4  NEUTRAL           0.0%
  DM ex-US Eq           -1.84  +0.27  +1.75  -1.21    -0.34    2/4  NEUTRAL          -1.3%
  EM Equity             +0.02  +1.18  +2.08  +1.53    +1.16    3/4  MEDIUM OW        +1.6%
  EM ex-China           +0.02  +1.18  +2.08  +1.58    +1.17    3/4  MEDIUM OW        +1.2%
  China Equity          +1.64  -0.68  +1.88  +0.65    +0.74    3/4  NEUTRAL           0.0%
-------------------------------------------------------------------------------------------
FI net tilt: +0.5%    Equity net tilt: +1.9%    Total |tilts|: 7.0%
```

Key observations: DM ex-US is the clear underweight (Fundamentals −1.84, driven by EZ + Japan weakness). LT US Corp is the standout FI opportunity (Valuation +2.25, 3/4 pillar agreement). EM equity favored over EM ex-China (China's weak momentum offsets its strong fundamentals). US equity sentiment (VIX + AAII + FCI) elevated but not reaching conviction threshold alone.

---

## 9. Known Limitations

### Data gaps

**EMBI replaced by EM BBB OAS.** The EM BBB corporate OAS diverges from sovereign EMBI during sovereign-specific episodes (Argentina, Turkey, etc.). Fix: FRED `BAMLHE00EHY2Y`.

**No CAPE for US equity.** Forward P/E covers only 2010+. The Shiller CAPE (130Y history) detects decade-long expensive regimes unreachable with 15Y P/E. Fix: FRED `CAPE10` (free, monthly from 1880).

**Modern TED starts 2018.** Pre-2018 funding stress uses the OAS/CDX proxy from `proxies.py`. This covers the 2018–2020 period well but doesn't capture 2008 or 2012 episodes in the new signal series.

### Methodology limitations

**No empirical validation of signal weights.** All pillar weights and pillar-to-composite weights are prior beliefs from the literature. No walk-forward backtest has measured IC per signal. Until this is done, there is no evidence that the chosen weights outperform equal-weighting.

**Short sample history (2015 start).** Only one full tightening cycle, one COVID shock, one post-COVID inflationary regime in the data. Signal behavior in 2008-style credit crises or 2000-style equity bubbles is untested.

**CESI contrarian-at-extremes not fully wired.** The methodology requires sign-flipping when CESI is above the 85th or below the 15th percentile. Currently CESI is used directionally for all percentile levels. Known divergence from spec.

**No transaction cost or turnover constraint.** Tilt changes of 1-2% represent hundreds of millions in trades for large insurance portfolios. A minimum tilt-change threshold (e.g., 50bp) is needed before this system drives actual rebalancing decisions.

**Tracking error approximation is flat.** The console displays `total_tilts * 0.16 = TE bps` using a flat 16% vol assumption. Actual TE depends on the full covariance matrix of tilted ACs.

---

## 10. Roadmap

### Tier 1 — Near-term (days to 1 week)

| Item | Effort | Impact | Data cost |
|---|---|---|---|
| Connect FRED free data: TED, DXY, EMBI, CAPE, T-bill real | 1 day | Very high | Free |
| Wire CESI contrarian at extremes in `pillars.py` | 2 hours | Medium | Already have data |
| Wire ISM New Orders/Inventories ratio in US equity F pillar | 1 hour | Medium | Already have data |
| Add real 3M T-bill signal to Money Market valuation | 1 hour | Medium | Free (FRED) |

### Tier 2 — Medium-term (1–3 months)

| Item | Effort | Impact |
|---|---|---|
| Walk-forward backtesting framework (`src/backtest.py`) — IC per signal, ICIR | 2–3 weeks | Critical — validates the whole system |
| IC-weighted signal aggregation (replace hardcoded weights) | 1 week | High |
| Macro regime overlay (4-phase Fed cycle, dynamic pillar weights) | 1 week | High |
| Solvency II SCR impact calculator (`src/scr.py`) | 3 days | High for insurance |
| Turnover dampener (only rebalance if tilt change >= 50bp) | 1 day | Medium |
| US sector rotation sub-model (`src/sectors.py`) | 2 weeks | Medium |

### Tier 3 — Long-term (3–12 months)

| Item | Effort | Impact |
|---|---|---|
| 2-state HMM regime detection (replaces crisis override) | 4 weeks | High |
| DM country breakdown: EZ / Japan / UK / Australia | 1 week | Medium |
| Commodity asset classes: Gold, Oil, TIPS | 2 weeks | High (diversification) |
| ML signal combination (gradient boosted, expanding window) | 4–8 weeks | High if ICs confirm |
| FX overlay for EUR-based hedging decisions | 2 weeks | High for EUR investors |
| Automated IC report PDF (weekly) | 1 week | High (governance) |

---

*TAA Signal System — Technical Guide v3.0 · April 2026*
