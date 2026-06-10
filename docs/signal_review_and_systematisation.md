# TAA Signal Review & Systematisation Analysis
## Rimac Group — TAA Signal System Audit

**Version 1.0 · June 2026**  
**Scope:** All signal series, transform logic, pillar wiring, and code architecture  
**Output type:** Analysis + Actionable Recommendations + Standard Operating Procedure  

---

## Summary of Findings

| Category | Issues Found | Critical | High | Medium |
|---|---|---|---|---|
| Structural / Architecture | 3 | 1 | 2 | 0 |
| Signal Data Quality | 7 | 2 | 3 | 2 |
| TAA Methodology | 7 | 2 | 3 | 2 |
| Systematisation Gaps | 4 | 0 | 2 | 2 |
| **Total** | **21** | **5** | **10** | **6** |

**Bottom line:** The production signal engine (`SignalEngine` + `build_all_pillars()`) is sound in its architecture, but it carries a large body of dead code from a previous pipeline iteration, two methodology inconsistencies that materially affect signal direction (LT Treasuries and Money Market momentum proxy mismatch), and a process gap that makes every signal update a multi-file manual operation with no automated validation.

---

## Table of Contents

1. [Part I — Structural Inconsistencies](#part-i--structural-inconsistencies)
2. [Part II — Signal Data Quality Issues](#part-ii--signal-data-quality-issues)
3. [Part III — TAA Methodology Inconsistencies](#part-iii--taa-methodology-inconsistencies)
4. [Part IV — Systematisation Gaps](#part-iv--systematisation-gaps)
5. [Priority Matrix & Action Plan](#priority-matrix--action-plan)
6. [Standard Operating Procedure — Signal Updates](#standard-operating-procedure--signal-updates)

---

## Part I — Structural Inconsistencies

### I-1. ⚠️ CRITICAL — Dual Pipeline: Dead Code vs Production

**Files affected:** `src/main.py`, `src/pillars.py`

**What exists:**

The system has two parallel, independent signal pipelines:

| | Pipeline A (Production) | Pipeline B (Dead Code) |
|---|---|---|
| **Signal source** | `SignalEngine.load_all()` reads DataSeries from `taa_config.xlsx` | `build_bloomberg_series()` in `main.py` hard-codes signal construction from loaded DataFrames |
| **Pillar builder** | `build_all_pillars()` reads weights from `SignalMapping` in `taa_config.xlsx` | `pillar_fundamentals()`, `pillar_momentum()`, `pillar_sentiment()`, `pillar_valuation()` in `pillars.py` with hardcoded weights |
| **Called in production?** | ✅ Yes — the only path used in `run_pipeline()` | ❌ No — `build_bloomberg_series()` is defined but never called. All four `pillar_*()` functions are imported but never called in `run_pipeline()`. |

**Evidence:** In `main.py:run_pipeline()`:
```python
# What actually runs:
engine  = SignalEngine()
signals = engine.load_all(verbose=verbose)
proxies = build_proxy_ext(data, verbose=verbose)
# ... merge ...
pillar_scores = {ac: build_all_pillars(ac, signals, signal_mapping) for ac in ASSET_CLASSES}
```

`build_bloomberg_series()` appears in the file but is never called anywhere. It returns a dict that is never used.

**Why this matters:**
- Maintenance confusion: `pillars.py` contains hardcoded signal weights that appear authoritative but are completely ignored. A developer debugging a signal issue will find two sets of weights and not know which one applies.
- Signal divergence: the hardcoded pillar weights in `pillars.py` differ from `SignalMapping` in several cases (e.g., `lt_em_fi` F pillar: `pillars.py` has `pmi_china 0.30` while `SignalMapping` may differ).
- The GDP column naming in `build_bloomberg_series()` is stale — it uses `"gdp_us_cur"/"gdp_us_nxt"` while the actual loaded columns are `"gdp_forecast_us_26"/"gdp_forecast_us_27"`. If anyone ever re-activated this function, it would silently produce empty GDP signals.

**Recommendation:**
1. Add a clear `# ─── DEAD CODE — scheduled for removal ───` banner at the top of `build_bloomberg_series()` in `main.py`
2. Add the same banner to all four legacy `pillar_*()` functions in `pillars.py` (keeping `build_all_pillars()` which is production)
3. Schedule removal in the next maintenance sprint (low risk — they are never called)
4. The pillar functions in `pillars.py` can serve as documentation of the design intent if retained as comments, but should not be callable code that diverges from `SignalMapping`

---

### I-2. 🔴 HIGH — `inv_mom_z` Deprecated but Active in Production

**File:** `src/signal_engine.py`, `config/taa_config.xlsx` (DataSeries)

**What happens:** `signal_engine.py` marks `inv_mom_z` as deprecated and emits a `DeprecationWarning` at runtime. However, several active production signals still use this transform:

From CLAUDE.md signal universe:
- `oas_bbb_mom`, `oas_hy_mom`, `oas_em_mom` — spread momentum signals (inv_mom_z)
- `gt02_mom`, `gt10_mom` — yield momentum signals (inv_mom_z)

Every pipeline run is emitting DeprecationWarnings for 5+ signals. This clutters output and will eventually cause confusion about which signals are actually broken vs. which are just using the deprecated transform.

**The migration path is zero-risk:** `inv_mom_z` computes `-ewma_zscore(diff(window))`. The mathematically equivalent replacement is:
1. Change `transform_code` from `inv_mom_z` → `diff_z` in DataSeries
2. Change `sign` from `+1` → `-1` in SignalMapping for the affected rows (or keep `+1` and add negation in `diff_z` — but the correct design is: raw direction in transform, economic direction in SignalMapping sign)

**Recommendation:** Migrate all 5+ `inv_mom_z` signals to `diff_z` + `sign=-1` in `taa_config.xlsx`. This is a pure config change in Excel — no Python code changes required.

---

### I-3. 🔴 HIGH — `diff_z` Transform Exists in Code but Undocumented

**File:** `src/signal_engine.py`, `CLAUDE.md`

**What exists:** `signal_engine.py` implements a `diff_z` transform:
```python
elif tc == "diff_z":
    # Direction-neutral: ewma_z(diff(window))
    diff = s.diff(window)
    return ewma_zscore(diff, span=EWMA_SPAN).rename(series_id)
```

**Not documented in:** `CLAUDE.md` (which lists only `ewma_z | rolling_z | pctile | mom_z | price_mom | inv_mom_z`), `docs/TAA_System_Guide.md`, `docs/data_quality.md`.

**Why this matters:** Anyone adding a new spread/yield momentum signal today would look at `CLAUDE.md`, not find `diff_z`, and use `inv_mom_z` instead — perpetuating the deprecated transform.

**Recommendation:** Update `CLAUDE.md` transform codes table to include `diff_z` and mark `inv_mom_z` as `DEPRECATED — use diff_z + sign=-1`.

---

## Part II — Signal Data Quality Issues

### II-1. ⚠️ CRITICAL — CDX Momentum Double Normalisation

**Files:** `src/build_custom_series.py`, `config/taa_config.xlsx` (DataSeries)

**What happens:**

`build_custom_series.py` calls `cdx_ig_momentum()` and `cdx_hy_momentum()` from `signals.py`. These functions already call `ewma_zscore()` internally:

```python
# In signals.py:
def cdx_ig_momentum(cdx_ig_spread):
    m1 = spread_momentum(cdx_ig_spread, 21, invert=True)  # calls ewma_zscore internally
    m3 = spread_momentum(cdx_ig_spread, 63, invert=True)  # calls ewma_zscore internally
    return (0.4 * m1 + 0.6 * m3).rename("cdx_ig_mom")   # already z-scored

# In build_custom_series.py:
series["cdx_ig_mom"] = cdx_ig_momentum(cdx_ig_spread)   # stored as z-score

# Then in SignalEngine:
# DataSeries row has transform_code = "ewma_z"
# → ewma_zscore(already_z_scored_series)  ← DOUBLE NORMALISATION
```

`ewma_zscore(z_score_series)` is not an identity operation — it computes the EWMA mean and std of the z-score series, then re-z-scores it. The result is a z-score of z-scores, which compresses the range and distorts the signal's temporal dynamics.

**Magnitude:** The distortion is approximately monotonic (it won't flip signs), but it will compress peaks and troughs and slow the signal's responsiveness. For momentum signals where the recency of tightening/widening matters, this is materially wrong.

**Correct design:**

```python
# Option A (preferred): Store raw composite diff (not z-score) in custom_series.xlsx
# build_custom_series.py:
def _cdx_ig_raw(spread):
    m1 = spread.diff(21)  # raw 1M change in bps
    m3 = spread.diff(63)  # raw 3M change in bps
    return (0.4 * m1 + 0.6 * m3)  # stored as raw diff; SignalEngine applies diff_z or ewma_z

# Option B: Store final z-score but set transform_code = "identity" (pass-through)
# Requires adding an identity transform to signal_engine.py
```

**Recommendation:** Implement Option A. Store raw diffs in `custom_series.xlsx` and let `SignalEngine` normalise. Change transform for `cdx_ig_mom` and `cdx_hy_mom` to `diff_z` (for CDX IG spread: `diff_z` + `sign=-1`) or `ewma_z` (for CDX HY price return: `ewma_z` on raw pct_change).

---

### II-2. 🔴 HIGH — Identical Custom Series With Different Names

**File:** `src/build_custom_series.py`

**What exists:**

```python
series["hy_stress"]     = oas_hy.diff(21).dropna()
series["hy_safe_haven"] = oas_hy.diff(21).dropna()  # identical computation

series["em_stress"] = oas_em.diff(21).dropna()
series["embi"]      = oas_em.diff(21).dropna()      # identical computation
```

Two pairs of series are **byte-for-byte identical**. The intent documented in CLAUDE.md is correct in principle — the sign differentiation happens in SignalMapping:
- `hy_stress` → `sign=-1` (spread widening = bearish for credit/equity)
- `hy_safe_haven` → `sign=+1` (spread widening = demand for safe assets = bullish for UST)

**Why this is a maintenance problem:**
1. `custom_series.xlsx` stores the same data twice, bloating the file
2. Future maintainers see two columns and may assume they're different series, spending time looking for the difference
3. If the 21-day lookback ever needs changing for one use case but not the other, the coupling is hidden

**Recommendation:** Keep a single series `oas_hy_stress_raw` and `oas_em_stress_raw`. In SignalMapping, wire each with the appropriate `sign` for each AC and pillar. Add a comment in `build_custom_series.py` and the DataSeries description explaining that sign differentiation happens in SignalMapping. This reduces duplication from 4 series to 2.

---

### II-3. 🔴 HIGH — `real_ff` ffill Uses Hardcoded 35 vs Config `MAX_FFILL_MONTHLY=31`

**Files:** `src/build_custom_series.py`, `src/config.py`

**What exists:**

```python
# build_custom_series.py
pce = pce_yoy.reindex(idx).ffill(limit=35)   # hardcoded

# config.py
MAX_FFILL_MONTHLY = 31  # documented as "1 month max" for monthly series
```

PCE YoY is a monthly series that gets forward-filled. The config explicitly defines `MAX_FFILL_MONTHLY=31` as the standard limit for monthly series. `real_ff` bypasses this constant with a hardcoded `35`.

**Recommendation:** Replace `limit=35` with `limit=MAX_FFILL_MONTHLY` in `build_custom_series.py`. Ensure the import is present. One-line fix.

---

### II-4. 🟡 MEDIUM — VIX Non-Linear Contrarian Logic Lost in SignalEngine Pipeline

**Files:** `src/signal_engine.py`, `src/signals.py`

**Background:** The correct treatment of VIX as a contrarian equity sentiment signal is non-linear. The function `vix_score()` in `signals.py` implements this correctly with discrete thresholds:
- VIX > 90th pctile → `+2.0` (extreme fear = contrarian buy)
- VIX > 75th pctile → `+1.0`
- VIX > 50th pctile → `0.0`
- VIX < 25th pctile → `−1.5` (complacency = warning)

**What SignalEngine does instead:** If VIX (`vix`) is in DataSeries with `transform_code = "ewma_z"`, the signal receives a linear EWMA z-score. High VIX → high positive z → bullish. The *direction* is correctly contrarian (if VIX is in SignalMapping with `sign=+1`), but the *shape* is linear rather than thresholded.

**Impact:** The non-linear contrarian effect (treating extreme fear readings as qualitatively different from moderate fear) is lost. In the 2020 COVID crash (VIX > 80) and 2022 spike (VIX ~35), the linear EWMA produces a moderate positive signal rather than the intended strong contrarian buy.

**Also affects:** PCR (Put/Call Ratio) — has the same issue. High PCR = extreme put buying = contrarian buy signal. Linear EWMA z is directionally correct but misses the non-linear threshold behavior.

**Recommendation:** Add a `contrarian_pctile` transform to `signal_engine.py` that implements the non-linear scoring currently in `vix_score()`. Apply it to `vix` and `pcr` in DataSeries. This aligns the production pipeline with the stated design intent.

---

### II-5. 🟡 MEDIUM — Sentiment Pillar Uses Two Different Normalisation Methods for Same Signal Type

**Files:** `src/pillars.py` (legacy), `src/signal_engine.py`

Within the legacy `pillar_sentiment()`:
- **VIX**: non-linear contrarian via `vix_score()` (percentile-based thresholds)
- **VSTOXX**: linear EWMA z-score via `ewma_zscore()`
- **MOVE**: linear EWMA z-score
- **PCR**: passed raw or as EWMA z from `ext` dict

All three (VIX, VSTOXX, PCR) are volatility/fear proxies used as contrarian indicators. They should receive consistent normalisation. Currently VIX is treated as special-case (non-linear) while VSTOXX and PCR are linear.

**Note:** Since `pillars.py` is dead code, this only matters through the SignalEngine pipeline. If SignalMapping applies `ewma_z` to all three, they're all linear. If a `contrarian_pctile` transform is added (Issue II-4), apply it consistently to `vix`, `vstoxx`, and `pcr`.

---

### II-6. 🟢 LOW — `skew_z` Status Ambiguous

**Files:** `CLAUDE.md`, `config/taa_config.xlsx` (unverifiable from code review)

**What CLAUDE.md says:** "Sentiment: `skew_z` (tail risk)" is listed in the active signal universe. `SKEW Index` is present in `SHEET5_COLS` (H5 sheet) as internal column `skew`.

**Cannot confirm from code review:** Whether `skew` has a DataSeries row with active wiring, and which AC/pillar combination it's mapped to in SignalMapping.

**Risk:** If `skew` is in the H5 sheet but not in DataSeries, it is silently excluded from the pipeline with no warning. The CLAUDE.md listing suggests it should be active.

**Recommendation:** Run `python src/main.py --verbose` and confirm `skew_z` appears in the "OK" signal load output. If it does not, add a DataSeries row and wire it in SignalMapping. Alternatively add a test assertion in `test_build_layer.py` for each signal listed in CLAUDE.md as "active."

---

### II-7. 🟢 LOW — Composite Re-Standardisation Uses 252d Fixed Window Regardless of Signal Speed

**File:** `src/signals.py`

```python
def standardise_pillar(s: pd.Series) -> pd.Series:
    return ewma_zscore(s, span=WINDOWS["medium"])  # medium = 252 days (1 year)
```

Every pillar composite — regardless of whether its constituent signals are fast (momentum, 63d EWMA) or slow (valuation, 2520d rolling) — gets re-standardised with a 1-year EWMA. This means the pillar's effective lookback for normalisation is always 1 year, creating an artificial speed homogenisation.

**Impact:** The Valuation pillar (which intentionally uses 10-year rolling windows for P/E and ERP) gets its recent deviation compressed into a 1-year z-score at the pillar level. A 10-year-cheap signal is partially masked.

**Recommendation:** Make `standardise_pillar()` accept a configurable `span` parameter, and call it with a slower window (e.g., `WINDOWS["long"] = 756d`) for the Valuation pillar. This is a minor improvement but aligns pillar normalisation with the intended signal speed per pillar.

---

## Part III — TAA Methodology Inconsistencies

### III-1. ⚠️ CRITICAL — LT Treasuries Momentum Uses EM Sovereign TR Index

**File:** `src/pillars.py` (legacy code — but `bsgv_price` is also in DataSeries/SignalMapping for production)

**What exists:**

In the legacy `pillar_momentum()` for `lt_treasuries`:
```python
signals = {
    "bsgv_mom": _fi_mom("bsgv_price"),  # 45% weight
    "gt10_mom": gt10_mom,               # 35%
    "oas_bbb_mom": oas_bbb_mom,         # 20%
}
```

`bsgv_price` = `BSGVTRUU` = **Bloomberg EM Sovereign Total Return Index**.

This is the same index used as the return proxy for `lt_em_fi` (LT EM Fixed Income), not for LT US Treasuries. Using EM Sovereign momentum to signal US Treasury momentum is **fundamentally incorrect** — EM sovereign bonds move on different drivers (USD strength, EM growth, political risk) from US Treasuries (Fed expectations, risk-off/flight-to-quality).

**Why the confusion likely arose:** `bsgv_price` was probably intended to be `bfcu_price` (Bloomberg US Corporate TR) or `lt03_price` (Bloomberg Long US Treasury TR) — the naming is close and easy to confuse.

**The correct proxy for LT Treasuries momentum:**
- Primary: `lt03_price` = LT03TRUU = Bloomberg Long US Treasury TR (already in the system)
- Secondary: `gt10_mom` (10Y Treasury yield momentum — falling yield = positive)

**Action:** Confirm what `bsgv_mom` maps to in the current SignalMapping for `lt_treasuries`. If `bsgv_price` is wired there, replace it with `lt03_price` immediately.

---

### III-2. ⚠️ CRITICAL — Money Market Momentum Uses Long-Duration Treasury TR Index

**File:** `src/pillars.py` (legacy — but verify in SignalMapping)

**What exists:**

In the legacy `pillar_momentum()` for `money_market`:
```python
signals = {
    "fi_mom": _fi_mom("lt03_price"),  # 60% weight — Bloomberg Long Treasury TR
    "gt02_mom": gt02_mom,             # 40%
}
```

`lt03_price` = LT03TRUU = **Bloomberg Long US Treasury TR** — a 10+ year duration bond index.

Money Market instruments are overnight to 1-year in duration. Using a long-duration Treasury momentum signal for money market is incorrect — the correlation between the two is low and directionally inconsistent during rate changes (when rates rise, LT Treasuries fall while money market yields rise).

**The correct proxy for Money Market momentum:**
- Primary: `gt02_mom` (2Y Treasury yield — closest to money market rates; already in system)
- Or: T-Bill rate momentum (tbill_3m from tsy sheet, `ewma_z(diff(21))`)

**Note:** Money Market is `active=False` in production (excluded from the scorecard). However, if it is re-enabled, this methodology error would propagate. Fix regardless.

---

### III-3. 🔴 HIGH — EM Equity and LT EM FI Share Identical Fundamentals Pillar

**Files:** `src/pillars.py`, `config/taa_config.xlsx` (SignalMapping)

**What exists:**

In legacy `pillar_fundamentals()`:
- `em_equity`: `pmi_china(0.30) + cesi_em(0.25) + gdp_em(0.25) + eps_em(0.20)`
- `lt_em_fi`: `pmi_china(0.30) + cesi_em(0.25) + gdp_em(0.25) + eps_em(0.20)`

Identical signals, identical weights. This is **economically unjustified** — EM equity and EM credit have distinct fundamental drivers:

| Signal | EM Equity F | LT EM FI F | Rationale |
|---|---|---|---|
| PMI China | ✅ Primary driver | ✅ | Growth = better EM earnings AND tighter spreads |
| CESI EM | ✅ | ✅ | Surprise captures data momentum |
| GDP EM | ✅ | ✅ | Both need EM growth |
| EPS EM | ✅ High weight (equity earnings) | 🟡 Lower weight (spreads care less about EPS) | EPS revision is equity-specific |
| US Real Fed Funds | 🚫 Not included | ✅ Should be included | Rate regime drives EM credit spread levels directly |
| Breakeven inflation | 🚫 Not included | 🟡 Minor (higher US inflation = Fed restrictive = EM credit headwind) | |
| CESI China specifically | 🟡 | 🚫 | EM equity more sensitive to China cycle than EM FI |

**Recommendation:** Differentiate the two:
- **EM Equity F:** Add `cesi_china` (+1, ~0.15), reduce `gdp_em` to 0.20. Add `eps_rev_em` if available (rev composite is more predictive than level EPS for equities).
- **LT EM FI F:** Reduce `eps_em` weight to 0.10 (less relevant for credit spreads). Add `real_ff` (-1, ~0.10) as a US rate environment signal (restrictive policy = EM credit headwind from duration + capital flows).

---

### III-4. 🔴 HIGH — DM Equity Momentum Lacks a Credit/Spread Dimension

**File:** `src/pillars.py`, `config/taa_config.xlsx` (SignalMapping)

**What exists:**

Legacy DM Equity M: `eafe_mom(0.65) + acwi_mom(0.35)` — purely price-based.

Compare with:
- **EM Equity M:** `em_mom(0.60) + oas_em_mom(0.40)` — includes EM credit momentum
- **US Equity M:** `price_mom(0.55) + hy_mom(0.25) + cdx_hy(0.20)` — includes HY credit conditions

DM equity is heavily weighted toward European financials and cyclicals that are sensitive to EZ credit conditions. The EZ version of credit signals exists in the system:
- `vstoxx_z` (EZ volatility — already in DM Sentiment)
- `fci_ez` (EZ Financial Conditions Index, in H7)
- OAS BBB or HY momentum as a proxy for global credit conditions

**Recommendation:** Add `oas_bbb_mom` or `cdx_ig_mom` to DM Equity M at ~15-20% weight, reducing `acwi_mom` from 0.35 to 0.15-0.20. ACWI adds noise to DM-specific signals — it blends US with DM and dilutes the regional signal.

---

### III-5. 🔴 HIGH — OAS BBB in LT Treasuries Valuation Pillar

**File:** `src/pillars.py`, `config/taa_config.xlsx` (SignalMapping)

**What exists:**

Legacy LT Treasuries V:
```python
signals = {
    "gt10":    _yl(gt10),       # 35%
    "ts":      _ts("lt_treasuries"),  # 25%
    "oas_bbb": _oas_lv(oas_bbb),     # 10%  ← credit signal in duration pillar
    "tips10":  _yl(tips10),     # 30%
}
```

**The problem:** OAS BBB is a **credit spread level** signal. For LT Treasuries, the Valuation question is "are UST yields attractive vs. history?" — this is answered by GT10, TIPS real yields, and term spread. OAS BBB is a separate dimension (credit risk premium) that belongs in the Sentiment pillar for LT Treasuries as a flight-to-quality indicator (wide spreads = demand for UST = sentiment positive), not in Valuation.

**Correct placement:** OAS BBB has no valuation interpretation for LT Treasuries. It is already captured in the Sentiment pillar via `hy_safe_haven` (OAS widening = positive for safe-haven assets). Having it in Valuation double-counts the credit stress signal.

**Recommendation:** Remove `oas_bbb` from LT Treasuries V. Redistribute weight to `gt10` (+5% → 40%) and `ts` (+5% → 30%). Final: `gt10(0.40) + tips10(0.30) + ts(0.30)`.

---

### III-6. 🟡 MEDIUM — Sign Convention Contamination in Multiple Files

**Files:** `src/build_custom_series.py`, `src/signal_engine.py`, `src/pillars.py`

The design rule states: **"Sign lives ONLY in SignalMapping."** In practice, sign inversions appear in multiple places:

| Location | Signal | Embedded sign | Correct location |
|---|---|---|---|
| `build_custom_series.py:_log_pe_ratio()` | Relative PE | `log(PE_b / PE_a)` — sign is in argument order | Should be explicit `sign=-1` in SignalMapping; formula should be symmetric `log(PE_a/PE_b)` |
| `signal_engine.py:inv_mom_z` | Spread/yield mom | `-ewma_zscore(diff(window))` | Migrate to `diff_z` + `sign=-1` in SignalMapping |
| `pillars.py:pillar_fundamentals()` | FI F pillar | `(-pmi_us)`, `(-cesi_us)` inline inversions | Sign should be in SignalMapping (dead code, but instructive of the design intent violation) |
| `pillars.py:pillar_sentiment()` | Various | `_inv(vix_eq)`, `(-dxy_s)` inline | Same — dead code |

**Why relative PE sign is particularly risky:** `_log_pe_ratio(pe_gro, pe_val)` computes `log(pe_val/pe_gro)`. This is **positive when growth is expensive** (pe_val < pe_gro → ratio < 1 → log < 0... wait, that means the result is negative when growth is cheap). Let me re-examine:

```python
# _log_pe_ratio(a, b) returns log(PE_b / PE_a)
series["rel_pe_gro_val"] = _rel_pe(pe_gro, pe_val)  # log(pe_val / pe_gro)
```
When growth is expensive (pe_gro > pe_val), pe_val/pe_gro < 1, log < 0 → negative series → after `ewma_z` applied in SignalEngine → negative z → with `sign=-1` in SignalMapping → positive contribution. This is **correct**: cheap value vs growth → positive signal for value tilts.

But the sign logic is entirely embedded in the argument order of `_log_pe_ratio` + the SignalMapping sign. This is fragile — if someone changes the argument order or the SignalMapping sign independently, the signal flips without warning.

**Recommendation:** Document the sign convention explicitly in `build_custom_series.py` comments for each relative PE series. Add a validation in `test_build_layer.py` that confirms the sign of the latest rel_pe series makes economic sense (e.g., rel_pe_gro_val should be negative when S&P Growth PE > S&P Value PE, which is current market reality).

---

### III-7. 🟡 MEDIUM — PCR Signal Is Directionally Correct but Misses Non-Linear Contrarian Shape

**File:** `config/taa_config.xlsx` (DataSeries), `src/signal_engine.py`

**What PCR measures:** CBOE Equity Put/Call Ratio. High PCR = more puts than calls = elevated hedging demand = extreme fear = contrarian **buy** signal. Historical extremes: PCR > 1.0 = crisis (COVID: 1.5-2.0+), PCR < 0.50 = complacency.

**Current treatment:** `transform_code = "ewma_z"` with `window = 756`. This produces a linear z-score where high PCR → high positive z → bullish signal. Directionally correct.

**What it misses:** The PCR's information is concentrated at the extremes. A PCR of 0.80 vs 0.90 is noise; a PCR of 1.40+ is a regime-level signal. Linear EWMA treats these identically in proportion. The proper treatment (like VIX) uses percentile thresholds:
- PCR > 90th pctile (extreme fear) → strong buy (+2)
- PCR < 25th pctile (complacency) → mild warning (-1)
- Middle range → neutral (0)

**Recommendation:** Add `contrarian_pctile` transform (see Issue II-4). Change PCR transform to `contrarian_pctile` in DataSeries.

---

## Part IV — Systematisation Gaps

### IV-1. 🔴 HIGH — Too Many Files to Update When Adding/Changing a Signal

**Current process (counted from CLAUDE.md):**

Adding a new **custom** signal requires touching:
1. `src/build_custom_series.py` — add computation
2. `config/taa_config.xlsx:DataSeries` — add series_id, type, sheet, column, transform, window
3. `config/taa_config.xlsx:SignalMapping` — add one row per (AC, pillar) combination
4. `src/config.py` (if it changes AC universe or pillar weights) — via `build_dashboard.py`
5. `CLAUDE.md` — update signal universe documentation
6. `docs/data_quality.md` — if new data quality rules apply
7. Run `build_custom_series.py`, `main.py`, `test_build_layer.py`, `chartbook_data.py`, `generate_dashboard.py`

Adding a new **original** (from input Excel) signal requires touching:
1. `config/taa_config.xlsx:DataSeries` — add row
2. `config/taa_config.xlsx:SignalMapping` — add mapping rows
3. `CLAUDE.md` — update documentation
4. Run `main.py`, `test_build_layer.py`

**The gap:** No single file or checklist governs this. The process lives in narrative in `CLAUDE.md`. Steps are easily missed. No automated check confirms that a newly added DataSeries row actually produces a signal that reaches a pillar.

**Recommendation:** Formalize as a Standard Operating Procedure (SOP) — see Section 6. Add a validation script that, given a `series_id`, confirms:
- It exists in DataSeries with a valid transform
- It appears in at least one SignalMapping row
- The SignalEngine successfully loads it (non-empty output)
- The pillar that uses it shows a different score when the signal is zeroed out (sanity check for wiring)

---

### IV-2. 🔴 HIGH — No Automated Signal Change Detection Between Runs

**Current state:** The Economic Sanity Report (`ESR_*.md`) compares signal z-scores to a previous run snapshot. However:
- The "Largest Signal Changes vs Previous Run" table was empty in the last ESR (the two runs were too close in time or the comparison logic failed)
- There is no automated alert when a signal changes by > 1 sigma between runs
- There is no attribution of scorecard movement to specific signals
- The `signal_z_snapshot.json` exists but is only compared manually

**Why this matters for systematisation:** Without automated detection, a data update that silently breaks a series (e.g., a column rename in Bloomberg export) produces a changed scorecard with no explanation of what drove the change.

**Recommendation:** Add a `compare_runs.py` script that:
1. Takes two `signal_z_snapshot.json` files (latest + previous)
2. Computes `Δz` per signal
3. Flags signals with `|Δz| > 1.0` as "large movers"
4. Computes which ACs are most affected by those signal moves
5. Outputs a one-page markdown diff (like `ESR_*.md` but signal-level)

This can be integrated into `generate_dashboard.py` or called standalone after each `main.py` run.

---

### IV-3. 🟡 MEDIUM — Health Test Does Not Validate Signal Wiring

**File:** `src/test_build_layer.py`

The 29-check health test validates:
- Correct number of active ACs (6)
- Minimum SignalMapping rows (100+)
- Config.py BUILD markers intact
- etc.

It does **not** validate:
- Every signal in SignalMapping exists in the SignalEngine output
- No signal in SignalMapping has a zero or near-zero contribution to its pillar
- Deprecated transforms are not used by active signals
- Sign convention consistency (e.g., a signal marked as FI with `sign=+1` for GDP growth, which should be `-1` for duration)

**Recommendation:** Add the following checks to the health test:
1. `CHECK_N: All SignalMapping series_id values appear in SignalEngine.load_all() output`
2. `CHECK_N: No active DataSeries row uses transform_code = "inv_mom_z" (deprecated)`
3. `CHECK_N: For each AC/pillar combination in SignalMapping, at least 2 signals are available`
4. `CHECK_N: signal_z_snapshot.json exists and has > 80 entries` (catches bulk loading failure)

---

### IV-4. 🟡 MEDIUM — CLAUDE.md Signal Universe Description Is Partially Stale

**File:** `CLAUDE.md`

Specific stale items found:

| Item | What CLAUDE.md says | Actual state |
|---|---|---|
| Transform codes | Lists `inv_mom_z` as active | Deprecated in `signal_engine.py` |
| Transform codes | Missing `diff_z` | Implemented in `signal_engine.py` |
| Signal universe size | "97 signals total" | Count not verified post-v6 changes |
| `gdpnow` H7 source | "H7, ewma_z" | Need to confirm DataSeries row exists |
| `skew_z` | Listed as active Sentiment signal | Wiring in SignalMapping unconfirmed |

**Recommendation:** After fixing the above issues, run a full `main.py --verbose` and count the actual loaded signals. Update CLAUDE.md signal count and confirm the transform table is accurate. Lock CLAUDE.md updates into the SOP for signal additions (every signal addition requires a CLAUDE.md update as part of the PR).

---

## Priority Matrix & Action Plan

### Severity Scale: Critical > High > Medium > Low

| # | Issue | Severity | Effort | File(s) to Change | Risk |
|---|---|---|---|---|---|
| I-1 | Dead code pipeline — flag for removal | Critical | 2h | `main.py`, `pillars.py` | Zero (no logic change) |
| I-2 | `inv_mom_z` migration to `diff_z` + sign | High | 1h | `taa_config.xlsx` only | Very Low |
| I-3 | `diff_z` missing from documentation | High | 30m | `CLAUDE.md` | Zero |
| II-1 | CDX double-normalisation | Critical | 3h | `build_custom_series.py`, `taa_config.xlsx` | Low |
| II-2 | Identical series with different names | High | 1h | `build_custom_series.py`, `taa_config.xlsx` | Low |
| II-3 | `real_ff` hardcoded `limit=35` | High | 5m | `build_custom_series.py` | Zero |
| II-4 | VIX/PCR non-linear contrarian lost | Medium | 4h | `signal_engine.py`, `taa_config.xlsx` | Low |
| II-5 | VIX vs VSTOXX normalisation inconsistency | Medium | 1h | `taa_config.xlsx` (transform change) | Low |
| II-6 | `skew_z` status ambiguous | Low | 30m | Verify only | Zero |
| II-7 | Pillar re-standardisation fixed at 252d | Low | 1h | `signals.py`, `pillars.py` | Low |
| III-1 | LT Treasuries M uses EM Sovereign TR | Critical | 1h | `taa_config.xlsx` SignalMapping | Medium |
| III-2 | Money Market M uses Long Treasury TR | Critical | 1h | `taa_config.xlsx` SignalMapping | Low (MM inactive) |
| III-3 | EM Equity vs LT EM FI identical F pillar | High | 2h | `taa_config.xlsx` SignalMapping | Medium |
| III-4 | DM Equity M lacks credit dimension | High | 1h | `taa_config.xlsx` SignalMapping | Medium |
| III-5 | OAS BBB in LT Treasuries V pillar | High | 30m | `taa_config.xlsx` SignalMapping | Low |
| III-6 | Sign convention contamination | Medium | 2h | `build_custom_series.py`, docs | Low |
| III-7 | PCR misses non-linear contrarian shape | Medium | Linked to II-4 | `taa_config.xlsx` | Low |
| IV-1 | No systematic signal addition process | High | 4h | New SOP + `validate_signal.py` | Zero |
| IV-2 | No automated change detection | High | 4h | New `compare_runs.py` | Zero |
| IV-3 | Health test missing signal wiring checks | Medium | 2h | `test_build_layer.py` | Zero |
| IV-4 | CLAUDE.md partially stale | Medium | 1h | `CLAUDE.md` | Zero |

### Recommended Sprint Order

**Sprint 1 — Zero-risk fixes (do immediately, 1 day of work):**
- I-1: Mark dead code with banners
- I-2: Migrate `inv_mom_z` → `diff_z` in `taa_config.xlsx`
- I-3: Update `CLAUDE.md` transforms table
- II-3: Fix `real_ff` ffill constant
- III-5: Remove `oas_bbb` from LT Treasuries V
- II-6: Verify `skew_z` wiring (inspect only)
- IV-4: Update CLAUDE.md signal count and status

**Sprint 2 — Signal quality fixes (verify against historical data first, 2 days):**
- II-1: Fix CDX double-normalisation (confirm before/after signal values)
- II-2: Consolidate identical custom series
- III-1: Fix LT Treasuries M (confirm `bsgv_price` is indeed EM Sovereign)
- III-3: Differentiate EM Equity vs LT EM FI F pillar

**Sprint 3 — Methodology improvements (require IC discussion, 3 days):**
- II-4 + III-7: Add `contrarian_pctile` transform for VIX/PCR
- III-4: Add credit dimension to DM Equity M
- III-2: Fix Money Market M (lower priority — MM is inactive)
- III-6: Document sign convention in custom series

**Sprint 4 — Systematisation infrastructure (can be parallel, 4 days):**
- IV-1: `validate_signal.py` + SOP documentation
- IV-2: `compare_runs.py` with automated run diffing
- IV-3: Extended health test with signal wiring checks

---

## Standard Operating Procedure — Signal Updates

The following SOP makes the update and implementation process systematic. It applies to:
- **Adding a new signal** (original or custom)
- **Removing a signal**
- **Changing a signal's transform, window, or sign**
- **Moving a signal between pillars**

### SOP-A: Adding a New ORIGINAL Signal (from input Excel)

A signal is "original" if it comes directly from a column in `Dashboard_TAA_Inputs.xlsx`.

**Step 1 — Confirm data availability**
```
□ Confirm the column exists in the correct Excel sheet (H1-H7, OAS, AAII)
□ Check the column has > 2000 non-null values (>8 years of daily data, or 5Y+ for monthly)
□ Record: sheet name, column name (exact Bloomberg ticker), data frequency
□ Record: first available date and confirm it's before MIN_DATE_FOR_SIGNALS (2013-02-01) + warm-up
□ Document in docs/data_quality.md: series_id, source, frequency, reliable_from date
```

**Step 2 — Choose transform**
```
□ Is the raw series mean-reverting with roughly symmetric distribution? → ewma_z
□ Is it a price/level with long-run trend (P/E, yield level, spread level)? → pctile or rolling_z
□ Is it a directional change where falling is bullish (spread, yield)?     → diff_z + sign=-1 in SignalMapping
□ Is it a % change momentum (EPS revision, GDP revision)?                  → mom_z
□ Is it a total return price index (equity/FI price)?                      → price_mom
□ Is it a contrarian fear indicator (VIX, PCR)?                            → contrarian_pctile (once added)
□ Choose window: fast (63d), medium (252d), long (756d), vlong (2520d) based on signal economics
```

**Step 3 — Add to `config/taa_config.xlsx:DataSeries`**
```
□ Add one row: series_id | series_type="original" | input_sheet | input_column | transform_code | window
□ series_id must be unique (check no existing series has the same name)
□ input_column must match EXACTLY the column name in the loaded DataFrame (after SHEET*_COLS mapping)
□ Run: python src/main.py --verbose
□ Confirm "OK  {series_id}" appears in output with expected point count
□ If EMPTY or error: check input_column spelling and sheet name
```

**Step 4 — Add to `config/taa_config.xlsx:SignalMapping`**
```
□ For each (AC, pillar) the signal applies to, add one row:
     ac_id | series_id | pillar | sign | weight_in_pillar
□ Sign convention: +1 = series positive → bullish for AC; -1 = series positive → bearish
□ Weight: expressed as fraction (0.25) or percent (25%)
□ Ensure weights per (AC, pillar) still sum to 1.0 after adding new signal
  (reduce other signal weights proportionally)
□ NEVER embed sign inversion in build_custom_series.py or signal_engine.py — sign lives here ONLY
```

**Step 5 — Validate**
```
□ python src/build_dashboard.py          # updates config.py BUILD blocks
□ python src/main.py --verbose           # confirm signal loads and reaches pillar
□ python src/test_build_layer.py         # 29/29 PASS
□ python src/validate_signal.py {series_id}  # [NEW TOOL] confirms end-to-end wiring
□ Check scorecard: does the AC's pillar z-score change in the expected direction?
□ Run src/economic_sanity.py and review the signal in the output
```

**Step 6 — Document**
```
□ Update CLAUDE.md: add series_id to the relevant pillar section of "Signal Universe"
□ Update docs/data_quality.md: add data quality entry (start date, known gaps, reliable_from)
□ If transform or sign is non-obvious: add one-line comment in DataSeries description column
```

---

### SOP-B: Adding a New CUSTOM Signal (derived series)

A signal is "custom" if it requires computation beyond loading a single column.

**Same as SOP-A, plus these additional steps:**

**Before Step 3, add computation to `build_custom_series.py`:**
```
□ Add the computation in the appropriate section
□ Store as RAW level (not pre-z-scored) — let SignalEngine apply the transform
□ Exception: if the formula involves sign inversion in the raw series, add a comment
  noting that the sign in SignalMapping must account for this
□ Add to the `series` dict with the series_id as the key
□ Run: python src/build_custom_series.py
□ Confirm the series appears in the output with expected row count
□ Add entry in `series` dict and confirm no exceptions
```

**Constraint:** `custom_series.xlsx` must contain only **raw (un-z-scored) values**. If you call a function from `signals.py` that internally applies `ewma_zscore()`, store the intermediate raw diff/return instead.

---

### SOP-C: Removing a Signal

```
□ Remove from SignalMapping: delete all rows for the signal's (AC, pillar) pairs
□ Redistribute weight among remaining signals in the same (AC, pillar) — must still sum to 1.0
□ Remove from DataSeries: delete the row (or mark active=False if the column exists)
□ For custom signals: remove or comment out computation in build_custom_series.py
□ Run: python src/main.py --verbose — confirm signal no longer appears in OK output
□ Run: python src/test_build_layer.py — 29/29 PASS
□ Update CLAUDE.md: move signal entry to docs/signal_improvements.md with reason for removal
□ Update docs/data_quality.md: add removal note with date
□ [Optionally] add to docs/signal_improvements.md with "To activate" instructions
```

---

### SOP-D: Weekly Data Update Checklist

After updating `Dashboard_TAA_Inputs.xlsx` with new Bloomberg data:

```
□ python src/build_custom_series.py      # regenerate derived series
□ python src/main.py                     # full pipeline run
□ python src/test_build_layer.py         # 29/29 PASS
□ python src/compare_runs.py             # [NEW TOOL] diff vs previous run
  → Review any signal with |Δz| > 1.0 sigma
  → Confirm OAS staleness warning if present (normal: OAS lags ~17 days)
□ python src/chartbook_data.py
□ python src/generate_dashboard.py
  → At prompt "Run economic sanity report?" → y
□ Review ESR: confirm large movers match compare_runs.py output
□ Open index.html: visual QC of scorecard and heatmap
```

---

*Document version: 1.0 | June 2026*  
*Next review: After Sprint 1-2 fixes are implemented*
