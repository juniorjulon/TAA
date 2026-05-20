# TAA Project — Complete Flow Diagram & File Inventory

---

## 1. SYSTEM FLOW DIAGRAM

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                        INPUTS (User-maintained)                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  data/Dashboard_TAA_Inputs.xlsx  ←── Weekly download from Bloomberg/FRED   ║
║  │  Sheets: OAS, H4, H5, H6, H1, H2, H3, H7, AAII                         ║
║  │                                                                          ║
║  config/taa_config.xlsx          ←── Maintained by analyst (signal config) ║
║  │  Sheets: AssetClasses, DataSeries, PillarWeights, SignalMapping,         ║
║  │          PillarNotes, TransformCodes, MomentumConfig                     ║
║  │                                                                          ║
║  config/portfolios.xlsx          ←── Maintained by analyst (4 portfolios)  ║
║     Sheets: Portfolios (SAA weights, TE budgets, force_zero_sum)            ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                     STEP 1: BUILD CUSTOM SERIES                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  src/build_custom_series.py                                                  ║
║  │  Reads: Dashboard_TAA_Inputs.xlsx                                         ║
║  │  Uses:  src/signals.py (pe_score, erp, cdx functions)                    ║
║  │  Uses:  src/data_loader.py (load_all sheets)                             ║
║  └─→ data/custom_series.xlsx  (41 derived series)                           ║
║       PMI composites, GDP blends, ERP, PE scores, OAS stress,               ║
║       CDX momentum, EPS revision, modern_ted, term_spread                   ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                     STEP 2: MAIN PIPELINE (main.py)                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  src/main.py                                                                 ║
║  │  Reads: Dashboard_TAA_Inputs.xlsx                                         ║
║  │  Reads: data/custom_series.xlsx                                           ║
║  │  Reads: config/taa_config.xlsx  (DataSeries + SignalMapping)             ║
║  │  Reads: config/portfolios.xlsx                                            ║
║  │                                                                          ║
║  │  ┌── src/signal_engine.py  (SignalEngine.load_all)                       ║
║  │  │    Reads taa_config.xlsx DataSeries (170 rows)                        ║
║  │  │    Applies 6 transforms → {series_id: z-score Series}                 ║
║  │  │    Uses: src/signals.py (ewma_zscore, rolling_zscore, etc.)           ║
║  │  │    Uses: src/data_loader.py (load_raw_sheet)                          ║
║  │  │                                                                       ║
║  │  ├── src/pillars.py  (build_all_pillars)                                  ║
║  │  │    Reads SignalMapping from taa_config.xlsx                           ║
║  │  │    Applies sign × weight per (AC, pillar)                             ║
║  │  │    Calls standardise_pillar() → re-standardised pillar z-scores       ║
║  │  │                                                                       ║
║  │  ├── src/scoring.py  (composite_score, score_snapshot)                   ║
║  │  │    Combines 4 pillar z-scores with PILLAR_WEIGHTS                     ║
║  │  │    Applies 35% abs + 65% relative blend                               ║
║  │  │    Maps to conviction → tilt fraction                                  ║
║  │  │                                                                       ║
║  │  ├── src/hierarchical_scoring.py  (HierarchicalViews.enrich)             ║
║  │  │    L1 aggregate z per bucket (lt_fi_aggregate synthetic)              ║
║  │  │    L2 = z_child − z_parent (zero-sum within bucket)                   ║
║  │  │                                                                       ║
║  │  ├── src/portfolio.py  (build_multi_portfolio_report)                    ║
║  │  │    Applies house view to each of 4 portfolios                        ║
║  │  │    Scales tilts by TE budget                                           ║
║  │  │    Enforces force_zero_sum + no-short constraint                       ║
║  │  │                                                                       ║
║  │  └── src/proxies.py  (fallback signals when engine has gaps)             ║
║  │                                                                          ║
║  └─→ results/RUN_YYYYMMDD_HHMMSS/                                           ║
║        taa_scorecard.csv           (z-scores + tilts per AC)                ║
║        taa_composite_series.csv    (full composite z history)               ║
║        pillars_{ac}.csv            (pillar z-score history, ×6 ACs)        ║
║        taa_hierarchy_scorecard.csv (L1/L2 z-scores and tilts)              ║
║        taa_bucket_summary.csv      (compact bucket summary)                 ║
║        multi_portfolio_views.xlsx  (4 portfolios × tilts)                   ║
║        signal_z_snapshot.json      (current z per series_id)                ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                     STEP 3: HEALTH CHECK                                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  src/test_build_layer.py                                                     ║
║  │  Reads: config/taa_config.xlsx, src/config.py                            ║
║  └─→ stdout: "29/29 PASS" or FAIL with diagnostics                          ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                     STEP 4: DASHBOARD GENERATION                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  src/chartbook_data.py                                                       ║
║  │  Reads: results/RUN_latest/taa_scorecard.csv                             ║
║  │  Reads: data/Dashboard_TAA_Inputs.xlsx  (raw series for chartbook)       ║
║  │  Reads: data/custom_series.xlsx                                           ║
║  └─→ results/chartbook_data.json   (all signal time series + PMI heatmap)   ║
║                                                                              ║
║  src/build_dashboard.py                                                      ║
║  │  Reads: config/taa_config.xlsx                                            ║
║  │  Generates JS blocks: SIG_MATRIX, AC_ORDER, FI/EQ_BLUEPRINT,            ║
║  │                        AC_LABEL_FULL, PW                                  ║
║  ├─→ src/config.py  (BUILD blocks: ASSET_CLASSES, PILLAR_WEIGHTS, MAX_TILT) ║
║  └─→ [also called inline by generate_dashboard.py]                          ║
║                                                                              ║
║  src/generate_dashboard.py                                                   ║
║  │  Reads: index.html  (source and output — updated in-place)               ║
║  │  Reads: results/RUN_latest/taa_scorecard.csv                             ║
║  │  Reads: results/RUN_latest/taa_composite_series.csv                      ║
║  │  Reads: results/chartbook_data.json                                       ║
║  │  Reads: results/signal_z_snapshot.json                                   ║
║  │  Calls: build_dashboard.py functions (inline methodology override)       ║
║  └─→ index.html  (updated in-place with live data)                          ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                     STEP 5: CONFIG PROPAGATION (when Excel changes)         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  src/build_dashboard.py                                                      ║
║  │  (same script, standalone run)                                            ║
║  ├─→ src/config.py  (ASSET_CLASSES, PILLAR_WEIGHTS, MAX_TILT_PCT BUILD blocks) ║
║  └─→ [does NOT update index.html — that's generate_dashboard.py]            ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

OUTPUT (end product):
  index.html   ← Single-file dashboard. Open in browser.
```

---

## 2. FILE INVENTORY — Active Pipeline Files

### Core Python Source (`src/`)

| File | Role | Called by | Critical? |
|---|---|---|---|
| `src/main.py` | Pipeline entry point | User | ✅ YES |
| `src/config.py` | All constants + ASSET_CLASSES, PILLAR_WEIGHTS | Every module | ✅ YES |
| `src/data_loader.py` | Loads 9 Excel sheets | main.py, build_custom_series | ✅ YES |
| `src/signals.py` | Atomic z-score primitives (ewma_z, rolling_z, etc.) | signal_engine, pillars, build_custom_series | ✅ YES |
| `src/signal_engine.py` | Generic signal loader (DataSeries → z-scores) | main.py | ✅ YES |
| `src/pillars.py` | Pillar construction (build_all_pillars + legacy) | main.py | ✅ YES |
| `src/scoring.py` | Composite → conviction → tilt | main.py | ✅ YES |
| `src/hierarchical_scoring.py` | L1/L2 hierarchy | main.py | ✅ YES |
| `src/portfolio.py` | Multi-portfolio TE-scaled tilts | main.py | ✅ YES |
| `src/proxies.py` | Fallback signals for gaps | main.py | ✅ YES |
| `src/build_custom_series.py` | 41 derived series computation | User (Step 1) | ✅ YES |
| `src/chartbook_data.py` | Exports chartbook_data.json | User (Step 4) | ✅ YES |
| `src/build_dashboard.py` | JS code generation from Excel | generate_dashboard.py, User | ✅ YES |
| `src/generate_dashboard.py` | Injects data into index.html | User (Step 4) | ✅ YES |
| `src/test_build_layer.py` | 29-check health test | User (Step 3) | ✅ YES |

### Config Files

| File | Role | Critical? |
|---|---|---|
| `config/taa_config.xlsx` | SINGLE SOURCE OF TRUTH: signals, weights, mappings | ✅ YES |
| `config/portfolios.xlsx` | 4 Rimac portfolios: SAA weights + TE budgets | ✅ YES |

### Data Files

| File | Role | Critical? |
|---|---|---|
| `data/Dashboard_TAA_Inputs.xlsx` | Primary market data (9 sheets, weekly refresh) | ✅ YES |
| `data/custom_series.xlsx` | 41 derived series (regenerated by build_custom_series.py) | ✅ YES (auto-generated) |

### Output Files

| File | Role | Critical? |
|---|---|---|
| `index.html` | THE dashboard — single standalone file | ✅ YES (output) |
| `results/RUN_*/taa_scorecard.csv` | Scorecard per run | ✅ YES (needed by generate_dashboard.py) |
| `results/RUN_*/taa_composite_series.csv` | Composite history per run | ✅ YES |
| `results/RUN_*/multi_portfolio_views.xlsx` | Per-portfolio tilts | ✅ YES (currently not in dashboard) |
| `results/chartbook_data.json` | Chartbook time series | ✅ YES |
| `results/signal_z_snapshot.json` | Latest z per signal | ✅ YES |

---

## 3. FILE INVENTORY — ORPHAN / UNUSED FILES

These files are **NOT read by any pipeline script**. They can be moved to `docs/archive/` or deleted.

### Source scripts that are NOT in the pipeline (`src/`)

| File | What it is | Status |
|---|---|---|
| `src/add_new_signals.py` | Template for batch-adding signals | 🗂 UTILITY — keep in `src/tools/` |
| `src/rebuild_signal_mapping.py` | One-time disaster recovery tool | 🗂 UTILITY — keep in `src/tools/` |
| `src/extend_taa_config.py` | One-time config extension tool | 🗂 UTILITY — keep in `src/tools/` |
| `src/seed_taa_config.py` | One-time config seed tool | 🗂 UTILITY — keep in `src/tools/` |
| `src/generate_methodology_doc.py` | Generates Word methodology doc | 🗂 UTILITY — keep but not weekly |

### ROOT-level orphan files

| File | What it is | Recommended action |
|---|---|---|
| `dashboard.html` | Old/legacy dashboard version | 🗑 DELETE or ARCHIVE |
| `Formato de gráficos.pptx` | Chart format reference (Spanish) | 🗂 MOVE → `docs/reference/` |
| `Pormpt.txt` | Typo'd prompt file | 🗑 DELETE |
| `.Rhistory` | R language history (not used) | 🗑 DELETE |
| `Dashboard TAA - Guidelines.docx` | Older guideline document | 🗂 MOVE → `docs/reference/` |
| `don't read` (folder) | Legacy/scratch | 🗑 DELETE (check contents first) |
| `backup oldest version` (folder) | Old backups | 🗑 DELETE (verify not needed) |
| `research/` (folder) | PDF paper references | 🗂 KEEP — academic references |
| `skills-lock.json` | Claude agent skill lock | ⚙️ SYSTEM — keep, don't touch |

### Docs folder orphans

| File | What it is | Recommended action |
|---|---|---|
| `docs/model_design.html` | Design reference only (not in pipeline) | 🗂 MOVE → `docs/reference/` |
| `docs/Detalle Ports.xlsx` | Old portfolio detail file | 🗂 CHECK if superseded by portfolios.xlsx |
| `docs/Other Inputs for TAA.xlsx` | Research inputs | 🗂 MOVE → `docs/reference/` |
| `docs/TAA_Dashboard.html` | Old dashboard version | 🗑 DELETE (superseded by index.html) |
| `docs/TAA_Scorecard_Views.html` | Old scorecard view | 🗑 DELETE or ARCHIVE |
| `docs/TAA_Signal_Methodology.html` | Old methodology HTML | 🗑 DELETE or ARCHIVE |
| `docs/chart_example.html` | Chart design reference | 🗂 MOVE → `docs/reference/` |
| `docs/taa_dashboard_charts_example.html` | Chart examples | 🗂 MOVE → `docs/reference/` |
| `docs/build_ic_deck.js` | Old JS script for deck building | 🗑 DELETE |
| `docs/TAA Signal Generation v1.0.md` | Old v1 methodology | 🗂 MOVE → `docs/archive/` |
| `docs/TAA Methology Local.docx` | Old local methodology doc | 🗂 MOVE → `docs/archive/` |
| `docs/create_improvement_doc.py` | One-time script to create Word doc | 🗑 DELETE after use |
| `docs/create_next_steps.py` | One-time script to create PPTX | 🗑 DELETE after use |
| `docs/create_transform_slides.py` | One-time script to create PPTX | 🗑 DELETE after use |
| `docs/~$A_Presentation_Improvements.docx` | Word temp file | 🗑 DELETE (Office lock file) |
| `docs/~$shboard TAA - Guidelines.docx` | Word temp file | 🗑 DELETE (Office lock file) |
| `docs/Fixed Income Momentum Metrics.md` | Research note | 🗂 KEEP in docs/ (reference) |
| `docs/Fixed-Income-Momentum-Metrics.html` | Same content as above (HTML) | 🗑 DELETE duplicate |

### Data folder orphans

| File | What it is | Recommended action |
|---|---|---|
| `data/Help_Inputs.xlsx` | Helper/reference inputs | 🗂 CHECK if still needed |
| `data/TAA System Economic Rationale.xlsx` | Research document | 🗂 MOVE → `docs/reference/` |

---

## 4. RECOMMENDED FOLDER STRUCTURE (Target State)

```
TAA/
├── config/                          ← INPUTS (Excel-driven config)
│   ├── taa_config.xlsx              ← Single source of truth
│   └── portfolios.xlsx              ← 4 Rimac portfolios
│
├── data/                            ← INPUTS (market data)
│   ├── Dashboard_TAA_Inputs.xlsx    ← Weekly refresh
│   └── custom_series.xlsx           ← Auto-generated (never edit)
│
├── src/                             ← PIPELINE (weekly run)
│   ├── main.py                      ← Entry point
│   ├── config.py                    ← Auto-generated BUILD blocks
│   ├── data_loader.py
│   ├── signals.py
│   ├── signal_engine.py
│   ├── pillars.py
│   ├── scoring.py
│   ├── hierarchical_scoring.py
│   ├── portfolio.py
│   ├── proxies.py
│   ├── build_custom_series.py
│   ├── chartbook_data.py
│   ├── build_dashboard.py
│   ├── generate_dashboard.py
│   ├── test_build_layer.py
│   └── tools/                       ← ONE-TIME / MAINTENANCE scripts
│       ├── add_new_signals.py
│       ├── rebuild_signal_mapping.py
│       ├── extend_taa_config.py
│       ├── seed_taa_config.py
│       └── generate_methodology_doc.py
│
├── results/                         ← OUTPUTS (auto-generated)
│   ├── RUN_YYYYMMDD_HHMMSS/         ← Latest run (keep last 3)
│   ├── chartbook_data.json          ← Latest chartbook
│   └── signal_z_snapshot.json       ← Latest signal z-scores
│
├── docs/                            ← DOCUMENTATION
│   ├── TAA_Methodology.md           ← Living methodology reference
│   ├── data_quality.md              ← Data quality rules
│   ├── signal_improvements.md       ← Signal roadmap
│   ├── economic_sanity_methodology.md  ← Sanity check rules
│   ├── transform_generalization_analysis.md
│   ├── portfolio_dashboard_analysis.md
│   ├── system_automation_analysis.md
│   ├── sanity_check_report.md
│   ├── chartbook_examples/          ← Chart design examples
│   ├── reference/                   ← Non-pipeline reference files
│   │   ├── model_design.html
│   │   ├── chart_example.html
│   │   ├── Formato de gráficos.pptx
│   │   └── Dashboard TAA - Guidelines.docx
│   └── archive/                     ← Old versions, superseded
│       ├── TAA Signal Generation v1.0.md
│       ├── TAA Methology Local.docx
│       └── TAA_Dashboard.html
│
├── presentations/                   ← SLIDE DECKS (separate from docs)
│   ├── TAA_IC_Presentation.pptx     ← Main IC deck
│   ├── TAA_Transform_Explanation.pptx
│   └── TAA_Next_Steps.pptx
│
├── research/                        ← ACADEMIC PAPERS
│   └── *.pdf
│
├── index.html                       ← THE DASHBOARD (output + source)
├── CLAUDE.md                        ← Claude Code instructions
└── requirements.txt                 ← Python dependencies
```

---

## 5. FILES TO DELETE (Safe to Remove)

```bash
# Office temp files (always safe)
del "docs\~$A_Presentation_Improvements.docx"
del "docs\~$shboard TAA - Guidelines.docx"

# Clearly obsolete files
del "docs\TAA_Dashboard.html"           # superseded by index.html
del "docs\TAA_Scorecard_Views.html"     # prototype
del "docs\TAA_Signal_Methodology.html"  # prototype
del "docs\Fixed-Income-Momentum-Metrics.html"  # duplicate of .md
del "docs\build_ic_deck.js"             # unused JS script
del "dashboard.html"                    # old root dashboard
del "Pormpt.txt"                        # scratch file
del ".Rhistory"                         # R artifact

# One-time scripts already completed (keep originals in git if needed)
del "docs\create_improvement_doc.py"
del "docs\create_next_steps.py"
del "docs\create_transform_slides.py"
```

---

## 6. KEY INSIGHT: What the Weekly Pipeline Actually Touches

Every Monday, the minimum set of files that MUST be updated/run:

```
1. data/Dashboard_TAA_Inputs.xlsx         ← USER UPDATES (Bloomberg download)
2. python src/build_custom_series.py      ← touches: data/custom_series.xlsx
3. python src/main.py                     ← touches: results/RUN_*/
4. python src/test_build_layer.py         ← read-only check
5. python src/chartbook_data.py           ← touches: results/chartbook_data.json
6. python src/generate_dashboard.py       ← touches: index.html

When taa_config.xlsx changes (add signal, change weight):
   python src/build_dashboard.py          ← touches: src/config.py
```

Everything else (`portfolios.xlsx`, `config.py` BUILD blocks, all docs) only changes when you explicitly modify the system — not on weekly data refreshes.
