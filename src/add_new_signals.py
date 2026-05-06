"""
src/add_new_signals.py
======================
Adds three new signal groups to config/taa_config.xlsx:

1. SKEW Index (original, H5):
   - S pillar: contrarian tail-risk signal for equities; safe-haven for LT Treasuries
2. ISM New Orders / Inventories ratio (original, H1):
   - F pillar: leading indicator for US growth (ratio > 1 = expanding)
3. EPS Revision Composites (custom, 3M+6M weighted):
   - F pillar: replaces shallow 21-day EPS revision with multi-horizon composite

Run once:
  python src/add_new_signals.py
"""

import os, sys, warnings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings("ignore")

from openpyxl import load_workbook
from config import CONFIG_XLSX

XLSX = CONFIG_XLSX

# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_sheet_headers(ws):
    rows = list(ws.values)
    return [str(h).strip() if h is not None else f"col_{i}"
            for i, h in enumerate(rows[0])] if rows else []

def _existing_ids(ws, id_col_idx=0):
    rows = list(ws.values)
    return {str(r[id_col_idx]).strip() for r in rows[1:] if r and r[id_col_idx]}


# ── New DataSeries rows ───────────────────────────────────────────────────────

# Format: (series_id, signal_name, ticker, source, frequency, pillar,
#           transformation, window, notes,
#           series_type, input_sheet, input_column, transform_code)

NEW_DS_ROWS = [
    # SKEW Index — tail-risk sentiment
    ("skew_z", "CBOE SKEW Index", "SKEW Index", "Bloomberg", "daily", "Sentiment",
     "EWMA z-score", "252*3", "High SKEW = institutional tail hedging; contrarian signal",
     "original", "H5", "SKEW Index", "ewma_z"),

    # ISM New Orders / Inventories ratio — leading growth indicator
    ("ism_no_inv", "ISM New Orders/Inventories", ".ISM G Index", "Bloomberg", "monthly", "Fundamentals",
     "EWMA z-score", "252", "Ratio > 1 = demand expanding faster than supply; leading ~3-6M",
     "original", "H1", ".ISM G Index", "ewma_z"),

    # EPS Revision Composites — multi-horizon (Chan/Jegadeesh/Lakonishok 1996)
    ("eps_rev_us", "US EPS Revision Composite (3M+6M)", "custom", "custom", "daily", "Fundamentals",
     "EWMA z-score", "252", "40%×pct_change(3M) + 60%×pct_change(6M); stronger signal than 1M alone",
     "custom", "custom_series", "eps_rev_us", "ewma_z"),

    ("eps_rev_em", "EM EPS Revision Composite (3M+6M)", "custom", "custom", "daily", "Fundamentals",
     "EWMA z-score", "252", "40%×pct_change(3M) + 60%×pct_change(6M)",
     "custom", "custom_series", "eps_rev_em", "ewma_z"),

    ("eps_rev_eafe", "EAFE EPS Revision Composite (3M+6M)", "custom", "custom", "daily", "Fundamentals",
     "EWMA z-score", "252", "40%×pct_change(3M) + 60%×pct_change(6M)",
     "custom", "custom_series", "eps_rev_eafe", "ewma_z"),

    ("eps_rev_china", "China EPS Revision Composite (3M+6M)", "custom", "custom", "daily", "Fundamentals",
     "EWMA z-score", "252", "40%×pct_change(3M) + 60%×pct_change(6M)",
     "custom", "custom_series", "eps_rev_china", "ewma_z"),
]


# ── New SignalMapping rows ────────────────────────────────────────────────────

# Format: (ac_id, series_id, pillar, sign, weight_in_pillar, description)
def _sm(ac, sid, pillar, sign, weight, desc=""):
    return (ac, sid, pillar, sign, weight, desc)

NEW_SM_ROWS = [
    # ── SKEW ─────────────────────────────────────────────────────────────────
    # High SKEW = tail-risk hedging = equity caution (contrarian: eventual reversal)
    _sm("us_equity",   "skew_z", "S", -1, 0.10, "High SKEW = institutional hedging = near-term equity headwind"),
    _sm("us_growth",   "skew_z", "S", -1, 0.10, "Growth more sensitive to tail-risk shifts"),
    _sm("us_value",    "skew_z", "S", -1, 0.08, "Value less sensitive to SKEW"),
    _sm("dm_equity",   "skew_z", "S", -1, 0.08, "DM equity: SKEW captures US systemic risk"),
    # High SKEW = flight-to-quality positive for Treasuries
    _sm("lt_treasuries", "skew_z", "S", +1, 0.10, "High SKEW = safe-haven demand for duration"),

    # ── ISM New Orders / Inventories ratio ────────────────────────────────────
    _sm("us_equity",   "ism_no_inv", "F", +1, 0.10, "NO/INV > 1 = demand expanding = bullish equity"),
    _sm("us_growth",   "ism_no_inv", "F", +1, 0.10, "Growth most sensitive to demand expansion"),
    _sm("us_value",    "ism_no_inv", "F", +1, 0.08, "Value benefits from demand cycle"),
    _sm("lt_us_corp",  "ism_no_inv", "F", +1, 0.10, "Demand expansion = tighter spreads"),
    _sm("lt_treasuries", "ism_no_inv", "F", -1, 0.08, "Demand up = rates rise = duration headwind"),
    _sm("short_term_fi", "ism_no_inv", "F", -1, 0.08, "Demand up = rates higher = STFI headwind (mild)"),

    # ── EPS Revision Composite (replaces weight from existing eps_* signals) ──
    # US Equity family
    _sm("us_equity",   "eps_rev_us", "F", +1, 0.15, "Multi-horizon EPS revision; stronger signal than 1M alone"),
    _sm("us_growth",   "eps_rev_us", "F", +1, 0.15, "Growth premium linked to EPS revision momentum"),
    _sm("us_value",    "eps_rev_us", "F", +1, 0.12, "Value: EPS revisions confirm fundamental recovery"),
    _sm("lt_us_corp",  "eps_rev_us", "F", +1, 0.12, "Corporate earnings → spread tightening"),
    # DM Equity
    _sm("dm_equity",   "eps_rev_eafe", "F", +1, 0.10, "EAFE EPS revision momentum"),
    # EM family
    _sm("em_equity",   "eps_rev_em", "F", +1, 0.12, "EM EPS revision composite"),
    _sm("em_xchina",   "eps_rev_em", "F", +1, 0.12, "EM ex-China: EM-wide EPS revision"),
    _sm("lt_em_fi",    "eps_rev_em", "F", +1, 0.12, "EM EPS → EM credit spread signal"),
    # China
    _sm("china_equity", "eps_rev_china", "F", +1, 0.15, "China EPS revision composite"),
]


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    wb = load_workbook(XLSX)

    # ── DataSeries ────────────────────────────────────────────────────────────
    ws_ds = wb["DataSeries"]
    ds_headers = _get_sheet_headers(ws_ds)
    existing_ds = _existing_ids(ws_ds, id_col_idx=0)

    # Find column indices for the 4 new executable columns
    idx_type   = ds_headers.index("series_type")   if "series_type"   in ds_headers else None
    idx_sheet  = ds_headers.index("input_sheet")   if "input_sheet"   in ds_headers else None
    idx_col    = ds_headers.index("input_column")  if "input_column"  in ds_headers else None
    idx_trans  = ds_headers.index("transform_code") if "transform_code" in ds_headers else None

    added_ds = 0
    for row in NEW_DS_ROWS:
        sid = row[0]
        if sid in existing_ds:
            print(f"  DataSeries: SKIP (exists) {sid}")
            continue
        # Build the full row matching header length
        base = list(row[:9])                        # first 9 fields
        full = base + [""] * (len(ds_headers) - 9)  # pad to header width
        # Fill executable columns if indices known
        if idx_type  is not None: full[idx_type]  = row[9]
        if idx_sheet is not None: full[idx_sheet] = row[10]
        if idx_col   is not None: full[idx_col]   = row[11]
        if idx_trans is not None: full[idx_trans] = row[12]
        ws_ds.append(full)
        added_ds += 1
        print(f"  DataSeries: ADD {sid}")

    # ── SignalMapping ─────────────────────────────────────────────────────────
    ws_sm = wb["SignalMapping"]
    sm_headers = _get_sheet_headers(ws_sm)
    existing_sm_keys = set()
    for r in list(ws_sm.values)[1:]:
        if r and r[0]:
            key = f"{str(r[0]).strip()}|{str(r[1]).strip()}|{str(r[2]).strip()}"
            existing_sm_keys.add(key)

    added_sm = 0
    for (ac, sid, pillar, sign, weight, desc) in NEW_SM_ROWS:
        key = f"{ac}|{sid}|{pillar}"
        if key in existing_sm_keys:
            print(f"  SignalMapping: SKIP {key}")
            continue
        ws_sm.append([ac, sid, pillar, sign, weight, desc])
        added_sm += 1
        print(f"  SignalMapping: ADD {key}")

    wb.save(XLSX)
    print(f"\nDone: added {added_ds} DataSeries rows, {added_sm} SignalMapping rows -> {XLSX}")


if __name__ == "__main__":
    main()
