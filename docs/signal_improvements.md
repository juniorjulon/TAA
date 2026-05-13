# TAA Signal Improvements — Future Enhancements

This document captures signals and relationships that were evaluated but excluded from the
current **plain-vanilla baseline** system. These are candidates for Phase 2 once the base
system is validated with the Investment Committee.

Each item includes the economic rationale, why it was excluded now, and what data is needed
to activate it.

---

## 1. Shiller CAPE (Cyclically-Adjusted P/E)

**Pillar:** Valuation | **ACs:** US Equity, US Growth, US Value

**What it is:** P/E ratio using 10-year real inflation-adjusted earnings average (Shiller 1981).
Less volatile than trailing or forward P/E; captures valuation across full business cycles.

**Economic rationale:** CAPE > 30 historically predicts below-average 10Y returns. Useful as
a long-horizon anchor for the V pillar alongside ERP.

**Why excluded:** Requires manually computing 10Y rolling average of real (CPI-adjusted) trailing
EPS. We have `SPX Index EPS` (trailing) in H3 and `CPI XYOY Index` in H5 — the data exists but
the computation needs validation against the published Shiller series.

**To activate:**
1. Add to `build_custom_series.py`:
   ```python
   from signals import rolling_zscore
   spx_eps = _safe(f3, "eps_fwd_us")   # use trailing EPS from H3
   cpi     = _safe(mkt, "cpi_us")
   real_eps = spx_eps / (1 + cpi/100).cumprod()
   cape     = spx_price / real_eps.rolling(252*10).mean()
   series["shiller_cape"] = cape
   ```
2. Add `series_type="custom"` DataSeries row for `shiller_cape`
3. Wire with `pe_score`-type transform (pctile or rolling_z)

---

## 2. CDX HY Momentum in US Growth / Credit Momentum Signals

**Pillar:** Momentum | **ACs:** US Growth, US Value, LT US Corp

**What it is:** CDX HY 5Y price momentum as a risk-appetite proxy.

**Economic rationale:** When HY credit prices rise (spreads tighten), risk appetite is rising
and equity momentum tends to follow. CDX HY price leads equity by 1-2 weeks historically.

**Why excluded:** The user requested plain-vanilla signals where every relationship is directly
explainable. CDX momentum adding to price momentum in the same pillar creates double-counting.
For the first delivery, pure price momentum (S&P 500 TR) is the cleaner anchor.

**To activate:**
- LT US Corp M: Re-add `cdx_hy_mom` at ~15-20% weight alongside spread momentum
- US Growth M: Add `cdx_hy_mom` at ~20% weight as a risk-appetite overlay
- Verify no double-counting with `oas_hy_mom` (different: CDX = synthetic index; OAS = cash market)

---

## 3. HY OAS Momentum in US Growth (M pillar)

**Pillar:** Momentum | **AC:** US Growth

**Economic rationale:** HY spread tightening = rising earnings expectations = growth style
premium. HY leads growth equity historically by ~2-4 weeks (same credit cycle transmission).

**Why excluded:** Plain-vanilla first delivery — US Growth M is cleanest with just the
growth index TR momentum. Adding HY creates a signal the committee needs to understand.

**To activate:** `oas_hy_mom` (+1, 0.20) in US Growth M, reduce `sp500_gro_tr` to 0.80.

---

## 4. BBB OAS Momentum and CDX IG in US Value (M pillar)

**Pillar:** Momentum | **AC:** US Value

**Economic rationale:** Value stocks (financials, energy, industrials) benefit from spread
tightening as a proxy for economic normalization. IG tightening leads value rotation.

**Why excluded:** Plain-vanilla first delivery. Value M is just `sp500_val_tr` for now.

**To activate:** Add `oas_bbb_mom` (+1, 0.20) and `cdx_ig_mom` (+1, 0.15) to US Value M.

---

## 5. DXY USD Strength for DM and EM Sentiment

**Pillar:** Sentiment | **ACs:** DM ex-US Equity, EM Equity, LT EM FI

**Economic rationale:** Strong USD hurts EM earnings (USD-denominated debt becomes more
expensive) and compresses DM EPS in USD terms. DXY is a direct macro transmission channel.

**Why excluded:** For LT EM FI (CEMBI): the user noted the relationship with EM credit is
indirect — CEMBI is USD-denominated, so DXY doesn't directly affect the instrument yield.
For DM: DXY matters for European multinationals but the effect is already in VSTOXX and
EZ FCI. Adding DXY separately risks double-counting.

**To activate when ready:**
- EM Equity S: `dxy_z` (-1, 0.20) — clear USD headwind for EM equity (in USD terms)
- LT EM FI S: Only if CEMBI index transitions to local currency; skip for USD CEMBI

---

## 6. EM BBB OAS Level in EM Equity Valuation

**Pillar:** Valuation | **AC:** EM Equity

**Economic rationale:** Wide EM credit spreads signal cheap EM risk broadly — attractive for
both EM equity and EM credit simultaneously. High OAS pctile = opportunity.

**Why excluded:** The relationship is cleaner for EM credit (LT EM FI V pillar, already wired)
than for EM equity — equity valuation is better expressed via P/E and ERP. Adding OAS to
EM equity V creates confusion: is it a credit or equity signal?

**To activate:** Add `oas_em` (+1, 0.10-0.15) to EM Equity V as a minor "risk premium
environment" signal, only after the P/E + ERP signals are well understood.

---

## 7. CBOE PCR (Put/Call Ratio) — ✅ ACTIVATED May 2026

**Pillar:** Sentiment | **ACs:** US Equity, US Growth, US Value

**Status:** ACTIVE — wired in SignalMapping with sign=+1, weight=0.15 for all 3 US equity ACs.

**Economic rationale:** High PCR = elevated put buying = fear = contrarian buy signal.
`PCRTEQTY Index` confirmed to have 3,844 clean daily values (2010–2026, range 0.38–2.46).

**Current configuration:**
- `series_type = "original"`, `input_sheet = "H5"`, `input_column = "PCRTEQTY Index"`
- `transform_code = "ewma_z"`, `window = 756`
- Wired to: us_equity (S, +1, 0.15), us_growth (S, +1, 0.15), us_value (S, +1, 0.15)

---

## 8. CFTC COT Positioning (S&P Futures + UST 10Y Futures)

**Pillar:** Sentiment | **ACs:** US Equity (S), LT Treasuries (S)

**Economic rationale:** When large speculators are extremely net long S&P futures, positioning
is crowded → contrarian sell signal. Extreme UST shorts → contrarian UST buy.

**Why excluded:** `cot_spx` and `cot_ust10` appear in the legacy DataSeries but have no data
in our Excel. Requires CFTC Commitment of Traders data (available free via CFTC website or FRED).

**To activate:**
1. Download COT data from FRED (`CFTCSP500` or equivalent)
2. Compute net speculator positioning as pctile
3. Wire as contrarian (sign -1 for S&P, +1 for UST)

---

## 9. Inflation Breakeven in LT EM FI Valuation

**Pillar:** Was V, suggestion is F | **AC:** LT EM FI

**Original question:** Should 10Y breakeven inflation be in V (valuation) or F (fundamentals)?

**Analysis:** 10Y breakeven inflation measures market expectations for future US inflation.
For LT EM FI (CEMBI):
- In **V**: High breakevens = high inflation expectations = UST yields likely to rise =
  CEMBI real return compressed. This is a *cost* signal, not a *carry* signal. Makes
  it more of a risk factor than a valuation signal.
- In **F**: High inflation expectations = Fed stays restrictive = headwind for EM credit
  fundamental backdrop. This is a legitimate Fundamentals interpretation.
- **Neither is obviously correct** for USD EM Corp. The primary CEMBI drivers are spread
  levels (V) and EM growth (F). Inflation is secondary.

**Recommendation:** Leave breakeven_10y OUT of LT EM FI for plain vanilla. If reintroduced:
- F pillar, sign -1, small weight (~10%), described as "US inflation expectations: higher =
  Fed restrictive = EM credit headwind"

---

## 10. Multi-Horizon GDP Revision Signal

**Pillar:** Fundamentals | **Multiple ACs**

**Economic rationale:** The monthly change in consensus GDP forecast (not the level) is more
predictive. Currently `gdp_us` uses the blended level (w_cur×current + w_nxt×next year).
Adding `pct_change(21d)` or `pct_change(63d)` on the blended GDP would capture revisions.

**Why excluded:** `gdp_us` already has `ewma_z` applied by the signal engine, which effectively
captures deviation from its moving average. Adding an explicit revision series would require
a new custom series computation.

**To activate:**
```python
# In build_custom_series.py
gdp_rev_us = series["gdp_us"].pct_change(21)
series["gdp_rev_us"] = gdp_rev_us
```
Then add as `ewma_z` signal in DataSeries.

---

## 11. EPS Revision Composites for DM (Japan)

**Pillar:** Fundamentals | **AC:** DM ex-US Equity

**Current state:** `eps_rev_eafe` (3M+6M composite) is wired. Japan-specific EPS revision
(`eps_rev_japan`) would improve the DM F pillar, as Japan is ~25% of EAFE.

**Why excluded:** `eps_fwd_japan` exists in H3. A `eps_rev_japan` custom series would be
straightforward to add. Excluded for simplicity in first delivery.

**To activate:**
```python
series["eps_rev_japan"] = _eps_composite("eps_fwd_japan")
```
Then add `eps_rev_japan` (+1, 0.10) to DM Equity F alongside `eps_rev_eafe`.

---

## 12. Bloomberg EZ FCI for Short-Term FI

**Pillar:** Sentiment | **AC:** Short-Term FI

**Economic rationale:** `fci_ez` (BFCIEU) captures EZ financial conditions broadly.
While US ST FI is USD-denominated, tight EZ FCI can signal global credit tightening
that spills into USD credit markets.

**Why excluded:** Too indirect for first delivery. The key ST FI sentiment drivers
are already covered by `modern_ted` and `move_z`.

**To activate when EZ spillover effects are documented:** `fci_ez` (-1, 0.15) in STFI S.

---

## 13. Chicago Fed NFCI as Supplementary US FCI

**Pillar:** Sentiment | **ACs:** US Equity, LT US Corp

**What it is:** `nfci` (NFCIINDX) = Chicago Fed National FCI. Broader measure than
Bloomberg FCI, includes credit, risk, leverage, and non-financial leverage components.

**Why excluded:** Highly correlated with `fci_z` (Bloomberg US FCI, already wired).
Having both would double-weight the same information. For plain vanilla, keep only
Bloomberg FCI which is more reactive.

**To activate:** Replace `fci_z` with `nfci` if Bloomberg FCI subscription ends, or
add as a 50/50 composite:
```python
series["fci_composite"] = (data["h7"]["fci_z"] + data["h7"]["nfci"]) / 2
```

---

## 14. DXY Momentum for EM Equity

**Pillar:** Momentum | **AC:** EM Equity

**Economic rationale:** DXY trending stronger over 3-6 months leads to EM capital
outflows as investors anticipate further USD gains. Momentum in DXY is bearish for EM.

**Why excluded:** The user's call: "eliminate by now and put in suggestions." The
static DXY level z-score (`dxy_z`) already captures USD stress in the S pillar.
Adding DXY momentum separately would double-count.

**To activate:** Compute `dxy_mom = ewma_z(dxy.pct_change(63))` and add to EM Equity M
at small weight (-1, ~0.10), only if static DXY signal is removed from S.

---

## Priority for Next Phase

| Priority | Signal | Ease | Impact | Status |
|---|---|---|---|---|
| ✅ | PCR (Put/Call Ratio) | Done | High for equity S pillar | **ACTIVE** |
| 1 | Shiller CAPE | Medium — compute from H3 trailing EPS | High for equity V pillar | Pending |
| 2 | DXY for EM Equity S | Easy — data exists | Medium for EM pillar quality | Pending |
| 3 | CDX HY Momentum overlays | Easy — data exists | Medium for US Growth M | Pending |
| 4 | GDP Revision composite | Easy — compute from existing data | Medium for F pillar | Pending |
| 5 | CFTC COT positioning | Hard — external data source | High if available | Pending |
| 5 | GDP Revision composite | Easy — compute from existing data | Medium for F pillar |
| 6 | CFTC COT positioning | Hard — external data source | High if available |
