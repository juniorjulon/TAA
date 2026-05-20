# TAA System — Automation & Hardcoding Audit

**Prepared:** May 2026 | **Scope:** Goals 3 and 4 — systematization analysis + chartbook design recommendations

---

## 1. EXECUTIVE SUMMARY

The TAA system has a **well-designed data injection architecture**: the six runtime constants
(`SCORECARD`, `COMPOSITES`, `CB`, `SIG_Z`, `SIG_MATRIX`, `FI_BLUEPRINT`, `EQ_BLUEPRINT`, `AC_LABEL_FULL`, `PW`)
are generated from Excel and injected at runtime by `generate_dashboard.py`. This covers the core data layer.

However, **11 distinct categories of content remain hardcoded** in `docs/model_design.html` that should
be Excel-driven. Most critically, the removed ACs (`em_xchina`, `china_equity`) are still referenced in
two JS arrays, creating an active **display bug**.

---

## 2. WHAT IS CORRECTLY INJECTED (Excel → Python → HTML)

| JS Constant | Source | Injected via |
|---|---|---|
| `SCORECARD` | `results/RUN_*/taa_scorecard.csv` | `generate_dashboard.py` |
| `COMPOSITES` | `results/RUN_*/taa_composite_series.csv` | `generate_dashboard.py` |
| `CB` | `results/chartbook_data.json` | `generate_dashboard.py` |
| `SIG_Z` | `results/signal_z_snapshot.json` | `generate_dashboard.py` |
| `SIG_MATRIX` | `taa_config.xlsx → SignalMapping` | `build_dashboard.py` (marker) |
| `FI_BLUEPRINT` | `taa_config.xlsx → SignalMapping` | `build_dashboard.py` (marker) |
| `EQ_BLUEPRINT` | `taa_config.xlsx → SignalMapping` | `build_dashboard.py` (marker) |
| `AC_LABEL_FULL` | `taa_config.xlsx → AssetClasses` | `build_dashboard.py` (marker) |
| `PW` | `taa_config.xlsx → PillarWeights` | `build_dashboard.py` (marker) |
| `AC_ORDER`, `AC_SHORT` | `taa_config.xlsx → AssetClasses` | `build_dashboard.py` (marker) |
| `ASSET_CLASSES`, `PILLAR_WEIGHTS`, `MAX_TILT_PCT` | `taa_config.xlsx` | `build_dashboard.py → config.py` |

---

## 3. WHAT IS HARDCODED (BUGS AND RISKS)

### 3.1 CRITICAL BUG — Removed ACs still in eqAC array

**File:** `docs/model_design.html` line 1057

```javascript
// CURRENT (WRONG):
const eqAC = ['us_equity','dm_equity','em_equity','em_xchina','china_equity'];

// SHOULD BE:
const eqAC = ['us_equity','dm_equity','em_equity'];
// (em_xchina and china_equity removed as active ACs in May 2026)
```

**Impact:** The composite time series chart for EQ assets attempts to read `COMPOSITES.em_xchina`
and `COMPOSITES.china_equity` — both are `undefined`, causing chart rendering errors (bars missing,
legends showing undefined).

**Fix:** Either:
(a) **Immediate**: manually update `eqAC` to exclude removed ACs, or
(b) **Systematic**: derive `fiAC`/`eqAC` from `AC_LABEL_FULL` and `SCORECARD` groups at runtime (see Section 5).

### 3.2 AC_LABEL Duplicated Twice (Lines 995 and 1075)

`AC_LABEL` is defined identically in two separate JS functions (`buildScorecard()` and `buildHeatmap()`).
It is already available as `AC_LABEL_FULL` (injected from Excel). This is pure duplication.

```javascript
// Duplicated at L995 AND L1075:
const AC_LABEL = {lt_treasuries:'LT Treasuries', lt_us_corp:'LT US Corp', ...};

// Fix: use the injected constant instead:
// AC_LABEL_FULL is already available as a global const from build_dashboard.py
```

### 3.3 AC_LABEL2 (Short Labels) Hardcoded (Line 1060)

```javascript
// HARDCODED:
const AC_LABEL2 = {lt_treasuries:'LT Tsy', lt_us_corp:'LT Corp', lt_em_fi:'LT EM FI', ...};
```

Short labels should come from an `ac_label_short` column in the `AssetClasses` sheet.

### 3.4 fiColors and eqColors Hardcoded (Lines 1058–1059)

```javascript
const fiColors = ['#60A5FA','#14B8A6','#2DD4BF'];       // 3 colors for 3 FI ACs
const eqColors = ['#4ADE80','#F97316','#A855F7','#C084FC','#E879F9'];  // 5 colors (wrong — 3 active EQ)
```

If a new AC is added to FI or EQ, colors must be manually added here. Colors should either:
(a) Come from a `color_hex` column in `AssetClasses` sheet, or
(b) Be auto-assigned by the JS from a color palette based on AC count.

### 3.5 Navigation Items Hardcoded (Lines 731–734)

```html
<a href="#" onclick="nav('cb-fund')" id="nav-cb-fund">I. Fundamentals</a>
<a href="#" onclick="nav('cb-mom')"  id="nav-cb-mom">II. Momentum</a>
<a href="#" onclick="nav('cb-sent')" id="nav-cb-sent">III. Sentiment</a>
<a href="#" onclick="nav('cb-val')"  id="nav-cb-val">IV. Valuation</a>
```

The pillar names and navigation order are hardcoded. They match `PILLAR_ORDER = ("F","M","S","V")`
in `build_dashboard.py`. If a new pillar were added (e.g., "Macro"), the nav bar would need manual update.

**Risk level:** LOW (pillar names are stable), but it is conceptually inconsistent with the
"single source of truth" principle.

### 3.6 Page Descriptions Hardcoded (Lines 797, 808–810)

```html
<div class="page-desc">Four FI asset classes with their specific pillar compositions...</div>
<div class="page-desc">Equity asset classes with sub-class detail. US Equity includes style tilts...</div>
```

These should either come from the `PillarNotes` sheet in Excel or be stable enough to leave as HTML.

**Recommendation:** Accept these as stable design text; add a `// HARDCODED-OK: design text` comment
so future maintainers know this is intentional.

### 3.7 REL_PE_OPTIONS Hardcoded (Lines 2267+)

The Valuation chartbook has a dropdown for relative PE comparisons. The options are hardcoded
JS objects with series IDs. These should be driven by the `DataSeries` sheet.

---

## 4. COMPLETE HARDCODING INVENTORY

| Location | Issue | Severity | Fix Cost |
|---|---|---|---|
| `eqAC` array (L1057) | Includes removed ACs `em_xchina`, `china_equity` | **BUG** | 1 line |
| `AC_LABEL` defined twice (L995, L1075) | Duplicates `AC_LABEL_FULL` (already injected) | HIGH | Replace with `AC_LABEL_FULL` |
| `AC_LABEL2` (L1060) | Short labels not in Excel | MEDIUM | Add column to AssetClasses sheet |
| `fiAC`/`eqAC` arrays (L1056–1057) | Should derive from SCORECARD groups | MEDIUM | Derive from `AC_ORDER` + `SCORECARD` |
| `fiColors`/`eqColors` (L1058–1059) | Must match AC count; wrong count for eqAC | MEDIUM | Add color column to Excel or auto-palette |
| Nav items text (L731–734) | Pillar names hardcoded | LOW | Add to Excel or mark as intentional |
| Page descriptions (L797, 808) | Design text hardcoded | LOW | Mark as intentional |
| `REL_PE_OPTIONS` (L2267) | Valuation dropdown options | LOW | Derive from DataSeries |

---

## 5. RECOMMENDED FIXES (Priority Order)

### Fix 1 — IMMEDIATE: Remove deleted ACs from eqAC (BUG FIX)

In `docs/model_design.html`, change line 1057:
```javascript
// FROM:
const eqAC = ['us_equity','dm_equity','em_equity','em_xchina','china_equity'];

// TO (derive from AC_ORDER which is injected from Excel):
const fiAC = AC_ORDER.filter(ac => SIG_MATRIX.length && 
  SCORECARD.find(r=>r.ac===ac)?.group==='FI');
const eqAC = AC_ORDER.filter(ac => 
  SCORECARD.find(r=>r.ac===ac)?.group==='EQ');
```

This makes `fiAC`/`eqAC` dynamically derived from the injected `SCORECARD` data. Adding or removing
an AC from `AssetClasses` in Excel now automatically updates the time series charts.

### Fix 2 — HIGH: Consolidate AC_LABEL duplicates

Replace both `AC_LABEL = {...}` definitions with `AC_LABEL_FULL` (already injected):
```javascript
// Both occurrences (L995, L1075):
// REMOVE: const AC_LABEL = {...}
// USE: AC_LABEL_FULL[r.ac] instead of AC_LABEL[r.ac]
```

### Fix 3 — MEDIUM: AC colors from Excel

Add a `color_hex` column to the `AssetClasses` sheet in `taa_config.xlsx`. Update `build_dashboard.py`
to include it in `AC_LABEL_FULL`. Then replace hardcoded `fiColors`/`eqColors` with:
```javascript
const fiColors = fiAC.map(ac => AC_COLORS[ac] || '#888');
const eqColors = eqAC.map(ac => AC_COLORS[ac] || '#888');
```

### Fix 4 — MEDIUM: AC_LABEL2 (short labels) from Excel

Add a `label_short` column to `AssetClasses` sheet. Update `build_dashboard.py` to generate
`AC_LABEL_SHORT` alongside `AC_LABEL_FULL`. Reference it in `model_design.html`.

### Fix 5 — LOW: Mark stable hardcoded content

Add comments to intentionally hardcoded items that are genuinely stable design elements:
```html
<!-- HARDCODED-OK: Pillar names are stable by design. Update manually if pillars change. -->
```

---

## 6. HOW TO ADD A NEW ASSET CLASS (Current vs. Target)

### Current process (too many manual steps):

```
1. Edit AssetClasses sheet in taa_config.xlsx (set active=True)
2. Add DataSeries rows for the new AC
3. Add SignalMapping rows for the new AC
4. Run python src/build_dashboard.py   ← updates config.py BUILD blocks
5. MANUALLY edit model_design.html:
   - Add AC key to fiAC or eqAC array (L1056/1057)
   - Add label to AC_LABEL dict (L995)
   - Add label to AC_LABEL2 dict (L1060)
   - Add label to AC_LABEL dict (L1075) — AGAIN
   - Add color to fiColors/eqColors (L1058/1059)
   - Add HTML section for FI or EQ blueprint
6. Run python src/generate_dashboard.py
7. Run python src/main.py
8. Run python src/test_build_layer.py
```

**Risk:** Steps 5a–5e are manual and frequently missed (evidenced by em_xchina still in eqAC).

### Target process (fully Excel-driven):

```
1. Edit AssetClasses sheet in taa_config.xlsx
   - Set active=True, add group (FI/EQ), color_hex, label_short
2. Add DataSeries rows
3. Add SignalMapping rows
4. Run python src/build_dashboard.py
5. Run python src/generate_dashboard.py
6. Run python src/main.py
7. Run python src/test_build_layer.py
```

**Steps 5a–5e become automatic** because `fiAC`/`eqAC` derive from `SCORECARD` groups, labels
come from `AC_LABEL_FULL`, colors come from `AC_COLORS`, and blueprint sections are generated
by `build_dashboard.py`.

---

## 7. HOW TO ADD A NEW SIGNAL SERIES (Current vs. Target)

### Current process (good — mainly Excel-driven):

```
1. If derived: add computation to build_custom_series.py
2. Run python src/build_custom_series.py
3. Edit DataSeries sheet in taa_config.xlsx (add row with series_id, source, transform, window)
4. Edit SignalMapping sheet in taa_config.xlsx (add rows: series_id × AC × pillar × sign × weight)
5. Run python src/build_dashboard.py   ← SIG_MATRIX + BLUEPRINTS regenerated automatically
6. Run python src/main.py
7. Run python src/test_build_layer.py
```

**Assessment:** This process is already Excel-driven. No hardcoded changes needed in Python for
plain-vanilla original series. For new custom/derived series, `build_custom_series.py` needs updating —
this is acceptable since derived series require formula logic.

### Only remaining gap:

For **chartbook display** of a new signal, `chartbook_data.py` must explicitly include it.
This is partly hardcoded (the list of series to export). Should be driven by a
`chartbook_include = True` column in `DataSeries`.

---

## 8. CHARTBOOK DESIGN RECOMMENDATIONS

### 8.1 Design Philosophy

The user's requirements for each chartbook section:

| Section | Primary View | Optional View | Extra |
|---|---|---|---|
| I. Fundamentals | **Raw series values** | Z-score overlay | N/A |
| II. Momentum | **Composite z-score** | Sub-metrics (RSI, MA, returns) | Price overlay (cumulative return) |
| III. Sentiment | **Raw series values** | Z-score overlay | N/A |
| IV. Valuation | **Raw series values** | Z-score overlay | Percentile bars (historical position) |

### 8.2 Chart Component Specifications

#### Fundamentals & Sentiment — Raw Value + Z-Score Toggle

```
Chart card structure:
  ┌─────────────────────────────────────────────────────────┐
  │ REGION  │  Series Name             │ Value: [12.3]  │
  │ Latest z-score: +1.4               │ Trend: ↑       │
  ├─────────────────────────────────────────────────────────┤
  │                                                         │
  │  [Raw Value View]  [Z-Score View]  ← TOGGLE PILLS      │
  │                                                         │
  │  Line chart: raw series value (e.g. PMI = 52.3)         │
  │  OR z-score time series (e.g. ewma_z = +0.44)          │
  │                                                         │
  │  Timeframe: [3M] [1Y] [3Y] [MAX*]                      │
  │  *MAX is default active                                  │
  └─────────────────────────────────────────────────────────┘
  Footer: Latest: 52.3 | Trend: +0.4 vs prev | Z: +0.44
```

**Key design note:** The raw value y-axis should always include the **threshold line** where
relevant (PMI: dotted line at 50; ISM New Orders/Inventories: dotted line at 1.0). In z-score
view, add ±1σ and ±2σ bands.

#### Valuation — Raw Value + Z-Score + Percentile Bars

```
Chart card structure:
  ┌─────────────────────────────────────────────────────────┐
  │ REGION  │  OAS HY Spread           │ 387 bps  │
  ├─────────────────────────────────────────────────────────┤
  │  Historical Percentile:  ████████░░  35th pctile (5Y)  │
  │  ┤25th                              ┤75th               │
  ├─────────────────────────────────────────────────────────┤
  │  [Raw Value] [Z-Score] [Percentile]  ← 3 VIEW PILLS    │
  │                                                         │
  │  Chart: spreads (bps), or z-score, or pctile [0-100]   │
  │                                                         │
  │  Timeframe: [3M] [1Y] [3Y] [MAX*]                      │
  └─────────────────────────────────────────────────────────┘
  Footer: Latest: 387bps | 5Y pctile: 35th | Z (ewma): -0.6
```

The **percentile position bar** (a horizontal progress bar with markers at 25th and 75th
percentiles) should appear above ALL valuation charts, not just the current subset. The bar
represents where today's value sits in its 5Y or 10Y history.

#### Momentum — Composite Z-Score + Sub-Metrics Toggle

```
Chart card structure:
  ┌─────────────────────────────────────────────────────────┐
  │ REGION  │  Asset Name Momentum     │ Z: +1.2  │
  ├─────────────────────────────────────────────────────────┤
  │  [Composite Z] [12-1M] [3M] [MA] [RSI]  ← SUB-METRICS │
  ├─────────────────────────────────────────────────────────┤
  │                                                         │
  │  Primary: Composite momentum z-score (line)             │
  │  Secondary (optional): Cumulative % price return (area) │
  │                        Grey area chart on right Y-axis  │
  │                                                         │
  │  Timeframe: [3M] [1Y] [3Y] [MAX*]                      │
  └─────────────────────────────────────────────────────────┘
  Footer: Latest z: +1.2 | 12-1M: +1.8 | 3M: +0.7 | RSI: +0.3
```

When a sub-metric pill is selected (e.g. "RSI"), the chart switches to show that specific
momentum component's z-score, allowing drill-down into momentum drivers.

### 8.3 Technical Implementation Approach

All four chart types share a common card structure:
- **Data source:** `CB` object (injected from `chartbook_data.json`)
- **Toggle state:** Managed via JS `data-view` attribute on the card container
- **Color:** Primary signal color comes from pillar CSS variable (`--pf`, `--pm`, `--ps`, `--pv`)
- **Z-score bands:** ±1σ (dotted, light) and ±2σ (dashed, medium) drawn as CSS-styled pseudo-elements

HTML examples are in `docs/chartbook_examples/` (see files below).

---

## 9. GOAL 4: FULLY EXCEL-DRIVEN SYSTEM — COMPLETE CHANGE LIST

### 9.1 What Must Stay in Python (formula logic, not config)

| Component | Why it stays in Python |
|---|---|
| `build_custom_series.py` formulas | GDP blends, ERP computation, PE scores require mathematical logic |
| `signals.py` transform functions | ewma_z, rolling_z, pctile, price_mom are algorithmic implementations |
| `scoring.py` conviction/tilt logic | The 35/65 blend, agreement multiplier are behavioral rules |
| `portfolio.py` zero-sum constraint | Force-zero-sum enforcement is algorithmic |
| Chart rendering JS in model_design.html | Layout/visual design is not data |

### 9.2 What Should Move to Excel (currently hardcoded in Python or HTML)

| Item | Current location | Target: Excel column |
|---|---|---|
| AC group (FI/EQ) | `config.py:ASSET_CLASS_GROUPS` (BUILD) | `AssetClasses.group` ← already there |
| AC color hex | `model_design.html` (hardcoded JS) | `AssetClasses.color_hex` — ADD |
| AC short label | `model_design.html:AC_LABEL2` | `AssetClasses.label_short` — ADD |
| AC display order | `model_design.html:AC_ORDER` (BUILD) | `AssetClasses.sort_order` — ADD |
| fiAC/eqAC arrays | `model_design.html` (hardcoded) | Derive from `AssetClasses.group` at runtime |
| Chartbook series list | `chartbook_data.py` (hardcoded list) | `DataSeries.chartbook_include` — ADD |
| Signal display name | `SIG_MATRIX` (from SignalMapping.display_name) | `SignalMapping.display_name` ← may already exist |
| Pillar description | `PillarNotes` sheet | `PillarNotes.note` ← already there |

### 9.3 Required Excel Schema Changes

#### AssetClasses sheet — add 3 columns:

| New column | Type | Example |
|---|---|---|
| `color_hex` | String | `#60A5FA` |
| `label_short` | String | `LT Tsy` |
| `sort_order` | Integer | `1` (FI first, then EQ) |

#### DataSeries sheet — add 1 column:

| New column | Type | Example |
|---|---|---|
| `chartbook_include` | Boolean | `True` |

This column controls which series appear in `chartbook_data.json` (currently hardcoded in `chartbook_data.py`).

### 9.4 Required Code Changes

#### `build_dashboard.py` — 2 additions:

1. Add `color_hex` and `label_short` to the `AC_META` render output (already renders `AC_ORDER` and `AC_SHORT`).
2. Generate `AC_COLORS` const alongside `AC_LABEL_FULL`.

#### `chartbook_data.py` — 1 change:

Read `DataSeries.chartbook_include = True` to build the export list dynamically, instead of the
current hardcoded list of series IDs.

#### `model_design.html` — 4 changes:

1. Replace `eqAC` definition with runtime derivation from `SCORECARD`:
   ```javascript
   const fiAC = AC_ORDER.filter(ac => SCORECARD.find(r=>r.ac===ac)?.group==='FI');
   const eqAC = AC_ORDER.filter(ac => SCORECARD.find(r=>r.ac===ac)?.group==='EQ');
   ```

2. Replace both `AC_LABEL = {...}` with `AC_LABEL_FULL`.

3. Replace `AC_LABEL2 = {...}` with `AC_LABEL_SHORT` (generated from Excel).

4. Replace `fiColors`/`eqColors` arrays with:
   ```javascript
   const fiColors = fiAC.map(ac => AC_COLORS[ac] || '#888');
   const eqColors = eqAC.map(ac => AC_COLORS[ac] || '#888');
   ```

### 9.5 Priority Implementation Order

| Priority | Change | Effort | Risk |
|---|---|---|---|
| **P0 — BUG** | Fix `eqAC` to exclude em_xchina/china_equity | 1 line | None |
| **P1 — HIGH** | Derive fiAC/eqAC from SCORECARD groups | 3 lines | Low |
| **P1 — HIGH** | Replace duplicate AC_LABEL with AC_LABEL_FULL | 2 replacements | Low |
| **P2 — MEDIUM** | Add color_hex + label_short columns to Excel | 2 columns | Low |
| **P2 — MEDIUM** | Generate AC_COLORS in build_dashboard.py | ~20 lines | Low |
| **P3 — LOW** | Add chartbook_include column to DataSeries | 1 column | Low |
| **P3 — LOW** | Update chartbook_data.py to read chartbook_include | ~10 lines | Low |

---

## 10. VERIFICATION CHECKLIST

After implementing the above changes, verify the "fully Excel-driven" state with:

```bash
# 1. Change an AC label in AssetClasses → verify index.html updates
# 2. Set em_xchina active=False → verify it disappears from fiAC/eqAC arrays
# 3. Add a new AC to AssetClasses → verify it appears in composite chart WITHOUT editing model_design.html
# 4. Change pillar weights in PillarWeights → verify PW const updates in index.html
# 5. Add chartbook_include=True to a new series → verify it appears in chartbook
python src/build_dashboard.py
python src/main.py
python src/test_build_layer.py   # 29/29 PASS
python src/chartbook_data.py
python src/generate_dashboard.py
# Open index.html and verify all sections render correctly
```

---

*Document generated: May 2026. Update after any structural changes to the pipeline.*
