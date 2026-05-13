# TAA System — Data Quality & Handling Reference

This document is the canonical reference for all data quality rules, known gaps,
and handling conventions. Consult it before interpreting any backtest result or
signal history prior to 2016.

---

## 1. Signal Reliability Floor

### Why signals before 2013 are unreliable

All EWMA z-scores use `EWMA_SPAN = 756 trading days` (~3 years).
Data starts 2010-12-31. The EWMA needs a full span before its mean and standard
deviation stabilize. Signals before 2013-02-01 are excluded as a safety floor.

**Global floor:** `MIN_DATE_FOR_SIGNALS = 2013-02-01` (enforced in `signal_engine.py`)

### Per-signal reliable_from

Each signal has a different effective start date based on:

```
reliable_from(series_id) =
    first_valid_date(series) + warm_up_period(transform_code)

Warm-up periods by transform:
  ewma_z    → EWMA_SPAN = 756 days
  rolling_z → window size (per DataSeries row)
  pctile    → window size (per DataSeries row)
  mom_z     → pct_change_window + EWMA_SPAN (~777 days for 21d pct + 756 ewma)
  price_mom → ~263 days (max of 12M horizon + skip month)
  inv_mom_z → diff_window + EWMA_SPAN
```

**Composite reliable_from per AC** = max(pillar reliable_from) across all 4 pillars.
This is exported as an informational column in `taa_scorecard.csv`.

### Key dates to know

| Signal | First valid date | reliable_from | Notes |
|---|---|---|---|
| OAS series | 1999-12-31 | 2003-01 (pctile 1260d) | Longest history in system |
| AAII | 1987-07-24 | 1990-07 (ewma span) | 36-year sentiment history |
| VIX, MOVE | 2010-12-31 | 2013-10 | ewma_z(756) |
| PMI US | 2010-12-31 | 2013-10 | ewma_z(756) |
| modern_ted | **2018-04-01** | **2020-12** | SOFR inception; gated in build_custom_series.py |
| pmi_china | 2023-04 | 2026-03 | Short history — EM F pillar limited |
| gdp_forecast_us_27 | 2025-01 | 2026-01 | Bloomberg next-year series only from 2025 |
| PCR (CBOE equity put/call) | 2010-12-31 | 2013-10 | ewma_z(756); now wired in S pillar |

---

## 2. Input Sheet Summary

| Sheet | Rows | Period | Frequency | NaN% | Critical Notes |
|---|---|---|---|---|---|
| OAS | ~6,937 | 1999–2026 | Daily+weekends | 0% | ~17 days behind H5; update weekly |
| H4 (PE/EY/TR) | 3,991 | 2010–2026 | Business days | 8.1% | msci_em_xchina 41% NaN (2010–2015 gap) |
| H5 (MKT) | 4,044 | 2010–2026 | Business days | 6.6% | SOFR 47% NaN (pre-2018) |
| H6 (Sectors) | 3,991 | 2010–2026 | Business days | 2.2% | sp500_re 37% NaN (inception ~2016) |
| H1 (PMI/CESI/GDP) | 4,003 | 2010–2026 | Mixed | 54.3% | GDP daily; PMI/CESI monthly |
| H2 (Regional) | 3,960 | 2010–2026 | Mixed | ~50% | Japan/China GDP; monthly PMI |
| H3 (EPS) | 3,991 | 2010–2026 | Business days | 0% | Clean; daily forward EPS |
| H7 (New macro) | 3,991 | 2010–2026 | Business days | 1.5% | gdpnow, NFCI, FCI_EZ, breakeven_1y |
| AAII | 10,105 | 1987–2026 | Weekly→daily | 0.1% | Resampled to business days; ffill 7d |

---

## 3. Forward-Fill Rules

Synthetic forward-filling is applied to prevent NaN propagation on non-trading days.
**Different limits apply by series type:**

| Series Type | Limit | Rationale |
|---|---|---|
| Daily prices (H4, H5, OAS) | 5 days (`MAX_FFILL_DAYS`) | Covers weekends + 1 holiday |
| Monthly PMI/CESI (H1) | 31 days (`MAX_FFILL_MONTHLY`) | Monthly = 1 month max synthetic fill |
| Daily GDP forecasts (H1/H2) | 31 days | Daily updates; 31d covers gaps |
| AAII (weekly) | 7 days | Spread to business days |
| SOFR / modern_ted | Gated at 2018-04-01 | Inception date |
| PCE YoY (monthly, H5) | 5 days | Only 5 days; monthly gaps → NaN |

**Code location:** `src/data_loader.py` `load_f1()` uses `MAX_FFILL_MONTHLY`.

---

## 4. Known Data Gaps by Series

### Critical gaps (affect signal quality)

**modern_ted (SOFR-based TED spread)**
- Available: 2018-04-01 onwards only
- Before 2018: entirely NaN — gated in `build_custom_series.py`
- EWMA reliable from: ~2020-12-01
- In S pillar: contributes zero for 2010–2020 backtests

**gdp_forecast_us_27 / gdp_forecast_em_27 (next-year Bloomberg consensus)**
- Available: ~2025 onwards (Bloomberg started publishing continuoously)
- Before 2025: NaN — blended GDP falls back to current-year forecast only
- Impact: `gdp_us` custom series is less forward-looking before 2025

**pmi_china, pmi_ez (composite)**
- Available: ~2023-04 onwards (only ~2 years of data as of 2026)
- Short history → `reliable_from(pmi_china, ewma_z(756))` ≈ 2026-03
- EM Equity F pillar is unreliable before 2026 due to this signal

### Medium gaps (known, expected)

| Series | NaN% | Period | Cause |
|---|---|---|---|
| msci_em_xchina (PE/EY) | 41% | 2010–2015 | Data provider gap |
| sp500_quality (PE/EY) | 32% | 2010–2016 | Index inception ~2016 |
| sp500_re (PE/EY) | 37% | 2010–2016 | REIT sub-index inception |
| sofr | 47% | 2010–2018 | Inception April 2018 |
| pce_yoy | 73% | Always | Monthly Federal Reserve release |

---

## 5. GDP Series Naming Convention

All Bloomberg GDP forecast series use the **year suffix** convention:

| Internal name | Bloomberg ticker | Description |
|---|---|---|
| `gdp_forecast_us_26` | ECGDUS 26 Index | US current-year GDP consensus (daily) |
| `gdp_forecast_us_27` | ECGDUS 27 Index | US next-year GDP consensus (daily, from 2025) |
| `gdp_forecast_em_26` | ECGDM1 26 Index | EM current-year |
| `gdp_forecast_em_27` | ECGDM1 27 Index | EM next-year |
| `gdp_forecast_dm_26` | ECGDD1 26 Index | DM current-year |
| `gdp_forecast_dm_27` | ECGDD1 27 Index | DM next-year |
| `gdp_forecast_eu_26` | ECGDEU 26 Index | Eurozone current-year |
| `gdp_forecast_eu_27` | ECGDEU 27 Index | Eurozone next-year |
| `gdp_forecast_jp_26` | ECGDJP 26 Index | Japan current-year |
| `gdp_forecast_jp_27` | ECGDJP 27 Index | Japan next-year |
| `gdp_forecast_cn_26` | ECGDCN 26 Index | China current-year |
| `gdp_forecast_cn_27` | ECGDCN 27 Index | China next-year |
| `gdp_forecast_latam_26` | ECGDR4 26 Index | LatAm current-year |
| `gdp_forecast_latam_27` | ECGDR4 27 Index | LatAm next-year |

**Blended GDP formula** (in `build_custom_series.py`):
```
gdp_blended = (month/12) × gdp_cur + (1 - month/12) × gdp_nxt
```
- January: 8.3% current / 91.7% next-year (next year is most forward-looking)
- December: 91.7% current / 8.3% next-year (current year almost locked in)

---

## 6. Normalization Conventions

| Transform | Description | Window | Output range |
|---|---|---|---|
| `ewma_z` | Exponentially Weighted Moving z-score | `EWMA_SPAN = 756 days` | Clipped ±3σ |
| `rolling_z` | Simple rolling z-score | Per DataSeries row | Clipped ±3σ |
| `pctile` | Percentile rank → rescaled `(p−0.5)×4` | Per DataSeries row | ≈ −2 to +2 |
| `mom_z` | `pct_change(window)` → ewma_z | Per row + EWMA_SPAN | Clipped ±3σ |
| `price_mom` | Composite: 12-1M (40%), 3M (25%), MA (25%), RSI (10%) | See MomentumConfig | Clipped ±3σ |
| `inv_mom_z` | `-ewma_z(diff(window))` — falling = positive | Per row + EWMA_SPAN | Clipped ±3σ |

**Outlier handling:**
- Return outliers > 5σ are set to NaN before momentum computation (prevents flash-crash contamination)
- All z-scores clipped at ±3.0 (`OUTLIER_CLIP_Z`) before pillar aggregation

---

## 7. Portfolio Constraints

### No short positions
All portfolios have `force_zero_sum = True`. This ensures:
1. Sum of tilts = 0% (portfolio stays 100% invested, no leverage)
2. Weights clipped at 0% lower bound (no short positions, Solvency II compliant)

If the TAA model produces, e.g., a −4% tilt on an AC with only 3% SAA weight,
the weight would go to −1%. The system clips this to 0% and adjusts the tilt.

### TE budget and tilt sizing
```
te_scale = portfolio.te_budget_bps / 100
max_tilt = config_default_max_tilt × te_scale
tilt     = signal_fraction × conviction_mult × max_tilt
```

| Portfolio | TE budget | Tilt scale vs reference (100bps) |
|---|---|---|
| IGCON_USD (Conservative) | 50 bps | 0.5× |
| IGMOD_USD (Moderate) | 75 bps | 0.75× |
| IGDIN_USD (Dynamic) | 100 bps | 1.0× |
| IGEQUS_USD (US Equity) | 125 bps | 1.25× |

---

## 8. Cross-Sheet Staleness

OAS sheet typically lags H5 by ~17 business days. A staleness warning is shown
in `main.py` output if OAS is > 7 days behind H5:

```
WARNING: OAS data is 17 days behind H5 (2026-03-31 vs 2026-04-17).
Credit signals (oas_bbb, oas_em, hy_stress) may be stale.
```

**Process fix:** Update OAS source weekly, aligned with H5 refresh cycle.

---

## 9. Holiday / Month-End Z-Score Spikes

Price momentum signals (`price_mom` using `pct_change(21)`) can spike ±1.5–2.9 z-units
on known calendar events: Dec 29–Jan 2, last 2 trading days of each quarter.

**Cause:** Year-end rebalancing flows inflate 1-month returns mechanically.

**Handling:**
- The system exports both `Z_composite_raw` (unsmoothed) and `Z_composite_smooth`
  (10-day rolling median, if `SMOOTH_COMPOSITE = True` in `config.py`)
- Default: `SMOOTH_COMPOSITE = False` — raw z-scores
- Backtests: exclude Dec 29–Jan 2 and month-end last 2 trading days from performance attribution

---

## 10. Custom Series Quality

`data/custom_series.xlsx` contains 41 derived series (never edit manually).
Regenerate with `python src/build_custom_series.py`.

| Group | Series | Formula |
|---|---|---|
| PMI composites | pmi_us, pmi_ez, pmi_china | (mfg + svcs) / 2 |
| GDP blends | gdp_us/dm/em/eu/jp/cn | w_cur×26 + (1−w)×27 |
| Rate environment | modern_ted (gated 2018-04), real_ff, term_spread | tbill−SOFR; FDTR−PCE; 10Y−2Y |
| ERP | erp_us/acwi/em/em_xchina/china | EY% − TIPS_10Y% |
| PE scores | pe_score_* (7 series) | pe_score() from signals.py |
| Relative PE | rel_pe_* (6 series) | log(PE_b / PE_a) |
| Stress proxies | hy_stress, em_stress, hy_safe_haven, embi | OAS.diff(21) |
| OAS ratio | hy_ig_ratio | OAS_HY / OAS_BBB |
| CDX momentum | cdx_ig_mom, cdx_hy_mom | signals.py composite functions |
| EPS revision | eps_rev_us/em/eafe/china | 0.4×pct(3M) + 0.6×pct(6M) |

---

## 11. Data Quality Scorecard

| Issue | Severity | Status | Fix Applied |
|---|---|---|---|
| EWMA warm-up 2010–2013 | HIGH | Fixed | MIN_DATE_FOR_SIGNALS = 2013-02-01 |
| SOFR gap 2010–2018 (modern_ted) | HIGH | Fixed | Gated to 2018-04-01 |
| GDP 27-series missing pre-2025 | MEDIUM | Documented | Falls back to current-year |
| F1 ffill too long (125 days) | MEDIUM | Fixed | Reduced to MAX_FFILL_MONTHLY = 31 |
| OAS lags H5 by ~17 days | MEDIUM | Warning added | Staleness warning in main.py |
| PE/YIELDS missing 32–41% (new indices) | MEDIUM | Documented | Expected inception gaps |
| Holiday z-score spikes | MEDIUM | Documented | SMOOTH_COMPOSITE toggle available |
| PCR had no data wired | LOW | Fixed | Added to H5 → DataSeries → SignalMapping |
| em_xchina/china_equity orphaned code | LOW | Fixed | Dead branches removed from pillars.py + scoring.py |
| Same-minute run collision | LOW | Fixed | RUN timestamp now includes seconds (%S) |
| GDP columns wrong in chartbook_data.py | LOW | Fixed | Updated to gdp_forecast_*_26/27 naming |
| Breakeven 5Y reading from wrong sheet | LOW | Fixed | Changed from f3 (H3) to mkt (H5) |
| TED spread reading defunct column | LOW | Fixed | Changed from mkt["ted"] to tsy["modern_ted"] |
| OAS spread charts empty in dashboard | LOW | Fixed | spreadMomChart reads (m1\|\|m3)?.dates structure |

## 12. GDP Series Naming Convention (updated May 2026)

Bloomberg publishes daily consensus GDP forecasts. Columns renamed to use year suffix:

| Old name | New name | Ticker |
|---|---|---|
| gdp_us_cur | gdp_forecast_us_26 | ECGDUS 26 Index |
| gdp_us_nxt | gdp_forecast_us_27 | ECGDUS 27 Index |
| gdp_em_cur | gdp_forecast_em_26 | ECGDM1 26 Index |
| gdp_em_nxt | gdp_forecast_em_27 | ECGDM1 27 Index |
| gdp_dm_cur | gdp_forecast_dm_26 | ECGDD1 26 Index |
| gdp_dm_nxt | gdp_forecast_dm_27 | ECGDD1 27 Index |
| gdp_eu_cur | gdp_forecast_eu_26 | ECGDEU 26 Index |
| gdp_eu_nxt | gdp_forecast_eu_27 | ECGDEU 27 Index |
| gdp_japan_cur | gdp_forecast_jp_26 | ECGDJP 26 Index |
| gdp_japan_nxt | gdp_forecast_jp_27 | ECGDJP 27 Index |
| gdp_china_cur | gdp_forecast_cn_26 | ECGDCN 26 Index |
| gdp_china_nxt | gdp_forecast_cn_27 | ECGDCN 27 Index |
| gdp_latam_cur | gdp_forecast_latam_26 | ECGDR4 26 Index |
| gdp_latam_nxt | gdp_forecast_latam_27 | ECGDR4 27 Index |

**Update all references** in `src/config.py` (SHEET_F1_COLS, SHEET_F2_COLS) and `src/build_custom_series.py` when adding new GDP series.
