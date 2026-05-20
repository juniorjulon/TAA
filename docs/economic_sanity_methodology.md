# TAA Dashboard — Economic Sanity Check Methodology
**Purpose:** Systematic, reproducible verification that the TAA pipeline produces economically coherent z-scores after every run.  
**When to run:** After every `python src/main.py` execution.  
**Automation:** Integrate as `python src/test_economic_sanity.py` → exit 0 if all pass, exit 1 if any FAIL.

---

## Design Philosophy

A z-score can be **technically correct** (right formula, right data) but **economically wrong** (opposite sign from market reality). The signal-level unit tests in `test_build_layer.py` verify code health; this methodology verifies **economic coherence**.

Three alert levels:
- 🟢 **PASS** — signal z-score consistent with current market regime
- 🟡 **REVIEW** — z-score plausible but requires analyst judgment
- 🔴 **FAIL** — z-score clearly inconsistent with observable market conditions

**FAIL** = the pipeline should raise a logged warning before the dashboard is shared with the IC.

---

## Rule 1: Sign Consistency Between Correlated Signals

Signals that measure the same economic phenomenon should generally agree in sign.

### 1.1 — Growth cluster (Fundamentals pillar, equity direction)

These signals capture the same economic cycle; all should have the same sign for equity:

| Signal | Expected relationship |
|---|---|
| `pmi_us` | Same sign as `cesi_us` |
| `gdp_us` | Same sign as `pmi_us` |
| `eps_rev_us` | Same sign or within ±1.5 z units |
| `gdpnow` | May diverge from `gdp_us` (short-run vs consensus), but not opposite by >2.5 |

**Alert rule:**
```python
# FAIL if pmi_us and cesi_us have opposite signs AND both |z| > 0.5
if sign(z["pmi_us"]) != sign(z["cesi_us"]):
    if abs(z["pmi_us"]) > 0.5 and abs(z["cesi_us"]) > 0.5:
        FAIL("pmi_us and cesi_us disagree on growth direction")

# FAIL if gdp_us and pmi_us have opposite signs AND both |z| > 0.7
if sign(z["gdp_us"]) != sign(z["pmi_us"]):
    if abs(z["gdp_us"]) > 0.7 and abs(z["pmi_us"]) > 0.7:
        FAIL("gdp_us and pmi_us disagree on growth direction")
```

### 1.2 — Credit stress cluster (Sentiment pillar)

```python
# hy_stress and em_stress should agree in sign (both measure risk-off)
# REVIEW if they disagree
if sign(z["hy_stress"]) != sign(z["em_stress"]):
    if abs(z["hy_stress"]) > 0.5 and abs(z["em_stress"]) > 0.5:
        REVIEW("hy_stress and em_stress disagree — check OAS data staleness")
```

### 1.3 — Inflation cluster

```python
# breakeven_5y and core_pce should agree (both measure inflation pressure)
if sign(z["breakeven_5y"]) != sign(z["core_pce"]):
    if abs(z["breakeven_5y"]) > 0.8 and abs(z["core_pce"]) > 0.3:
        REVIEW("breakeven_5y and core_pce disagree — check PCE data (monthly, may lag)")
```

---

## Rule 2: Boundary Detection (Winsorisation)

Any signal at exactly ±3.0 has been clipped. This is a data quality flag.

```python
for series_id, z_val in signals.items():
    if abs(z_val) >= 2.98:
        FAIL(f"Signal {series_id} at clip boundary (z={z_val:.2f}). "
             f"Check raw data for spike or data error.")
```

**Expected in current run:** `eps_china = +3.00` → requires manual verification of China EPS revision data.

---

## Rule 3: VIX / Volatility Direction

VIX should respond to market stress. When VIX is elevated (e.g., > 25), it must generate a positive z-score (contraction in z-score terms from EWMA).

```python
# VIX z-score direction rule:
# - If VIX actual level > 25: z["vix"] should be > 0 (elevated vs EWMA mean)
# - If VIX actual level < 15: z["vix"] should be < 0 (low, complacency)
# Implementation: read latest VIX close from CB data

vix_level = CB["sentiment"]["vix"]["latest"]   # latest raw value in CB
if vix_level > 25 and z["vix"] < -0.5:
    FAIL(f"VIX={vix_level:.1f} (elevated) but z={z['vix']:.2f} (negative). "
         f"EWMA may have shifted — check if VIX was even higher in recent months.")
if vix_level < 15 and z["vix"] > 0.5:
    FAIL(f"VIX={vix_level:.1f} (low) but z={z['vix']:.2f} (positive). Inconsistent.")
```

---

## Rule 4: Asset Class Pillar Direction Consistency

The Fundamentals pillar for equity ACs and the Fundamentals pillar for long-duration FI should have **opposite signs** (growth is bullish for equity but bearish for duration).

```python
# F pillar: equity vs duration must disagree
z_F_equity = scorecard.loc["us_equity", "Z_F"]
z_F_tsy    = scorecard.loc["lt_treasuries", "Z_F"]

# They must have opposite signs when both have signal (|z| > 0.3)
if sign(z_F_equity) == sign(z_F_tsy):
    if abs(z_F_equity) > 0.3 and abs(z_F_tsy) > 0.3:
        FAIL(f"F pillar: us_equity (z={z_F_equity:.2f}) and lt_treasuries "
             f"(z={z_F_tsy:.2f}) have SAME sign. Growth signals must be inverted "
             f"for duration. Check SignalMapping sign column for lt_treasuries.")
```

---

## Rule 5: Momentum Pillar vs Price Reality

If equities have had clearly positive returns YTD (e.g., > +5%), the momentum pillar for equity should be positive.

```python
# Check: if price_mom z-score direction matches actual asset direction
# sp500_tr is the price momentum signal for us_equity
# Its z-score should match the direction of recent price return

sp500_mom_z = z.get("sp500_tr", None)
if sp500_mom_z is not None:
    # price_mom should be > 0 if S&P is above its 200-day MA (typical momentum condition)
    # We proxy this via the MA component in the composite
    # Simple rule: if z < -1.5, require an explanation (market would need to be in steep downtrend)
    if sp500_mom_z < -1.5:
        REVIEW(f"sp500_tr momentum z={sp500_mom_z:.2f} (very negative). "
               f"Verify S&P 500 is indeed in a downtrend.")
```

---

## Rule 6: Credit Spreads vs Credit Valuation

OAS spread levels and credit momentum should be directionally consistent.

```python
# If OAS has been TIGHTENING (positive momentum signal, oas_bbb_mom > 0):
# Then OAS level should be in a lower percentile (oas_bbb pctile-z < 0 = tight)
# This is consistent: spreads tightening → lower percentile rank → oas_bbb z < 0

oas_mom_z   = z.get("oas_bbb_mom", None)
oas_level_z = z.get("oas_bbb", None)

if oas_mom_z is not None and oas_level_z is not None:
    # If momentum strongly tightening AND level still elevated: possible data lag
    if oas_mom_z > 1.5 and oas_level_z > 1.5:
        REVIEW(f"oas_bbb: momentum z={oas_mom_z:.2f} (tightening) but "
               f"level z={oas_level_z:.2f} (still wide). "
               f"Check OAS data staleness — OAS sheet typically lags H5 by ~17 days.")
    # If momentum widening AND level at low pctile: unusual
    if oas_mom_z < -1.5 and oas_level_z < -1.5:
        REVIEW(f"oas_bbb: momentum z={oas_mom_z:.2f} (widening rapidly) "
               f"but level already cheap (z={oas_level_z:.2f}). Consistent with "
               f"spreads already elevated and continuing to widen.")
```

---

## Rule 7: ERP vs Equity Valuation Score

The Equity Risk Premium and the P/E score should directionally agree for the same equity region.

```python
# If ERP is negative (equities expensive vs bonds), pe_score should also be negative
# (stock cheap → pe_score positive; stock expensive → pe_score negative)
# They measure related things: disagreement requires explanation

erp_us     = z.get("erp_us", None)
pe_sp500   = z.get("pe_score_sp500", None)

if erp_us is not None and pe_sp500 is not None:
    # ERP negative = expensive; pe_score positive = cheap — contradiction
    if erp_us < -1.0 and pe_sp500 > 1.0:
        REVIEW(f"erp_us={erp_us:.2f} (expensive vs bonds) but "
               f"pe_score_sp500={pe_sp500:.2f} (cheap on P/E). "
               f"Likely due to short PE data window (~1Y). "
               f"The ERP view is more reliable (uses full 10Y history).")
```

**This rule will ALWAYS trigger in the current system** because PE data is ~1 year. Use this as a systematic reminder to communicate the PE data limitation to the IC.

---

## Rule 8: Composite Scorecard Cross-Checks

### 8.1 — Agreement between composite z and dominant pillar

If a composite z-score is strongly positive (> 1.0), at least one pillar should also be positive (> 0.5).

```python
for ac in scorecard.index:
    z_comp = scorecard.loc[ac, "Z_composite"]
    pillars = [scorecard.loc[ac, f"Z_{p}"] for p in "FMSV"]
    if z_comp > 1.0:
        if max(pillars) < 0.3:
            FAIL(f"{ac}: Z_composite={z_comp:.2f} (positive) but all pillars < 0.3. "
                 f"Composite-pillar inconsistency. Check scoring.py pillar combination.")
```

### 8.2 — Conviction-tilt consistency

If conviction is NEUTRAL, final_tilt must be ≈ 0.

```python
for ac in scorecard.index:
    conv = scorecard.loc[ac, "conviction"]
    tilt = scorecard.loc[ac, "final_tilt_%"]
    if conv == "NEUTRAL" and abs(tilt) > 0.5:
        FAIL(f"{ac}: conviction=NEUTRAL but final_tilt={tilt:.2f}%. "
             f"Check conviction multiplier in scoring.py.")
```

### 8.3 — Zero-sum within portfolio

```python
for portfolio_id, df in portfolio_views.items():
    net_tilt = df["portfolio_tilt"].sum()
    if abs(net_tilt) > 0.01:  # tolerance for float arithmetic
        FAIL(f"Portfolio {portfolio_id}: net tilt = {net_tilt:.4f}% ≠ 0. "
             f"force_zero_sum enforcement failed. Check portfolio.py.")
```

---

## Rule 9: Data Freshness

### 9.1 — OAS staleness check (already in main.py, formalize here)

```python
oas_date   = data["oas"].index.max()
h5_date    = data["mkt"].index.max()
lag_days   = (h5_date - oas_date).days

if lag_days > 7:
    REVIEW(f"OAS data is {lag_days} business days behind H5 ({oas_date} vs {h5_date}). "
           f"Credit signals (oas_bbb, oas_em, hy_stress) may be stale.")
if lag_days > 20:
    FAIL(f"OAS data is {lag_days} days old. Requires immediate data update.")
```

### 9.2 — AAII freshness (weekly series)

```python
aaii_date = data["aaii"].index.max()
run_date  = pd.Timestamp.today()
aaii_lag  = (run_date - aaii_date).days
if aaii_lag > 14:
    REVIEW(f"AAII data is {aaii_lag} days old (latest: {aaii_date.date()}). "
           f"May not reflect current week's survey.")
```

---

## Rule 10: Minimum Signal Coverage

Each active pillar for each AC should have at least 1 non-NaN signal.

```python
for ac in ASSET_CLASSES:
    for pillar in "FMSV":
        z_pillar = scorecard.loc[ac, f"Z_{pillar}"]
        if pd.isna(z_pillar):
            FAIL(f"{ac} pillar {pillar}: z-score is NaN. "
                 f"All signals for this pillar may be missing or empty.")
```

---

## Complete Alert Framework — Implementation Template

```python
# src/test_economic_sanity.py
"""
Run after: python src/main.py
Usage:     python src/test_economic_sanity.py
Exit 0 = all checks pass (with optional REVIEW warnings)
Exit 1 = one or more FAIL alerts — do not share dashboard with IC
"""

import sys, json, pandas as pd, numpy as np

RESULTS_DIR = "results"
PASS = "PASS"; REVIEW = "REVIEW"; FAIL = "FAIL"
alerts = []

def check(level, rule_id, message):
    alerts.append({"level": level, "rule": rule_id, "msg": message})
    prefix = {"PASS": "✅", "REVIEW": "⚠️ ", "FAIL": "🔴"}[level]
    print(f"  {prefix} [{rule_id}] {message}")

# Load data
sc   = pd.read_csv(f"{RESULTS_DIR}/RUN_.../taa_scorecard.csv", index_col=0)
z    = json.load(open(f"{RESULTS_DIR}/signal_z_snapshot.json"))

# ── Rule 1: Correlated signals ────────────────────────────────────────────────
pmi, cesi = z.get("pmi_us",0), z.get("cesi_us",0)
if np.sign(pmi) != np.sign(cesi) and abs(pmi)>.5 and abs(cesi)>.5:
    check(FAIL, "R1.1", f"pmi_us={pmi:.2f} and cesi_us={cesi:.2f} disagree on growth")
else:
    check(PASS, "R1.1", f"Growth cluster aligned: pmi_us={pmi:.2f}, cesi_us={cesi:.2f}")

# ── Rule 2: Clip boundary ─────────────────────────────────────────────────────
for sid, zv in z.items():
    if abs(zv) >= 2.98:
        check(FAIL, "R2", f"{sid} at clip boundary (z={zv:.2f}) — verify raw data")

# ── Rule 4: F pillar equity vs duration ──────────────────────────────────────
z_F_eq  = sc.loc["us_equity",    "Z_F"]
z_F_tsy = sc.loc["lt_treasuries","Z_F"]
if np.sign(z_F_eq) == np.sign(z_F_tsy) and abs(z_F_eq)>.3 and abs(z_F_tsy)>.3:
    check(FAIL, "R4", f"F pillar same sign for us_equity({z_F_eq:.2f}) "
          f"and lt_treasuries({z_F_tsy:.2f}) — growth inversion error?")
else:
    check(PASS, "R4", f"F pillar correctly inverted: EQ={z_F_eq:.2f} vs TSY={z_F_tsy:.2f}")

# ── Rule 7: ERP vs PE score ───────────────────────────────────────────────────
erp_us = z.get("erp_us",0); pe_sp  = z.get("pe_score_sp500",0)
if erp_us < -1.0 and pe_sp > 1.0:
    check(REVIEW, "R7", f"erp_us={erp_us:.2f} (expensive) vs pe_score_sp500={pe_sp:.2f} "
          f"(cheap) — PE data window only ~1Y, ERP view more reliable")

# ── Rule 8.2: Conviction-tilt consistency ────────────────────────────────────
for ac in sc.index:
    conv, tilt = sc.loc[ac,"conviction"], sc.loc[ac,"final_tilt_%"]
    if conv == "NEUTRAL" and abs(tilt) > 0.5:
        check(FAIL, "R8.2", f"{ac}: NEUTRAL conviction but tilt={tilt:.2f}%")

# ── Summary ───────────────────────────────────────────────────────────────────
fails   = [a for a in alerts if a["level"] == FAIL]
reviews = [a for a in alerts if a["level"] == REVIEW]
passed  = [a for a in alerts if a["level"] == PASS]

print(f"\n{'='*60}")
print(f"Economic Sanity: {len(passed)} PASS | {len(reviews)} REVIEW | {len(fails)} FAIL")
if fails:
    print("🔴 DO NOT share dashboard with IC — resolve FAILs first.")
    sys.exit(1)
elif reviews:
    print("⚠️  Dashboard OK but review highlighted signals before IC presentation.")
else:
    print("✅ All checks pass. Dashboard is safe to share.")
sys.exit(0)
```

---

## Summary of All Rules

| # | Rule | Condition | Alert |
|---|---|---|---|
| R1.1 | Growth cluster sign | `pmi_us` vs `cesi_us` opposite signs with \|z\| > 0.5 | FAIL |
| R1.2 | Credit stress cluster | `hy_stress` vs `em_stress` opposite signs | REVIEW |
| R1.3 | Inflation cluster | `breakeven_5y` vs `core_pce` opposite signs | REVIEW |
| R2 | Clip boundary | Any signal \|z\| ≥ 2.98 | FAIL |
| R3 | VIX direction | VIX level > 25 but z < -0.5 | FAIL |
| R4 | F pillar inversion | `us_equity` Z_F same sign as `lt_treasuries` Z_F | FAIL |
| R5 | Momentum vs price | `sp500_tr` z < -1.5 | REVIEW |
| R6 | Credit momentum vs level | Both `oas_bbb_mom` > 1.5 AND `oas_bbb` > 1.5 simultaneously | REVIEW |
| R7 | ERP vs PE score | `erp_us` < -1.0 AND `pe_score_sp500` > 1.0 | REVIEW |
| R8.1 | Composite-pillar consistency | Z_composite > 1.0 but all pillars < 0.3 | FAIL |
| R8.2 | Conviction-tilt | NEUTRAL conviction with \|tilt\| > 0.5% | FAIL |
| R8.3 | Portfolio zero-sum | Net tilt ≠ 0 per portfolio | FAIL |
| R9.1 | OAS staleness | Lag > 7 days = REVIEW; > 20 days = FAIL | FAIL/REVIEW |
| R9.2 | AAII freshness | AAII data > 14 days old | REVIEW |
| R10 | Signal coverage | Any pillar z-score = NaN | FAIL |

**Total: 6 FAIL rules + 9 REVIEW rules. Target: 0 FAIL before any IC presentation.**
