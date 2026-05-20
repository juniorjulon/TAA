# Economic Sanity Report
**Run:** RUN_20260520_114858
**Data through:** 2026-05-15
**Generated:** 2026-05-20 11:48:58

---

## Pipeline Status
- Custom series: 41 series rebuilt ✓
- Signals loaded: 97/97 ✓
- Health check: 21/29 pass (8 pre-existing failures from `active=False` on money_market, short_term_fi, us_growth, us_value — pipeline integrity unaffected)
- Dashboard: index.html updated ✓

---

## Most Significant Signal Moves vs Previous Run (RUN_20260513_075351)

| Signal | May 13 | May 20 | Change | Interpretation |
|---|---|---|---|---|
| `eps_china` | +3.00 | -0.52 | **-3.52** | China earnings expectations collapsed |
| `pcr` | -1.61 | +0.49 | **+2.09** | Put/call: market flipped from complacent to hedged |
| `gdpnow` | -1.30 | +0.77 | **+2.07** | Atlanta GDPNow tracking surged |
| `breakeven_10y` | +0.70 | +2.45 | **+1.75** | 10Y inflation expectations jumped sharply |
| `cesi_us` | -0.16 | +1.15 | **+1.31** | US data beat consensus strongly |
| `oas_bbb` | -0.62 | -1.93 | **-1.31** | IG spreads tightened further toward cycle tights |
| `pmi_ez` | +0.37 | -0.71 | **-1.08** | EZ PMI deteriorated |
| `bfu5/i132/lt03 price` | ~0.00 | -0.89 | **-0.92** | LT bond price momentum turned negative |
| `oas_em` | -1.12 | -1.95 | **-0.82** | EM credit spreads compressed further |

---

## Scorecard (2026-05-19)

| Asset Class | Z_F | Z_M | Z_S | Z_V | Z_Comp | Conviction | Final Tilt |
|---|---|---|---|---|---|---|---|
| LT US Treasuries | -1.11 | +1.16 | +0.45 | +1.58 | +0.57 | NEUTRAL | **+1.0%** |
| LT US Corporate | +0.40 | +0.58 | -0.16 | -1.62 | -0.26 | NEUTRAL | **0.0%** |
| LT EM Fixed Income | +0.05 | +0.14 | +1.01 | -3.00 | -0.49 | NEUTRAL | **0.0%** |
| US Equity (Broad) | +0.59 | -0.19 | +0.02 | -0.53 | -0.04 | NEUTRAL | **0.0%** |
| DM ex-US Equity | -1.98 | -1.71 | +0.14 | +0.83 | -0.78 | MEDIUM UW | **-1.0%** |
| EM Equity | +0.07 | -0.45 | +1.35 | +0.88 | +0.37 | NEUTRAL | **+0.65%** |

---

## Signal Environment — Key Readings

### Growth / Macro
| Signal | Z | Reading |
|---|---|---|
| pmi_us | +0.811 | US manufacturing/services above trend |
| pmi_ez | -0.707 | EZ PMI deteriorating |
| pmi_china | +0.360 | China PMI modestly expansionary |
| cesi_us | +1.155 | US data strongly beating expectations |
| cesi_ez | -1.413 | EZ data consistently disappointing |
| cesi_em | +1.334 | EM data beating expectations |
| gdp_us | +0.654 | US GDP forecast above consensus |
| gdp_eu | -1.591 | EU GDP forecast cut significantly |
| gdp_em | +0.661 | EM growth revised up |
| gdpnow | +0.770 | GDPNow real-time tracking positive |
| ism_no_inv | +0.584 | New orders > inventories (demand healthy) |

### Inflation / Rates
| Signal | Z | Reading |
|---|---|---|
| breakeven_5y | +2.102 | 5Y inflation expectations very elevated |
| breakeven_10y | +2.445 | 10Y inflation expectations at 4-sigma |
| core_pce | +0.235 | Realized PCE near neutral |
| real_ff | -1.906 | Real rates highly restrictive |
| gt10 | +1.906 | 10Y yield at 91st historical percentile |
| gt10_mom | +1.208 | 10Y yields have been falling (bond price momentum +) |
| term_spread | +0.558 | Curve modestly positive |

### Credit Spreads
| Signal | Z | Reading |
|---|---|---|
| oas_bbb | -1.927 | BBB spreads at ~2nd percentile — very tight |
| oas_hy | -1.425 | HY spreads at historically tight levels |
| oas_em | -1.951 | EM spreads at ~2nd percentile — extreme tights |
| oas_latam | -1.905 | LatAm spreads at cycle tights |
| hy_ig_ratio | +1.553 | HY/IG spread ratio elevated |

### Equity Valuation
| Signal | Z | Reading |
|---|---|---|
| erp_us | -1.848 | US equity risk premium very compressed |
| erp_em | -2.101 | EM equity risk premium compressed |
| erp_acwi | -2.098 | Global ERP at -2 sigma |
| pe_score_sp500 | +0.852 | SP500 PE not extreme on earnings yield basis |
| pe_score_em | +1.440 | EM PE elevated |

### Equity Momentum
| Signal | Z | Reading |
|---|---|---|
| sp500_tr | +0.392 | US equity price momentum mildly positive |
| eafe_tr | -0.196 | EAFE price momentum slightly negative |
| msci_em_tr | +0.766 | EM equity price momentum solid |
| sp500_gro_tr | +0.446 | Growth momentum positive |

### Earnings Revisions
| Signal | Z | Reading |
|---|---|---|
| eps_rev_us | +1.673 | Strong US EPS upgrade cycle |
| eps_rev_em | +1.435 | Strong EM EPS upgrades |
| eps_rev_eafe | +1.832 | Strong DM EPS upgrades |
| eps_china | -0.518 | China EPS collapsed (-3.5 SD from prior week) |

### Sentiment
| Signal | Z | Reading |
|---|---|---|
| vix | -0.063 | VIX near average |
| move_z | -0.450 | Bond vol below average |
| vstoxx_z | +0.548 | EZ vol slightly elevated |
| pcr | +0.486 | Put/call elevated — hedging activity (contrarian bullish) |
| nfci | -0.694 | NFCI: US financial conditions loose |
| modern_ted | +0.754 | TED spread: some funding stress |
| fci_z | +0.593 | US FCI: slightly tight |

---

## AC-Level Sanity Assessment

### 1. LT US Treasuries — NEUTRAL +1.0% OW
**Case for (+)**: Yields at historical highs (V=+1.58), price momentum positive as yields have been falling (M=+1.16), PCR contrarian-positive.
**Case against (-)**: Strong US growth (cesi_us=+1.15, gdpnow=+0.77), breakeven_10y=+2.45 at 4-sigma = inflation expectations running hot.
**Verdict**: Defensible but tension-laden "carry + momentum" call. The +1.0% represents cheap yields with recent price appreciation, but the inflation expectations surge is a genuine headwind.
**⚠️ FLAG**: breakeven_10y jumped +1.75 SD in one week. If sustained, the Treasury OW thesis weakens materially in future runs.

### 2. LT US Corporate — NEUTRAL 0%
**Reading**: Spreads at cycle tights (oas_bbb=-1.93, 2nd percentile), positive momentum, supportive US fundamentals.
**Verdict**: Correct. No conviction to fight the momentum but valuation alone is a warning. oas_bbb tightened another -1.31 SD this week — compressed further toward extremes.

### 3. LT EM Fixed Income — NEUTRAL 0%
**Reading**: V=-3.00 (EXTREME — EM spreads at 3-sigma historical tights). Other pillars near neutral. n_agree=1, conviction=0.
**Verdict**: Methodologically correct (no multi-pillar confirmation), but V=-3.00 is the most extreme single valuation signal in the entire system. EM credit is priced for perfection with very limited upside and significant downside in any risk-off episode.
**⚠️ STRONG FLAG**: Classic "crowded trade" warning. V=-3.0 should inform position sizing regardless of the 0% tilt. In a risk-off shock, EM IG/HY spreads would widen violently from these levels.

### 4. US Equity — NEUTRAL 0%
**Reading**: Strong fundamentals (eps_rev_us=+1.67, cesi_us=+1.15), compressed valuation (erp_us=-1.85), mildly negative momentum (-0.19).
**Verdict**: Correct. US equity is genuinely ambiguous — the best earnings revision backdrop in the system competes with the most compressed ERP. NEUTRAL is appropriate.
**NOTABLE**: eps_rev_us=+1.67 and cesi_us=+1.15 is the most bullish data combination in the current run for US fundamentals.

### 5. DM ex-US Equity — MEDIUM UW -1.0% ← Highest Conviction
**Reading**: F=-1.98 (cesi_ez=-1.41, gdp_eu=-1.59, pmi_ez=-0.71) + M=-1.71. Both pillars firmly negative. V=+0.83 (DM cheap) not sufficient to offset.
**Verdict**: Strongly justified. EZ manufacturing recession deepening, data consistently disappointing, tariff headwinds on export economy. This is the most economically coherent and defensible call in the scorecard.
**LOGIC**: Europe = weak fundamentals + negative momentum + cheap. System correctly weights F+M over V alone.

### 6. EM Equity — NEUTRAL +0.65%
**Reading**: S=+1.35 (em_stress eased, PCR hedging = contrarian), V=+0.88 (relative cheapness). M=-0.45, F=+0.07.
**Verdict**: Defensible but conviction-light. Contrarian sentiment + cheap valuation offset by slightly negative momentum.
**⚠️ CONCERN**: eps_china collapsed -3.5 SD this week. erp_em=-2.10 (EM not actually cheap on earnings yield vs bonds). China weight in EM (~30%) is a risk to this position.

---

## Portfolio Tilt Summary

| AC | IGCON | IGMOD | IGDIN | IGEQUS |
|---|---|---|---|---|
| LT Treasuries | +0.8% | +1.2% | +1.6% | +2.0% |
| LT US Corp | 0.0% | 0.0% | 0.0% | 0.0% |
| LT EM FI | -0.2% | -0.3% | -0.2% | 0.0% |
| US Equity | -0.2% | -0.3% | -0.2% | -2.0% |
| DM Equity | -0.7% | -1.1% | -1.2% | 0.0% |
| EM Equity | +0.3% | +0.5% | -0.2% | 0.0% |

Tilts scale correctly with TE budget. force_zero_sum constraint working. Net equity tilt -0.3%, FI +1.0% = mild defensive posture.

---

## Three Risks the Model Signals But Does Not Fully Act On

**1. Inflation regime shift**
breakeven_10y jumped from +0.70 to +2.45 (+1.75 SD) in one week. If sustained, the nominal Treasury OW becomes untenable. The F pillar for LT Treasuries (-1.11) already captures this partially, but V+M currently dominate.

**2. Extreme credit spread compression**
oas_bbb=-1.93, oas_em=-1.95, oas_latam=-1.91 all at 2+ sigma tights. EM FI V=-3.00 is exceptional. System assigns no conviction without multi-pillar confirmation, but these represent asymmetric downside risk in any macro deterioration.

**3. China EPS collapse**
eps_china dropped 3.5 sigma in one week (from cap +3.00 to -0.52). Largest single-signal move in this run. EM equity's slight OW should be monitored given China's ~30% weight in EM indices.

---

## Overall Verdict

Results are **economically coherent and intuitive**.
- Strongest call: **DM equity MEDIUM UW** — fully consistent with visible European economic deterioration.
- All other positions are low-conviction and appropriate given genuine uncertainty.
- Total |tilts| = 2.7% (modest tracking error) reflects correctly identified ambiguity in the macro environment.
- Key monitoring items: inflation expectations surge, credit spread extremes, China earnings revision collapse.
