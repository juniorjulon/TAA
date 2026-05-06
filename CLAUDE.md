# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**TAA Dashboard** is an institutional-grade Tactical Asset Allocation (TAA) signal generation system
for insurance portfolios. It scores 12 asset classes across four signal pillars —
**Fundamentals (F), Momentum (M), Sentiment (S), Valuation (V)** — then maps composite z-scores
to conviction-based tilts around strategic benchmarks.

For insurance portfolios (Solvency II / NAIC RBC), tilts are capped at **±5%** per asset class
with a tracking error budget of **50–150bp**. A +3% equity tilt consumes ~1.2% incremental SCR.

**Single source of truth for configuration**: `config/taa_config.xlsx` — edit this file to
add/modify signals, asset classes, or pillar weights, then run `python src/build_dashboard.py`
to propagate changes into `index.html` and `src/config.py`.

---

## Development History (chronological)

| Date | Phase | What was built |
|---|---|---|
| April 2026 | v1 | Signal pipeline, scoring, proxies, dashboard, 29-check health test |
| April 2026 | v2 | Excel-driven signal engine: DataSeries → signal_engine.py → build_all_pillars() |
| April 2026 | v2 | build_custom_series.py → custom_series.xlsx (41 derived series) |
| April 2026 | v2 | taa_config.xlsx extended: series_type, input_sheet, input_column, transform_code, MomentumConfig, TransformCodes |
| May 2026 | v3 | Hierarchical views: AC_HIERARCHY in config.py, hierarchical_scoring.py (Level 1 + Level 2) |
| May 2026 | v3 | Multi-portfolio engine: portfolio.py, portfolios.xlsx (4 real portfolios: IGCON/IGMOD/IGDIN/IGEQUS), TE-scaled tilts |
| May 2026 | v3 | Signal improvements: SKEW index, ISM N.O./Inv ratio, EPS revision composites (3M+6M) |
| May 2026 | v4 | Removed em_xchina and china_equity as active ACs (10 ACs); series kept for signal use |
| May 2026 | v4 | Added H7 sheet: 5 new series (breakeven_1y, gdpnow, nfci, fci_ez, fci_uk) |
| May 2026 | v4 | Complete SignalMapping rebuild: 130 clean rows, no orphans, no duplicates (plain-vanilla) |
| May 2026 | v4 | Improvement backlog documented in docs/signal_improvements.md |

---

## Complete Script Inventory

| Script | What it does | Key output(s) |
|---|---|---|
| `src/seed_taa_config.py` | One-time seed — creates `config/taa_config.xlsx` from scratch | `config/taa_config.xlsx` |
| `src/extend_taa_config.py` | Adds executable columns + SignalMapping rows to existing taa_config.xlsx | `config/taa_config.xlsx` (updated) |
| `src/add_new_signals.py` | Adds incremental new DataSeries + SignalMapping rows to taa_config.xlsx | `config/taa_config.xlsx` (updated) |
| `src/build_custom_series.py` | Computes all derived series (PMI, GDP blends, ERP, PE scores, stress proxies, EPS revision) | `data/custom_series.xlsx` |
| `src/build_dashboard.py` | Reads Excel, regenerates 5 JS blocks in `index.html` and 3 Python blocks in `src/config.py` | `index.html`, `src/config.py` |
| `src/main.py` | Full TAA signal pipeline: signals → pillars → composites → tilts → hierarchy → multi-portfolio | `results/RUN_*/` folder (6 files) |
| `src/chartbook_data.py` | Extracts signal-level time series from pipeline results | `results/chartbook_data.json` (~4.6 MB) |
| `src/generate_dashboard.py` | Embeds CSVs + JSON into the main dashboard (auto-detects latest run) | `index.html` |
| `src/generate_methodology_doc.py` | Generates the consolidated Word methodology reference | `docs/TAA_Methodology.docx` |
| `src/test_build_layer.py` | 29-check health test for the config/build/doc layer | Exit 0 = all pass |

---

## Full Pipeline — Standard Weekly Refresh

```bash
# Step 1 — Rebuild derived series (after data update in Dashboard_TAA_Inputs.xlsx)
python src/build_custom_series.py
# -> data/custom_series.xlsx  (41 derived series: PMI, GDP blend, ERP, PE, stress, CDX, EPS revision)

# Step 2 — Run TAA signal pipeline
python src/main.py
# -> results/RUN_YYYYMMDD_HHMM/taa_scorecard.csv            latest z-scores + tilts
# -> results/RUN_YYYYMMDD_HHMM/taa_composite_series.csv      full composite history
# -> results/RUN_YYYYMMDD_HHMM/pillars_{ac}.csv              per-AC pillar history (x12)
# -> results/RUN_YYYYMMDD_HHMM/taa_hierarchy_scorecard.csv   L1 aggregate + L2 within-class z-scores
# -> results/RUN_YYYYMMDD_HHMM/taa_bucket_summary.csv        compact bucket summary
# -> results/RUN_YYYYMMDD_HHMM/multi_portfolio_views.xlsx    10-portfolio tilt recommendations

# Step 3 — Health check
python src/test_build_layer.py
# Expected: 29/29 PASS

# Step 4 (optional) — Regenerate dashboard
python src/chartbook_data.py
python src/generate_dashboard.py
# -> index.html  (single dashboard: methodology + chartbook + scorecard + heatmap)
```

## Adding a New Signal (Zero-Python workflow)

### Case A — Series directly in Dashboard_TAA_Inputs.xlsx

1. Ensure the column exists in the correct sheet (H1–H5, OAS, AAII)
2. Add ONE row to `DataSeries` sheet in `config/taa_config.xlsx`:
   - `series_type = "original"`, `input_sheet = "H5"`, `input_column = "TICKER Index"`, `transform_code = "ewma_z"`
3. Add rows to `SignalMapping` sheet: `ac_id, series_id, pillar, sign, weight_in_pillar`
4. Run `python src/main.py` — the SignalEngine loads and normalises it automatically

### Case B — Derived/computed series

1. Add the computation to `src/build_custom_series.py` in the appropriate section
2. Add `series["my_series"] = ...` to the `series` dict
3. Run `python src/build_custom_series.py` — appears as new column in `data/custom_series.xlsx`
4. Add to `DataSeries`: `series_type = "custom"`, `input_sheet = "custom_series"`, `input_column = "my_series"`, `transform_code = "ewma_z"`
5. Add to `SignalMapping`: `ac_id, series_id, pillar, sign, weight`
6. Run `python src/main.py`

Or use `src/add_new_signals.py` as a template for batch additions.

---

## System Architecture

### Data Flow (current, v3)

```
Dashboard_TAA_Inputs.xlsx (H1-H5, OAS, H6, AAII)
         |
   data_loader.py   load_all()  ->  data dict {sheet: DataFrame}
         |
   build_custom_series.py  ->  data/custom_series.xlsx  (41 derived series)
         |
   signal_engine.py  SignalEngine.load_all()
         |   Reads DataSeries from taa_config.xlsx
         |   For each active row: load from correct sheet, apply transform_code
         |   6 transforms: ewma_z | rolling_z | pctile | mom_z | price_mom | inv_mom_z
         |   Returns: {series_id: pd.Series (z-score)}  -- 92 signals total
         |
   proxies.py  build_proxy_ext()  ->  fallback signals when engine has gaps
         |
   pillars.py  build_all_pillars(ac, signals, signal_mapping)
         |   Generic pillar builder: reads SignalMapping from taa_config.xlsx
         |   Applies sign and weight per (ac, series_id, pillar) row
         |   _wavg() + standardise_pillar() per pillar
         |
   scoring.py  composite_score() + score_snapshot()
         |   Pillar z-scores -> weighted composite -> pillar_agreement -> conviction
         |   35% absolute view + 65% relative (cross-sectional) view -> final_tilt_%
         |
   hierarchical_scoring.py  HierarchicalViews.enrich()
         |   Level 1: aggregate z-score per top-level bucket (lt_fi, us_equity, em_equity)
         |   Level 2: z_child - z_parent  (zero-sum within each bucket)
         |   Adds: Z_L1, Z_L2, tilt_L1_pct, tilt_L2_pct, tilt_hier_pct columns
         |
   portfolio.py  build_multi_portfolio_report()
         |   Reads config/portfolios.xlsx (10 portfolio SAAs + TE budgets)
         |   Scales tilts by TE budget: tilt[p,ac] = signal_fraction x conv x max_tilt x (TE/100)
         |   Optional force_zero_sum for Solvency II mandates
         |
   results/RUN_YYYYMMDD_HHMM/  (6 output files per run)
```

### Module Responsibilities

| File | Responsibility |
|---|---|
| `src/config.py` | All paths, column maps, windows, pillar weights, conviction thresholds, `AC_HIERARCHY`, `AC_PARENT` |
| `src/data_loader.py` | Loads all Excel sheets; forward-fills max 5 days; includes `load_raw_sheet()` for generic access |
| `src/signals.py` | Atomic z-score primitives — all return `pd.Series` with DatetimeIndex |
| `src/build_custom_series.py` | Computes all derived series (PMI composite, GDP blend, ERP, PE scores, stress proxies, EPS revision, CDX momentum) |
| `src/signal_engine.py` | `SignalEngine` class: reads DataSeries from taa_config.xlsx, loads from correct source, applies transform_code |
| `src/pillars.py` | `build_all_pillars()` — generic SignalMapping-driven builder; legacy `pillar_*()` functions preserved |
| `src/proxies.py` | Derives VIX/MOVE/TED/stress proxies from price data when engine has gaps |
| `src/scoring.py` | Composite → pillar agreement multiplier → absolute+relative views → final tilt |
| `src/hierarchical_scoring.py` | `HierarchicalViews.enrich()` — Level 1 aggregate + Level 2 within-class z-scores and tilts |
| `src/portfolio.py` | `PortfolioConfig`, `apply_house_view()`, `build_multi_portfolio_report()` — TE-scaled tilts per portfolio |
| `src/main.py` | Pipeline entry point: orchestrates all steps, exports results |

---

## Key Configuration Files

| File | Contents | How to edit |
|---|---|---|
| `config/taa_config.xlsx` | AssetClasses, DataSeries (165 rows), PillarWeights, PillarNotes, SignalMapping (355 rows), TransformCodes, MomentumConfig | Edit directly; run `build_dashboard.py` after changes |
| `config/portfolios.xlsx` | 10 portfolio definitions: SAA weights, TE budget, alpha_abs, force_zero_sum, risk_profile | Edit in Excel; read automatically by `main.py` |
| `data/custom_series.xlsx` | 41 derived series (custom_series sheet); regenerated by `build_custom_series.py` | Never edit manually; always regenerate via script |
| `src/config.py` | Python constants (auto-generated blocks between BUILD markers) + AC_HIERARCHY, AC_PARENT | BUILD blocks updated by `build_dashboard.py`; hierarchy manually |

---

## Asset Class Universe

12 asset classes in `config.py:ASSET_CLASSES`:

| Key | Label | Group | Hierarchy role |
|---|---|---|---|
| `money_market` | Money Market | FI | Standalone (Level 1 only) |
| `short_term_fi` | Short-Term FI | FI | Standalone (Level 1 only) |
| `lt_treasuries` | LT US Treasuries | FI | Child of `lt_fi_aggregate` |
| `lt_us_corp` | LT US Corporate | FI | Child of `lt_fi_aggregate` |
| `lt_em_fi` | LT EM Fixed Income | FI | Child of `lt_fi_aggregate` |
| `us_equity` | US Equity (Broad) | EQ | Parent — L1 aggregate for US styles |
| `us_growth` | US Growth | EQ | Child of `us_equity` |
| `us_value` | US Value | EQ | Child of `us_equity` |
| `dm_equity` | DM ex-US Equity | EQ | Standalone (Level 1 only) |
| `em_equity` | EM Equity | EQ | Parent — L1 aggregate for EM split |
| `em_xchina` | EM ex-China | EQ | Child of `em_equity` |
| `china_equity` | China Equity | EQ | Child of `em_equity` |

### Hierarchical Structure (AC_HIERARCHY in config.py)

```
Level 1 — 6 top-level views (direction of aggregate position)
  money_market     standalone
  short_term_fi    standalone
  lt_fi_aggregate  SYNTHETIC — z = 0.40×lt_tsy + 0.35×lt_corp + 0.25×lt_em
  us_equity        own composite z IS the L1 view
  dm_equity        standalone
  em_equity        own composite z IS the L1 view

Level 2 — within-bucket rotation (zero-sum; sum of weighted L2 z-scores = 0)
  Within lt_fi:    z_L2 = z_child - z_lt_fi_agg
  Within us_equity: z_L2 = z_child - z_us_equity
  Within em_equity: z_L2 = z_child - z_em_equity
```

Outputs (in `taa_hierarchy_scorecard.csv`): `Z_L1`, `Z_L2`, `tilt_L1_pct`, `tilt_L2_pct`, `tilt_hier_pct`

---

## Signal Universe — 92 Active Signals

### Transform Codes (signal_engine.py)

| Code | Input | Output | Example |
|---|---|---|---|
| `ewma_z` | raw level | EWMA z-score (span=window, default 756d) | VIX, DXY, FCI, PMI composites |
| `rolling_z` | raw level | Rolling z-score (window days) | Breakevens, yields for valuation |
| `pctile` | raw level | Percentile → rescaled `(p-0.5)×4` | OAS levels, yield pctile |
| `mom_z` | raw level | `pct_change(window)` → EWMA z-score | Forward EPS revisions (1M) |
| `price_mom` | price level | Composite: 12-1M (40%) + 3M (25%) + MA (25%) + RSI (10%) | TR indices |
| `inv_mom_z` | spread/yield | `-ewma_z(diff(window))` — falling = positive | OAS, GT02, GT10 |

### Signals by Pillar

**Pillar F — Fundamentals**

| series_id | Source | Key economic logic |
|---|---|---|
| `pmi_us`, `pmi_ez`, `pmi_china` | custom: H1 mfg+svcs avg | Leading business cycle (3-6M horizon) |
| `gdp_us`, `gdp_dm`, `gdp_em`, `gdp_eu`, `gdp_japan`, `gdp_china` | custom: blended cur+nxt year forecast | Consensus real growth with time-varying blend |
| `cesi_us`, `cesi_ez`, `cesi_em`, `cesi_china`, `cesi_japan` | H1/H2 | Economic surprise (contrarian at extremes) |
| `eps_us`, `eps_em`, `eps_eafe`, `eps_china`, `eps_japan` | H3 | EPS revision momentum 1M `mom_z` |
| `eps_rev_us`, `eps_rev_em`, `eps_rev_eafe`, `eps_rev_china` | custom | **NEW** Multi-horizon EPS revision (40%×3M + 60%×6M) |
| `ism_no_inv` | H1: `.ISM G Index` | **NEW** ISM New Orders/Inventories ratio (>1 = expanding demand) |
| `breakeven_5y`, `breakeven_10y` | H5 | Inflation expectations vs 2% target |
| `core_pce` | H5 | Core PCE YoY (restrictive signal for FI) |
| `real_ff` | custom: FDTR − PCE | Real Fed Funds rate (positive = restrictive = MM attractive) |

**Pillar M — Momentum**

| series_id | Source | Key economic logic |
|---|---|---|
| `sp500_tr`, `sp500_gro_tr`, `sp500_val_tr` | H4 TR | US equity price momentum |
| `eafe_tr`, `msci_em_tr`, `em_xchina_tr`, `china_tr`, `msci_acwi_tr` | H4 TR | Regional equity momentum |
| `bfu5_price`, `i132_price`, `lt03_price`, `bsgv_price` | H4 TR | FI price momentum |
| `oas_bbb_mom`, `oas_hy_mom`, `oas_em_mom` | OAS `inv_mom_z` | Spread tightening = positive |
| `gt02_mom`, `gt10_mom` | H5 `inv_mom_z` | Yield falling = duration positive |
| `cdx_ig_mom`, `cdx_hy_mom` | custom: signals.py functions | CDX momentum composites |

**Pillar S — Sentiment**

| series_id | Source | Key economic logic |
|---|---|---|
| `vix` | H5 | VIX: contrarian for equity; flight-to-quality for FI |
| `move_z` | H5 | MOVE: bond vol — safe-haven for UST |
| `vstoxx_z` | H5 | European equity vol — contrarian for DM |
| `skew_z` | H5: `SKEW Index` | **NEW** Tail-risk hedging → equity headwind; UST safe-haven |
| `modern_ted` | custom: tbill_3m − SOFR | Funding stress — risk-off indicator |
| `hy_stress`, `hy_safe_haven` | custom: OAS_HY.diff(21) | HY stress proxy (sign in SignalMapping controls direction) |
| `em_stress`, `embi` | custom: OAS_EM.diff(21) | EM stress / EMBI proxy |
| `dxy_z` | H5 | USD strength — EM headwind (sign −1 for EM ACs) |
| `aaii_z` | AAII | Retail sentiment — contrarian (sign −1 for equity: euphoria = sell) |
| `fci_z` | H5 | Bloomberg FCI — tight = equity headwind (sign −1) |

**Pillar V — Valuation**

| series_id | Source | Key economic logic |
|---|---|---|
| `pe_score_sp500/eafe/em/emx/china/gro/val` | custom: pe_score() | P/E percentile (adaptive window); cheap = positive |
| `erp_us/acwi/em/em_xchina/china` | custom: EY% − TIPS% | Earnings Yield − Real Rate; most powerful cross-asset signal |
| `rel_pe_gro_val`, `rel_pe_val_gro` | custom: log(PE_b/PE_a) | Style relative value |
| `rel_pe_dm_us`, `rel_pe_em_us`, `rel_pe_us_em`, `rel_pe_china_us` | custom | Regional relative value |
| `oas_bbb`, `oas_hy`, `oas_em`, `oas_latam` | OAS `pctile` | Credit spread carry attractiveness |
| `hy_ig_ratio` | custom: OAS_HY/OAS_BBB | HY vs IG relative cheapness |
| `gt02`, `gt10`, `tips_5y`, `tips_10y` | H5 `pctile` | Yield carry attractiveness |
| `term_spread` | custom: GT10 − GT02 | Curve shape: inverted = bullish short duration |

---

## Scoring Pipeline

### Step 1 — Signal loading (signal_engine.py)

```python
engine  = SignalEngine()                       # reads DataSeries from taa_config.xlsx
signals = engine.load_all(verbose=True)        # {series_id: pd.Series (z-score)}
# + proxy fallbacks from proxies.py for any gaps
```

### Step 2 — Pillar aggregation (pillars.py)

```python
signal_mapping = engine.get_signal_mapping()   # DataFrame from SignalMapping sheet
for ac in ASSET_CLASSES:
    pillar_scores[ac] = build_all_pillars(ac, signals, signal_mapping)
    # Each pillar = _wavg(signals × sign, weights) + standardise_pillar()
```

### Step 3 — Composite scoring (scoring.py)

```python
Z_composite = sum(weight_p × Z_p for p in FMSV)   # pillar weights from PILLAR_WEIGHTS
# Pillar agreement multiplier: 4/4→1.0, 3/4→0.8, 2/4→0.5, 1/4→0.0
conviction_mult = PILLAR_AGREEMENT_MULTIPLIERS[n_agree]
# Absolute view (35%) + Relative cross-sectional view (65%)
final_tilt = ALPHA_ABS × abs_tilt + (1-ALPHA_ABS) × rel_tilt
```

### Step 4 — Hierarchical views (hierarchical_scoring.py)

```python
hv = HierarchicalViews()
hierarchy_scorecard = hv.enrich(scorecard)
# New columns: Z_L1, Z_L2, tilt_L1_pct, tilt_L2_pct, tilt_hier_pct
# Z_L2 is zero-sum within each bucket: weighted_sum(Z_L2) = 0.0000
```

### Step 5 — Multi-portfolio (portfolio.py)

```python
portfolios = load_portfolio_configs("config/portfolios.xlsx")
for p in portfolios:
    # tilt[p,ac] = signal_fraction × conviction_mult × max_tilt × (TE_budget/100)
    portfolio_scorecard = apply_house_view(scorecard, p)
# Exported to multi_portfolio_views.xlsx (one sheet per portfolio + Tilt_Summary)
```

### Conviction Thresholds

| Z-composite | Conviction | Tilt fraction |
|---|---|---|
| > +1.50 | HIGH OW | +1.0 |
| +0.75 to +1.50 | MEDIUM OW | +0.5 |
| −0.75 to +0.75 | NEUTRAL | 0.0 |
| −1.50 to −0.75 | MEDIUM UW | −0.5 |
| < −1.50 | HIGH UW | −1.0 |

### Crisis Override

Activates when VIX pctile > 80th AND MOVE pctile > 80th simultaneously.
All tilts set to 0. Lifts when both drop below 70th percentile.

---

## Multi-Portfolio System

### Portfolio Configuration (config/portfolios.xlsx)

10 portfolios defined with these parameters:

| portfolio_id | label | te_budget_bps | risk_profile | force_zero_sum |
|---|---|---|---|---|
| portfolio_01 | Balanced 60-40 | 100 | moderate | No |
| portfolio_02 | Growth 70-30 | 150 | aggressive | No |
| portfolio_03 | Conservative 30-70 | 50 | conservative | No |
| portfolio_04 | Insurance Core | 50 | conservative | **Yes** |
| portfolio_05 | EM Growth Tilt | 120 | aggressive | No |
| portfolio_06 | FI Heavy (Pension LDI) | 75 | moderate | No |
| portfolio_07 | US Equity Focus | 125 | aggressive | No |
| portfolio_08 | Global Multi-Asset | 100 | moderate | No |
| portfolio_09 | DM Equity Tilt | 110 | moderate | No |
| portfolio_10 | Solvency II Constrained | 60 | conservative | **Yes** |

### Tilt Scaling Formula

```python
# Same direction for all portfolios; size proportional to TE budget
te_scale = portfolio.te_budget_bps / 100.0           # reference TE = 100bps
max_tilt_portfolio = config_default_max_tilt × te_scale
tilt = signal_fraction × conviction_mult × max_tilt_portfolio
# portfolio_02 (150bps) gets exactly 3× the tilt of portfolio_03 (50bps) — verified
```

### Zero-Sum Portfolios

`force_zero_sum=True` enforces sum(tilts) = 0 by pro-rata reduction.
Used for Solvency II mandates where net equity/FI exposure is regulated.

---

## Excel Input: `Dashboard_TAA_Inputs.xlsx`

Sheet structure updated April 2026: sheets renamed H1–H6, histories extended to 2010.

| Sheet | Rows | Period | Content |
|---|---|---|---|
| `OAS` | ~6,937 | 1999–2026 | ICE BofA credit spreads: BBB, HY, EM BBB, LatAm |
| `H4` | 3,991 | 2010–2026 | Forward P/E, EY, TR price levels (12 equity/FI indices) |
| `H5` | 4,044 | 2010–2026 | VIX, MOVE, VSTOXX, SKEW, CDX, Treasury yields, TIPS, DXY, FCI, SOFRRATE, PCE YoY, Breakevens |
| `H6` | 3,991 | 2010–2026 | MSCI World + S&P 11 sectors — Forward PE, EY, TR (36 cols) |
| `H1` | 4,003 | 2010–2026 | ISM PMI (mfg/svcs/emp/NO-Inv ratio), CESI (US/EZ/China/Global), GDP (US/DM/EM/EU/World) |
| `H2` | 3,960 | 2010–2026 | PMI (Japan/UK/Global), CESI (UK/Japan/EM), GDP (Japan/China/LatAm) |
| `H3` | 3,991 | 2010–2026 | Forward EPS: US, World, EM, China, Japan, EAFE, LatAm |
| `AAII` | 10,105 | 1987–2026 | AAII Bull/Bear weekly (resampled to daily via ffill) |

Key internal column names (after data_loader.py mapping):
- H5: `vix`, `move`, `vstoxx`, `skew`, `cdx_ig_spread`, `cdx_hy_price`, `dxy`, `fci`, `sofr`, `pce_yoy`, `breakeven_5y`, `breakeven_10y`, `usy_10y`, `usy_2y`, `tbill_3m`, `tips_10y`, `tips_5y`, `fedrate`
- H1: `pmi_ism_mfg`, `pmi_ism_svcs`, `ism_new_ord_inv`, `cesi_us`, `cesi_ez`, `cesi_china`, `gdp_us_cur/nxt`, ...
- H2: `pmi_japan_mfg`, `cesi_em`, `cesi_japan`, `gdp_japan_cur/nxt`, `gdp_china_cur/nxt`, ...

---

## Custom Series (`data/custom_series.xlsx`)

41 series computed by `build_custom_series.py`. Never edit manually.

| Series group | Names | Formula |
|---|---|---|
| PMI composites | `pmi_us`, `pmi_ez`, `pmi_china` | (mfg + svcs) / 2 |
| GDP blends | `gdp_us/dm/em/eu/japan/china` | `w_cur×cur + (1-w)×nxt`, `w = month/12` |
| Rate environment | `modern_ted`, `real_ff`, `term_spread` | tbill−SOFR; FDTR−PCE; GT10−GT02 |
| ERP | `erp_us/acwi/em/em_xchina/china` | EY% − TIPS_10Y% |
| PE scores | `pe_score_sp500/eafe/em/emx/china/gro/val` | `pe_score()` from signals.py |
| Relative PE | `rel_pe_gro_val`, `rel_pe_dm_us`, etc. | `log(PE_b / PE_a)` |
| OAS proxies | `hy_stress`, `hy_safe_haven`, `em_stress`, `embi` | `oas.diff(21)` (raw 1M change) |
| OAS ratio | `hy_ig_ratio` | `OAS_HY / OAS_BBB` |
| CDX momentum | `cdx_ig_mom`, `cdx_hy_mom` | `signals.py` composite functions |
| EPS revision | `eps_rev_us/em/eafe/china` | **NEW** `0.4×pct_change(3M) + 0.6×pct_change(6M)` |

---

## Key Design Rules (Non-Obvious)

- **Adaptive windows**: All normalization uses `min(target_window, available_observations)`. Never break this.
- **Graceful degradation**: Missing signals are silently skipped; weights renormalize automatically.
- **Signal sign lives in SignalMapping**: The `sign` column in taa_config.xlsx:SignalMapping is the ONLY place where +1/−1 inversions are applied. Do not invert inside `build_custom_series.py` or `signals.py`.
- **Zero-sum constraint**: Not enforced globally. The 35% absolute + 65% relative blend (Wang & Kochard 2012) produces approximately zero-sum tilts via the relative view. Cash (money_market) acts as residual absorber.
- **Hierarchical views are additive**: L1 and L2 tilts can coexist. OW LT FI at L1 + OW Corp at L2 = net long LT FI with Corp tilt. No conflict.
- **CESI contrarian at extremes**: At pctile > 85% or < 15%, flip sign. Implemented in `proxies.py` for proxy; should be added to custom_series or transform if wired directly.
- **EWMA vs rolling**: EWMA is default for daily/monthly signals. Rolling only for slow valuation (P/E, ERP) where 10Y window is intentional.
- **Re-standardize after pillar aggregation**: `standardise_pillar()` called after `_wavg()` in `pillars.py`. Do not remove.
- **custom_series.xlsx stores raw levels**: The transform_code in DataSeries handles normalization. Never store pre-normalized custom series (except CDX momentum which is already composite).
- **ISM N.O./Inv ratio**: Stored in H1 as pre-computed ratio (`.ISM G Index`). > 1.0 = demand expanding; normalize with `ewma_z`.
- **SKEW Index**: High SKEW = institutional put-buying = tail risk building. For equity: sign = −1 (headwind). For LT Tsy: sign = +1 (safe-haven). In H5 as `SKEW Index`.
- **EPS revision multi-horizon**: `eps_rev_*` are in custom_series (3M+6M composite). The older `eps_*` series (1M only, via `mom_z`) remain in DataSeries for backward compatibility — both are wired in SignalMapping.

---

## Extending the System (Current Workflow)

### Add a signal to an existing asset class

```bash
# 1. If derived: add computation in build_custom_series.py → run it
python src/build_custom_series.py

# 2. Use add_new_signals.py as a template, or edit taa_config.xlsx DataSeries + SignalMapping directly

# 3. Run pipeline and check the new signal appears
python src/main.py  # look for "OK  my_series_id" in verbose output

# 4. Run health check
python src/test_build_layer.py
```

### Change pillar weights

1. Edit `PillarWeights` sheet in `config/taa_config.xlsx` (each row must sum to 1.0)
2. Run `python src/build_dashboard.py` (updates `src/config.py:PILLAR_WEIGHTS` via BUILD markers)
3. Run `python src/main.py`

### Add a new portfolio

1. Add a row to `config/portfolios.xlsx` sheet "Portfolios" with SAA weights summing to 100
2. Run `python src/main.py` — appears automatically in `multi_portfolio_views.xlsx`

### Modify hierarchy structure

1. Edit `AC_HIERARCHY` dict in `src/config.py` (children, model_weights, max_tilt_l1/l2)
2. Update `AC_PARENT` reverse lookup dict
3. Run `python src/main.py` — `taa_hierarchy_scorecard.csv` reflects new structure

---

## Configuration Management Layer (Build Markers)

Machine-managed blocks in `index.html` and `src/config.py` are wrapped in `<<<BUILD:...>>>` markers.
Run `python src/build_dashboard.py` to update them from `config/taa_config.xlsx`.

**index.html markers**: `BUILD:SIG_MATRIX`, `BUILD:AC_META`, `BUILD:FI_BLUEPRINT`, `BUILD:EQ_BLUEPRINT`, `BUILD:AC_LABEL_PW`

**src/config.py markers**: `BUILD:PY_AC_UNIVERSE`, `BUILD:PY_PILLAR_WEIGHTS`, `BUILD:PY_MAX_TILT`

The `AC_HIERARCHY`, `AC_PARENT`, `AC_STANDALONE` dicts in `config.py` are **NOT** auto-generated — edit manually.

---

## Dashboard Layer

| File | Purpose |
|---|---|
| `src/chartbook_data.py` | Extracts 5Y signal time series → `results/chartbook_data.json` (~4.6 MB) |
| `src/generate_dashboard.py` | Embeds CSVs + JSON inline → `index.html` (standalone, no server); auto-detects latest run |
| `index.html` | **Single dashboard** — methodology + chartbook + live signals; open in any browser |

Dashboard has 9 navigation items covering Chartbook (F/M/S/V signals), TAA Methodology (signal matrix, pillar blueprints), and TAA Signals (scorecard, heatmap, time series).

Design tokens: `--brand:#C41230`, pillars: F=`#14B8A6`, M=`#F59E0B`, S=`#A855F7`, V=`#3A7BD5`. Dark `#0B1220` bg. Chart.js 4.4.1.

---

## Academic References

- Brinson, Hood & Beebower (1986) — asset allocation explains 80–90% of performance variance
- Grinold & Kahn (2000) — TE-budget is superior to zero-sum constraint (higher transfer coefficient)
- Wang & Kochard (2012) — 35/65 absolute/relative z-score TAA blend (validates current scoring design)
- Asness, Moskowitz & Pedersen (2013) — value + momentum everywhere; cross-asset momentum robust
- Koijen, Moskowitz, Pedersen & Vrugt (2018) — carry is universal; OAS/ERP/yield carry is correct
- Maillard, Roncalli & Teïletche (2010) — hierarchical risk parity; L1 and L2 views are orthogonal
- Chan, Jegadeesh & Lakonishok (1996) — earnings revision momentum strongest at 3–6M, not 1M
- Lee (2000) — multi-portfolio TAA: scale tilts by portfolio risk capacity, not flat bps
