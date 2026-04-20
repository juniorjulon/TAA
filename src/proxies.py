"""
taa_system/proxies.py
=====================
Internal proxy signals derived from available Excel data.

When Bloomberg series (PMI, CESI, GDP, VIX, MOVE, DXY) are not yet
connected, these proxies approximate their behaviour using data already
in the workbook. The proxy design follows these principles:

PROXY LOGIC:
  Growth / PMI proxy   →  cyclical sector outperformance + OAS tightening trend
  CESI proxy           →  same as growth proxy (both capture economic momentum)
  GDP revision proxy   →  growth proxy + term spread steepening
  Inflation proxy      →  Fed Funds rate level + 10Y yield trend
  EPS growth proxy     →  earnings yield direction + price direction
  VIX proxy            →  HY OAS stress (speed of spread widening)
  TED spread proxy     →  IG CDX spread level (funding stress indicator)
  EMBI proxy           →  EM OAS level (EM sovereign stress)

IMPORTANT: When real Bloomberg series are connected in main.py,
they automatically override these proxies (Bloomberg > proxy).

All proxies return pd.Series with DatetimeIndex, winsorised ±3σ.
"""

import pandas as pd
import numpy as np

from signals import (
    ewma_zscore, spread_momentum, _adaptive_window,
    OUTLIER_CLIP_Z, WINDOWS
)


# ─────────────────────────────────────────────────────────────────────────────
# PRIVATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _safe_get(df: pd.DataFrame, col: str) -> pd.Series | None:
    """Return df[col] if it exists and is non-empty, else None."""
    if not df.empty and col in df.columns:
        s = df[col].dropna()
        return s if len(s) > 0 else None
    return None


def _weighted_combine(*pairs) -> pd.Series:
    """
    Combine multiple (series, weight) pairs into a weighted average.
    Skips None or empty series. Re-normalises weights to sum to 1.

    Parameters
    ----------
    *pairs : (pd.Series or None, float) tuples
    """
    valid    = [(s, w) for s, w in pairs if s is not None and
                isinstance(s, pd.Series) and s.dropna().shape[0] > 0]
    if not valid:
        return pd.Series(dtype=float)
    total_w  = sum(w for _, w in valid)
    result   = None
    for s, w in valid:
        contrib = (w / total_w) * s.clip(-OUTLIER_CLIP_Z, OUTLIER_CLIP_Z)
        result  = contrib if result is None else result.add(contrib, fill_value=np.nan)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# GROWTH & PMI PROXIES
# ─────────────────────────────────────────────────────────────────────────────

def growth_regime_proxy(data: dict) -> pd.Series:
    """
    Cyclical/defensive sector return differential → growth regime proxy.

    When the economy expands, cyclicals (Tech, Industrials, Financials,
    Discretionary, Materials) outperform defensives (Utilities, Staples,
    Healthcare). The 1-month return difference captures PMI-like dynamics
    at daily frequency.

    Uses TR sheet for sectors (short history) OR fi_px growth/value
    prices for longer history.
    """
    tr = data.get("tr", pd.DataFrame())
    fi = data.get("fi_px", pd.DataFrame())

    # Cyclical sectors (from TR sheet, 1-year history)
    cyc_cols  = ["sp500_tech", "sp500_ind", "sp500_fin",
                 "sp500_disc", "sp500_mat", "sp500_energy"]
    def_cols  = ["sp500_util", "sp500_health", "sp500_staples"]

    cyc_rets  = [tr[c].pct_change(21) for c in cyc_cols if c in tr.columns]
    def_rets  = [tr[c].pct_change(21) for c in def_cols if c in tr.columns]

    # Fallback: use Growth vs Value price ratio from fi_px (longer history)
    if not cyc_rets or not def_rets:
        gro = _safe_get(fi, "sp500_gro_px")
        val = _safe_get(fi, "sp500_val_px")
        if gro is not None and val is not None:
            ratio = gro.pct_change(63) - val.pct_change(63)  # 3M growth vs value
            return ewma_zscore(ratio, span=WINDOWS["medium"]).rename("growth_proxy")
        return pd.Series(dtype=float, name="growth_proxy")

    cyc_avg  = pd.concat(cyc_rets, axis=1).mean(axis=1)
    def_avg  = pd.concat(def_rets, axis=1).mean(axis=1)
    diff     = cyc_avg - def_avg   # positive = cyclicals winning = expansion
    return ewma_zscore(diff, span=WINDOWS["medium"]).rename("growth_proxy")


def credit_cycle_proxy(data: dict) -> pd.Series:
    """
    OAS tightening trend → credit cycle / growth proxy.

    Sustained OAS tightening signals improving corporate health and growth.
    Uses the 3-month and 6-month spread change direction.
    """
    oas = data.get("oas", pd.DataFrame())
    bbb = _safe_get(oas, "oas_bbb")
    if bbb is None:
        return pd.Series(dtype=float, name="credit_cycle_proxy")
    # Tightening = negative change = positive signal (invert=True)
    mom3  = spread_momentum(bbb, 63,  invert=True)
    mom6  = spread_momentum(bbb, 126, invert=True)
    proxy = _weighted_combine((mom3, 0.5), (mom6, 0.5))
    return ewma_zscore(proxy, span=WINDOWS["medium"]).rename("credit_cycle_proxy") \
           if proxy is not None else pd.Series(dtype=float)


def term_spread_regime_proxy(data: dict) -> pd.Series:
    """
    Term spread direction (steepening) → growth regime proxy.

    A steepening yield curve (rising 10Y-2Y) signals improving growth
    expectations and potential Fed tightening ahead.
    Uses the 3-month change in term spread.
    """
    tsy = data.get("tsy", pd.DataFrame())
    ts  = _safe_get(tsy, "term_spread")
    if ts is None:
        return pd.Series(dtype=float, name="term_spread_regime")
    steepening = ewma_zscore(ts.diff(63), span=WINDOWS["medium"])
    return steepening.rename("term_spread_regime")


def inflation_regime_proxy(data: dict) -> pd.Series:
    """
    Fed Funds rate + 10Y yield direction → inflation regime proxy.

    High Fed Funds (above neutral ~2.5%) = restrictive policy = inflation fight.
    Rising 10Y yield = market pricing higher inflation ahead.
    """
    fi  = data.get("fi_px", pd.DataFrame())
    tsy = data.get("tsy",   pd.DataFrame())
    fed = _safe_get(fi,  "fedrate")
    g10 = _safe_get(tsy, "usy_10y")

    parts = []
    if fed is not None:
        parts.append((ewma_zscore(fed, span=WINDOWS["long"]), 0.5))
    if g10 is not None:
        parts.append((ewma_zscore(g10.diff(63), span=WINDOWS["medium"]), 0.5))

    if not parts:
        return pd.Series(dtype=float, name="inflation_proxy")
    proxy = _weighted_combine(*parts)
    return ewma_zscore(proxy, span=WINDOWS["long"]).rename("inflation_proxy")


def earnings_revision_proxy(data: dict, region: str = "us") -> pd.Series:
    """
    Earnings yield direction + price direction → EPS revision proxy.

    If earnings yield rises WHILE prices rise → earnings improving (bullish).
    If earnings yield rises while prices fall → valuation de-rating (bearish).

    Parameters
    ----------
    region : 'us', 'em', 'dm', or 'china'
    """
    yields = data.get("yields", pd.DataFrame())
    fi     = data.get("fi_px",  pd.DataFrame())

    ey_map = {"us": "sp500_ey",  "em": "msci_em_ey",
              "dm": "msci_acwi_ey", "china": "china_ey"}
    px_map = {"us": "sp500_tr_px", "em": "msci_em_px",
              "dm": "msci_acwi_px", "china": "china_px"}

    ey  = _safe_get(yields, ey_map.get(region, "sp500_ey"))
    px  = _safe_get(fi,     px_map.get(region, "sp500_tr_px"))

    if ey is None:
        return pd.Series(dtype=float, name=f"eps_proxy_{region}")

    ey_z  = ewma_zscore(ey.diff(21), span=WINDOWS["medium"])
    if px is not None:
        px_z  = ewma_zscore(px.pct_change(21), span=WINDOWS["medium"])
        proxy = _weighted_combine((ey_z, 0.5), (px_z, 0.5))
    else:
        proxy = ey_z

    if proxy is None or (isinstance(proxy, pd.Series) and proxy.dropna().empty):
        return pd.Series(dtype=float, name=f"eps_proxy_{region}")
    return ewma_zscore(proxy, span=WINDOWS["medium"]).rename(f"eps_proxy_{region}")


# ─────────────────────────────────────────────────────────────────────────────
# SENTIMENT PROXIES
# ─────────────────────────────────────────────────────────────────────────────

def hy_stress_proxy(data: dict) -> pd.Series:
    """
    HY OAS rapid widening → VIX proxy (credit stress indicator).

    Rationale: HY spread widening is the credit-market equivalent of
    the VIX spike. When HY OAS widens fast, equity market fear tends
    to be simultaneously elevated.

    Applies contrarian scoring at extremes (same as vix_score):
    Extreme stress (very wide OAS, widening fast) → contrarian buy signal.
    """
    oas = data.get("oas", pd.DataFrame())
    hy  = _safe_get(oas, "oas_hy")
    if hy is None:
        return pd.Series(dtype=float, name="hy_stress_proxy")

    # Combine: rapid 1M change + level percentile
    from signals import pctile_rank
    chg_z     = ewma_zscore(hy.diff(21), span=WINDOWS["long"])
    w         = _adaptive_window(hy, WINDOWS["xlarge"])
    level_pct = pctile_rank(hy, w)

    # Convert percentile to [-2, +2] scale
    level_z   = -2.0 + 4.0 * level_pct   # high OAS level = stress

    stress    = _weighted_combine((chg_z, 0.6), (level_z, 0.4))
    if stress is None or (isinstance(stress, pd.Series) and stress.dropna().empty):
        return pd.Series(dtype=float)

    # Non-linear contrarian scoring (like VIX)
    s_pct    = pctile_rank(stress, _adaptive_window(stress, WINDOWS["xlarge"]))
    score    = stress.copy()
    extreme_hi = s_pct > 0.90   # crisis territory → contrarian buy
    extreme_lo = s_pct < 0.10   # very calm → complacency warning
    score[extreme_hi] =  2.0
    score[extreme_lo] = -1.5
    return score.clip(-OUTLIER_CLIP_Z, OUTLIER_CLIP_Z).rename("hy_stress_proxy")


def ig_risk_appetite(data: dict) -> pd.Series:
    """
    IG CDX spread level → risk appetite / TED spread proxy.

    Low and falling IG spreads = risk-on / cheap funding = positive.
    CDX IG captures institutional risk appetite more directly than retail surveys.
    """
    cds = data.get("cds", pd.DataFrame())
    ig  = _safe_get(cds, "cdx_ig_spread")
    if ig is None:
        return pd.Series(dtype=float, name="ig_risk_appetite")

    level_z = -ewma_zscore(ig, span=WINDOWS["medium"])   # low spread = positive
    chg_z   = -ewma_zscore(ig.diff(21), span=WINDOWS["medium"])  # tightening = +
    proxy   = _weighted_combine((level_z, 0.5), (chg_z, 0.5))
    return (proxy if proxy is not None else pd.Series(dtype=float)
            ).clip(-OUTLIER_CLIP_Z, OUTLIER_CLIP_Z).rename("ig_risk_appetite")


def em_stress_proxy(data: dict) -> pd.Series:
    """
    EM OAS level → EMBI sovereign stress proxy.

    Wide EM corporate spreads correlate closely with sovereign spreads
    (EMBI) and USD strength. High = EM stress = negative for EM assets.
    """
    oas     = data.get("oas", pd.DataFrame())
    em_oas  = _safe_get(oas, "oas_em")
    lat_oas = _safe_get(oas, "oas_latam")

    parts = []
    if em_oas  is not None:
        parts.append((-ewma_zscore(em_oas,  span=WINDOWS["long"]), 0.6))
    if lat_oas is not None:
        parts.append((-ewma_zscore(lat_oas, span=WINDOWS["long"]), 0.4))

    if not parts:
        return pd.Series(dtype=float, name="em_stress_proxy")
    proxy = _weighted_combine(*parts)
    return (proxy if proxy is not None else pd.Series(dtype=float)
            ).clip(-OUTLIER_CLIP_Z, OUTLIER_CLIP_Z).rename("em_stress_proxy")


# ─────────────────────────────────────────────────────────────────────────────
# MASTER PROXY BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_proxy_ext(data: dict, verbose: bool = False) -> dict:
    """
    Build all internal proxy signals and return as an `ext` dict
    compatible with pillar_fundamentals() and pillar_sentiment().

    This function is called when Bloomberg/FRED series are unavailable.
    When real series ARE available (passed through main.py), they
    automatically override these proxies.

    Parameters
    ----------
    data    : cleaned data dict from data_loader.load_all()
    verbose : print proxy observation counts

    Returns
    -------
    dict : {signal_name: pd.Series or None}
      Keys match the `ext` parameter expected by pillar functions.
      Private keys starting with '_' contain diagnostics.
    """
    # Compute base signals
    growth_us    = growth_regime_proxy(data)
    credit_cycle = credit_cycle_proxy(data)
    ts_regime    = term_spread_regime_proxy(data)
    infl_proxy   = inflation_regime_proxy(data)
    eps_us       = earnings_revision_proxy(data, "us")
    eps_em       = earnings_revision_proxy(data, "em")
    hy_stress    = hy_stress_proxy(data)
    ig_appetite  = ig_risk_appetite(data)
    em_stress    = em_stress_proxy(data)

    if verbose:
        for nm, s in [("growth_proxy", growth_us), ("credit_cycle", credit_cycle),
                      ("ts_regime", ts_regime), ("inflation", infl_proxy),
                      ("eps_us", eps_us), ("eps_em", eps_em),
                      ("hy_stress", hy_stress), ("ig_appetite", ig_appetite),
                      ("em_stress", em_stress)]:
            n    = s.dropna().shape[0] if isinstance(s, pd.Series) else 0
            last = s.dropna().iloc[-1] if n > 0 else float("nan")
            print(f"    {nm:<22}  obs={n:5d}  last={last:+.3f}")

    # Build composite proxies for each signal type
    pmi_us_proxy   = _weighted_combine(
        (growth_us, 0.40), (credit_cycle, 0.35), (ts_regime, 0.25))
    pmi_ez_proxy   = _weighted_combine(
        (credit_cycle, 0.55), (ts_regime, 0.45))
    pmi_china_proxy = _weighted_combine(
        (em_stress, 0.60), (eps_em, 0.40))
    cesi_us_proxy  = _weighted_combine(
        (growth_us, 0.55), (credit_cycle, 0.45))
    cesi_em_proxy  = _weighted_combine(
        (em_stress, 0.55), (eps_em, 0.45))
    gdp_us_proxy   = _weighted_combine(
        (growth_us, 0.40), (ts_regime, 0.30), (eps_us, 0.30))
    gdp_em_proxy   = _weighted_combine(
        (em_stress, 0.55), (eps_em, 0.45))

    return {
        # ── Fundamentals proxies ──────────────────────────────────────────
        "pmi_us":        pmi_us_proxy,
        "pmi_ez":        pmi_ez_proxy,
        "pmi_china":     pmi_china_proxy,
        "cesi_us":       cesi_us_proxy,
        "cesi_ez":       pmi_ez_proxy,     # reuse EZ proxy
        "cesi_em":       cesi_em_proxy,
        "gdp_us":        gdp_us_proxy,
        "gdp_em":        gdp_em_proxy,
        "eps_us":        eps_us,
        "eps_em":        eps_em,
        "breakeven_5y":  infl_proxy,       # inflation proxy for STFI
        "breakeven_10y": infl_proxy,       # inflation proxy for LT duration
        # ── Sentiment proxies ─────────────────────────────────────────────
        "vix":   hy_stress,    # HY stress ≈ VIX (fear gauge)
        "move":  None,         # no proxy available (needs MOVE Index)
        "ted":   ig_appetite,  # IG credit ≈ TED spread (funding conditions)
        "dxy":   None,         # no proxy (needs FX data)
        "embi":  em_stress,    # EM OAS ≈ EMBI sovereign spreads
        "pcr":   ig_appetite,  # IG appetite ≈ put/call ratio (risk sentiment)
        # ── Diagnostic series (for reporting only) ────────────────────────
        "_growth_us":    growth_us,
        "_credit_cycle": credit_cycle,
        "_ts_regime":    ts_regime,
        "_infl_proxy":   infl_proxy,
        "_hy_stress":    hy_stress,
        "_ig_appetite":  ig_appetite,
        "_em_stress":    em_stress,
    }
