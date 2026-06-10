# TAA System — Comprehensive Improvement Plan
## Rimac Group · June 2026

**Scope:** Full system audit — architecture, file inventory, hardcoding, Excel design, inconsistencies, and a target design for systematic extensibility.

---

## Table of Contents

1. [How the System Actually Works — Accurate Flow](#1-how-the-system-actually-works--accurate-flow)
2. [File Inventory — Active, Stale, One-Time-Use](#2-file-inventory--active-stale-one-time-use)
3. [Hardcoding Audit — What Must Move to Config](#3-hardcoding-audit--what-must-move-to-config)
4. [Excel Architecture Review](#4-excel-architecture-review)
5. [Main Inconsistencies (Cross-File)](#5-main-inconsistencies-cross-file)
6. [Prioritised Improvement Recommendations](#6-prioritised-improvement-recommendations)
7. [Target Architecture](#7-target-architecture)

---

## 1. How the System Actually Works — Accurate Flow

This is the **production pipeline** as it runs today. Several files that appear in the codebase are not part of this flow (see Section 2).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  INPUTS                                                                     │
│                                                                             │
│  Dashboard_TAA_Inputs.xlsx          config/taa_config.xlsx                  │
│  ├── OAS      (1999–now)            ├── AssetClasses  (10 rows: 6 active)   │
│  ├── H4 PE/EY/TR  (2011–now)       ├── DataSeries    (170 rows)            │
│  ├── H5 mkt/tsy/cds (2011–now)     ├── SignalMapping (130 rows)            │
│  ├── H6 Sectors    (2011–now)       ├── PillarWeights (10 rows)            │
│  ├── H1+H2 PMI/CESI/GDP            ├── PillarNotes                        │
│  ├── H3 Forward EPS                ├── MomentumConfig                     │
│  ├── H7 GDPNow/NFCI/FCI_EZ        └── TransformCodes                     │
│  └── AAII Sentiment                                                         │
└────────────────────┬───────────────────────────┬───────────────────────────┘
                     │                           │
                     ▼                           ▼
┌────────────────────────────┐   ┌─────────────────────────────────────────┐
│  STEP 0 — CUSTOM SERIES    │   │  STEP 1 — DATA LOADING                  │
│  build_custom_series.py    │   │  data_loader.py → load_all()            │
│  ├── PMI composites        │   │  ├── Renames Bloomberg tickers to        │
│  ├── GDP blends (w_cur/nxt)│   │  │   internal column names              │
│  ├── modern_ted            │   │  ├── Computes term_spread, modern_ted   │
│  ├── real_ff, term_spread  │   │  │   (ALSO computed here — duplication) │
│  ├── ERP (EY − TIPS10Y)    │   │  ├── Clips, ffills, validates index     │
│  ├── PE scores             │   │  └── Returns: {oas,pe,yields,fi_px,     │
│  ├── Relative PE (log)     │   │     sectors,tsy,cds,mkt,f1,f3,aaii,h7} │
│  ├── OAS stress proxies    │   └─────────────────────────────────────────┘
│  ├── EPS revision (3M+6M)  │
│  └── CDX momentum          │   ← ISSUE: CDX already z-scored here
│  OUTPUT: custom_series.xlsx│
└────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 2 — SIGNAL ENGINE (signal_engine.py → SignalEngine.load_all())        │
│                                                                             │
│  Reads DataSeries sheet from taa_config.xlsx                                │
│  For each active row:                                                       │
│    series_type="original" → load_raw_sheet(Dashboard_TAA_Inputs.xlsx,      │
│                              sheet_name, input_column)                      │
│    series_type="custom"   → read custom_series.xlsx[series_id]             │
│                                                                             │
│  Applies transform_code:                                                    │
│    ewma_z        → ewma_zscore(raw, span=window)                            │
│    rolling_z     → rolling_zscore(raw, window)                             │
│    pctile        → pctile_rank(raw, window) → rescale (p-0.5)×4            │
│    mom_z         → ewma_zscore(pct_change(window), span=EWMA_SPAN)         │
│    price_mom     → composite_price_momentum() [MomentumConfig params]       │
│    diff_z        → ewma_zscore(diff(window), span=EWMA_SPAN)               │
│    inv_mom_z     → DEPRECATED → same as -diff_z                             │
│                                                                             │
│  Clips all signals at MIN_DATE_FOR_SIGNALS (2013-02-01)                     │
│  Returns: {series_id: pd.Series (z-score)}  ← ~97 signals                 │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                     ┌───────────┴───────────┐
                     │                       │
                     ▼                       ▼
     [Signal dict]               [Proxy fallback — proxies.py]
     ~97 z-scored signals        Fills empty slots ONLY if signal missing:
                                   pmi_us, pmi_ez, cesi_us, etc.
                     └───────────┬───────────┘
                                 │ merge (real signals override proxies)
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 3 — PILLAR BUILDER (pillars.py → build_all_pillars())                 │
│                                                                             │
│  Reads SignalMapping from taa_config.xlsx via signal_engine.get_signal_mapping()
│  For each AC × pillar:                                                      │
│    Collects signals[series_id] × sign from SignalMapping                    │
│    Computes weighted average (_wavg): gracefully handles missing signals     │
│    Re-standardises with standardise_pillar() [252d EWMA]                   │
│    Returns: {'F':Series, 'M':Series, 'S':Series, 'V':Series} per AC        │
│                                                                             │
│  NOTE: pillar_fundamentals(), pillar_momentum(), pillar_sentiment(),        │
│        pillar_valuation() exist in pillars.py but are NEVER CALLED here.   │
│        Only build_all_pillars() is used. The others are dead code.          │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 4 — COMPOSITE + SCORECARD (scoring.py)                                │
│                                                                             │
│  composite_score()  : weighted pillar average per AC (PILLAR_WEIGHTS)       │
│  pillar_agreement() : counts pillars agreeing on direction                  │
│  score_snapshot()   : cross-sectional z (Z_relative) + abs/rel blend       │
│  apply_crisis_override(): zeros all tilts if VIX+MOVE both > 80th pctile   │
│                                                                             │
│  Final tilt = ALPHA_ABS × abs_tilt + (1-ALPHA_ABS) × rel_tilt             │
│  abs_tilt = z_to_conviction(Z_composite) × conviction_mult × MAX_TILT_PCT  │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                     ┌───────────┴───────────┐
                     ▼                       ▼
┌──────────────────────────┐   ┌─────────────────────────────────────────────┐
│  STEP 5A                 │   │  STEP 5B                                     │
│  Hierarchical Views       │   │  Portfolio Engine                            │
│  hierarchical_scoring.py │   │  portfolio.py                                │
│  ├── L1: aggregate z     │   │  ├── Reads portfolios.xlsx (4 portfolios)    │
│  │   (weighted children) │   │  ├── Scales tilts by TE budget               │
│  └── L2: child − parent  │   │  ├── force_zero_sum=True                    │
│      (within-bucket rot.)│   │  └── No-short enforcement                   │
└──────────────────────────┘   └─────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 6 — OUTPUTS                                                           │
│  export_results() → results/RUN_YYYYMMDD_HHMMSS/                           │
│  ├── taa_scorecard.csv                                                      │
│  ├── taa_composite_series.csv                                               │
│  ├── pillars_{ac}.csv                                                       │
│  ├── taa_hierarchy_scorecard.csv                                            │
│  ├── taa_bucket_summary.csv                                                 │
│  └── multi_portfolio_views.xlsx                                             │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                     ┌────────────┴───────────┐
                     ▼                        ▼
          chartbook_data.py            economic_sanity.py
          → results/chartbook_data.json → results/economic_sanity/ESR_*.md
                     │
                     ▼
          generate_dashboard.py
          → index.html (injected in-place)
```

---

## 2. File Inventory — Active, Stale, One-Time-Use

### 2.1 Python Files (`src/`)

| File | Status | Role | Action |
|---|---|---|---|
| `config.py` | ✅ **ACTIVE** | All constants; BUILD blocks regenerated from Excel | Keep. Move hardcoded hierarchy/thresholds to Excel (see §3) |
| `data_loader.py` | ✅ **ACTIVE** | Loads and cleans all input sheets | Keep. Remove two hardcoded derived series (§3) |
| `signal_engine.py` | ✅ **ACTIVE** | Reads DataSeries, applies transforms, returns signals | Keep. Remove `inv_mom_z` after migration |
| `signals.py` | ✅ **ACTIVE** | Atomic transform functions | Keep. Add `contrarian_pctile` transform |
| `build_custom_series.py` | ✅ **ACTIVE** | Computes 41 derived series → custom_series.xlsx | Keep. Fix CDX pre-z-scoring (§5) |
| `pillars.py` | ⚠️ **SPLIT** | `build_all_pillars()` ACTIVE; all `pillar_*()` functions DEAD | Keep `build_all_pillars()`. Add `# DEAD CODE` banners to `pillar_fundamentals/momentum/sentiment/valuation()` |
| `main.py` | ⚠️ **SPLIT** | `run_pipeline()` ACTIVE; `build_bloomberg_series()` DEAD | Remove `build_bloomberg_series()` function entirely |
| `scoring.py` | ✅ **ACTIVE** | Composite → conviction → tilt | Keep |
| `hierarchical_scoring.py` | ✅ **ACTIVE** | L1/L2 hierarchical views | Keep. Drive from taa_config.xlsx (§6) |
| `portfolio.py` | ✅ **ACTIVE** | Multi-portfolio tilt scaling | Keep |
| `build_dashboard.py` | ✅ **ACTIVE** | Excel → JS blocks + config.py BUILD blocks | Keep. Extend to also export hierarchy config |
| `generate_dashboard.py` | ✅ **ACTIVE** | Injects live data into index.html | Keep |
| `chartbook_data.py` | ✅ **ACTIVE** | Full signal history → chartbook_data.json | Keep |
| `economic_sanity.py` | ✅ **ACTIVE** | ESR markdown report | Keep. Wire run-to-run signal diff |
| `test_build_layer.py` | ✅ **ACTIVE** | 29-check health test | Keep. Extend with signal wiring checks |
| `proxies.py` | ⚠️ **LEGACY** | Fallback signals when real data missing | Retain as emergency fallback. Add warning log when proxy is actually used |
| `add_new_signals.py` | 🟡 **ONE-TIME** | Was run once to add SKEW/ISM/EPS signals | Archive to `src/archive/`. Replace with SOP + validate_signal.py |
| `rebuild_signal_mapping.py` | 🟡 **ONE-TIME** | Was run once to rebuild SignalMapping | Archive to `src/archive/`. Disaster-recovery only |
| `extend_taa_config.py` | 🟡 **ONE-TIME** | Was run once to extend DataSeries columns | Archive to `src/archive/` |
| `seed_taa_config.py` | 🟡 **ONE-TIME** | Creates taa_config.xlsx from scratch | Archive to `src/archive/`. Only needed for full reset |
| `generate_methodology_doc.py` | ✅ **ACTIVE** | Generates TAA_Methodology.docx | Keep. Run after major methodology changes |

### 2.2 Documentation Files (`docs/`)

| File | Status | Notes | Action |
|---|---|---|---|
| `TAA_System_Guide.md` | ✅ **ACTIVE** | Technical implementation reference | Keep. Update after system changes |
| `TAA_Methodology.md` | ✅ **ACTIVE** | Methodology narrative | Keep |
| `TAA_Methodology.docx` | ✅ **GENERATED** | Auto-generated from Excel | Never edit manually |
| `data_quality.md` | ✅ **ACTIVE** | Data quality rules and known gaps | Keep. Update with every new series |
| `signal_improvements.md` | ✅ **ACTIVE** | Excluded signals with activation instructions | Keep |
| `economic_sanity_methodology.md` | ✅ **ACTIVE** | ESR framework documentation | Keep |
| `chart_management_proposal.md` | ✅ **ACTIVE** | 94-signal catalog + add/remove process | Keep |
| `backtesting_calibration_framework.md` | ✅ **NEW** | Backtesting framework (June 2026) | Keep |
| `signal_review_and_systematisation.md` | ✅ **NEW** | Signal audit (June 2026) | Keep |
| `system_improvement_plan.md` | ✅ **NEW** | This document | Keep |
| **Design templates/** | ✅ **REFERENCE** | Chart design specs (4 types + AC card) | Keep as reference |
| `TAA Signal Generation v1.0.md` | 🔴 **STALE** | v1 methodology, superseded by v6 | Archive or delete |
| `system_automation_analysis.md` | 🔴 **STALE** | Early-phase analysis, superseded by CLAUDE.md | Archive or delete |
| `sanity_check_report.md` | 🔴 **STALE** | One-time sanity check from April 2026 | Archive or delete |
| `transform_generalization_analysis.md` | 🔴 **STALE** | v2 analysis, transform logic now implemented | Archive or delete |
| `portfolio_dashboard_analysis.md` | 🟡 **UNCERTAIN** | Portfolio dashboard analysis — verify if superseded | Review content; archive if superseded |
| `project_flow_diagram.md` | 🟡 **UNCERTAIN** | Flow diagram — verify if current | Replace with §1 of this document |
| `series_catalog_raw.csv` | 🟡 **UNCERTAIN** | Raw series catalog — may be superseded by DataSeries | Verify; archive if DataSeries is more current |
| `series_catalog_full.csv` | 🟡 **UNCERTAIN** | Full catalog — same as above | Same action |
| `build_ic_deck.js` | 🔴 **ORPHAN** | Standalone JS in docs/ — no connection to pipeline | Archive or delete |
| `~$shboard TAA - Guidelines.docx` | 🔴 **TEMP FILE** | MS Word/Excel temp lock file | Delete immediately |

**Recommended archiving:** Create `docs/archive/` and `src/archive/` folders. Move stale files there rather than deleting, preserving history.

---

## 3. Hardcoding Audit — What Must Move to Config

The design principle is: **nothing should be hardcoded except** (a) atomic transform implementations in `signals.py` and (b) computed formulas in `build_custom_series.py`. Everything else should be driven by `taa_config.xlsx` or `config.py` (which itself is regenerated from Excel).

### 3.1 In `data_loader.py` — Three Hardcoded Items

**Problem A: `bfu5_price` silently aliased to `i132_price`**
```python
# Line 153 — data_loader.py
if "i132_price" in out.columns and "bfu5_price" not in out.columns:
    out["bfu5_price"] = out["i132_price"]   # ← wrong proxy, hardcoded
```
`bfu5` should be "Bloomberg US Corporate 5+ Year" — a different duration than `i132_price` (Long Corp). This alias silently provides the wrong series to any signal that asks for `bfu5_price`. **Fix:** Remove the alias. Add the correct `bfu5_price` column to H4 in the Bloomberg export. If unavailable, document explicitly in `data_quality.md` that `bfu5_price` is not available and wire a declared proxy in `DataSeries` with `series_type="original"` pointing to `i132_price` with a description note.

**Problem B: `term_spread` computed in `data_loader.py`**
```python
# load_tsy() — data_loader.py
out["term_spread"] = out["usy_10y"] - out["usy_2y"]
```
`term_spread` is a derived series. It is also computed in `build_custom_series.py`. This duplicates logic and means two different DataFrames carry `term_spread` (once in `tsy`, once in `custom_series.xlsx`). **Fix:** Remove from `data_loader.py`. Ensure `build_custom_series.py` is the single source. The `tsy` sheet should return only raw loaded columns.

**Problem C: `modern_ted` computed in `data_loader.py`**
```python
# load_tsy() — data_loader.py
out["modern_ted"] = (out["tbill_3m"] - out["sofr"]).clip(lower=-1, upper=5)
```
Same issue. `modern_ted` is a derived series computed in `data_loader.py` AND re-computed (with gating) in `build_custom_series.py`. **Fix:** Remove from `data_loader.py`. The gated version in `build_custom_series.py` is more correct (gates to 2018-04-01).

**Problem D: `data["tr"] = data.get("fi_px")` legacy alias**
```python
# load_all() — data_loader.py
data["tr"] = data.get("fi_px", pd.DataFrame())  # legacy alias
```
The `"tr"` key is referenced in `proxies.py` and old code. **Fix:** Remove the alias. Update `proxies.py` to use `"fi_px"` directly. Search codebase for `data.get("tr")` and replace.

**Problem E: `fi_px` naming is misleading**
The key `fi_px` (Fixed Income Price) contains equity TR indices (`sp500_tr_px`, `msci_em_px`, etc.) as well as FI TR indices. Rename to `tr_indices` or `price_indices` for clarity.

### 3.2 In `main.py` — Dead Code + Hardcoded ffill

**Problem A: `build_bloomberg_series()` is dead code with stale logic**
This 150-line function computes signals that are never used. It also uses stale column names (`"gdp_us_cur"` instead of `"gdp_forecast_us_26"`). **Fix:** Delete the function entirely.

**Problem B: `limit=35` hardcoded**
```python
pce = pce_yoy.reindex(idx).ffill(limit=35)  # should be MAX_FFILL_MONTHLY
```
**Fix:** Replace with `MAX_FFILL_MONTHLY`.

### 3.3 In `signal_engine.py` — EWMA Span Overrides

```python
elif tc == "mom_z":
    chg = s.pct_change(window)
    return ewma_zscore(chg, span=EWMA_SPAN).rename(series_id)  # ← ignores DataSeries window for smoothing

elif tc == "diff_z":
    diff = s.diff(window)
    return ewma_zscore(diff, span=EWMA_SPAN).rename(series_id)  # ← same issue
```

The `window` parameter from DataSeries controls the lookback for the diff/pct_change, but the EWMA smoothing span is always `EWMA_SPAN` (756d). A DataSeries row cannot override the smoothing span for `mom_z` or `diff_z`. **Fix:** Parse a second parameter `ewma_span` (or `smooth_window`) from DataSeries. Default to `EWMA_SPAN` if not provided. This allows momentum signals to have different smoothing speeds without code changes.

### 3.4 In `config.py` — Parameters That Should Be in Excel

The following constants are hardcoded in `config.py` and cannot be changed from Excel:

| Constant | Current Value | Impact if changed | Should live in |
|---|---|---|---|
| `CONVICTION_THRESHOLDS` | ±0.75, ±1.50 | Changes tilt frequency and sizing | `taa_config.xlsx:ModelParameters` sheet |
| `ALPHA_ABS` | 0.35 | Changes abs/rel blend | `taa_config.xlsx:ModelParameters` |
| `PILLAR_AGREEMENT_MULTIPLIERS` | {4:1.0, 3:0.8, 2:0.5, 1:0.0} | Changes how many-pillar agreement scales tilt | `taa_config.xlsx:ModelParameters` |
| `PILLAR_AGREEMENT_THRESHOLD` | 0.25 | Controls noise filtering in pillar agreement | `taa_config.xlsx:ModelParameters` |
| `OUTLIER_CLIP_Z` | 3.0 | Winsorisation level | `taa_config.xlsx:ModelParameters` |
| `EWMA_SPAN` | 756 days | Default EWMA window for all transforms | `taa_config.xlsx:ModelParameters` |
| `MIN_DATE_FOR_SIGNALS` | 2013-02-01 | Signal floor date | `taa_config.xlsx:ModelParameters` |
| `AC_HIERARCHY` | dict with children + weights | Defines L1/L2 structure | `taa_config.xlsx:AssetClasses` (parent_ac column) |
| `AC_STANDALONE` | list | Controls which ACs have no sub-ACs | Derivable from `parent_ac` column |
| `AC_PARENT` | reverse lookup dict | Child → parent | Derivable from `parent_ac` column |

**The hierarchy constants are the most important to move.** Currently, adding a new hierarchical AC requires editing `config.py` manually (outside the Excel-driven system). The AssetClasses sheet should have columns `parent_ac`, `l1_model_weight`, `max_tilt_l1`, `max_tilt_l2`.

### 3.5 In `build_custom_series.py` — Acceptable vs Non-Acceptable Hardcoding

| What | Acceptable? | Note |
|---|---|---|
| GDP blend formula `w_cur = month/12` | ✅ Yes | Economic formula, not configuration |
| PMI = (mfg + svcs) / 2 | ✅ Yes | Fixed economic definition |
| EPS revision `0.40×3M + 0.60×6M` | ✅ Yes | Literature-based formula (Chan et al.) |
| CDX momentum `0.4×1M + 0.6×3M` | ✅ Yes | Fixed blend formula |
| modern_ted gate `"2018-04-01"` | ⚠️ Should move to data_quality.md + be referenced | Document start date |
| real_ff clip `-10` to `15` | ✅ Acceptable | Sanity range for Fed Funds real rate |
| OAS stress proxy window `21` days | ⚠️ Should match DataSeries `window` parameter | Currently hardcoded |

---

## 4. Excel Architecture Review

### 4.1 `taa_config.xlsx` — Current Sheets and Issues

| Sheet | Purpose | Issues | Recommended Changes |
|---|---|---|---|
| `Instructions` | Documentation | Likely stale | Update after improvements |
| `AssetClasses` | 10 ACs, active flag, group, labels | Missing: `parent_ac`, `l1_model_weight`, `max_tilt_l1`, `max_tilt_l2`, `hierarchy_level` | Add 5 columns (see §6) |
| `DataSeries` | 170 signal rows: id, type, sheet, column, transform, window | Missing: `description`, `reliable_from`, `ewma_smooth_span`, `notes`, `last_verified_date` | Add 5 columns |
| `SignalMapping` | 130 rows: ac, series, pillar, sign, weight | Missing: `weight_check` formula, `last_updated`, `description_override` validation | Add validation columns |
| `PillarWeights` | 10 rows of F/M/S/V weights | ✅ Good. Already has validation (sums to 1) | Add `sum_check` formula visible in sheet |
| `PillarNotes` | Methodology notes per AC/pillar | Good but may be sparsely populated | Require one note per AC×pillar (48 rows) |
| `MomentumConfig` | Per-series price momentum parameters | ✅ Good design | Ensure all `price_mom` series have a row here |
| `TransformCodes` | Reference table of valid transforms | ✅ Good — but does it list `diff_z`? | Add `diff_z`, mark `inv_mom_z` as DEPRECATED |

**Proposed new sheet: `ModelParameters`**

| Parameter | Value | Description |
|---|---|---|
| ALPHA_ABS | 0.35 | Absolute view weight (balance: 35% abs / 65% relative) |
| CONVICTION_MID_THRESHOLD | 0.75 | Z-score at which MEDIUM OW/UW conviction triggers |
| CONVICTION_HIGH_THRESHOLD | 1.50 | Z-score at which HIGH OW/UW conviction triggers |
| PILLAR_AGREEMENT_THRESHOLD | 0.25 | Min |z| for a pillar to count as having signal |
| AGREE_4 | 1.00 | Conviction multiplier when 4/4 pillars agree |
| AGREE_3 | 0.80 | Conviction multiplier when 3/4 pillars agree |
| AGREE_2 | 0.50 | Conviction multiplier when 2/4 pillars agree |
| AGREE_1 | 0.00 | Conviction multiplier when 1/4 pillars agree |
| OUTLIER_CLIP_Z | 3.0 | Winsorisation level for all z-scores |
| EWMA_DEFAULT_SPAN | 756 | Default EWMA span in days (3Y half-life) |
| MIN_DATE_FOR_SIGNALS | 2013-02-01 | Signal floor date (EWMA warm-up) |
| SMOOTH_COMPOSITE | False | Toggle 10-day rolling median on composite z |
| CRISIS_VIX_PCTILE | 0.80 | VIX percentile above which crisis override triggers |
| CRISIS_MOVE_PCTILE | 0.80 | MOVE percentile above which crisis override triggers |

`build_dashboard.py` reads this sheet and propagates values to `config.py` via a new BUILD block. No more hardcoded constants in Python.

**Proposed changes to `AssetClasses` sheet columns:**

Add after existing columns:
- `parent_ac` — e.g., `lt_fi_aggregate` for the 3 FI children; empty for standalone
- `l1_model_weight` — the weight of this child in the parent's aggregate z (e.g., 0.40 for lt_treasuries)
- `max_tilt_l1` — aggregate L1 tilt capacity (only populated on synthetic aggregate definitions)
- `max_tilt_l2` — within-bucket L2 tilt capacity
- `hierarchy_level` — `L1` or `L2` for display purposes

This allows `hierarchical_scoring.py` and `build_dashboard.py` to rebuild `AC_HIERARCHY`, `AC_PARENT`, `AC_STANDALONE` dynamically from Excel.

**Proposed changes to `DataSeries` sheet columns:**

Add:
- `description` — one-sentence description of what the series measures and why it's included
- `reliable_from` — the date from which the z-score is reliable (first_valid + warm_up); currently only a global MIN_DATE exists
- `ewma_smooth_span` — override for the EWMA smoothing span used in `mom_z`/`diff_z` (defaults to EWMA_DEFAULT_SPAN from ModelParameters)
- `last_verified_date` — when was this signal's data and wiring last confirmed working
- `notes` — free text for data quality issues, caveats, data gaps

### 4.2 `Dashboard_TAA_Inputs.xlsx` — Issues

**Issue A: No data validation sheet**  
Each time the file is updated, there's no automated check of row counts, last available dates per column, or % NaN values. A team member must inspect visually.

**Recommendation:** Add a `_Validation` sheet with Excel formulas/PivotTables showing:
- Last date per sheet (e.g., `=MAX(H5!A:A)`)
- Row count per sheet
- Number of non-empty cells per key column

This sheet refreshes automatically when data is updated in Bloomberg and catches staleness immediately.

**Issue B: `fi_px` sheet contains both equity AND FI indices**  
The H4 sheet (mapped to `fi_px` dict key) contains S&P 500, MSCI EAFE, MSCI EM (equity) alongside Bloomberg Long Treasury, Long Corp, EM Sovereign (FI). The naming causes confusion — anyone seeing `data.get("fi_px")` assumes it's Fixed Income Price data.

**Recommendation:** Rename the internal dict key from `fi_px` to `tr_indices` in `data_loader.py`. Update all references (`pillars.py`, `proxies.py`, `main.py`). This is a pure refactor with no logic change.

**Issue C: H5 is overloaded (11 different types of data in one sheet)**  
Sheet H5 currently holds: CDX spreads, VIX family (VIX, VSTOXX, VIX3M, MOVE), SKEW, PCR, DXY, US FCI, Fed Funds, SOFR, PCE, yields (GT10, GT02, T-bill), TIPS, breakeven inflation, CPI.

**Recommendation:** Keep H5 as-is (refactoring the Excel is high-effort). But in `data_loader.py`, clearly comment which sub-groups come from H5. The logical split is already done by separate load functions (`load_tsy()`, `load_cds()`, `load_mkt()`).

**Issue D: Column naming is raw Bloomberg tickers**  
`data_loader.py` renames columns from Bloomberg tickers to internal names via `SHEET*_COLS` dicts in `config.py`. But `signal_engine.py` uses `load_raw_sheet()` which does NOT rename — it reads raw tickers. This creates a dual naming system where the same data has two different column names depending on how it's accessed.

**Current state:**
- `data_loader.py` → `data["mkt"]["vix"]` (internal name)
- `signal_engine.py` → `df["VIX Index"]` (raw Bloomberg ticker, from DataSeries `input_column`)

**This duplication is a maintenance risk.** If Bloomberg renames a column, you must update it in TWO places: `config.py:SHEET5_COLS` and `taa_config.xlsx:DataSeries:input_column`.

**Recommended fix:** `signal_engine.py` should use the same renaming maps from `config.py`. Add a `sheet_column_maps` parameter to `load_raw_sheet()` (optional). When the signal engine loads a sheet, apply the same rename as `data_loader.py`. Then DataSeries `input_column` can use internal names consistently.

---

## 5. Main Inconsistencies (Cross-File Summary)

These are inconsistencies across multiple files that create confusion or incorrect results. (Detailed analysis in `signal_review_and_systematisation.md`.)

| # | Inconsistency | Files | Severity |
|---|---|---|---|
| 1 | `build_bloomberg_series()` dead code with stale GDP column names (`gdp_us_cur` vs `gdp_forecast_us_26`) | `main.py` | Critical |
| 2 | `inv_mom_z` deprecated in code but used by 5+ active signals | `signal_engine.py`, `taa_config.xlsx` | High |
| 3 | CDX momentum (`cdx_ig_mom`, `cdx_hy_mom`) pre-z-scored in `build_custom_series.py`, then z-scored again by SignalEngine | `build_custom_series.py`, `taa_config.xlsx` | High |
| 4 | `bfu5_price` silently aliased to `i132_price` — different duration, wrong proxy | `data_loader.py` | High |
| 5 | `term_spread` and `modern_ted` computed in BOTH `data_loader.py` AND `build_custom_series.py` | `data_loader.py`, `build_custom_series.py` | High |
| 6 | Column naming dual-system: `data_loader.py` uses internal names, `signal_engine.py` uses raw Bloomberg tickers | `data_loader.py`, `signal_engine.py`, `config.py`, `taa_config.xlsx` | High |
| 7 | `AC_HIERARCHY`, `AC_PARENT`, `AC_STANDALONE` hardcoded in `config.py` — not driven by taa_config.xlsx | `config.py`, `hierarchical_scoring.py` | High |
| 8 | LT Treasuries Momentum uses `bsgv_price` (EM Sovereign TR) instead of `lt03_price` (US Long Treasury TR) | `taa_config.xlsx:SignalMapping` | Critical |
| 9 | Money Market Momentum uses `lt03_price` (Long Treasury TR) — wrong duration for money market | `taa_config.xlsx:SignalMapping` | High |
| 10 | EM Equity and LT EM FI share identical Fundamentals pillar signals and weights | `taa_config.xlsx:SignalMapping` | High |
| 11 | `diff_z` transform exists in code but missing from `CLAUDE.md` and `TransformCodes` sheet | `signal_engine.py`, `CLAUDE.md`, `taa_config.xlsx` | Medium |
| 12 | `real_ff` ffill uses `limit=35` instead of `MAX_FFILL_MONTHLY=31` | `build_custom_series.py`, `config.py` | Medium |
| 13 | `fi_px` dict key contains equity TR indices — misleading name | `data_loader.py` and all callers | Medium |
| 14 | `standardise_pillar()` always uses 252d EWMA regardless of pillar speed | `signals.py`, `pillars.py` | Medium |
| 15 | VIX gets non-linear contrarian scoring in legacy code; in SignalEngine it gets linear `ewma_z` | `signal_engine.py`, `signals.py` (dead path) | Medium |
| 16 | One-time-use scripts (`add_new_signals.py`, `rebuild_signal_mapping.py`, etc.) sitting alongside production scripts | `src/` directory | Medium |
| 17 | 5+ stale documentation files with outdated system descriptions | `docs/` directory | Low |

---

## 6. Prioritised Improvement Recommendations

### Tier 1 — Do Immediately (Zero Risk, High Clarity, < 1 Day)

**R1.1 — Delete `build_bloomberg_series()` from `main.py`**  
It is never called. Removing it eliminates 150 lines of stale, misleading code with wrong column names.

**R1.2 — Archive one-time scripts**  
Create `src/archive/`. Move: `add_new_signals.py`, `rebuild_signal_mapping.py`, `extend_taa_config.py`, `seed_taa_config.py`. These are not part of the weekly workflow.

**R1.3 — Archive stale docs**  
Create `docs/archive/`. Move: `TAA Signal Generation v1.0.md`, `system_automation_analysis.md`, `sanity_check_report.md`, `transform_generalization_analysis.md`. Delete `~$shboard TAA - Guidelines.docx` (temp file).

**R1.4 — Fix `real_ff` ffill constant**  
`build_custom_series.py`: change `limit=35` → `limit=MAX_FFILL_MONTHLY`. Import the constant if not already imported.

**R1.5 — Migrate `inv_mom_z` signals to `diff_z` + `sign=-1`**  
In `taa_config.xlsx:DataSeries`, for every row with `transform_code = inv_mom_z`, change to `diff_z`. In `SignalMapping`, ensure the corresponding rows have `sign = -1`. No Python change required.

**R1.6 — Add `diff_z` to TransformCodes sheet and CLAUDE.md**  
Update the TransformCodes sheet description. Update CLAUDE.md transform table. Mark `inv_mom_z` as `DEPRECATED`.

**R1.7 — Remove `data["tr"]` alias from `data_loader.py`**  
Update all references to use `data["fi_px"]` directly (`proxies.py` line 84). This removes the confusing alias.

---

### Tier 2 — Fix This Sprint (Signal Quality, Low-Medium Risk, 2-3 Days)

**R2.1 — Fix LT Treasuries Momentum proxy**  
In SignalMapping, verify and fix `lt_treasuries` M pillar. Replace `bsgv_price` (EM Sovereign) with `lt03_price` (Long US Treasury TR). Adjust weights: `lt03_price (0.50) + gt10_mom (0.30) + oas_bbb_mom (0.20)`.

**R2.2 — Fix CDX pre-z-scoring in `build_custom_series.py`**  
Change `cdx_ig_momentum()` and `cdx_hy_momentum()` calls to store raw diffs instead of z-scores:
```python
# Before: series["cdx_ig_mom"] = cdx_ig_momentum(cdx_ig_spread)  # already z-scored
# After:
m1 = cdx_ig_spread.diff(21) * -1   # tightening = positive
m3 = cdx_ig_spread.diff(63) * -1
series["cdx_ig_mom_raw"] = (0.4 * m1 + 0.6 * m3)
```
Update DataSeries `input_column` and `transform_code = ewma_z`. Rename series if desired.

**R2.3 — Fix `bfu5_price` alias**  
Remove the hardcoded alias from `data_loader.py`. If `bfu5_price` is unavailable in H4, add an explicit DataSeries row with `input_column = "I13282US Index TR"` (i132_price) and a note in `description` column: "Proxy: using Long Corp TR as STFI momentum proxy; replace when 5Y Corp TR available."

**R2.4 — Remove duplicate derived series from `data_loader.py`**  
Remove `term_spread` and `modern_ted` computation from `load_tsy()`. These are already in `build_custom_series.py`. The `tsy` dict should return only raw loaded columns. Update any downstream code that reads `tsy["term_spread"]` or `tsy["modern_ted"]` to use `custom_series.xlsx` via SignalEngine instead.

**R2.5 — Differentiate EM Equity vs LT EM FI Fundamentals**  
In SignalMapping, add `cesi_china (+1, 0.10)` to EM Equity F, reduce `gdp_em` to `0.20`. For LT EM FI F, reduce `eps_em` weight to `0.10`, add `real_ff (-1, 0.10)` (US rate environment: tight policy = EM credit headwind).

---

### Tier 3 — Architecture Improvements (1-2 Weeks, Controlled)

**R3.1 — Add `ModelParameters` sheet to `taa_config.xlsx`**  
Add the sheet as described in §4.1. Update `build_dashboard.py` to read it and generate a new `BUILD:PY_MODEL_PARAMS` block in `config.py`. Remove hardcoded values from `config.py`.

**R3.2 — Move hierarchy config to `AssetClasses` sheet**  
Add `parent_ac`, `l1_model_weight`, `max_tilt_l1`, `max_tilt_l2` columns to `AssetClasses`. Update `build_dashboard.py` to generate `AC_HIERARCHY`, `AC_PARENT`, `AC_STANDALONE` dynamically. Remove these from `config.py`.

**R3.3 — Resolve column naming dual-system**  
Add an optional `col_rename_map` parameter to `load_raw_sheet()`. Pass the appropriate `SHEET*_COLS` map so that `signal_engine.py` can also use internal column names. Update DataSeries `input_column` to use internal names consistently. Remove the separate column maps from `config.py` (they become redundant — the DataSeries is the map).

**R3.4 — Add `contrarian_pctile` transform to `signal_engine.py`**  
Implement non-linear contrarian scoring (identical to `vix_score()` in signals.py but generalisable). Apply to `vix` and `pcr` via DataSeries `transform_code = "contrarian_pctile"`.

**R3.5 — Add `validate_signal.py` tool**  
New standalone script:
```
python src/validate_signal.py {series_id}
```
Checks:
1. DataSeries row exists and is valid
2. SignalEngine can load it (non-empty output, correct date range)
3. At least one SignalMapping row references it
4. The pillar score changes when the signal is included vs excluded
5. Sign is economically consistent (asks user to confirm)

**R3.6 — Add `compare_runs.py` tool**  
New standalone script that diffs two `signal_z_snapshot.json` files:
```
python src/compare_runs.py [--prev RUN_1] [--curr RUN_2]
```
Outputs: table of signals with `|Δz| > 0.5`, affected ACs, and scorecard impact.

**R3.7 — Rename `fi_px` to `tr_indices` throughout codebase**  
Pure refactor. Update `data_loader.py` return value and all callers.

**R3.8 — Add 5 new DataSeries columns to taa_config.xlsx**  
`description`, `reliable_from`, `ewma_smooth_span`, `last_verified_date`, `notes`. Populate for all 170 rows (can be done incrementally — add column with blanks, fill over time). Update `build_dashboard.py` to export `description` into dashboard blueprints.

**R3.9 — Extend health test**  
Add to `test_build_layer.py`:
- All SignalMapping `series_id` values exist in SignalEngine output
- No active DataSeries uses `transform_code = inv_mom_z`
- Each (AC, pillar) pair has ≥ 2 signals in SignalMapping
- `signal_z_snapshot.json` has > 80 entries

---

## 7. Target Architecture

The target design eliminates all hardcoded configuration and makes the system extensible via Excel alone for most operations.

```
config/taa_config.xlsx  ←── SINGLE SOURCE OF TRUTH FOR ALL CONFIGURATION
│
│  Sheets:
│  ├── AssetClasses      ← AC universe + hierarchy (parent_ac, l1_weight, max_tilt)
│  ├── DataSeries        ← signal registry (series_id, type, sheet, column, transform,
│  │                        window, ewma_span, description, reliable_from, last_verified)
│  ├── SignalMapping      ← wiring (ac, series, pillar, sign, weight, description)
│  ├── PillarWeights      ← F/M/S/V weights per AC (sum to 1.0 enforced)
│  ├── PillarNotes        ← methodology text per AC/pillar (48 rows)
│  ├── ModelParameters    ← ALPHA_ABS, thresholds, EWMA_SPAN, clip levels (NEW)
│  ├── MomentumConfig     ← price_mom parameters per series (horizon weights)
│  ├── TransformCodes     ← reference table of all valid transform codes
│  └── Instructions       ← human-readable guide for editing

data/Dashboard_TAA_Inputs.xlsx  ←── SINGLE SOURCE FOR MARKET DATA
│  ├── OAS, H4, H5, H6, H7, H1, H2, H3, AAII
│  └── _Validation  (NEW) ← auto-refreshing data quality summary

src/ Python layer (minimal hardcoding)
│
├── config.py              ← AUTO-GENERATED blocks from taa_config.xlsx
│                             ModelParameters block (NEW) + existing blocks
│
├── data_loader.py         ← Load + clean only; no derived series
│   ├── load_raw_sheet()   ← with optional col_rename_map (FIX)
│   └── Returns: {oas, pe, yields, tr_indices, sectors, tsy, cds, mkt, f1, f3, aaii, h7}
│                              ^renamed from fi_px
│
├── build_custom_series.py ← Derived series only (PMI, GDP, ERP, PE scores, etc.)
│   └── Stores RAW values in custom_series.xlsx (no pre-z-scoring)
│
├── signal_engine.py       ← Reads DataSeries, applies transforms
│   ├── Transforms: ewma_z, rolling_z, pctile, mom_z, price_mom, diff_z,
│   │              contrarian_pctile (NEW), identity (NEW for pre-processed)
│   └── Uses col_rename_map from data_loader for consistent column access
│
├── pillars.py             ← build_all_pillars() only (legacy pillar_*() REMOVED)
│
├── signals.py             ← Atomic transform functions (NEVER call directly from config)
│
├── scoring.py             ← Reads ModelParameters from config.py (not hardcoded)
│
├── hierarchical_scoring.py ← Reads AC_HIERARCHY from config.py (generated from Excel)
│
├── portfolio.py           ← Reads portfolios.xlsx (unchanged)
│
├── build_dashboard.py     ← Generates ALL config.py BUILD blocks + JS
│   Blocks: AC_UNIVERSE, PILLAR_WEIGHTS, MAX_TILT, MODEL_PARAMS (NEW),
│           AC_HIERARCHY (NEW), SIG_MATRIX, BLUEPRINTS
│
├── main.py                ← Clean pipeline; no dead code
│   run_pipeline():
│     1. load_all() → data dict
│     2. SignalEngine.load_all() → signals dict
│     3. proxies fallback (with warning when used)
│     4. build_all_pillars() → pillar scores
│     5. composite + scoring
│     6. hierarchical views
│     7. crisis override
│     8. portfolio engine
│
├── validate_signal.py     ← NEW: end-to-end signal validation tool
├── compare_runs.py        ← NEW: run-to-run signal diff tool
│
└── archive/               ← Archived one-time scripts
    ├── add_new_signals.py
    ├── rebuild_signal_mapping.py
    ├── extend_taa_config.py
    └── seed_taa_config.py

### Adding a New Signal (Target State — 3 Steps)

1. Update taa_config.xlsx:
   - DataSeries: add one row (no Python required for original signals)
   - SignalMapping: add rows for each AC/pillar

2. If custom: add computation to build_custom_series.py (stores raw value)

3. Validate:
   python src/build_custom_series.py   # if custom
   python src/validate_signal.py {series_id}  # confirms end-to-end
   python src/test_build_layer.py     # 29+/29 PASS

No changes to: main.py, pillars.py, signal_engine.py, scoring.py, config.py
```

---

*Document version: 1.0 | June 2026*  
*Supersedes: `project_flow_diagram.md`, `system_automation_analysis.md`*
