"""
src/chartbook_data.py
=====================
Extracts signal-level time series from the TAA pipeline and exports
them as a single JSON file for use by dashboard.html.

Outputs raw values (PMI levels, P/E ratios, VIX, OAS in basis points,
etc.) alongside z-scores and percentile ranks so the chartbook can
display actual market data with context bands.

Run from project root:
  python src/chartbook_data.py

Output:
  results/chartbook_data.json
"""

import os
import sys
import json
import warnings
import numpy as np
import pandas as pd
from datetime import datetime

warnings.filterwarnings("ignore")
_SRC = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SRC)
sys.path.insert(0, _SRC)

from data_loader import load_all
from proxies import build_proxy_ext
from signals import (
    ewma_zscore, rolling_zscore, pctile_rank, relative_pe,
    equity_risk_premium, oas_level_score, yield_level_score,
    WINDOWS
)
from config import OUTPUT_DIR, CUSTOM_SERIES_PATH


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

MAX_ROWS = 252 * 5  # ~5 years, enough for all timeframe toggles + context


def _ser(s: pd.Series, n: int = MAX_ROWS) -> dict:
    """Serialize a pd.Series to {dates, values}, keeping last n observations."""
    if s is None or not isinstance(s, pd.Series):
        return {"dates": [], "values": []}
    s = s.dropna().tail(n)
    if s.empty:
        return {"dates": [], "values": []}
    return {
        "dates":  [d.strftime("%Y-%m-%d") for d in s.index],
        "values": [round(float(v), 4) if not np.isnan(v) else None for v in s.values],
    }


def _ser_raw_and_z(s: pd.Series, z_span: int = None,
                   pctile_window: int = None, n: int = MAX_ROWS) -> dict:
    """
    Return raw, z-score, and optionally percentile rank for a series.
    Used for valuation signals where both the absolute level and relative
    position are needed to draw threshold bands on the chart.
    """
    if s is None or not isinstance(s, pd.Series) or s.dropna().empty:
        return {"dates": [], "values": [], "z": [], "pctile": []}
    raw = s.dropna().tail(n)
    z   = ewma_zscore(raw, span=z_span or WINDOWS["long"]).tail(n)
    out = {
        "dates":  [d.strftime("%Y-%m-%d") for d in raw.index],
        "values": [round(float(v), 4) if not np.isnan(v) else None for v in raw.values],
        "z":      [round(float(v), 4) if not np.isnan(v) else None for v in z.reindex(raw.index).values],
    }
    if pctile_window:
        pct = pctile_rank(raw, min(pctile_window, len(raw))).tail(n)
        out["pctile"] = [round(float(v), 4) if not np.isnan(v) else None for v in pct.reindex(raw.index).values]
    return out


def _get(df: pd.DataFrame, col: str):
    """Return df[col] dropna if available, else None."""
    if df is not None and not df.empty and col in df.columns:
        s = df[col].dropna()
        return s if len(s) >= 20 else None
    return None


# ─────────────────────────────────────────────────────────────────────────────
# MOMENTUM: individual component z-scores per equity price series
# ─────────────────────────────────────────────────────────────────────────────

def _rsi_signal(price: pd.Series, window: int = 14) -> pd.Series:
    """RSI(14) mapped [0,100] → [-1,+1]."""
    delta = price.diff()
    up    = delta.clip(lower=0)
    down  = (-delta).clip(lower=0)
    rs    = (up.ewm(span=window, adjust=False).mean() /
             down.ewm(span=window, adjust=False).mean())
    rsi   = 100 - (100 / (1 + rs))
    return ((rsi - 50) / 50).clip(-1, 1).rename("rsi")


def compute_momentum_components(price: pd.Series, n: int = MAX_ROWS) -> dict:
    """
    Compute individual momentum z-score components for a price series.
    Returns dict keyed by component name, each as _ser() output.
    Also includes 'price_pct' — cumulative % return from first data point
    (normalized to 0 at start) for display alongside the z-score metrics.
    """
    if price is None or price.dropna().shape[0] < 63:
        return {}

    px = price.dropna()
    h  = {"1m": 21, "3m": 63, "6m": 126, "12m": 252, "skip": 21}
    out = {}

    if len(px) >= h["1m"] + 20:
        out["ret_1m"]   = _ser(ewma_zscore(px.pct_change(h["1m"])).tail(n))
    if len(px) >= h["3m"] + 20:
        out["ret_3m"]   = _ser(ewma_zscore(px.pct_change(h["3m"])).tail(n))
    if len(px) >= h["6m"] + 20:
        out["ret_6m"]   = _ser(ewma_zscore(px.pct_change(h["6m"])).tail(n))
    if len(px) >= h["12m"] + h["skip"] + 20:
        mom12 = px.shift(h["skip"]).pct_change(h["12m"] - h["skip"])
        out["ret_12_1m"] = _ser(ewma_zscore(mom12).tail(n))
    if len(px) >= 200 + 20:
        ma50  = px.rolling(50,  min_periods=25).mean()
        ma200 = px.rolling(200, min_periods=100).mean()
        out["ma_dist"]  = _ser(ewma_zscore((ma50 - ma200) / ma200.replace(0, np.nan)).tail(n))
    if len(px) >= 14 + 20:
        out["rsi"]      = _ser(ewma_zscore(_rsi_signal(px)).tail(n))

    # Price level as cumulative % return from first point (for visual overlay)
    px_tail = px.tail(n)
    base    = float(px_tail.iloc[0])
    if base > 0:
        pct_return = ((px_tail / base) - 1) * 100
        out["price_pct"] = _ser(pct_return)

    return out


def compute_spread_momentum_components(spread: pd.Series, n: int = MAX_ROWS) -> dict:
    """OAS spread momentum: tightening = positive (sign-inverted)."""
    if spread is None or spread.dropna().shape[0] < 63:
        return {}
    s   = spread.dropna()
    out = {}
    if len(s) >= 21 + 20:
        z1 = ewma_zscore(-s.diff(21), span=WINDOWS["long"])
        out["spread_mom_1m"] = _ser(z1.tail(n))
    if len(s) >= 63 + 20:
        z3 = ewma_zscore(-s.diff(63), span=WINDOWS["long"])
        out["spread_mom_3m"] = _ser(z3.tail(n))
    return out


def compute_yield_momentum_components(yield_: pd.Series, n: int = MAX_ROWS) -> dict:
    """Yield momentum: falling yields = positive (sign-inverted)."""
    if yield_ is None or yield_.dropna().shape[0] < 63:
        return {}
    y   = yield_.dropna()
    out = {}
    if len(y) >= 21 + 20:
        out["yield_mom_1m"] = _ser(ewma_zscore(-y.diff(21), span=WINDOWS["long"]).tail(n))
    if len(y) >= 63 + 20:
        out["yield_mom_3m"] = _ser(ewma_zscore(-y.diff(63), span=WINDOWS["long"]).tail(n))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# GDP REVISION helper (blended current/next with time-varying weights)
# ─────────────────────────────────────────────────────────────────────────────

def _blended_gdp_revision(f1: pd.DataFrame, cur_col: str, nxt_col: str) -> pd.Series:
    """Blended GDP level series; returns MoM revision (Δ1M)."""
    def _s(col): return f1[col].dropna() if (not f1.empty and col in f1.columns) else None
    cur = _s(cur_col)
    nxt = _s(nxt_col)
    if cur is None and nxt is None:
        return pd.Series(dtype=float)
    if cur is None:
        blended = nxt
    elif nxt is None:
        blended = cur
    else:
        idx   = cur.index.union(nxt.index)
        cur_r = cur.reindex(idx).ffill()
        nxt_r = nxt.reindex(idx).ffill()
        w_cur = pd.Series(idx.month / 12, index=idx)
        blended = w_cur * cur_r + (1 - w_cur) * nxt_r
    return blended.diff(21).rename("gdp_rev")  # 1M revision (more predictive)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN EXTRACTOR
# ─────────────────────────────────────────────────────────────────────────────

def compute_pmi_heatmap(data: dict, start_year: int = 2023) -> dict:
    """
    PMI & Leading Indicators heatmap — MONTHLY columns grouped by Quarter/Year.

    Format matches LGT Capital Partners reference:
      - Columns: Year → Quarter (Q1/Q2/Q3/Q4) → Month (J/F/M/A/M/J/J/A/S/O/N/D)
      - Colors: independent per row (each row normalized on its own range)
      - PMI rows: threshold at 50 (green=expansion, red=contraction)
      - Non-PMI rows: percentile rank within own history for color intensity

    Series included:
      PMI:        Global, US (mfg/svcs), Eurozone (mfg/svcs), China (mfg/svcs), Japan, UK
      US context: ISM N.O./Inv ratio, GDP 2026 expectations, Corp EPS revision,
                  Atlanta Fed GDPNow, Bloomberg US FCI, Chicago Fed NFCI
    """
    f1  = data.get("f1",  pd.DataFrame())
    mkt = data.get("mkt", pd.DataFrame())
    h7  = data.get("h7",  pd.DataFrame())

    # Load custom series for EPS revision
    custom = pd.DataFrame()
    if os.path.exists(CUSTOM_SERIES_PATH):
        try:
            custom = pd.read_excel(CUSTOM_SERIES_PATH, sheet_name="custom_series",
                                   index_col=0, parse_dates=True)
        except Exception:
            pass

    def _gs(df, col):
        if df is not None and not df.empty and col in df.columns:
            s = df[col].dropna()
            return s if len(s) >= 6 else None
        return None

    # Build monthly date range: from start_year-01-01 to latest available data
    today = pd.Timestamp.today()
    months = pd.date_range(
        start=pd.Timestamp(start_year, 1, 1),
        end=today,
        freq="ME"
    )

    def _mvals(s, months):
        """Extract last available value in each month. Returns list of floats or None."""
        if s is None or s.empty:
            return [None] * len(months)
        sm = s.resample("ME").last()
        out = []
        for m in months:
            matches = sm[(sm.index.year == m.year) & (sm.index.month == m.month)]
            if len(matches) > 0:
                v = float(matches.iloc[0])
                out.append(round(v, 3) if not np.isnan(v) else None)
            else:
                out.append(None)
        return out

    def _pctile_within_row(values):
        """For each value, compute its percentile rank within the row's own non-null values.
        Returns list of 0-1 floats (or None). Used for independent per-row color scaling."""
        valid = [v for v in values if v is not None]
        if len(valid) < 3:
            return [None] * len(values)
        mn, mx = min(valid), max(valid)
        rng = mx - mn
        if rng < 1e-9:
            return [0.5 if v is not None else None for v in values]
        return [round((v - mn) / rng, 3) if v is not None else None for v in values]

    # ── Row definitions ────────────────────────────────────────────────────────
    # color_mode: "threshold" = fixed midpoint (PMI=50, ratio=1.0)
    #             "percentile" = normalized within own row history
    # invert: True means HIGH value = RED (e.g. tight FCI = bad)
    rows_def = [
        # ── PMI: Global & United States ────────────────────────────────────────
        ("header", "PMI — Global"),
        ("threshold", "Global Manufacturing PMI",  _gs(f1, "pmi_global_mfg"),        50.0, False),
        ("header", "PMI — United States"),
        ("threshold", "ISM Manufacturing PMI",     _gs(f1, "pmi_ism_mfg"),           50.0, False),
        ("threshold", "ISM Services PMI",          _gs(f1, "pmi_ism_svcs"),          50.0, False),
        ("threshold", "ISM N.O. / Inventories",    _gs(f1, "ism_new_ord_inv"),        1.0, False),
        # ── US Macro & Financial Conditions ────────────────────────────────────
        ("header", "US — Macro & Financial Conditions"),
        ("percentile", "GDP 2026 Expectations (%)", _gs(f1, "gdp_forecast_us_27"),   None, False),
        ("percentile", "Atlanta Fed GDPNow (%)",    _gs(h7, "gdpnow"),               None, False),
        ("percentile", "Corp EPS Revision Composite", _gs(custom, "eps_rev_us"),     None, False),
        ("percentile", "Bloomberg US FCI",          _gs(mkt, "fci"),                 None, True),
        ("percentile", "Chicago Fed NFCI",          _gs(h7, "nfci"),                 None, True),
        # ── PMI: Eurozone, China, Japan & UK ───────────────────────────────────
        ("header", "PMI — Eurozone"),
        ("threshold", "Eurozone Manufacturing PMI", _gs(f1, "pmi_ez_mfg"),           50.0, False),
        ("threshold", "Eurozone Services PMI",      _gs(f1, "pmi_ez_svcs"),          50.0, False),
        ("header", "PMI — China"),
        ("threshold", "China Manufacturing (Caixin)",_gs(f1, "pmi_china_mfg"),       50.0, False),
        ("threshold", "China Services (Caixin)",    _gs(f1, "pmi_china_svcs"),       50.0, False),
        ("header", "PMI — Japan & UK"),
        ("threshold", "Japan Manufacturing PMI",    _gs(f1, "pmi_japan_mfg"),        50.0, False),
        ("threshold", "UK Manufacturing PMI",       _gs(f1, "pmi_uk_mfg"),           50.0, False),
    ]

    # Build column metadata (3 levels: year → quarter → month)
    MONTH_SHORT = ["J","F","M","A","M","J","J","A","S","O","N","D"]
    MONTH_FULL  = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    QTR_MONTHS  = {1:[1,2,3], 2:[4,5,6], 3:[7,8,9], 4:[10,11,12]}

    col_meta = []   # [{year, quarter, month_short, month_full}]
    for m in months:
        col_meta.append({
            "year":        m.year,
            "quarter":     (m.month - 1) // 3 + 1,
            "month_idx":   m.month,
            "month_short": MONTH_SHORT[m.month - 1],
            "month_full":  MONTH_FULL[m.month - 1],
        })

    # Year group info (for colspan)
    years_info = {}
    for i, cm in enumerate(col_meta):
        y = cm["year"]
        if y not in years_info:
            years_info[y] = {"year": y, "start_idx": i, "count": 0}
        years_info[y]["count"] += 1
    years_list = sorted(years_info.values(), key=lambda x: x["year"])

    # Quarter group info per year (for colspan)
    qtr_info = []
    seen = set()
    for i, cm in enumerate(col_meta):
        key = (cm["year"], cm["quarter"])
        if key not in seen:
            seen.add(key)
            qtr_info.append({
                "year": cm["year"],
                "quarter": cm["quarter"],
                "label": f"Q{cm['quarter']}",
                "start_idx": i,
                "count": 0,
            })
        qtr_info[-1]["count"] += 1

    # Build rows output
    rows_out = []
    for row_def in rows_def:
        if row_def[0] == "header":
            rows_out.append({"type": "header", "label": row_def[1]})
        elif row_def[0] == "threshold":
            _, label, raw_s, threshold, invert = row_def
            vals = _mvals(raw_s, months)
            rows_out.append({
                "type":       "data",
                "label":      label,
                "color_mode": "threshold",
                "threshold":  threshold,
                "invert":     invert,
                "values":     vals,
            })
        else:  # percentile
            _, label, raw_s, _, invert = row_def
            vals = _mvals(raw_s, months)
            pcts = _pctile_within_row(vals)
            rows_out.append({
                "type":       "data",
                "label":      label,
                "color_mode": "percentile",
                "invert":     invert,
                "values":     vals,
                "percentiles": pcts,
            })

    return {
        "col_meta":  col_meta,
        "years":     years_list,
        "quarters":  qtr_info,
        "rows":      rows_out,
        "subtitle":  "PMI, leading indicators & financial conditions · monthly data · colors independent per row",
    }


def build_chartbook_data() -> dict:
    print("Loading pipeline data...")
    data    = load_all(verbose=False)
    proxies = build_proxy_ext(data, verbose=False)
    ext     = {k: v for k, v in proxies.items()}

    f1  = data.get("f1",     pd.DataFrame())
    f3  = data.get("f3",     pd.DataFrame())
    mkt = data.get("mkt",    pd.DataFrame())
    oas = data.get("oas",    pd.DataFrame())
    tsy = data.get("tsy",    pd.DataFrame())
    cds = data.get("cds",    pd.DataFrame())
    pe  = data.get("pe",     pd.DataFrame())
    yl  = data.get("yields", pd.DataFrame())
    fi  = data.get("fi_px",  pd.DataFrame())
    aaii_df = data.get("aaii", pd.DataFrame())

    print("Extracting PMI heatmap...")
    fundamentals_heatmap = compute_pmi_heatmap(data, start_year=2023)

    print("Extracting fundamentals...")
    # ── I. FUNDAMENTALS ────────────────────────────────────────────────────────
    fundamentals = {
        "pmi": {
            "ism_mfg":     _ser_raw_and_z(_get(f1, "pmi_ism_mfg"),  pctile_window=WINDOWS["xlarge"]),
            "ism_svc":     _ser_raw_and_z(_get(f1, "pmi_ism_svcs"),  pctile_window=WINDOWS["xlarge"]),
            "ez_mfg":      _ser_raw_and_z(_get(f1, "pmi_ez_mfg"),    pctile_window=WINDOWS["xlarge"]),
            "ez_svc":      _ser_raw_and_z(_get(f1, "pmi_ez_svcs"),   pctile_window=WINDOWS["xlarge"]),
            "china_mfg":   _ser_raw_and_z(_get(f1, "pmi_china_mfg"), pctile_window=WINDOWS["xlarge"]),
            "china_svc":   _ser_raw_and_z(_get(f1, "pmi_china_svcs"),pctile_window=WINDOWS["xlarge"]),
            "japan_mfg":   _ser_raw_and_z(_get(f1, "pmi_japan_mfg"), pctile_window=WINDOWS["xlarge"]),
            "uk_mfg":      _ser_raw_and_z(_get(f1, "pmi_uk_mfg"),    pctile_window=WINDOWS["xlarge"]),
            "global_mfg":  _ser_raw_and_z(_get(f1, "pmi_global_mfg"),pctile_window=WINDOWS["xlarge"]),
        },
        "cesi": {
            "cesi_us":     _ser_raw_and_z(_get(f1, "cesi_us"),     pctile_window=WINDOWS["medium"]),
            "cesi_ez":     _ser_raw_and_z(_get(f1, "cesi_ez"),     pctile_window=WINDOWS["medium"]),
            "cesi_china":  _ser_raw_and_z(_get(f1, "cesi_china"),  pctile_window=WINDOWS["medium"]),
            "cesi_em":     _ser_raw_and_z(_get(f1, "cesi_em"),     pctile_window=WINDOWS["medium"]),
            "cesi_japan":  _ser_raw_and_z(_get(f1, "cesi_japan"),  pctile_window=WINDOWS["medium"]),
            "cesi_uk":     _ser_raw_and_z(_get(f1, "cesi_uk"),     pctile_window=WINDOWS["medium"]),
            "cesi_global": _ser_raw_and_z(_get(f1, "cesi_global"), pctile_window=WINDOWS["medium"]),
        },
        "gdp_revision": {
            "us":    _ser(_blended_gdp_revision(f1, "gdp_forecast_us_26", "gdp_forecast_us_27")),
            "ez":    _ser(_blended_gdp_revision(f1, "gdp_forecast_eu_26", "gdp_forecast_eu_27")),
            "china": _ser(_blended_gdp_revision(f1, "gdp_forecast_cn_26", "gdp_forecast_cn_27")),
            "em":    _ser(_blended_gdp_revision(f1, "gdp_em_cur",    "gdp_em_nxt")),
            "japan": _ser(_blended_gdp_revision(f1, "gdp_japan_cur", "gdp_japan_nxt")),
            "dm":    _ser(_blended_gdp_revision(f1, "gdp_dm_cur",    "gdp_dm_nxt")),
        },
        "earnings": {
            "eps_fwd_us":    _ser_raw_and_z(_get(f3, "eps_fwd_us")),
            "eps_fwd_em":    _ser_raw_and_z(_get(f3, "eps_fwd_em")),
            "eps_fwd_world": _ser_raw_and_z(_get(f3, "eps_fwd_world")),
            "eps_fwd_china": _ser_raw_and_z(_get(f3, "eps_fwd_china")),
            "eps_fwd_japan": _ser_raw_and_z(_get(f3, "eps_fwd_japan")),
            "eps_fwd_eafe":  _ser_raw_and_z(_get(f3, "eps_fwd_eafe")),
        },
        "inflation": {
            "breakeven_5y":  _ser_raw_and_z(_get(mkt, "breakeven_5y"),  pctile_window=WINDOWS["xlarge"]),
            "breakeven_10y": _ser_raw_and_z(_get(mkt, "breakeven_10y"), pctile_window=WINDOWS["xlarge"]),
            "cpi_us":        _ser_raw_and_z(_get(mkt, "cpi_us")),
        },
    }

    print("Extracting momentum...")
    # ── II. MOMENTUM ──────────────────────────────────────────────────────────
    # Equity price columns → asset class map
    eq_map = {
        "us_equity":    "sp500_tr_px",
        "us_growth":    "sp500_gro_px",
        "us_value":     "sp500_val_px",
        "dm_equity":    "eafe_px",
        "msci_world":   "msci_acwi_px",
        "em_equity":    "msci_em_px",
        "em_xchina":    "em_xchina_px",
        "china_equity": "china_px",
    }
    fi_map = {
        "lt_treasuries": "bsgv_price",
        "lt_us_corp":    "usagg_price",
        "short_term_fi": "i132_price",
        "lt03":          "lt03_price",
    }

    mom_equity = {}
    for ac, col in eq_map.items():
        px = _get(fi, col)
        if px is not None:
            mom_equity[ac] = compute_momentum_components(px)

    mom_fi = {}
    for ac, col in fi_map.items():
        px = _get(fi, col)
        if px is not None:
            mom_fi[ac] = compute_momentum_components(px)
            # Add yield momentum for FI
            if ac == "lt_treasuries":
                mom_fi[ac].update(compute_yield_momentum_components(_get(tsy, "usy_10y")))
            elif ac in ("short_term_fi", "lt03"):
                mom_fi[ac].update(compute_yield_momentum_components(_get(tsy, "usy_2y")))
            elif ac == "lt_us_corp":
                mom_fi[ac].update(compute_yield_momentum_components(_get(tsy, "usy_10y")))

    mom_spreads = {
        "oas_bbb":   compute_spread_momentum_components(_get(oas, "oas_bbb")),
        "oas_hy":    compute_spread_momentum_components(_get(oas, "oas_hy")),
        "oas_em":    compute_spread_momentum_components(_get(oas, "oas_em")),
        "oas_latam": compute_spread_momentum_components(_get(oas, "oas_latam")),
    }

    momentum = {
        "equity":  mom_equity,
        "fi":      mom_fi,
        "spreads": mom_spreads,
    }

    print("Extracting sentiment...")
    # ── III. SENTIMENT ────────────────────────────────────────────────────────
    vix_s    = _get(mkt, "vix")
    move_s   = _get(mkt, "move")
    vstoxx_s = _get(mkt, "vstoxx")
    ted_s    = _get(tsy, "modern_ted")   # modern_ted = tbill_3m - SOFR (available from 2018)
    pcr_s    = _get(mkt, "pcr")
    aaii_s   = _get(aaii_df, "aaii_bull_bear")

    sentiment = {
        "volatility": {
            "vix":    _ser_raw_and_z(vix_s,    pctile_window=WINDOWS["xlarge"]),
            "move":   _ser_raw_and_z(move_s,   pctile_window=WINDOWS["xlarge"]),
            "vstoxx": _ser_raw_and_z(vstoxx_s, pctile_window=WINDOWS["xlarge"]),
        },
        "funding": {
            "ted":  _ser_raw_and_z(ted_s,  pctile_window=WINDOWS["xlarge"]),
            "embi": _ser_raw_and_z(
                _get(oas, "oas_em"),  # EM BBB OAS as EMBI proxy
                pctile_window=WINDOWS["xlarge"]
            ),
        },
        "positioning": {
            "aaii_bull_bear": _ser_raw_and_z(aaii_s, pctile_window=WINDOWS["vlong"]),
            "pcr":            _ser_raw_and_z(pcr_s,  pctile_window=WINDOWS["xlarge"]),
        },
    }

    print("Extracting valuation...")
    # ── IV. VALUATION ─────────────────────────────────────────────────────────
    pe_sp500    = _get(pe, "sp500")
    pe_acwi     = _get(pe, "msci_acwi")
    pe_eafe     = _get(pe, "msci_eafe")
    pe_em       = _get(pe, "msci_em")
    pe_emx      = _get(pe, "msci_em_xchina")
    pe_china    = _get(pe, "msci_china")
    pe_growth   = _get(pe, "sp500_growth")
    pe_value    = _get(pe, "sp500_value")
    pe_quality  = _get(pe, "sp500_quality")

    tips_10y    = _get(tsy, "tips_10y")
    tips_5y     = _get(tsy, "tips_5y")
    gt10        = _get(tsy, "usy_10y")
    gt02        = _get(tsy, "usy_2y")
    tbill       = _get(tsy, "tbill_3m")
    fedrate     = _get(tsy, "fedrate")
    term_spread = _get(tsy, "term_spread")
    if term_spread is None and gt10 is not None and gt02 is not None:
        term_spread = (gt10 - gt02.reindex(gt10.index).ffill()).rename("term_spread")

    sp500_ey    = _get(yl, "sp500_ey")
    acwi_ey     = _get(yl, "msci_acwi_ey")
    em_ey       = _get(yl, "msci_em_ey")
    china_ey    = _get(yl, "china_ey")
    emx_ey      = _get(yl, "em_xchina_ey")

    erp_yield   = tips_10y if tips_10y is not None else gt10

    # Raw P/E levels with percentile rank
    def _pe_raw(s, label):
        if s is None:
            return {"dates": [], "values": [], "pctile": []}
        raw = s.dropna().tail(MAX_ROWS)
        pct = pctile_rank(raw, min(WINDOWS["vlong"], len(raw))).tail(MAX_ROWS)
        return {
            "dates":  [d.strftime("%Y-%m-%d") for d in raw.index],
            "values": [round(float(v), 2) if not np.isnan(v) else None for v in raw.values],
            "pctile": [round(float(v), 4) if not np.isnan(v) else None
                       for v in pct.reindex(raw.index).values],
        }

    # ERP raw level
    def _erp_raw(ey, bond_yield):
        if ey is None or bond_yield is None:
            return {"dates": [], "values": [], "z": []}
        erp_raw = (ey - bond_yield.reindex(ey.index).ffill()).dropna().tail(MAX_ROWS)
        erp_z   = ewma_zscore(erp_raw, span=WINDOWS["vlong"]).tail(MAX_ROWS)
        return {
            "dates":  [d.strftime("%Y-%m-%d") for d in erp_raw.index],
            "values": [round(float(v), 4) if not np.isnan(v) else None for v in erp_raw.values],
            "z":      [round(float(v), 4) if not np.isnan(v) else None
                       for v in erp_z.reindex(erp_raw.index).values],
        }

    # Relative P/E ratio + z-score
    def _rel_pe_raw(pe_a, pe_b):
        if pe_a is None or pe_b is None:
            return {"dates": [], "ratio": [], "z": []}
        idx   = pe_a.index.intersection(pe_b.index)
        a, b  = pe_a.reindex(idx).dropna(), pe_b.reindex(idx).dropna()
        idx2  = a.index.intersection(b.index)
        a, b  = a.reindex(idx2), b.reindex(idx2)
        ratio = (a / b.replace(0, np.nan)).dropna().tail(MAX_ROWS)
        z_raw = relative_pe(a, b)            # inverted z-score
        z_s   = z_raw.reindex(ratio.index).tail(MAX_ROWS)
        return {
            "dates": [d.strftime("%Y-%m-%d") for d in ratio.index],
            "ratio": [round(float(v), 4) if not np.isnan(v) else None for v in ratio.values],
            "z":     [round(float(v), 4) if not np.isnan(v) else None
                      for v in z_s.reindex(ratio.index).values],
        }

    pe_ref_us = pe_acwi if pe_acwi is not None else pe_sp500

    valuation = {
        "pe_absolute": {
            "sp500":       _pe_raw(pe_sp500,   "S&P 500"),
            "msci_acwi":   _pe_raw(pe_acwi,    "MSCI ACWI"),
            "msci_eafe":   _pe_raw(pe_eafe,    "MSCI EAFE"),
            "msci_em":     _pe_raw(pe_em,      "MSCI EM"),
            "msci_em_xch": _pe_raw(pe_emx,     "EM ex-China"),
            "msci_china":  _pe_raw(pe_china,   "MSCI China"),
            "sp500_growth":_pe_raw(pe_growth,  "S&P 500 Growth"),
            "sp500_value": _pe_raw(pe_value,   "S&P 500 Value"),
            "sp500_qual":  _pe_raw(pe_quality, "S&P 500 Quality"),
        },
        "pe_relative": {
            "growth_vs_value": _rel_pe_raw(pe_growth,  pe_value),
            "value_vs_growth": _rel_pe_raw(pe_value,   pe_growth),
            "us_vs_em":        _rel_pe_raw(pe_ref_us,  pe_em),
            "dm_vs_us":        _rel_pe_raw(pe_eafe,    pe_ref_us),
            "em_vs_us":        _rel_pe_raw(pe_em,      pe_ref_us),
            "china_vs_em":     _rel_pe_raw(pe_china,   pe_em),
            "china_vs_us":     _rel_pe_raw(pe_china,   pe_ref_us),
            "em_vs_dm":        _rel_pe_raw(pe_em,      pe_eafe),
        },
        "erp": {
            "us_equity": _erp_raw(sp500_ey, erp_yield),
            "acwi":      _erp_raw(acwi_ey,  erp_yield),
            "em_equity": _erp_raw(em_ey,    erp_yield),
            "china":     _erp_raw(china_ey, erp_yield),
        },
        "oas": {
            "bbb":   _ser_raw_and_z(_get(oas, "oas_bbb"),   pctile_window=WINDOWS["xlarge"],
                                    z_span=WINDOWS["xlarge"]),
            "hy":    _ser_raw_and_z(_get(oas, "oas_hy"),    pctile_window=WINDOWS["xlarge"],
                                    z_span=WINDOWS["xlarge"]),
            "em":    _ser_raw_and_z(_get(oas, "oas_em"),    pctile_window=WINDOWS["xlarge"],
                                    z_span=WINDOWS["xlarge"]),
            "latam": _ser_raw_and_z(_get(oas, "oas_latam"), pctile_window=WINDOWS["xlarge"],
                                    z_span=WINDOWS["xlarge"]),
        },
        "yields": {
            "usy_10y":     _ser_raw_and_z(gt10,        pctile_window=WINDOWS["vlong"]),
            "usy_2y":      _ser_raw_and_z(gt02,        pctile_window=WINDOWS["vlong"]),
            "tbill_3m":    _ser_raw_and_z(tbill,       pctile_window=WINDOWS["xlarge"]),
            "tips_10y":    _ser_raw_and_z(tips_10y,    pctile_window=WINDOWS["vlong"]),
            "tips_5y":     _ser_raw_and_z(tips_5y,     pctile_window=WINDOWS["xlarge"]),
            "fedrate":     _ser_raw_and_z(fedrate,     pctile_window=WINDOWS["vlong"]),
            "term_spread": _ser_raw_and_z(term_spread, pctile_window=WINDOWS["vlong"]),
        },
    }

    meta = {
        "run_date": datetime.today().strftime("%Y-%m-%d"),
        "max_rows": MAX_ROWS,
        "description": "TAA Dashboard chartbook data — all signal series",
    }

    return {
        "meta":                  meta,
        "fundamentals":          fundamentals,
        "fundamentals_heatmap":  fundamentals_heatmap,
        "momentum":              momentum,
        "sentiment":             sentiment,
        "valuation":             valuation,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────────────────────────────────────

def export_chartbook_data(out_path: str = None) -> str:
    if out_path is None:
        out_path = os.path.join(_ROOT, "results", "chartbook_data.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    data = build_chartbook_data()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, allow_nan=False, separators=(",", ":"))

    size_mb = os.path.getsize(out_path) / 1024 / 1024
    print(f"\n  chartbook_data.json -> {out_path}")
    print(f"  File size: {size_mb:.2f} MB")
    return out_path


if __name__ == "__main__":
    export_chartbook_data()
