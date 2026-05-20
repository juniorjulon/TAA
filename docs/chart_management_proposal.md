# Chart Management System — Proposal
**Version 1.0 | May 2026**

---

## 1. Problem Statement

Currently, adding or removing charts from the TAA Dashboard requires editing multiple files (`chartbook_data.py`, `generate_dashboard.py`, `index.html`) with no central registry. There is no systematic way to know which series are available, what their data windows are, or which design template applies.

This document proposes a **Chart Registry** approach that makes chart management declarative and auditable.

---

## 2. Design Templates — Assignment Rules

All charts follow one of five templates in `docs/design templates/`:

| Template | File | Used for | Key features |
|---|---|---|---|
| **Design 1** | `chart_design_1.html` | Fundamentals, Sentiment | SVG line chart, raw value primary + Z overlay toggle, hover crosshair, timeframes 3M/1Y/3Y/MAX |
| **Design 2** | `chart_design_2.html` | Momentum | Chart.js, price TR index overlay (grey, right axis), momentum Z on left, metric pills (Composite/12-1M/3M/MA/RSI), timeframes 3M/1Y/3Y/MAX |
| **Design 3** | `chart_design_3.html` | Valuation | Same as Design 1 but adds percentile position band (25th/75th over 5Y or 10Y) |
| **Design 4** | `chart_design_4.html` | FI & Equity Composite Z | Multi-series SVG, 3Y history default, zero-line + sigma bands, no raw value toggle |
| **AC Card** | `asset_class_card_design.html` | Asset class overview cards | Pillar score bars, composite Z badge, conviction label, tilt indicator |

### Template assignment by signal type

| Signal category | Template |
|---|---|
| PMI, CESI, GDP, EPS revisions, Breakevens, Core PCE, GDPNow | Design 1 (Fundamentals) |
| Price momentum (equity TR, FI TR) | Design 2 (Momentum) |
| Spread momentum (OAS diff, CDX mom), Yield momentum | Design 1 (Momentum — no price overlay variant) |
| VIX, MOVE, VSTOXX, SKEW, PCR, AAII, FCI, TED, Stress proxies | Design 1 (Sentiment) |
| OAS levels, Yield levels, PE scores, ERP, Relative PE | Design 3 (Valuation) |
| Composite Z-score history per AC | Design 4 |
| Per-AC summary card | AC Card |

---

## 3. Chart Registry Concept

### 3.1 Registry file: `config/chart_registry.yml`

Each chart is defined as a YAML entry. Adding a chart = adding one entry. Removing = deleting the entry. The dashboard generation scripts read this file automatically.

**Schema:**
```yaml
- id: pmi_us_composite           # unique chart ID
  title: "PMI US Composite"      # display title
  region_tag: "US"               # mono uppercase tag above title
  series_id: pmi_us              # must exist in DataSeries
  pillar: F                      # F | M | S | V
  template: design_1             # design_1 | design_2 | design_3 | design_4
  section: fundamentals          # dashboard section: fundamentals | momentum | sentiment | valuation
  timeframes: [3M, 1Y, 3Y, MAX]  # available timeframe pills; MAX always shows full history
  default_tf: MAX                # active on page load
  show_z_toggle: true            # show Z-score overlay toggle (design_1/3 only)
  show_percentile_band: false    # show 25th/75th band (design_3 only)
  percentile_window_y: 10        # 5 or 10 years (design_3 only)
  price_overlay: false           # show TR price index overlay (design_2 only)
  footer_stats: [Latest, Z, Pctile]  # stats shown in card footer
  active: true                   # false = excluded from dashboard without deleting
```

### 3.2 How `generate_dashboard.py` uses the registry

1. Load `config/chart_registry.yml`
2. For each active chart entry, locate the series in `chartbook_data.json`
3. Apply the specified template, injecting the data and metadata
4. Insert into the correct dashboard section

This means **`chartbook_data.py` must export ALL available series** (not just pre-selected ones), and the registry controls what is actually displayed.

---

## 4. Process for Adding a Chart

### Step 1 — Confirm the series exists

Check `docs/series_catalog_full.csv`. If it's not there:
- For raw inputs: add to `Dashboard_TAA_Inputs.xlsx` and `DataSeries` sheet
- For derived series: add to `build_custom_series.py` and `DataSeries` sheet
- Run `python src/build_custom_series.py` to regenerate

### Step 2 — Choose the template

Use the assignment table in Section 2. If uncertain:
- Raw macro indicators → Design 1
- Price TR series → Design 2
- Spread/yield levels with historical context → Design 3
- Multi-AC composite comparison → Design 4

### Step 3 — Add entry to chart registry

Add a YAML block to `config/chart_registry.yml` following the schema above.

### Step 4 — Ensure chartbook exports the series

Verify `src/chartbook_data.py` exports the series under the correct section key. If not, add it.

### Step 5 — Regenerate dashboard

```bash
python src/chartbook_data.py
python src/generate_dashboard.py
```

Open `index.html` and verify the chart renders correctly with full history on MAX.

---

## 5. Process for Removing a Chart

1. In `config/chart_registry.yml`, set `active: false` (soft delete — preserves the definition)
2. Run `python src/generate_dashboard.py`
3. To hard delete: remove the YAML entry entirely

**Do not** remove series from `chartbook_data.py` unless the series is also removed from `DataSeries` — other charts may share the same underlying data.

---

## 6. Full Signal Catalog (94 Active Series, as of 2026-05-20)

> Source: `config/taa_config.xlsx` → `DataSeries` sheet, filtered to rows with `transform_code` populated.
> Current Z-scores from run `RUN_20260520_114858` (data through 2026-05-15).

### 6.1 Fundamentals (F) — 31 signals

| series_id | Signal Name | Transform | Frequency | Source | Current Z |
|---|---|---|---|---|---|
| pmi_us | PMI US Composite | ewma_z | Monthly | custom_series | +0.81 |
| pmi_ez | PMI Eurozone Composite | ewma_z | Monthly | custom_series | -0.71 |
| pmi_china | PMI China Composite | ewma_z | Monthly | custom_series | +0.36 |
| pmi_japan_mfg | Japan Mfg PMI | ewma_z | Monthly | H2 | +3.00 |
| cesi_us | Citi US Surprise | ewma_z | Daily | H1 | +1.15 |
| cesi_ez | Citi Eurozone Surprise | ewma_z | Daily | H1 | -1.41 |
| cesi_china | Citi China Surprise | ewma_z | Daily | H1 | +0.91 |
| cesi_em | Citi EM Surprise | ewma_z | Daily | H2 | +1.33 |
| cesi_japan | Citi Japan Surprise | ewma_z | Daily | H2 | -0.52 |
| gdp_us | US GDP Blend | ewma_z | Daily | custom_series | +0.65 |
| gdp_eu | EU GDP Blend | ewma_z | Daily | custom_series | -1.59 |
| gdp_em | EM GDP Blend | ewma_z | Daily | custom_series | +0.66 |
| gdp_dm | DM GDP Blend | ewma_z | Daily | custom_series | -0.16 |
| gdp_china | China GDP Blend | ewma_z | Daily | custom_series | +0.93 |
| gdp_japan | Japan GDP Forecast | ewma_z | Monthly | custom_series | +0.16 |
| gdpnow | Atlanta Fed GDPNow | ewma_z | Daily | H7 | +0.77 |
| breakeven_1y | 1Y Breakeven Inflation | rolling_z | Daily | H7 | +0.59 |
| breakeven_5y | 5Y Breakeven Inflation | rolling_z | Daily | H5 | +2.10 |
| breakeven_10y | 10Y Breakeven Inflation | rolling_z | Daily | H5 | +2.45 |
| core_pce | US Core PCE YoY | ewma_z | Monthly | H5 | +0.24 |
| real_ff | Real Fed Funds Rate | rolling_z | Daily | custom_series | -1.91 |
| eps_us | US Fwd EPS Revision (1M) | mom_z | Daily | H3 | +0.19 |
| eps_em | EM Fwd EPS Revision (1M) | mom_z | Daily | H3 | +0.10 |
| eps_eafe | EAFE Fwd EPS Revision (1M) | mom_z | Daily | H3 | +0.26 |
| eps_china | China Fwd EPS Revision (1M) | mom_z | Daily | H3 | -0.52 |
| eps_japan | Japan Fwd EPS Revision (1M) | mom_z | Monthly | H3 | +0.15 |
| eps_rev_us | US EPS Revision Composite (3M+6M) | ewma_z | Daily | custom_series | +1.67 |
| eps_rev_em | EM EPS Revision Composite (3M+6M) | ewma_z | Daily | custom_series | +1.44 |
| eps_rev_eafe | EAFE EPS Revision Composite (3M+6M) | ewma_z | Daily | custom_series | +1.83 |
| eps_rev_china | China EPS Revision Composite (3M+6M) | ewma_z | Daily | custom_series | +1.01 |
| ism_no_inv | ISM New Orders / Inventories | ewma_z | Monthly | H1 | +0.58 |

**Data window**: Most daily F signals available from 2013-02-01 (MIN_DATE_FOR_SIGNALS). GDP blends start ~Feb 2025 (rolling 12-month forecast blend). Monthly PMI/GDP data starts 2010-12-31 raw, normalized from 2013-02-01.

---

### 6.2 Momentum (M) — 19 signals

| series_id | Signal Name | Transform | Frequency | Source | Current Z |
|---|---|---|---|---|---|
| sp500_tr | S&P 500 Total Return | price_mom | Daily | H4 | +0.39 |
| sp500_gro_tr | S&P 500 Growth TR | price_mom | Daily | H4 | +0.45 |
| sp500_val_tr | S&P 500 Value TR | price_mom | Daily | H4 | +0.19 |
| eafe_tr | MSCI EAFE TR | price_mom | Daily | H4 | -0.20 |
| msci_em_tr | MSCI EM TR | price_mom | Daily | H4 | +0.77 |
| em_xchina_tr | MSCI EM ex-China TR | price_mom | Daily | H4 | +1.09 |
| china_tr | MSCI China TR | price_mom | Daily | H4 | -0.57 |
| msci_acwi_tr | MSCI ACWI TR | price_mom | Daily | H4 | +0.34 |
| bfu5_price | BFU5 / 1-3Y UST TR | price_mom | Daily | H4 | -0.89 |
| i132_price | ICE 1-3Y UST TR | price_mom | Daily | H4 | -0.89 |
| lt03_price | LT03 Short Govt TR | price_mom | Daily | H4 | -0.92 |
| bsgv_price | BSGV Long Govt TR | price_mom | Daily | H4 | -0.36 |
| oas_bbb_mom | BBB OAS Momentum | diff_z | Daily | OAS | -0.39 |
| oas_hy_mom | HY OAS Momentum | diff_z | Daily | OAS | +0.04 |
| oas_em_mom | EM Corp OAS Momentum | diff_z | Daily | OAS | -0.30 |
| gt02_mom | US 2Y Yield Momentum | diff_z | Daily | H5 | +1.23 |
| gt10_mom | US 10Y Yield Momentum | diff_z | Daily | H5 | +1.21 |
| cdx_ig_mom | CDX IG 5Y Momentum | ewma_z | Daily | custom_series | -0.07 |
| cdx_hy_mom | CDX HY Momentum | ewma_z | Daily | custom_series | +0.31 |

**Data window**: price_mom series: 2013-02-01 to present (~3,466 obs). OAS momentum: 2013-02-01 (~3,514 obs). CDX momentum: 2013-02-01 (~3,513 obs).

---

### 6.3 Sentiment (S) — 16 signals

| series_id | Signal Name | Transform | Frequency | Source | Current Z |
|---|---|---|---|---|---|
| vix | CBOE VIX Index | ewma_z | Daily | H5 | -0.06 |
| move_z | ICE MOVE Index | ewma_z | Daily | H5 | -0.45 |
| vstoxx_z | VSTOXX (EZ Vol) | ewma_z | Daily | H5 | +0.55 |
| skew_z | CBOE SKEW Index | ewma_z | Daily | H5 | +0.10 |
| pcr | CBOE Put/Call Ratio | ewma_z | Daily | H5 | +0.49 |
| aaii_z | AAII Bull-Bear Spread | ewma_z | Weekly | AAII | +0.05 |
| modern_ted | Modern TED (T-bill − SOFR) | ewma_z | Daily | custom_series | +0.75 |
| fci_z | Bloomberg US FCI | ewma_z | Daily | H5 | +0.59 |
| fci_ez | Bloomberg EZ FCI | ewma_z | Daily | H7 | +0.36 |
| fci_uk | Bloomberg UK FCI | ewma_z | Daily | H7 | +0.39 |
| nfci | Chicago Fed NFCI | ewma_z | Daily | H7 | -0.69 |
| dxy_z | USD DXY Index | ewma_z | Daily | H5 | -0.42 |
| hy_stress | HY Spread Stress Proxy | ewma_z | Daily | custom_series | +0.04 |
| hy_safe_haven | HY Safe Haven Proxy | ewma_z | Daily | custom_series | +0.04 |
| em_stress | EM Spread Stress Proxy | ewma_z | Daily | custom_series | -0.48 |
| embi | EMBI Proxy (EM OAS chg) | ewma_z | Daily | custom_series | -0.48 |

**Data window**: Most from 2013-02-01. modern_ted gated at 2018-04-01 (~2,086 obs). AAII weekly from 1987 (normalized from 2013, ~692 usable obs post-gate). fci_ez/fci_uk/nfci from 2013-02-01 (~3,466 obs).

---

### 6.4 Valuation (V) — 28 signals

| series_id | Signal Name | Transform | Frequency | Source | Current Z |
|---|---|---|---|---|---|
| oas_bbb | BBB OAS Level (pctile) | pctile | Daily | OAS | -1.93 |
| oas_hy | HY OAS Level (pctile) | pctile | Daily | OAS | -1.43 |
| oas_em | EM Corp OAS Level (pctile) | pctile | Daily | OAS | -1.95 |
| oas_latam | LatAm Corp OAS (pctile) | pctile | Daily | OAS | -1.90 |
| gt02 | US 2Y Yield Level (pctile) | pctile | Daily | H5 | +1.12 |
| gt10 | US 10Y Yield Level (pctile) | pctile | Daily | H5 | +1.91 |
| tips_5y | TIPS 5Y Real Yield (pctile) | pctile | Daily | H5 | +1.09 |
| tips_10y | TIPS 10Y Real Yield (pctile) | pctile | Daily | H5 | +1.75 |
| term_spread | Term Spread 10Y-2Y | ewma_z | Daily | custom_series | +0.56 |
| hy_ig_ratio | HY/IG Spread Ratio | ewma_z | Daily | custom_series | +1.55 |
| erp_us | US Equity Risk Premium | rolling_z | Daily | custom_series | -1.85 |
| erp_em | EM Equity Risk Premium | rolling_z | Daily | custom_series | -2.10 |
| erp_acwi | ACWI ERP | rolling_z | Daily | custom_series | -2.10 |
| erp_em_xchina | EM ex-China ERP | rolling_z | Daily | custom_series | -1.96 |
| erp_china | China ERP | rolling_z | Daily | custom_series | -1.82 |
| pe_score_sp500 | S&P 500 PE Score | ewma_z | Daily | custom_series | +0.85 |
| pe_score_eafe | EAFE PE Score | ewma_z | Daily | custom_series | -0.25 |
| pe_score_em | MSCI EM PE Score | ewma_z | Daily | custom_series | +1.44 |
| pe_score_emx | EM ex-China PE Score | ewma_z | Daily | custom_series | +1.38 |
| pe_score_china | China PE Score | ewma_z | Daily | custom_series | +0.46 |
| pe_score_gro | US Growth PE Score | ewma_z | Daily | custom_series | +1.06 |
| pe_score_val | US Value PE Score | ewma_z | Daily | custom_series | +0.20 |
| rel_pe_gro_val | Growth vs Value Rel PE | ewma_z | Daily | custom_series | +0.78 |
| rel_pe_val_gro | Value vs Growth Rel PE | ewma_z | Daily | custom_series | -0.78 |
| rel_pe_dm_us | DM vs US Rel PE | ewma_z | Daily | custom_series | -0.62 |
| rel_pe_em_us | EM vs US Rel PE | ewma_z | Daily | custom_series | +0.86 |
| rel_pe_us_em | US vs EM Rel PE | ewma_z | Daily | custom_series | -0.86 |
| rel_pe_china_us | China vs US Rel PE | ewma_z | Daily | custom_series | -0.06 |

**Data window**: OAS levels from 1999-12-31 raw (~6,972 obs, normalized from 2013-02-01). PE scores/ERP/Rel PE from ~2013-02-01 (~3,513 obs). pe_score_emx from ~2017-07-06 (~2,250 obs).

---

## 7. MAX Timeframe — Full History Policy

**Current issue**: `chartbook_data.py` caps all exports at `MAX_ROWS = 252 * 5` (~5 years = 1,260 obs). When the user selects MAX in the dashboard, they only see 5 years even if 15 years of data are available.

**Required fix**: Remove the `MAX_ROWS` cap from `chartbook_data.py`. Each series should export its full history (from `MIN_DATE_FOR_SIGNALS = 2013-02-01`, or the series' own `reliable_from` date, whichever is later). The timeframe pills (3M/1Y/3Y/MAX) then slice the already-loaded data client-side.

**Impact on dashboard file size**: Full-history export will increase `chartbook_data.json` from ~4.7 MB to an estimated ~15–20 MB. This is acceptable for a local institutional dashboard.

---

## 8. Current Chart Inventory (Chartbook Sections)

As exported by `chartbook_data.py`:

| Section | Group | Series exported |
|---|---|---|
| Fundamentals | pmi | ism_mfg, ism_svc, ez_mfg, ez_svc, china_mfg, china_svc, japan_mfg, uk_mfg, global_mfg |
| Fundamentals | cesi | cesi_us, cesi_ez, cesi_em, cesi_china, cesi_japan, cesi_global, cesi_uk |
| Fundamentals | gdp_revision | us, ez, china |
| Fundamentals | earnings | eps_fwd_us, eps_fwd_em, eps_fwd_eafe, eps_fwd_china, eps_fwd_japan, eps_fwd_world |
| Fundamentals | inflation | breakeven_5y, breakeven_10y, cpi_us |
| Fundamentals | fundamentals_heatmap | PMI monthly matrix (15 rows × months since Jan 2023) |
| Momentum | equity | per-AC: price_pct, ret_1m, ret_3m, ret_6m, ret_12_1m, ma_dist, rsi |
| Momentum | fi | per-FI index: price_pct, ret_1m, ret_3m, ret_12_1m, ma_dist |
| Momentum | spreads | oas_bbb, oas_hy, oas_em + momentum |
| Sentiment | volatility | vix, move, vstoxx, skew, pcr |
| Sentiment | funding | modern_ted, nfci, fci_z |
| Sentiment | positioning | aaii, dxy |
| Valuation | pe_absolute | pe_sp500, pe_eafe, pe_em, pe_china, pe_gro, pe_val |
| Valuation | pe_relative | rel_pe_gro_val, rel_pe_dm_us, rel_pe_em_us |
| Valuation | erp | erp_us, erp_em, erp_acwi |
| Valuation | oas | oas_bbb, oas_hy, oas_em, oas_latam + levels |
| Valuation | yields | gt02, gt10, tips_5y, tips_10y, term_spread |

---

## 9. Implementation Roadmap

| Priority | Task | Effort |
|---|---|---|
| P0 | Fix MAX timeframe — remove `MAX_ROWS` cap in `chartbook_data.py` | Low |
| P0 | Make all charts comply with design templates (see Section 2) | High |
| P1 | Create `config/chart_registry.yml` as single source of truth | Medium |
| P1 | Refactor `generate_dashboard.py` to read registry and apply templates | High |
| P2 | Add missing series to chartbook export (breakeven_1y, gdpnow, real_ff, ism_no_inv) | Low |
| P2 | Add fci_ez, fci_uk, nfci, skew_z, pcr to Sentiment section | Low |

---

## 10. Notes on Inactive / Candidate Signals

The DataSeries sheet contains 77 additional series rows without `transform_code` — these are **documented but not yet wired** into the signal engine. They include: Shiller CAPE, COT positioning, credit default swaps, sector PE ratios, and others. These are candidates for future signals. See `docs/signal_improvements.md` for rationale on exclusions.

---
*Generated: 2026-05-20 | Maintained in: `docs/chart_management_proposal.md`*
