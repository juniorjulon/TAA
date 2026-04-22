"""
taa_system/data_loader.py
=========================
Loads, validates, and cleans every relevant sheet from the TAA Excel workbook.

Excel sheet inventory (v2 structure — H1-H6, AAII, OAS):
  OAS  : ICE BofA credit spreads — long history from 1999 (~6,900 rows)
  H4   : PE ratios, earnings yields, TR price indices — from 2011 (~3,991 rows)
  H5   : VIX, MOVE, CDX, yields, DXY, FCI, SOFR, PCE, breakevenss — from 2011 (~4,044 rows)
  H6   : MSCI World + S&P 11 sectors — PE, EY, TR — from 2011 (~3,991 rows)
  H1   : PMI, CESI, GDP forecasts — from 2011 (~4,003 rows)
  H2   : Additional PMI, CESI, GDP — from 2011 (~3,960 rows)
  H3   : Forward EPS — from 2011 (~3,991 rows)
  AAII : AAII investor sentiment (weekly) — from 1987

load_all() returns a dict with these keys:
  'oas'     : OAS credit spreads (long history)
  'pe'      : Forward P/E ratios (from H4)
  'yields'  : Earnings yields (from H4) — used for ERP
  'fi_px'   : TR price levels (from H4) — primary momentum source
  'sectors' : Sector PE, EY, TR (from H6) — sector rotation
  'tsy'     : Treasury yields + term_spread + TIPS + Fed Funds (from H5)
  'cds'     : CDX indices (from H5)
  'mkt'     : VIX, MOVE, PCR, SKEW, DXY, FCI, SOFR, PCE, breakevens (from H5)
  'f1'      : PMI, CESI, GDP fundamentals (H1+H2 combined)
  'f3'      : Forward EPS (from H3)
  'aaii'    : AAII bull-bear spread (weekly -> daily resampled)
"""

import warnings
import pandas as pd
import numpy as np

from config import (
    EXCEL_PATH,
    OAS_COLS, SHEET4_PE_COLS, SHEET4_EY_COLS, SHEET4_TR_COLS,
    SHEET_H6_PE_COLS, SHEET_H6_EY_COLS, SHEET_H6_TR_COLS,
    SHEET5_COLS, SHEET_F1_COLS, SHEET_F2_COLS, SHEET_F3_COLS,
    SHEET_AAII_COLS,
    MAX_FFILL_DAYS, RETURN_OUTLIER_ZSCORE,
)

warnings.filterwarnings("ignore", category=UserWarning)


# ─────────────────────────────────────────────────────────────────────────────
# PRIVATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _sort_asc(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_index()


def _clean_prices(df: pd.DataFrame) -> pd.DataFrame:
    """Replace zeros, forward-fill up to MAX_FFILL_DAYS, drop all-NaN rows."""
    df = df.replace(0, np.nan)
    df = df.ffill(limit=MAX_FFILL_DAYS)
    df = df.dropna(how="all")
    return df


def _remove_return_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """Replace daily returns exceeding ±5σ with NaN and re-fill."""
    rets  = df.pct_change()
    mu    = rets.mean()
    sigma = rets.std().replace(0, np.nan)
    z     = (rets - mu) / sigma
    mask  = z.abs() > RETURN_OUTLIER_ZSCORE
    df_out = df.copy()
    df_out[mask] = np.nan
    df_out = df_out.ffill(limit=MAX_FFILL_DAYS)
    return df_out


def _validate_index(df: pd.DataFrame, name: str) -> None:
    if not df.index.is_monotonic_increasing:
        raise ValueError(f"[{name}] DatetimeIndex not monotonically increasing.")


def _parse_date_col(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce first column to datetime, set as index, sort ascending."""
    df = df.copy()
    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col])
    df = df.set_index(date_col)
    df.index.name = "Date"
    return _sort_asc(df)


def _select_rename(df: pd.DataFrame, col_map: dict) -> pd.DataFrame:
    """Keep only columns present in col_map and rename to internal names."""
    rename = {k: v for k, v in col_map.items() if k in df.columns}
    df = df.rename(columns=rename)
    keep = [v for v in col_map.values() if v in df.columns]
    return df[keep]


# ─────────────────────────────────────────────────────────────────────────────
# OAS — long history credit spreads
# ─────────────────────────────────────────────────────────────────────────────

def load_oas() -> pd.DataFrame:
    """ICE BofA OAS spreads (FRED), long history from 1999. Decimal percent."""
    df = pd.read_excel(EXCEL_PATH, sheet_name="OAS", parse_dates=["Date"])
    df = df.set_index("Date")
    df = _select_rename(df, OAS_COLS)
    df = _sort_asc(df)
    df = df.clip(lower=0, upper=30).replace(0, np.nan)
    df = df.ffill(limit=MAX_FFILL_DAYS)
    _validate_index(df, "OAS")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# SHEET H4 — PE, Earnings Yields, TR price levels
# ─────────────────────────────────────────────────────────────────────────────

def _load_h4_raw() -> pd.DataFrame:
    df = pd.read_excel(EXCEL_PATH, sheet_name="H4")
    return _parse_date_col(df)


def load_pe() -> pd.DataFrame:
    """Forward P/E ratios from H4. Adaptive window used in pe_score()."""
    df  = _load_h4_raw()
    out = _select_rename(df, SHEET4_PE_COLS)
    out = out.dropna(axis=1, how="all")
    out = out.ffill(limit=MAX_FFILL_DAYS)
    out = out.clip(lower=0.01, upper=100).replace(0.01, np.nan)
    _validate_index(out, "PE")
    return out


def load_yields() -> pd.DataFrame:
    """Earnings yields (%) from H4 — used for ERP calculation."""
    df  = _load_h4_raw()
    out = _select_rename(df, SHEET4_EY_COLS)
    out = out.dropna(axis=1, how="all")
    out = out.ffill(limit=MAX_FFILL_DAYS)
    out = out.clip(lower=0, upper=30)
    _validate_index(out, "YIELDS")
    return out


def load_fi_px() -> pd.DataFrame:
    """TR price level indices from H4. Primary momentum source."""
    df  = _load_h4_raw()
    out = _select_rename(df, SHEET4_TR_COLS)
    out = _clean_prices(out)
    out = _remove_return_outliers(out)
    # bfu5_price alias (Bloomberg 1-5Y Treasury not in H4 — use i132_price proxy)
    if "i132_price" in out.columns and "bfu5_price" not in out.columns:
        out["bfu5_price"] = out["i132_price"]
    _validate_index(out, "FI_PX")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# SHEET H6 — MSCI World + S&P 11 Sectors (PE, EY, TR)
# ─────────────────────────────────────────────────────────────────────────────

def _load_h6_raw() -> pd.DataFrame:
    df = pd.read_excel(EXCEL_PATH, sheet_name="H6")
    return _parse_date_col(df)


def load_sectors() -> pd.DataFrame:
    """
    MSCI World + all 11 S&P 500 sectors from H6.
    Returns combined PE, EY, and TR columns for sector rotation and valuation.
    """
    df = _load_h6_raw()
    pe  = _select_rename(df, SHEET_H6_PE_COLS)
    ey  = _select_rename(df, SHEET_H6_EY_COLS)
    tr  = _select_rename(df, SHEET_H6_TR_COLS)

    pe  = pe.clip(lower=0.01, upper=100).replace(0.01, np.nan).ffill(limit=MAX_FFILL_DAYS)
    ey  = ey.clip(lower=0, upper=30).ffill(limit=MAX_FFILL_DAYS)
    tr  = _clean_prices(tr)
    tr  = _remove_return_outliers(tr)

    out = pd.concat([pe, ey, tr], axis=1)
    _validate_index(out, "SECTORS")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# SHEET H5 — Market data: yields, CDX, VIX, MOVE, DXY, FCI, SOFR, PCE
# ─────────────────────────────────────────────────────────────────────────────

def _load_h5_raw() -> pd.DataFrame:
    df = pd.read_excel(EXCEL_PATH, sheet_name="H5")
    return _parse_date_col(df)


def load_tsy() -> pd.DataFrame:
    """
    US Treasury yields (2Y, 10Y, 3M T-bill), TIPS real yields, Fed Funds.
    Also loads SOFR (from 2018) and PCE YoY (monthly).
    Computes: term_spread = 10Y − 2Y, modern_ted = tbill_3m − sofr.
    """
    df  = _load_h5_raw()
    tsy_keys = ("usy_10y", "usy_2y", "tbill_3m", "tips_10y", "tips_5y",
                "fedrate", "sofr", "pce_yoy")
    tsy_cols = {k: v for k, v in SHEET5_COLS.items() if v in tsy_keys}
    out = _select_rename(df, tsy_cols)
    out = _sort_asc(out)
    out = out.clip(lower=-5, upper=25)   # yields outside [-5%, 25%] are errors
    out = out.ffill(limit=MAX_FFILL_DAYS)

    if "usy_10y" in out.columns and "usy_2y" in out.columns:
        out["term_spread"] = out["usy_10y"] - out["usy_2y"]

    # Modern TED = 3M T-bill − SOFR (funding stress, replaces defunct BASPTDSP)
    if "tbill_3m" in out.columns and "sofr" in out.columns:
        out["modern_ted"] = (out["tbill_3m"] - out["sofr"]).clip(lower=-1, upper=5)

    _validate_index(out, "TSY")
    return out


def load_cds() -> pd.DataFrame:
    """CDX IG spread (bps) and CDX HY price (~100 par) from H5."""
    df  = _load_h5_raw()
    cds_cols = {k: v for k, v in SHEET5_COLS.items()
                if v in ("cdx_ig_spread", "cdx_hy_price")}
    out = _select_rename(df, cds_cols)
    out = _sort_asc(out)
    out = out.ffill(limit=MAX_FFILL_DAYS)
    if "cdx_ig_spread" in out.columns:
        out["cdx_ig_spread"] = out["cdx_ig_spread"].clip(lower=0, upper=500)
    if "cdx_hy_price" in out.columns:
        out["cdx_hy_price"]  = out["cdx_hy_price"].clip(lower=50, upper=120)
    _validate_index(out, "CDS")
    return out


def load_mkt() -> pd.DataFrame:
    """
    Sentiment and volatility indicators from H5: VIX, MOVE, PCR, SKEW,
    VSTOXX, VIX3M, DXY, FCI (BFCIUS), breakeven inflation, CPI.
    New: DXY (from 2011), BFCIUS/FCI (from 2011), SOFR is in tsy.
    """
    df  = _load_h5_raw()
    mkt_keys = ("vix", "move", "vstoxx", "vix3m", "pcr", "skew",
                "dxy", "fci", "breakeven_5y", "breakeven_10y", "cpi_us")
    mkt_cols = {k: v for k, v in SHEET5_COLS.items() if v in mkt_keys}
    out = _select_rename(df, mkt_cols)
    out = _sort_asc(out)
    out = out.ffill(limit=MAX_FFILL_DAYS)

    # Clip non-negative indicators
    for col in ("vix", "move", "vstoxx", "vix3m", "pcr", "skew"):
        if col in out.columns:
            out[col] = out[col].clip(lower=0)
    # DXY: reasonable range
    if "dxy" in out.columns:
        out["dxy"] = out["dxy"].clip(lower=50, upper=200)
    # Breakevens: clip to plausible range
    for col in ("breakeven_5y", "breakeven_10y"):
        if col in out.columns:
            out[col] = out[col].clip(lower=-2, upper=8)

    _validate_index(out, "MKT")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# SHEETS H1 + H2 — Fundamentals (PMI, CESI, GDP)
# ─────────────────────────────────────────────────────────────────────────────

def load_f1() -> pd.DataFrame:
    """
    H1 + H2 fundamentals: PMI, CESI, GDP forecasts.
    Returns combined DataFrame with all available fundamental series.
    """
    h1 = pd.read_excel(EXCEL_PATH, sheet_name="H1")
    h1 = _parse_date_col(h1)
    h1 = _select_rename(h1, SHEET_F1_COLS)

    h2 = pd.read_excel(EXCEL_PATH, sheet_name="H2")
    h2 = _parse_date_col(h2)
    h2 = _select_rename(h2, SHEET_F2_COLS)

    combined = h1.join(h2, how="outer")
    combined = _sort_asc(combined)
    # Forward-fill monthly data over daily calendar (up to 25 days for monthly PMI)
    combined = combined.ffill(limit=MAX_FFILL_DAYS * 5)
    _validate_index(combined, "F1")
    return combined


# ─────────────────────────────────────────────────────────────────────────────
# SHEET H3 — Forward EPS
# ─────────────────────────────────────────────────────────────────────────────

def load_f3() -> pd.DataFrame:
    """
    Forward EPS levels from H3. Breakeven inflation moved to H5/mkt.
    EPS signals use month-over-month % change (revision) in main.py.
    """
    df = pd.read_excel(EXCEL_PATH, sheet_name="H3")
    df = _parse_date_col(df)
    out = _select_rename(df, SHEET_F3_COLS)
    out = _sort_asc(out)
    out = out.ffill(limit=MAX_FFILL_DAYS)
    _validate_index(out, "F3")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# AAII — Weekly investor sentiment
# ─────────────────────────────────────────────────────────────────────────────

def load_aaii() -> pd.DataFrame:
    """
    AAII weekly Bull-Bear spread, forward-filled to daily frequency.
    Long history from 1987 (~2,022 weekly observations).
    """
    df = pd.read_excel(EXCEL_PATH, sheet_name="AAII")
    df = _parse_date_col(df)
    out = _select_rename(df, SHEET_AAII_COLS)
    out = out.dropna(how="all")
    out = _sort_asc(out)

    daily_idx = pd.date_range(start=out.index.min(), end=out.index.max(), freq="B")
    out = out.reindex(daily_idx).ffill(limit=7)
    out.index.name = "Date"
    return out


# ─────────────────────────────────────────────────────────────────────────────
# MASTER LOADER
# ─────────────────────────────────────────────────────────────────────────────

def load_all(verbose: bool = True) -> dict:
    """
    Load and clean all relevant data sheets.

    Returns
    -------
    dict with keys:
      'oas'     : OAS credit spreads (long history from 1999)
      'pe'      : Forward P/E ratios (H4, from 2011)
      'yields'  : Earnings yields (H4, from 2011)
      'fi_px'   : TR price levels (H4, from 2011) — primary momentum source
      'sectors' : Sector PE/EY/TR (H6, from 2011)
      'tsy'     : Treasury yields + TIPS + term_spread + modern_ted (H5)
      'cds'     : CDX indices (H5)
      'mkt'     : VIX, MOVE, DXY, FCI, PCR, SKEW, breakevens (H5)
      'f1'      : PMI, CESI, GDP fundamentals (H1+H2)
      'f3'      : Forward EPS (H3)
      'aaii'    : AAII bull-bear spread (weekly -> daily)

    Legacy alias:
      'tr'      : alias for fi_px
    """
    if verbose:
        print("Loading and cleaning data...")

    loaders = {
        "oas":     load_oas,
        "pe":      load_pe,
        "yields":  load_yields,
        "fi_px":   load_fi_px,
        "sectors": load_sectors,
        "tsy":     load_tsy,
        "cds":     load_cds,
        "mkt":     load_mkt,
        "f1":      load_f1,
        "f3":      load_f3,
        "aaii":    load_aaii,
    }

    data = {}
    for name, fn in loaders.items():
        try:
            data[name] = fn()
            if verbose:
                df   = data[name]
                nans = df.isnull().sum().sum()
                pct  = nans / max(df.size, 1) * 100
                rng  = (f"{df.index.min().date()} to {df.index.max().date()}"
                        if not df.empty else "empty")
                print(f"  OK {name:<10}  shape={str(df.shape):<16}  "
                      f"NaN={pct:.1f}%  {rng}")
        except Exception as exc:
            import traceback
            print(f"  ERR {name:<10}  ERROR: {exc}")
            if verbose:
                traceback.print_exc()
            data[name] = pd.DataFrame()

    data["tr"] = data.get("fi_px", pd.DataFrame())  # legacy alias
    return data


# ─────────────────────────────────────────────────────────────────────────────
# CONVENIENCE ACCESSOR
# ─────────────────────────────────────────────────────────────────────────────

def get_series(data: dict, sheet: str, col: str) -> pd.Series:
    """Safe accessor: returns data[sheet][col], or empty Series if not found."""
    df = data.get(sheet, pd.DataFrame())
    if not df.empty and col in df.columns:
        return df[col].dropna()
    return pd.Series(dtype=float, name=col)
