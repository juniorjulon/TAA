# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Project Overview

**TAA Dashboard** is an institutional-grade Tactical Asset Allocation (TAA) signal generation system
for insurance portfolios (Rimac Group). It scores **6 active asset classes** across four signal
pillars — **Fundamentals (F), Momentum (M), Sentiment (S), Valuation (V)** — then maps composite
z-scores to conviction-based tilts around strategic benchmarks.

The 10-AC universe is defined in `config/taa_config.xlsx` (AssetClasses sheet), but only 6 are
`active=True`: `lt_treasuries`, `lt_us_corp`, `lt_em_fi`, `us_equity`, `dm_equity`, `em_equity`.
The 4 inactive ACs (`money_market`, `short_term_fi`, `us_growth`, `us_value`) are excluded from
the signal pipeline entirely. MM and STFI's SAA weights are implicit absorbers in the
multi-portfolio view; US Growth and US Value are not considered at all.

The system serves **4 real portfolios** (IGCON / IGMOD / IGDIN / IGEQUS) with different SAA
weights and active risk budgets (50–125 bps TE). All tilts enforce `force_zero_sum = True`
(no short positions — Solvency II / insurance mandate).

**Single source of truth for configuration**: `config/taa_config.xlsx`
**Single source of truth for dashboard**: `index.html` (CSS, JS, layout — updated in place each run)

---

## Development History (chronological)

| Date | Phase | What was built |
|---|---|---|
| Apr 2026 | v1 | Signal pipeline, scoring, proxies, dashboard, 29-check health test |
| Apr 2026 | v2 | Excel-driven signal engine: DataSeries → signal_engine.py → build_all_pillars() |
| Apr 2026 | v2 | build_custom_series.py → custom_series.xlsx (41 derived series) |
| Apr 2026 | v2 | taa_config.xlsx extended: series_type, input_sheet, input_column, transform_code |
| May 2026 | v3 | Hierarchical views (L1/L2), multi-portfolio engine, portfolios.xlsx |
| May 2026 | v3 | SKEW index, ISM N.O./Inv ratio, EPS revision composites (3M+6M) |
| May 2026 | v4 | Removed em_xchina + china_equity as ACs → 10 active ACs |
| May 2026 | v4 | H7 sheet: 5 new series (breakeven_1y, gdpnow, nfci, fci_ez, fci_uk) |
| May 2026 | v4 | Complete SignalMapping rebuild: 130 clean rows, plain-vanilla signals only |
| May 2026 | v4 | 4 real portfolios (Detalle Ports.xlsx) → portfolios.xlsx; force_zero_sum=True |
| May 2026 | v5 | Data quality fixes: GDP cols renamed, modern_ted gated, MIN_DATE_FOR_SIGNALS |
| May 2026 | v5 | PCR (CBOE Put/Call) added to US Equity Sentiment pillar |
| May 2026 | v5 | chart_example.html visual format: IBM Plex fonts, value row, date labels, stats footer |
| May 2026 | v5 | PMI heatmap in Chartbook Fundamentals: monthly columns, 10 series, percentile bars |
| May 2026 | v5 | Chartbook: all charts use MAX default, percentile bands, price overlay in Momentum |
| May 2026 | v5 | generate_dashboard.py updates index.html in-place (model_design.html = design reference only) |
| May 2026 | v6 | economic_sanity.py: standalone report generator → results/economic_sanity/ESR_*.md |
| May 2026 | v6 | generate_dashboard.py: optional "[y/N] Run economic sanity?" prompt at end of pipeline |
| May 2026 | v6 | Momentum (Design 2): single-select metric pills (Composite default), component z-score footer |
| May 2026 | v6 | Composite Z charts (Design 4): 3Y default, sigma bands (±1), TF buttons, colored legend |
| May 2026 | v6 | chartbook_data.py: MAX_ROWS cap removed → full history exported; MAX TF shows full series |
| May 2026 | v6 | generate_dashboard.py: COMPOSITES extended to 756 days (3Y); CB no longer sampled |
| May 2026 | v6 | docs/chart_management_proposal.md: full 94-signal catalog + systematic add/remove process |
| May 2026 | v6 | Health check updated: expects 6 active ACs (not 10), 3 active FI + 3 active EQ blocks |

---

## Complete Script Inventory

| Script | What it does | Key output(s) |
|---|---|---|
| `src/build_custom_series.py` | Computes all 41 derived series (PMI, GDP blends, ERP, PE scores, stress proxies, EPS revision, CDX) | `data/custom_series.xlsx` |
| `src/build_dashboard.py` | Reads taa_config.xlsx, regenerates BUILD blocks in `src/config.py`; skips index.html if no markers | `src/config.py` |
| `src/main.py` | Full TAA pipeline: signals → pillars → composites → tilts → hierarchy → multi-portfolio | `results/RUN_YYYYMMDD_HHMMSS/` |
| `src/chartbook_data.py` | Extracts full signal time series (full history, no cap) + PMI heatmap for dashboard | `results/chartbook_data.json` |
| `src/generate_dashboard.py` | Injects live data into `index.html` in-place; prompts optionally to run economic sanity | `index.html` |
| `src/economic_sanity.py` | Generates economic sanity report: signal movers, AC assessment, macro flags, tilt summary | `results/economic_sanity/ESR_*.md` |
| `src/generate_methodology_doc.py` | Generates Word methodology reference | `docs/TAA_Methodology.docx` |
| `src/test_build_layer.py` | 29-check health test (6 active ACs, 100+ SignalMapping rows, config.py markers) | Exit 0 = all pass |
| `src/add_new_signals.py` | Template for batch additions of signals to taa_config.xlsx | `config/taa_config.xlsx` |
| `src/rebuild_signal_mapping.py` | One-time tool: complete SignalMapping rebuild (disaster recovery) | `config/taa_config.xlsx` |

---

## Full Pipeline — Standard Weekly Refresh

```bash
# Step 1 — Rebuild derived series (after updating Dashboard_TAA_Inputs.xlsx)
python src/build_custom_series.py
# -> data/custom_series.xlsx  (41 series: PMI, GDP blends, ERP, PE scores, stress, CDX, EPS revision)

# Step 2 — Run TAA signal pipeline
python src/main.py
# -> results/RUN_YYYYMMDD_HHMMSS/taa_scorecard.csv            z-scores + tilts per AC
# -> results/RUN_YYYYMMDD_HHMMSS/taa_composite_series.csv      full composite history
# -> results/RUN_YYYYMMDD_HHMMSS/pillars_{ac}.csv              per-AC pillar history (x10)
# -> results/RUN_YYYYMMDD_HHMMSS/taa_hierarchy_scorecard.csv   L1/L2 views
# -> results/RUN_YYYYMMDD_HHMMSS/taa_bucket_summary.csv        bucket summary
# -> results/RUN_YYYYMMDD_HHMMSS/multi_portfolio_views.xlsx    4 portfolios × tilts

# Step 3 — Health check
python src/test_build_layer.py  # Expected: 29/29 PASS

# Step 4 — Regenerate dashboard
python src/chartbook_data.py     # -> results/chartbook_data.json  (full history, ~15 MB)
python src/generate_dashboard.py # -> index.html  (open in browser)
#   At end of generate_dashboard.py, you'll be prompted:
#   "Run economic sanity report? [y/N]"
#   Answer y to generate results/economic_sanity/ESR_YYYYMMDD_HHMMSS.md

# Step 5 (optional, standalone) — Economic sanity report only
python src/economic_sanity.py    # -> results/economic_sanity/ESR_*.md

# Step 6 (only when config changes) — Propagate to config.py
python src/build_dashboard.py    # -> src/config.py BUILD blocks updated
```

---

## System Architecture

### Data Flow (v5, current)

```
Dashboard_TAA_Inputs.xlsx (OAS, H1-H7, AAII — 9 sheets)
         |
   data_loader.py  load_all()  →  dict{oas, pe, yields, fi_px, sectors,
                                       tsy, cds, mkt, f1, f3, aaii, h7}
         |
   build_custom_series.py  →  data/custom_series.xlsx (41 derived series)
         |
   signal_engine.py  SignalEngine.load_all()
         |   Reads DataSeries from taa_config.xlsx (170 rows)
         |   For each active row: load from correct sheet, apply transform_code
         |   6 transforms: ewma_z | rolling_z | pctile | mom_z | price_mom | inv_mom_z
         |   Clips all signals to dates >= MIN_DATE_FOR_SIGNALS (2013-02-01)
         |   Returns: {series_id: pd.Series (z-score)}  — 97 signals total
         |
   proxies.py  build_proxy_ext()  →  fallback signals for gaps
         |
   pillars.py  build_all_pillars(ac, signals, signal_mapping)
         |   Reads SignalMapping (130 rows); applies sign × weight per (ac, pillar)
         |   _wavg() + standardise_pillar() per pillar
         |
   scoring.py  composite_score() + score_snapshot()
         |   Pillar z-scores → 35% absolute + 65% relative view → conviction → tilt
         |
   hierarchical_scoring.py  HierarchicalViews.enrich()
         |   L1 aggregate z per bucket; L2 = z_child − z_parent (zero-sum within bucket)
         |
   portfolio.py  build_multi_portfolio_report()
         |   Reads portfolios.xlsx (4 portfolios); scales tilts by TE budget
         |   force_zero_sum=True: redistributes excess among positive-SAA ACs
         |   portfolio_weight.clip(lower=0): no short positions ever
         |
   results/RUN_YYYYMMDD_HHMMSS/  (6 output files)
         |
   chartbook_data.py  →  results/chartbook_data.json
         |   PMI heatmap (monthly, from 2023), momentum price overlays,
         |   GDP revision, breakeven, modern_ted from tsy sheet
         |
   generate_dashboard.py  reads and updates index.html in-place
         |   Injects: SCORECARD, COMPOSITES, CB, SIG_MATRIX, FI/EQ_BLUEPRINT, PW
         |   Adds: buildFundamentalsHeatmap() JS (PMI/macro heatmap)
         →  index.html  (single dashboard file)
```

### Module Responsibilities

| File | Responsibility |
|---|---|
| `src/config.py` | Paths, column maps, windows, `MIN_DATE_FOR_SIGNALS`, `MAX_FFILL_MONTHLY`, `SMOOTH_COMPOSITE`, `AC_HIERARCHY`, `AC_PARENT`, `PILLAR_WEIGHTS` |
| `src/data_loader.py` | Loads 9 Excel sheets; `MAX_FFILL_DAYS=5` for daily, `MAX_FFILL_MONTHLY=31` for H1 monthly |
| `src/signals.py` | Atomic z-score primitives — all return `pd.Series` with DatetimeIndex |
| `src/build_custom_series.py` | GDP blends (gdp_forecast_*_26/27), ERP, PE scores, modern_ted (gated 2018-04-01), stress proxies |
| `src/signal_engine.py` | `SignalEngine` class: loads → normalizes → clips at `MIN_DATE_FOR_SIGNALS` |
| `src/pillars.py` | `build_all_pillars()` generic builder; legacy `pillar_*()` functions preserved (not called) |
| `src/proxies.py` | Fallback signals when engine has gaps |
| `src/scoring.py` | Composite → pillar agreement multiplier → absolute+relative → tilt |
| `src/hierarchical_scoring.py` | L1 aggregate + L2 within-class z-scores and tilts |
| `src/portfolio.py` | `PortfolioConfig`, `apply_house_view()`, zero-sum + no-short enforcement |
| `src/main.py` | Pipeline entry; OAS staleness warning; RUN timestamp with seconds |
| `docs/model_design.html` | Design reference only — NOT read by generate_dashboard.py; used as visual spec |
| `src/generate_dashboard.py` | Injects live data into index.html in-place |
| `src/chartbook_data.py` | Exports chartbook_data.json: PMI heatmap + all signal time series |

---

## Key Configuration Files

| File | Contents | How to edit |
|---|---|---|
| `config/taa_config.xlsx` | AssetClasses (10), DataSeries (170 rows), PillarWeights (10 rows), SignalMapping (130 rows), TransformCodes, MomentumConfig | Edit directly; run `build_dashboard.py` after changes |
| `config/portfolios.xlsx` | **4 real portfolios**: IGCON/IGMOD/IGDIN/IGEQUS — SAA weights, TE budgets, force_zero_sum=True | Edit in Excel; loaded automatically by `main.py` |
| `data/custom_series.xlsx` | 41 derived series; regenerated by `build_custom_series.py` | Never edit manually |
| `src/config.py` | Python constants (BUILD-marker blocks: ASSET_CLASSES, PILLAR_WEIGHTS, MAX_TILT_PCT) + AC_HIERARCHY, AC_PARENT, MIN_DATE_FOR_SIGNALS, MAX_FFILL_MONTHLY | BUILD blocks via `build_dashboard.py`; others edit manually |
| `docs/model_design.html` | Design reference only — not part of the pipeline; kept for reference | Do not edit; not read by any script |
| `docs/data_quality.md` | Data quality rules, known gaps, ffill limits, reliable_from dates | Reference document — update when adding new series |
| `docs/signal_improvements.md` | Excluded signals with rationale and activation instructions | Update when reviewing signals |

---

## Asset Class Universe — 10 Active ACs

| Key | Label | Group | Hierarchy | Portfolio SAA |
|---|---|---|---|---|
| `money_market` | Money Market | FI | Standalone (L1 only) | 5–15% |
| `short_term_fi` | Short-Term FI (USD) | FI | Standalone (L1 only) | 0–25% |
| `lt_treasuries` | LT US Treasuries | FI | Child of `lt_fi_aggregate` | 0% (tracked) |
| `lt_us_corp` | LT US Corporate | FI | Child of `lt_fi_aggregate` | 0% (tracked) |
| `lt_em_fi` | LT EM Corp (CEMBI) | FI | Child of `lt_fi_aggregate` | 15–30% |
| `us_equity` | US Equity (Broad) | EQ | Parent of us_value/us_growth | 19–95% |
| `us_growth` | US Growth | EQ | Child of `us_equity` | 0 (L2 tilt) |
| `us_value` | US Value | EQ | Child of `us_equity` | 0 (L2 tilt) |
| `dm_equity` | DM ex-US Equity | EQ | Standalone (L1 only) | 0–18% |
| `em_equity` | Emerging Markets Equity | EQ | Standalone (L1 only) | 3–8% |

**Note:** em_xchina and china_equity were removed as active ACs in May 2026. Their underlying data series (em_xchina_tr, pmi_china, etc.) remain in DataSeries and are used as signals for em_equity.

### Real Portfolios (config/portfolios.xlsx)

| Portfolio | Label | TE Budget | Risk Profile | SAA: MM/STFI/LT EM/US Eq/DM/EM |
|---|---|---|---|---|
| IGCON_USD | IG Conservador USD | 50 bps | Conservative | 15/25/30/19.2/7.5/3.3 |
| IGMOD_USD | IG Moderado USD | 75 bps | Moderate | 10/15/25/32.0/12.5/5.5 |
| IGDIN_USD | IG Dinámico USD | 100 bps | Aggressive | 5/10/15/44.8/17.5/7.7 |
| IGEQUS_USD | IG Acciones EE.UU. | 125 bps | Aggressive | 5/0/0/95.0/0/0 |

All 4 portfolios have `force_zero_sum=True` (no leverage, no shorts).

### Hierarchical Structure (AC_HIERARCHY in config.py)

```
Level 1 — 5 top-level views
  money_market     standalone
  short_term_fi    standalone
  lt_fi_aggregate  SYNTHETIC — z = 0.40×lt_tsy + 0.35×lt_corp + 0.25×lt_em
  us_equity        own composite z IS the L1 view
  dm_equity        standalone
  em_equity        standalone  (no sub-ACs since em_xchina/china removed)

Level 2 — within-bucket rotation (zero-sum within bucket)
  Within lt_fi:    z_L2 = z_child − z_lt_fi_agg
  Within us_equity: z_L2 = z_child − z_us_equity
```

---

## Data Quality Rules (see docs/data_quality.md for full reference)

| Rule | Value | Reason |
|---|---|---|
| Signal floor | `MIN_DATE_FOR_SIGNALS = 2013-02-01` | EWMA 756d warm-up from 2010-12-31 start |
| modern_ted gate | Starts 2018-04-01 | SOFR inception; EWMA reliable from ~2020-12 |
| Daily ffill | `MAX_FFILL_DAYS = 5` | Weekend + 1 holiday max |
| Monthly ffill | `MAX_FFILL_MONTHLY = 31` | PMI/CESI/GDP in H1 — 1 month max |
| GDP series naming | `gdp_forecast_us_26`, `gdp_forecast_us_27`, etc. | Year-suffix convention (26=current, 27=next) |
| Breakevens source | H5 (`mkt` DataFrame) | Moved from H3 (`f3`) to H5 in data structure — `_get(mkt, "breakeven_5y")` |
| Modern TED source | `tsy["modern_ted"]` | `_get(tsy, "modern_ted")`; NOT `mkt["ted"]` (defunct since 2019) |
| OAS staleness warning | Shown if OAS > 7 days behind H5 | OAS typically lags ~17 business days |
| RUN timestamp format | `RUN_%Y%m%d_%H%M%S` includes seconds | Prevents collision if two runs start in same minute |
| Composite smoothing | `SMOOTH_COMPOSITE = False` (toggle) | 10-day rolling median available; off by default |

---

## Signal Universe — 97 Active Signals

### Transform Codes

| Code | Output | Example |
|---|---|---|
| `ewma_z` | EWMA z-score (span=window, default 756d) | VIX, DXY, FCI, PMI composites |
| `rolling_z` | Rolling z-score (window days) | Breakevens, ERP, term spread |
| `pctile` | Percentile → `(p−0.5)×4` rescaled | OAS levels, yield pctile |
| `mom_z` | `pct_change(window)` → EWMA z-score | Forward EPS revisions |
| `price_mom` | Composite: 12-1M (40%) + 3M (25%) + MA (25%) + RSI (10%) | TR price indices |
| `inv_mom_z` | `−ewma_z(diff(window))` — falling = positive | OAS spreads, yields |

### Plain-Vanilla Signal Design (v4/v5)

SignalMapping follows these rules:
- Every signal has real, verified data in Dashboard_TAA_Inputs.xlsx or custom_series.xlsx
- No duplicate signals within the same (AC, pillar)
- No signals without clear, direct economic rationale
- Sign convention: `+1` = series positive → bullish for AC; `−1` = series positive → bearish
- Sign lives ONLY in SignalMapping — never inverted in build_custom_series.py or signals.py
- Complex/uncertain signals documented in `docs/signal_improvements.md` (not wired)

Key signals by pillar:

**Pillar F — Fundamentals**
- PMI composites (pmi_us, pmi_ez, pmi_china): H1 mfg+svcs/2
- GDP blends (gdp_us, gdp_em, etc.): w_cur×gdp_forecast_*_26 + (1−w)×gdp_forecast_*_27
- CESI surprise indices (cesi_us, cesi_ez, cesi_em, cesi_china, cesi_japan)
- EPS revisions: eps_us (1M mom_z) + eps_rev_us (40%×3M + 60%×6M composite)
- ISM N.O./Inventories ratio: ism_no_inv (threshold 1.0 = demand > inventory)
- GDPNow real-time: gdpnow (H7, ewma_z) — US only, supplement to consensus
- Breakevens: breakeven_1y (STFI F), breakeven_5y/10y (FI fundamentals)
- Rate environment: real_ff (FDTR − PCE), core_pce

**Pillar M — Momentum**
- Price momentum (price_mom): sp500_tr, sp500_gro_tr, sp500_val_tr, eafe_tr, msci_em_tr, bfu5_price, i132_price, lt03_price, bsgv_price
- Spread momentum (inv_mom_z): oas_bbb_mom, oas_hy_mom, oas_em_mom
- Yield momentum (inv_mom_z): gt02_mom, gt10_mom
- CDX momentum: cdx_ig_mom, cdx_hy_mom (custom composite)

**Pillar S — Sentiment**
- Volatility: vix (+1 contrarian equity, safe-haven FI), move_z (bond vol), vstoxx_z (EZ), skew_z (tail risk)
- Funding stress: modern_ted (tbill_3m − SOFR, gated 2018+)
- Stress proxies: hy_stress, hy_safe_haven, em_stress, embi (all = OAS.diff(21))
- Contrarian positioning: aaii_z (sign −1 for equity), **pcr** (CBOE Put/Call, sign +1 contrarian equity — added May 2026)
- Financial conditions: fci_z (Bloomberg US FCI, sign −1), fci_ez (Bloomberg EZ FCI, sign −1 for DM)

**Pillar V — Valuation**
- PE scores: pe_score_sp500/eafe/em/emx/gro/val (pe_score() from signals.py)
- ERP: erp_us/acwi/em/em_xchina/china (EY% − TIPS_10Y%)
- Relative PE: rel_pe_gro_val, rel_pe_dm_us, rel_pe_em_us, rel_pe_us_em, rel_pe_val_gro
- OAS levels (pctile): oas_bbb, oas_hy, oas_em, oas_latam
- HY/IG ratio: hy_ig_ratio
- Yield levels (pctile): gt02, gt10, tips_5y, tips_10y, term_spread

---

## Input Data — Dashboard_TAA_Inputs.xlsx

9 sheets loaded by `data_loader.load_all()`:

| Sheet | Internal key | Period | Key series |
|---|---|---|---|
| OAS | `oas` | 1999–2026 | oas_bbb, oas_hy, oas_em, oas_latam |
| H4 | `pe`, `yields`, `fi_px` | 2010–2026 | PE ratios, earnings yields, TR price levels |
| H5 | `mkt`, `tsy`, `cds` | 2010–2026 | VIX, MOVE, VSTOXX, SKEW, PCR, DXY, FCI, breakevens, SOFR, yields |
| H6 | `sectors` | 2010–2026 | S&P 11 sectors PE/EY/TR |
| H1 | `f1` (part) | 2010–2026 | PMI (ISM, EZ, China), CESI (US/EZ/CN/Global), GDP forecasts |
| H2 | `f1` (part) | 2010–2026 | PMI (Japan/UK), CESI (EM/Japan), GDP (Japan/China/LatAm) |
| H3 | `f3` | 2010–2026 | Forward EPS (US/EM/EAFE/China/Japan) |
| H7 | `h7` | 2010–2026 | breakeven_1y, gdpnow, nfci, fci_ez, fci_uk |
| AAII | `aaii` | 1987–2026 | aaii_bull_bear (weekly → daily ffill) |

**Important column renaming** (May 2026):
- GDP forecast columns now use year-suffix: `gdp_forecast_us_26` (current year), `gdp_forecast_us_27` (next year)
- All regions follow same pattern: us/em/dm/eu/jp/cn/latam + 26/27

---

## Custom Series (data/custom_series.xlsx) — 41 Series

Regenerated by `build_custom_series.py`. Never edit manually.

| Group | Series | Formula |
|---|---|---|
| PMI composites | pmi_us, pmi_ez, pmi_china | (mfg + svcs) / 2 |
| GDP blends | gdp_us/dm/em/eu/jp/cn | w_cur × gdp_forecast_*_26 + (1−w) × gdp_forecast_*_27, w=month/12 |
| Rate environment | modern_ted (gated 2018-04), real_ff, term_spread | tbill−SOFR; FDTR−PCE; 10Y−2Y |
| ERP | erp_us/acwi/em/em_xchina/china | EY% − TIPS_10Y% |
| PE scores | pe_score_sp500/eafe/em/emx/china/gro/val | pe_score() from signals.py |
| Relative PE | rel_pe_gro_val, rel_pe_val_gro, rel_pe_dm_us, rel_pe_em_us, rel_pe_us_em, rel_pe_china_us | log(PE_b / PE_a) |
| OAS proxies | hy_stress, hy_safe_haven, em_stress, embi | OAS.diff(21) (raw; sign in SignalMapping) |
| OAS ratio | hy_ig_ratio | OAS_HY / OAS_BBB |
| CDX momentum | cdx_ig_mom, cdx_hy_mom | signals.py composite functions |
| EPS revision | eps_rev_us/em/eafe/china | 0.4×pct_change(63d) + 0.6×pct_change(126d) |

---

## Dashboard — index.html

Single standalone file. **Do NOT edit directly** — regenerate via scripts.

### Single dashboard file: index.html
All CSS, JS logic, chart rendering, layout, and live data live in `index.html`.
`generate_dashboard.py` reads `index.html`, replaces the JS data constants in-place, and writes it back.
`docs/model_design.html` is a **design reference only** — it is not read by any script.

**Chart design** (chart_example.html reference format):
- IBM Plex Mono + IBM Plex Sans fonts
- Card: region label (mono uppercase) + chart name + large value row + date labels + timeframe pills (3M/1Y/3Y/MAX) + stats footer (Latest / Trend / Z or Pctile)
- MAX is the default active timeframe (shows full history)
- Percentile position bars above Sentiment + Valuation charts (25th/75th over 5Y or 10Y window)
- Momentum charts include cumulative % price return overlay (grey area, secondary Y-axis)

### PMI/Leading Indicators Heatmap (Chartbook → I. Fundamentals)
- Monthly columns from 2023-01 to current, grouped by Quarter → Year
- 15 rows in 5 groups: Global, United States, Eurozone, China, Japan & UK
- Colors: PMI rows use absolute 50-threshold (green=expansion, red=contraction)
- Non-PMI rows (FCI, GDPNow, EPS revision, GDP forecasts): independent per-row percentile scale
- Data source: `CB.fundamentals_heatmap` (computed in `chartbook_data.py`)

### Regeneration workflow

```bash
# After any data update:
python src/build_custom_series.py
python src/main.py
python src/chartbook_data.py
python src/generate_dashboard.py  # → index.html

# After config/signal changes:
python src/build_dashboard.py     # → src/config.py BUILD blocks
python src/generate_dashboard.py  # → index.html (picks up new SIG_MATRIX etc.)
```

### What generate_dashboard.py injects

| Constant | Source | Description |
|---|---|---|
| `SCORECARD` | `results/RUN_*/taa_scorecard.csv` | Latest z-scores + tilts per AC |
| `COMPOSITES` | `results/RUN_*/taa_composite_series.csv` | 252-day composite history |
| `CB` | `results/chartbook_data.json` | All signal time series + heatmap |
| `SIG_MATRIX` | `taa_config.xlsx` via `build_dashboard.py` | Signal × AC coverage matrix |
| `FI_BLUEPRINT` | `taa_config.xlsx` via `build_dashboard.py` | FI pillar signal details |
| `EQ_BLUEPRINT` | `taa_config.xlsx` via `build_dashboard.py` | EQ pillar signal details |
| `AC_LABEL_FULL`, `PW` | `taa_config.xlsx` via `build_dashboard.py` | AC labels + pillar weights |

---

## Key Design Rules (Non-Obvious)

- **MIN_DATE_FOR_SIGNALS = 2013-02-01**: All z-scores before this date are dropped. EWMA span=756 days; data starts 2010-12-31; signals only reliable after 756 days of warm-up. Each series has its own `reliable_from` date computed as first_valid_date + warm_up_period.
- **modern_ted gated at 2018-04-01**: SOFR inception. Before 2018, the series is NaN. Gating prevents the NaN gap from warping the EWMA mean.
- **force_zero_sum=True for all portfolios**: Redistributes net tilt excess proportionally among positive-SAA ACs. Money market absorbs any residual. No weight ever goes below 0%.
- **`active` column in taa_config.xlsx**: Single control for AC inclusion. Setting `active=False` excludes an AC from the entire pipeline (signal generation, scorecard, portfolio view, config.py export). Currently `False` for: `money_market`, `short_term_fi` (structural absorbers — their SAA weights in portfolios.xlsx remain valid implicitly), `us_growth`, `us_value` (not considered at all). To re-enable an AC: set `active=True` in Excel and re-run `python src/build_dashboard.py`.
- **MM and STFI as implicit absorbers**: With `active=False`, MM and STFI are not in the scorecard or portfolio view. The 6 active tactical ACs' tilts sum to ~zero (via `force_zero_sum`), and MM/STFI's SAA weights in portfolios.xlsx provide the structural balance — they're not displayed but their weights are preserved in the portfolio math.
- **Sign lives in SignalMapping only**: Never invert in build_custom_series.py or signals.py.
- **GDP series naming**: Bloomberg tickers end in 26 (current year) or 27 (next year). Internal names follow `gdp_forecast_{region}_{year}` convention.
- **OAS staleness**: OAS sheet typically lags H5 by ~17 business days. A warning prints in main.py when lag > 7 days.
- **custom_series.xlsx is never edited manually**: Always regenerate via `build_custom_series.py`.
- **SMOOTH_COMPOSITE = False** (toggle in config.py): When True, applies 10-day rolling median to composite z-scores before conviction mapping (eliminates holiday/month-end spikes). Both raw and smooth exported.
- **EWMA vs rolling**: EWMA is the default. Rolling only for slow valuation (P/E, ERP) where 10Y window is intentional.
- **Re-standardize after pillar aggregation**: `standardise_pillar()` called after `_wavg()`. Do not remove.
- **chartbook_data.py MAX_ROWS**: Removed cap (was 252×5). Full series history exported (~15 MB JSON). Client-side `sliceTF()` handles timeframe windowing. Dashboard file size ~16 MB.
- **Chart design templates** (in `docs/design templates/`): Fundamentals/Sentiment = Design 1 (SVG + Z toggle), Momentum = Design 2 (Chart.js, single-select metric pills, price overlay, component z-footer), Valuation = Design 3 (Design 1 + percentile band), Composite Z = Design 4 (multi-series, 3Y default, sigma bands). AC overview cards = asset_class_card_design.html.
- **COMPOSITES history**: generate_dashboard.py exports last 756 days (3Y) per Design 4 requirement. Composite Z charts have TF buttons (3M/1Y/3Y/MAX) with 3Y as default active.

---

## Extending the System

### Add a signal to an existing AC

```bash
# If derived: add computation in build_custom_series.py, then:
python src/build_custom_series.py

# Add to taa_config.xlsx DataSeries + SignalMapping
# (use add_new_signals.py as template for batch additions)

python src/main.py               # look for "OK  series_id" in verbose output
python src/test_build_layer.py   # 29/29 PASS
```

### Change pillar weights

1. Edit `PillarWeights` sheet in `config/taa_config.xlsx` (must sum to 1.0 per row)
2. `python src/build_dashboard.py` — updates `src/config.py:PILLAR_WEIGHTS`
3. `python src/main.py`

### Add a new portfolio

1. Add row to `config/portfolios.xlsx` sheet "Portfolios" with SAA weights summing to 100
2. Set `force_zero_sum = True` (required — no short positions)
3. `python src/main.py` — appears in `multi_portfolio_views.xlsx`

### Modify the dashboard visual design

1. Edit `index.html` directly (CSS, JS functions, chart rendering)
2. `python src/generate_dashboard.py` — re-injects live data back into `index.html`

---

## Academic References

- **Brinson/Hood/Beebower (1986)** — asset allocation explains 80–90% of variance
- **Grinold & Kahn (2000)** — TE-budget superior to zero-sum constraint
- **Wang & Kochard (2012)** — 35/65 absolute/relative z-score blend (validates current design)
- **Asness/Moskowitz/Pedersen (2013)** — value + momentum everywhere
- **Koijen et al. (2018)** — carry is universal; OAS/ERP/yield carry is correct
- **Maillard/Roncalli/Teïletche (2010)** — hierarchical risk parity; L1 and L2 views are orthogonal
- **Chan/Jegadeesh/Lakonishok (1996)** — earnings revision momentum strongest at 3–6M
- **Lee (2000)** — multi-portfolio TAA: scale tilts by portfolio risk capacity
