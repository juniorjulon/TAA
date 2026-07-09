# TAA Dashboard Implementation Guide

## Quick Start

### 1. Load Required Libraries
```r
install.packages(c("shiny","shinydashboard","shinyWidgets",
  "readxl","dplyr","tidyr","plotly","DT","TTR","zoo","scales"))
```

### 2. Run the App
```r
shiny::runApp("taa_dashboard.R")
```
The dashboard will open at `http://localhost:3838`

---

## New Features: 4-Pillar Framework

### **Home Tab: "4-Pillar Unified"**
Located at the **top of the sidebar** under "TAA FRAMEWORK"

#### What You See:
1. **Pillar Analysis Table**
   - Rows: Fundamentals, Momentum & Sentiment, Positioning, Valuation
   - Columns: Pillar name, Weight (%), Current z-score
   - Color coding: Green (bullish) → Yellow (neutral) → Red (bearish)

2. **Composite Score (Large Display)**
   - Single number showing weighted aggregation of all 4 pillars
   - Range: −2.0 to +2.0 (z-score scale)
   - Color indicates direction: Green (+) vs. Red (−)

3. **Conviction Level**
   - Translated signal: "Very High OW", "High OW", "Neutral", "Underweight", "Very High UW"
   - Used to determine portfolio position sizing

4. **Pillar Agreement Rate**
   - % of pillars pointing in same direction as composite
   - 100% = perfect consensus; <50% = conflicting signals

5. **Waterfall Chart**
   - Bar chart showing each pillar's contribution to final composite score
   - Highlights which pillar is driving the signal

6. **Radar Chart**
   - Polygon showing relative strength of each pillar
   - Normalized to −1 to +1 range for easy comparison
   - Helps identify unbalanced signals (e.g., momentum strong, valuation weak)

---

## How to Interpret the Signals

### **Very High (Composite Z > +1.5) 🟢**
- **Action**: 100% of risk budget; overweight tactically
- **Frequency**: Rare (2–3 times per year)
- **Meaning**: All 4 pillars aligned → strong buy signal
- **Example**: Post-crisis recovery (April 2009, March 2020) with strong PMI, positive momentum, tight spreads, attractive valuations

### **High (+0.5 to +1.5) 🔵**
- **Action**: 75% of risk budget; moderate overweight
- **Meaning**: 3 of 4 pillars bullish (>50% pillar agreement)
- **Example**: Mid-cycle with good earnings momentum but expensive valuations

### **Neutral (−0.5 to +0.5) 🟡**
- **Action**: 50% of risk budget (stay at strategic allocation)
- **Meaning**: Insufficient signal; mixed pillar views
- **Example**: Balanced market with offsetting signals (good momentum ↔ tight valuations)

### **Underweight (−1.0 to −0.5) 🟠**
- **Action**: 25% of risk budget; defensive positioning
- **Meaning**: Mixed-but-negative; majority negative
- **Example**: Late cycle with slowing macro, but still positive momentum

### **Very High UW (< −1.5) 🔴**
- **Action**: 0% of risk budget; maximum defense
- **Frequency**: Crisis periods only (liquidity crises, regime shifts)
- **Meaning**: All pillars aligned → strong sell / reduce risk
- **Example**: 2008 Q4, 2020 March 15–20 (COVID panic)

---

## Understanding Each Pillar

### **Pillar 1: Fundamentals (25%)**
**What it measures**: Direction of economic activity and credit health

**Key Inputs**:
- ISM PMI (>50 = expanding, <50 = contracting)
- Earnings revisions momentum
- IG leverage ratios (Net Debt/EBITDA)
- Default rates (Moody's 12M trailing HY default %)

**When it works best**: 
- Turning points (late expansion → recession, trough → recovery)
- 3–12 month horizon

**When it fails**: 
- Mid-cycle when growth is stable/priced in (May 2018, Sept 2019)
- QE-driven rallies (2012–2014) decoupled from fundamentals

**Action if Strong Positive** (z > +0.5):
- PMI rising above 50, earnings revisions broadening
- Good for: Equities, cyclicals, EM, high-yield credit
- Action: Increase risk exposure

---

### **Pillar 2: Momentum & Sentiment (30%)**
**What it measures**: Price trends and market fear/greed extremes

**Key Inputs**:
- 12-month rolling returns
- RSI(14) — overbought/oversold
- MA50 vs. MA200 crossovers (trend identification)
- MOVE Index (bond volatility = market stress gauge)

**When it works best**: 
- 3–12 month horizon
- Momentum persists for 3–6 months before reversal

**When it fails**: 
- Regime turning points (momentum crashes)
- March 2009: trend-followers got crushed at the exact bottom
- Q1 2020: VIX spike + momentum reversal (sell winners, buy losers)

**Action if Strong Positive** (z > +0.5):
- RSI 50–70 (bullish but not overbought), MA50 > MA200 (uptrend)
- 12M returns >+15% or positive and rising
- Action: Ride the trend; lean into risk assets

**Action if Strong Negative** (z < −0.5):
- RSI <30 (oversold), MA50 < MA200 (downtrend)
- 12M returns negative or deteriorating
- Action: Defensive; raise cash, reduce volatility

---

### **Pillar 3: Positioning (15%)**
**What it measures**: Supply/demand imbalance, fund flows, liquidity

**Key Inputs**:
- OAS spreads vs. 50/200-day moving averages
- EPFR fund flows (equity inflows = risk-on)
- Credit issuance vs. seasonal norms
- Net speculative positioning (CFTC data, margin debt)

**When it works best**: 
- Detecting sentiment extremes at 3–12 month horizon
- Especially powerful as *contrarian signal*
- Extreme inflows = crowded long → reversal risk

**When it fails**: 
- Long-duration positioning (>1 year); flows are noisy
- Hedging activity masks true conviction

**Action if Strong Positive** (z > +0.5):
- Spreads tightening (OAS down vs. MA)
- Steady inflows into equities
- Low issuance (companies confident)
- Action: Risk-on; overweight equities

**Action if Strong Negative** (z < −0.5):
- Spreads widening (OAS up vs. MA)
- Outflows from equities or increased margin selling
- Heavy supply (companies raising capital defensively)
- Action: Risk-off; cut equity exposure

---

### **Pillar 4: Valuation (20%)**
**What it measures**: Is the market cheap or expensive vs. history & fair value?

**Key Inputs**:
- Forward P/E multiples (S&P 500, EM, IG credit)
- CAPE ratio (10-year cyclical P/E)
- 10Y TIPS Real Yield (>2.0% = restrictive, <0% = ultra-loose)
- Equity Risk Premium (Fwd Earnings Yield − TIPS Real)

**When it works best**: 
- 3–12 month horizon (and especially 1–3 year)
- CAPE explains 85% of 10-year returns (post-2025)
- Excellent for ranking *asset classes* (equities vs. bonds)

**When it fails**: 
- 1–3 month horizon (R² = 10%)
- Regime shifts can push valuations to extremes for years
- Tech bubble (2000), ZIRP era (2010–2021)

**Interpretation**:
- **P/E < 16x**: Cheap (buy signal, z > +0.5)
- **P/E 16–22x**: Fair value (neutral)
- **P/E > 22x**: Expensive (sell signal, z < −0.5)

**Action if Strong Positive** (z > +0.5):
- P/E below 16x, CAPE in bottom 25%
- Real yields >2% but equity yields >bond yields
- Action: Build positions; valuations provide margin of safety

**Action if Strong Negative** (z < −0.5):
- P/E >22x, CAPE in top 25%
- Real yields <0%, equities yield <bonds
- Action: Trim risk; valuation froth limits upside

---

## Using the Radar Chart

**What it shows**: Relative strength of all 4 pillars simultaneously

**Reading the polygon**:
- **Balanced star shape** (all arms equal length): Consensus signal
  - Strong bullish consensus = All arms point outward
  - Strong bearish consensus = All arms point inward
  
- **Lumpy/uneven shape**: Conflicting signals
  - One strong, three weak = Single pillar driving signal (fragile)
  - Example: High momentum + low valuation = Risky long (relies on sentiment continuing)

**Action from Radar**:
- **Perfect star (bullish)** → High conviction; full risk budget
- **Uneven bullish** → Moderate conviction; watch the weak pillar (risk reversal)
- **Mixed/balanced** → Low conviction; stay near benchmark

---

## Connecting to Other Tabs

The "4-Pillar Unified" tab aggregates signals from the existing tabs:

| Pillar | Data Source Tabs |
|---|---|
| **Fundamentals** | Not yet in dashboard (requires macro data integration) |
| **Momentum** | "I. MOMENTUM" tabs (RSI, MA crosses, 12M returns) |
| **Positioning** | "II. VALUATION → OAS" tab (spread dynamics) |
| **Valuation** | "II. VALUATION → P/E Absolute/Relative, Yield Curve" |

**Workflow**:
1. Click "4-Pillar Unified" to see composite signal
2. If signal is unclear, click into individual pillar tabs to see details
3. Example: Composite = "Neutral" but Momentum > +1.0
   - Check "I. MOMENTUM" tabs to see if reversal is building
   - Check "II. VALUATION" tabs to see if valuation explains the weakness

---

## Daily Workflow (Portfolio Manager)

**5-Minute Check**:
1. Open dashboard → "4-Pillar Unified" tab
2. Glance at **Composite Score** and **Conviction**
3. Scan **Radar Chart** for pillar consensus
4. Note **Pillar Agreement %**: >75% = act on signal, <50% = wait for clarity

**15-Minute Deep Dive**:
1. Click **Pillar Analysis Table**: Which pillar changed most?
2. Jump to that pillar's tab (e.g., if Valuation changed, go to "P/E Absolute")
3. Check 2-year history in that tab's charts
4. Confirm signal makes sense (not a data glitch)

**Tactical Decision**:
- Composite **Very High (+1.5+)**: Overweight; buy on dips
- Composite **High (+0.5 to +1.5)**: Moderate overweight; add on weakness
- Composite **Neutral (−0.5 to +0.5)**: Stay at benchmark
- Composite **Underweight (<−0.5)**: Reduce risk; wait for 2+ pillars to improve

---

## Customization & Troubleshooting

### **If Composite Score Doesn't Change**
- Check that data is loading: Look at "I. MOMENTUM" tab (tables should populate)
- Verify `Dashboard_TAA.xlsx` exists and has sheets: "TR Index", "PE", "OAS", "CDS", "TSY"
- Check browser console (F12) for JavaScript errors

### **If You Want to Change Pillar Weights**
Edit `compute_taa_unified_score()` function (line ~330):
```r
pillars <- list(
  list(pillar = fundamentals, weight = 0.25),  # Change here
  list(pillar = momentum, weight = 0.30),      # Change here
  ...
)
```
Current weights (25/30/15/20) reflect 1–3 month predictive power. Adjust if your investment horizon differs.

### **If You Want to Add a New Indicator**
1. Create a new `compute_*_pillar()` function (follow template)
2. Add it to `taa_composite()` reactive
3. Update weights to sum to 1.0 across all pillars

---

## FAQ

**Q: Why are fundamentals at 25% if they're so important?**  
A: Fundamentals are powerful at *cycle turning points*, but the 1–3 month TAA horizon is shorter. Momentum + sentiment are stronger at this timeframe. Increase fundamentals weight if your horizon is 6–12 months.

**Q: The signal changed overnight. Should I rebalance?**  
A: Not unless **2+ pillars shifted together**. Single-pillar moves are noise. Wait for consensus.

**Q: Why is the Composite Score so sensitive to momentum?**  
A: Momentum gets 30% weight and is calculated daily from price action. Fundamentals/Valuation update monthly. If you want less price-action sensitivity, lower momentum weight to 20% and rebalance.

**Q: How do I validate this framework?**  
A: Run a backtest! Create a simple strategy:
- BUY when Composite > 0 (or > 0.5)
- SELL when Composite < 0 (or < −0.5)
- Compare returns to 60/40 benchmark
- Look at win rate, max drawdown, Sharpe ratio

**Q: What's the next enhancement?**  
A: Add real macro data feeds (ISM, GDP Nowcast, NFCI) to unlock the Fundamentals pillar. Currently it's a placeholder.

---

## Support & Maintenance

**Dashboard Version**: 2.0 (4-Pillar)  
**Last Updated**: April 13, 2026  
**Maintained By**: Investment Management Team  

For questions or bugs, check the code comments:
- Search `# ──` to find section headers
- Search `compute_` to find calculation functions
- Search `output$` to find output definitions

---

**Happy thinkin'! 📊**
