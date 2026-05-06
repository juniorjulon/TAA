"""
src/build_custom_series.py
==========================
Computes all custom series and writes data/custom_series.xlsx.

Run:
  python src/build_custom_series.py

Each column in custom_series.xlsx corresponds to a series_id registered
in config/taa_config.xlsx:DataSeries with series_type="custom".
All columns are stored as raw levels; signal_engine.py normalises them
according to each series' transform_code before pillar aggregation.

To add a new custom series:
  1. Add the computation below under the appropriate section.
  2. Add it to the `series` dict.
  3. Register a DataSeries row (series_type="custom", input_sheet="custom_series").
  4. Add a SignalMapping row with sign and weight.
  5. Run: python src/build_custom_series.py && python src/main.py
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings("ignore")

from data_loader import load_all
from signals import pe_score
from config import CUSTOM_SERIES_PATH, MAX_FFILL_DAYS


def _safe(df: pd.DataFrame, col: str) -> pd.Series:
    """Return df[col] if available, else empty Series."""
    if not df.empty and col in df.columns:
        return df[col].dropna()
    return pd.Series(dtype=float, name=col)


def _blended_gdp(cur: pd.Series, nxt: pd.Series) -> pd.Series:
    """Time-varying blend: w_cur = month/12; blend = w_cur*cur + (1-w_cur)*nxt."""
    if cur.dropna().empty:
        return nxt
    if nxt.dropna().empty:
        return cur
    idx   = cur.index.union(nxt.index)
    cur   = cur.reindex(idx).ffill()
    nxt   = nxt.reindex(idx).ffill()
    w_cur = pd.Series(idx.month / 12, index=idx)
    return (w_cur * cur + (1 - w_cur) * nxt).rename("blended_gdp")


def _log_pe_ratio(pe_a: pd.Series, pe_b: pd.Series) -> pd.Series:
    """
    Log ratio log(PE_b / PE_a): positive when A is cheap relative to B.

    Convention: _rel_pe(a, b) → positive when a is CHEAP (low PE) vs b.
    This ensures sign=+1 in SignalMapping = bullish for the cheaper asset.
    """
    ratio = pe_b / pe_a.replace(0, np.nan)
    ratio = ratio.replace([np.inf, -np.inf], np.nan)
    return np.log(ratio.clip(lower=0.01))


def build_custom_series(verbose: bool = True) -> pd.DataFrame:
    """
    Compute all custom series from loaded Excel data.

    Returns a DataFrame indexed by date, one column per series_id.
    """
    if verbose:
        print("Loading source data...")

    data = load_all(verbose=verbose)

    f1   = data.get("f1",     pd.DataFrame())
    mkt  = data.get("mkt",    pd.DataFrame())
    tsy  = data.get("tsy",    pd.DataFrame())
    oas  = data.get("oas",    pd.DataFrame())
    pe   = data.get("pe",     pd.DataFrame())
    yld  = data.get("yields", pd.DataFrame())
    cds  = data.get("cds",    pd.DataFrame())

    series: dict[str, pd.Series] = {}

    # ── PMI Composites ────────────────────────────────────────────────────────

    def _pmi(mfg_col: str, svcs_col: str = None) -> pd.Series:
        mfg = _safe(f1, mfg_col)
        if svcs_col:
            svcs = _safe(f1, svcs_col)
            if not svcs.dropna().empty and not mfg.dropna().empty:
                return (mfg + svcs) / 2
        return mfg

    series["pmi_us"]    = _pmi("pmi_ism_mfg",   "pmi_ism_svcs")
    series["pmi_ez"]    = _pmi("pmi_ez_mfg",     "pmi_ez_svcs")
    series["pmi_china"] = _pmi("pmi_china_mfg",  "pmi_china_svcs")

    # ── GDP Blends ────────────────────────────────────────────────────────────

    # GDP blends — use renamed series (26 = current year, 27 = next year)
    series["gdp_us"]    = _blended_gdp(_safe(f1, "gdp_forecast_us_26"),    _safe(f1, "gdp_forecast_us_27"))
    series["gdp_dm"]    = _blended_gdp(_safe(f1, "gdp_forecast_dm_26"),    _safe(f1, "gdp_forecast_dm_27"))
    series["gdp_em"]    = _blended_gdp(_safe(f1, "gdp_forecast_em_26"),    _safe(f1, "gdp_forecast_em_27"))
    series["gdp_eu"]    = _blended_gdp(_safe(f1, "gdp_forecast_eu_26"),    _safe(f1, "gdp_forecast_eu_27"))
    series["gdp_japan"] = _blended_gdp(_safe(f1, "gdp_forecast_jp_26"),    _safe(f1, "gdp_forecast_jp_27"))
    series["gdp_china"] = _blended_gdp(_safe(f1, "gdp_forecast_cn_26"),    _safe(f1, "gdp_forecast_cn_27"))

    # ── Rate Environment ──────────────────────────────────────────────────────

    tbill_3m = _safe(tsy, "tbill_3m")
    sofr      = _safe(tsy, "sofr")
    fedrate   = _safe(tsy, "fedrate")
    pce_yoy   = _safe(tsy, "pce_yoy")
    usy_10y   = _safe(tsy, "usy_10y")
    usy_2y    = _safe(tsy, "usy_2y")
    tips_10y  = _safe(tsy, "tips_10y")
    tips_5y   = _safe(tsy, "tips_5y")

    # Modern TED = 3M T-bill − SOFR (SOFR inception: 2018-04-01).
    # Gate to 2018-04-01 to avoid NaN padding warping the EWMA warm-up.
    # EWMA reliable_from = 2018-04-01 + 756 days ≈ 2020-12-01.
    modern_ted_loaded = _safe(tsy, "modern_ted")
    if not modern_ted_loaded.dropna().empty:
        series["modern_ted"] = modern_ted_loaded["2018-04-01":]
    elif not tbill_3m.dropna().empty and not sofr.dropna().empty:
        idx = tbill_3m.index.union(sofr.index)
        ted = (tbill_3m.reindex(idx).ffill() - sofr.reindex(idx).ffill()).dropna()
        series["modern_ted"] = ted["2018-04-01":]

    # Real Fed Funds = FDTR − PCE YoY (monthly → ffill 35 days)
    if not fedrate.dropna().empty and not pce_yoy.dropna().empty:
        idx = fedrate.index.union(pce_yoy.index)
        ff  = fedrate.reindex(idx).ffill(limit=MAX_FFILL_DAYS)
        pce = pce_yoy.reindex(idx).ffill(limit=35)
        series["real_ff"] = (ff - pce).clip(-10, 15)

    # Term spread = 10Y − 2Y (raw basis-point difference)
    if not usy_10y.dropna().empty and not usy_2y.dropna().empty:
        idx = usy_10y.index.union(usy_2y.index)
        series["term_spread"] = (usy_10y.reindex(idx).ffill() -
                                 usy_2y.reindex(idx).ffill())

    # ── Equity Risk Premium (ERP) ─────────────────────────────────────────────
    # ERP = Earnings Yield (%) − TIPS 10Y (%). Both in percent.

    def _erp(ey_col: str, bond: pd.Series) -> pd.Series:
        ey = _safe(yld, ey_col)
        if ey.dropna().empty or bond.dropna().empty:
            return pd.Series(dtype=float)
        idx = ey.index.union(bond.index)
        return (ey.reindex(idx).ffill() - bond.reindex(idx).ffill()).dropna()

    series["erp_us"]        = _erp("sp500_ey",       tips_10y)
    series["erp_acwi"]      = _erp("msci_acwi_ey",   tips_10y)
    series["erp_em"]        = _erp("msci_em_ey",     tips_10y)
    series["erp_em_xchina"] = _erp("em_xchina_ey",   tips_10y)
    series["erp_china"]     = _erp("china_ey",        tips_10y)

    # ── P/E Scores ────────────────────────────────────────────────────────────
    # pe_score() returns [-2, +2]: cheap=positive, expensive=negative.

    def _pe(col: str) -> pd.Series:
        s = _safe(pe, col)
        return pe_score(s) if not s.dropna().empty else pd.Series(dtype=float)

    series["pe_score_sp500"] = _pe("sp500")
    series["pe_score_eafe"]  = _pe("msci_eafe")
    series["pe_score_em"]    = _pe("msci_em")
    series["pe_score_emx"]   = _pe("msci_em_xchina")
    series["pe_score_china"] = _pe("msci_china")
    series["pe_score_gro"]   = _pe("sp500_growth")
    series["pe_score_val"]   = _pe("sp500_value")

    # ── Relative P/E (log ratios, raw) ───────────────────────────────────────
    # Stored as log(PE_a / PE_b); signal_engine applies ewma_z.
    # A cheap relative to B → low ratio → low log → signal_engine's ewma_z negative
    # → sign −1 in SignalMapping flips to positive. Convention: higher series_id cheaper.

    pe_sp500  = _safe(pe, "sp500")
    pe_eafe   = _safe(pe, "msci_eafe")
    pe_em     = _safe(pe, "msci_em")
    pe_emx    = _safe(pe, "msci_em_xchina")
    pe_china  = _safe(pe, "msci_china")
    pe_gro    = _safe(pe, "sp500_growth")
    pe_val    = _safe(pe, "sp500_value")

    def _rel_pe(a: pd.Series, b: pd.Series) -> pd.Series:
        if a.dropna().empty or b.dropna().empty:
            return pd.Series(dtype=float)
        idx = a.index.union(b.index)
        return _log_pe_ratio(a.reindex(idx).ffill(), b.reindex(idx).ffill())

    series["rel_pe_gro_val"]   = _rel_pe(pe_gro,   pe_val)
    series["rel_pe_val_gro"]   = _rel_pe(pe_val,   pe_gro)
    series["rel_pe_dm_us"]     = _rel_pe(pe_eafe,  pe_sp500)
    series["rel_pe_em_us"]     = _rel_pe(pe_em,    pe_sp500)
    series["rel_pe_us_em"]     = _rel_pe(pe_sp500, pe_em)
    series["rel_pe_china_us"]  = _rel_pe(pe_china, pe_sp500)

    # ── OAS-Derived Custom Series ─────────────────────────────────────────────

    oas_bbb = _safe(oas, "oas_bbb")
    oas_hy  = _safe(oas, "oas_hy")
    oas_em  = _safe(oas, "oas_em")

    # HY/IG ratio: raw spread ratio (signal_engine applies ewma_z)
    if not oas_hy.dropna().empty and not oas_bbb.dropna().empty:
        idx = oas_hy.index.union(oas_bbb.index)
        series["hy_ig_ratio"] = (oas_hy.reindex(idx).ffill() /
                                 oas_bbb.reindex(idx).ffill().replace(0, np.nan)).dropna()

    # Stress proxies: raw 1-month spread change (positive = widening = stress up).
    # Sign in SignalMapping controls direction:
    #   sign = -1 → bearish for credit/EM (high stress = negative)
    #   sign = +1 → bullish for safe-haven (high stress = positive)
    if not oas_hy.dropna().empty:
        series["hy_stress"]     = oas_hy.diff(21).dropna()
        series["hy_safe_haven"] = oas_hy.diff(21).dropna()

    if not oas_em.dropna().empty:
        series["em_stress"] = oas_em.diff(21).dropna()
        series["embi"]      = oas_em.diff(21).dropna()

    # ── EPS Revision Composite (multi-horizon, Chan/Jegadeesh/Lakonishok 1996) ──
    # 21-day (1M) revision momentum misses the 3–6 month earnings cycle.
    # Composite: 40% × pct_change(3M) + 60% × pct_change(6M); stored as raw level.
    # signal_engine applies ewma_z to normalize.

    f3 = data.get("f3", pd.DataFrame())

    def _eps_composite(col: str) -> pd.Series:
        s = _safe(f3, col)
        if s.dropna().shape[0] < 126:
            return pd.Series(dtype=float, name=col)
        rev_3m = s.pct_change(63)
        rev_6m = s.pct_change(126)
        idx = rev_3m.index.union(rev_6m.index)
        comp = (0.40 * rev_3m.reindex(idx).ffill() +
                0.60 * rev_6m.reindex(idx).ffill())
        return comp.dropna()

    series["eps_rev_us"]    = _eps_composite("eps_fwd_us")
    series["eps_rev_em"]    = _eps_composite("eps_fwd_em")
    series["eps_rev_eafe"]  = _eps_composite("eps_fwd_eafe")
    series["eps_rev_china"] = _eps_composite("eps_fwd_china")

    # ── CDX Momentum ─────────────────────────────────────────────────────────
    # Pre-computed multi-horizon momentum; signal_engine applies ewma_z.

    cdx_ig_spread = _safe(cds, "cdx_ig_spread")
    cdx_hy_price  = _safe(cds, "cdx_hy_price")

    if not cdx_ig_spread.dropna().empty:
        from signals import cdx_ig_momentum
        series["cdx_ig_mom"] = cdx_ig_momentum(cdx_ig_spread)

    if not cdx_hy_price.dropna().empty:
        from signals import cdx_hy_momentum
        series["cdx_hy_mom"] = cdx_hy_momentum(cdx_hy_price)

    # ── Assemble DataFrame ────────────────────────────────────────────────────

    frames = {}
    for name, s in series.items():
        if isinstance(s, pd.Series) and not s.dropna().empty:
            frames[name] = s.rename(name)
        else:
            if verbose:
                print(f"  SKIP {name} — empty")

    df = pd.DataFrame(frames)
    df.index.name = "Date"
    df.sort_index(inplace=True)

    if verbose:
        print(f"\nCustom series built: {len(df.columns)} series, "
              f"{len(df)} rows ({df.index.min().date()} to {df.index.max().date()})")
        for col in df.columns:
            n = df[col].dropna().shape[0]
            start = df[col].dropna().index.min().date() if n > 0 else "—"
            print(f"  {col:<25} {n:>5} rows  from {start}")

    return df


def main():
    df = build_custom_series(verbose=True)

    out_path = CUSTOM_SERIES_PATH
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_excel(out_path, sheet_name="custom_series", index=True)
    print(f"\nWritten: {out_path}")


if __name__ == "__main__":
    main()
