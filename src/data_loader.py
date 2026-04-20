"""
taa_system/data_loader.py
=========================
Loads, validates, and cleans every relevant sheet from the TAA Excel workbook.

Excel sheet inventory (sheets Main, PAR_2, B1, B2 are intentionally excluded):
  OAS   : ICE BofA credit spreads — long history from 1999 (~6,900 rows)
  4     : PE ratios, earnings yields, TR price indices — from 2015 (~2,686 rows)
  5     : VIX, MOVE, CDX, Treasury yields, sentiment indicators — from 2015 (~2,669 rows)
  F1    : PMI, CESI, GDP forecasts — from 2016 (~2,490 rows)
  F2    : Additional PMI, CESI, GDP — from 2016 (~2,490 rows)
  F3    : Forward EPS, breakeven inflation — from 2016 (~2,490 rows)
  AAII  : AAII investor sentiment (weekly) — from ~1987

load_all() returns a dict with these keys:
  'oas'   : OAS credit spreads (long history)
  'pe'    : Forward P/E ratios (from sheet 4)
  'yields': Earnings yields (from sheet 4) — used for ERP
  'fi_px' : TR price levels (from sheet 4) — primary momentum source
  'tsy'   : Treasury yields + term_spread + TIPS + Fed Funds (from sheet 5)
  'cds'   : CDX indices (from sheet 5)
  'mkt'   : VIX, MOVE, PCR, SKEW, TED, VSTOXX (from sheet 5) — raw levels
  'f1'    : PMI, CESI, GDP (from sheets F1+F2 combined)
  'f3'    : Forward EPS, breakeven inflation (from sheet F3)
  'aaii'  : AAII bull-bear spread (weekly → daily resampled)
"""

import warnings
import pandas as pd
import numpy as np

from config import (
    EXCEL_PATH,
    OAS_COLS, SHEET4_PE_COLS, SHEET4_EY_COLS, SHEET4_TR_COLS,
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
# OAS — long history credit spreads (unchanged from original design)
# ─────────────────────────────────────────────────────────────────────────────

def load_oas() -> pd.DataFrame:
    """
    ICE BofA OAS spreads from FRED, long history from 1999.
    Spreads in decimal percent (1.53 = 153 bps).
    """
    df = pd.read_excel(EXCEL_PATH, sheet_name="OAS", parse_dates=["Date"])
    df = df.set_index("Date")
    df = _select_rename(df, OAS_COLS)
    df = _sort_asc(df)
    df = df.clip(lower=0, upper=30).replace(0, np.nan)
    df = df.ffill(limit=MAX_FFILL_DAYS)
    _validate_index(df, "OAS")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# SHEET 4 — PE, Earnings Yields, TR price levels
# ─────────────────────────────────────────────────────────────────────────────

def _load_sheet4_raw() -> pd.DataFrame:
    df = pd.read_excel(EXCEL_PATH, sheet_name="4")
    df = _parse_date_col(df)
    return df


def load_pe() -> pd.DataFrame:
    """
    Forward P/E ratios from sheet 4 (~2,686 rows from 2015).
    Adaptive window used in pe_score() since history is shorter than 10Y.
    """
    df  = _load_sheet4_raw()
    out = _select_rename(df, SHEET4_PE_COLS)
    out = out.dropna(axis=1, how="all")
    out = out.ffill(limit=MAX_FFILL_DAYS)
    out = out.clip(lower=0.01, upper=100).replace(0.01, np.nan)
    _validate_index(out, "PE")
    return out


def load_yields() -> pd.DataFrame:
    """
    Earnings yields (%) from sheet 4 — used for ERP calculation.
    Values are in percent (e.g. 4.22 means 4.22% earnings yield).
    """
    df  = _load_sheet4_raw()
    out = _select_rename(df, SHEET4_EY_COLS)
    out = out.dropna(axis=1, how="all")
    out = out.ffill(limit=MAX_FFILL_DAYS)
    out = out.clip(lower=0, upper=30)  # > 30% EY would be an error
    _validate_index(out, "YIELDS")
    return out


def load_fi_px() -> pd.DataFrame:
    """
    Total Return price level indices from sheet 4.
    Primary source for equity and FI price momentum (replaces old Hoja2).
    Adds bfu5_price alias (Bloomberg 1-5Y Tsy not available → uses i132_price).
    """
    df  = _load_sheet4_raw()
    out = _select_rename(df, SHEET4_TR_COLS)
    out = _clean_prices(out)
    out = _remove_return_outliers(out)

    # bfu5_price (Bloomberg 1-5Y Treasury) not in sheet 4 — alias i132_price
    if "i132_price" in out.columns and "bfu5_price" not in out.columns:
        out["bfu5_price"] = out["i132_price"]

    _validate_index(out, "FI_PX")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# SHEET 5 — Market data: yields, CDX, VIX, MOVE, sentiment
# ─────────────────────────────────────────────────────────────────────────────

def _load_sheet5_raw() -> pd.DataFrame:
    df = pd.read_excel(EXCEL_PATH, sheet_name="5")
    df = _parse_date_col(df)
    return df


def load_tsy() -> pd.DataFrame:
    """
    US Treasury yields (2Y, 10Y, 3M T-bill), TIPS real yields, Fed Funds.
    Adds computed term_spread = 10Y − 2Y.
    """
    df  = _load_sheet5_raw()
    tsy_cols = {k: v for k, v in SHEET5_COLS.items()
                if v in ("usy_10y", "usy_2y", "tbill_3m",
                         "tips_10y", "tips_5y", "fedrate")}
    out = _select_rename(df, tsy_cols)
    out = _sort_asc(out)
    out = out.clip(lower=-5, upper=25)   # yields outside [-5%, 25%] are errors
    out = out.ffill(limit=MAX_FFILL_DAYS)

    if "usy_10y" in out.columns and "usy_2y" in out.columns:
        out["term_spread"] = out["usy_10y"] - out["usy_2y"]

    _validate_index(out, "TSY")
    return out


def load_cds() -> pd.DataFrame:
    """
    CDX IG spread (bps) and CDX HY price (~100 par) from sheet 5.
    IBOXUMAE = CDX NA IG 5Y spread in bps; tightening = positive for credit.
    IBOXHYAE = CDX NA HY 5Y price; rising = positive for risk appetite.
    """
    df  = _load_sheet5_raw()
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
    Sentiment and volatility indicators from sheet 5: VIX, MOVE, PCR, SKEW,
    VSTOXX, VIX3M, TED proxy. Raw levels — normalisation done in signals.py.
    """
    df  = _load_sheet5_raw()
    mkt_cols = {k: v for k, v in SHEET5_COLS.items()
                if v in ("vix", "move", "vstoxx", "vix3m",
                         "ted", "pcr", "skew")}
    out = _select_rename(df, mkt_cols)
    out = _sort_asc(out)
    out = out.ffill(limit=MAX_FFILL_DAYS)
    out = out.clip(lower=0)   # all are non-negative by construction

    _validate_index(out, "MKT")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# SHEETS F1 + F2 — Fundamentals (PMI, CESI, GDP)
# ─────────────────────────────────────────────────────────────────────────────

def load_f1() -> pd.DataFrame:
    """
    F1 + F2 fundamentals: PMI (ISM, EZ, China, Japan, UK, Global),
    CESI (US, EUR, China, Global, EM, UK, Japan), GDP forecasts.
    Returns combined DataFrame with all available fundamental series.
    """
    f1 = pd.read_excel(EXCEL_PATH, sheet_name="F1")
    f1 = _parse_date_col(f1)
    f1 = _select_rename(f1, SHEET_F1_COLS)

    f2 = pd.read_excel(EXCEL_PATH, sheet_name="F2")
    f2 = _parse_date_col(f2)
    f2 = _select_rename(f2, SHEET_F2_COLS)

    # Merge F1 and F2 on date index (outer join to keep all dates)
    combined = f1.join(f2, how="outer")
    combined = _sort_asc(combined)
    # Forward-fill monthly data over daily calendar (PMI/CESI published ~monthly)
    combined = combined.ffill(limit=MAX_FFILL_DAYS * 5)  # allow up to 25-day fill for monthly
    _validate_index(combined, "F1")
    return combined


# ─────────────────────────────────────────────────────────────────────────────
# SHEET F3 — Forward EPS, Inflation
# ─────────────────────────────────────────────────────────────────────────────

def load_f3() -> pd.DataFrame:
    """
    Forward EPS levels and breakeven inflation from sheet F3.
    EPS signals use month-over-month % change (revision) not raw level.
    """
    df = pd.read_excel(EXCEL_PATH, sheet_name="F3")
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
    Only the non-NaN rows (when actual survey data exists) are used.
    """
    df = pd.read_excel(EXCEL_PATH, sheet_name="AAII")
    df = _parse_date_col(df)

    # Only keep columns that are in SHEET_AAII_COLS mapping
    out = _select_rename(df, SHEET_AAII_COLS)
    out = out.dropna(how="all")
    out = _sort_asc(out)

    # Resample to daily business days and forward-fill (weekly → daily)
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
      'oas'   : OAS credit spreads (long history from 1999)
      'pe'    : Forward P/E ratios (sheet 4, from 2015)
      'yields': Earnings yields (sheet 4, from 2015)
      'fi_px' : TR price levels (sheet 4, from 2015) — primary momentum source
      'tsy'   : Treasury yields + TIPS + term_spread (sheet 5, from 2015)
      'cds'   : CDX indices (sheet 5, from 2015)
      'mkt'   : VIX, MOVE, PCR, SKEW, TED (sheet 5, from 2015)
      'f1'    : PMI, CESI, GDP fundamentals (sheets F1+F2, from 2016)
      'f3'    : Forward EPS, breakeven inflation (sheet F3, from 2016)
      'aaii'  : AAII bull-bear spread (weekly → daily)

    Legacy key compatibility (for pillars.py / proxies.py):
      'tr'    : alias for fi_px (short TR data lived here in old design)
    """
    if verbose:
        print("Loading and cleaning data...")

    loaders = {
        "oas":    load_oas,
        "pe":     load_pe,
        "yields": load_yields,
        "fi_px":  load_fi_px,
        "tsy":    load_tsy,
        "cds":    load_cds,
        "mkt":    load_mkt,
        "f1":     load_f1,
        "f3":     load_f3,
        "aaii":   load_aaii,
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
                print(f"  OK {name:<8}  shape={str(df.shape):<14}  "
                      f"NaN={pct:.1f}%  {rng}")
        except Exception as exc:
            import traceback
            print(f"  ERR {name:<8}  ERROR: {exc}")
            if verbose:
                traceback.print_exc()
            data[name] = pd.DataFrame()

    # Legacy alias: pillars.py uses data['tr'] for sector TR (not critical now)
    data["tr"] = data.get("fi_px", pd.DataFrame())

    return data


# ─────────────────────────────────────────────────────────────────────────────
# CONVENIENCE ACCESSOR
# ─────────────────────────────────────────────────────────────────────────────

def get_series(data: dict, sheet: str, col: str) -> pd.Series:
    """
    Safe accessor: returns data[sheet][col], or empty Series if not found.
    """
    df = data.get(sheet, pd.DataFrame())
    if not df.empty and col in df.columns:
        return df[col].dropna()
    return pd.Series(dtype=float, name=col)
