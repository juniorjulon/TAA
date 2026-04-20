"""
taa_system/pillars.py
=====================
Builds the four pillar scores (F, M, S, V) for every asset class.

Architecture:
  - Each pillar_*() function takes (asset_class, data, [ext]) and returns
    a pd.Series (DatetimeIndex, z-score, ±3 winsorised).
  - A private _wavg() helper combines signals with explicit weights,
    gracefully skipping absent or empty series.
  - After combining, each pillar is re-standardised via standardise_pillar()
    to ensure equal variance contribution at the composite stage.

CRITICAL SIGN CONVENTIONS:
  Fixed Income (duration):   growth/macro signals are INVERTED
    → PMI up, GDP revision up → rates rise → bond prices fall
    → Multiply by -1 before including in FI pillar
  Credit (Corp/EM FI):       spread signals are signed for credit
    → OAS tightening (negative change) → positive signal
    → Growth signals are slightly positive (better earnings = tighter spreads)
  Equity:                    all growth signals are DIRECT (positive sign)

DATA SOURCES:
  fi_px sheet (Hoja2 Last Price) : ALWAYS used for equity/FI momentum
    because it has full history from 1999 (6,848 rows).
    The TR sheet (261 rows) is NOT used for momentum — too short.
  PE sheet (261 rows)            : used for P/E valuation with adaptive window.
  yields sheet (6,848 rows)      : used for ERP calculation.
  oas / cds / tsy sheets         : used for spread and yield signals.
"""

import pandas as pd
import numpy as np

from signals import (
    composite_price_momentum, spread_momentum, yield_momentum,
    cdx_ig_momentum, cdx_hy_momentum,
    pe_score, equity_risk_premium, relative_pe, oas_level_score,
    yield_level_score, term_spread_score, ewma_zscore, oas_stress_proxy,
    vix_score, standardise_pillar,
    OUTLIER_CLIP_Z, WINDOWS, MIN_HISTORY_DAYS,
)


# ─────────────────────────────────────────────────────────────────────────────
# PRIVATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get(df: pd.DataFrame, col: str):
    """Return df[col] if non-empty, else None."""
    if df is not None and not df.empty and col in df.columns:
        s = df[col].dropna()
        return s if len(s) >= MIN_HISTORY_DAYS else None
    return None


def _wavg(signals: dict, weights: dict) -> pd.Series:
    """
    Weighted average of z-score signals.

    Gracefully skips absent (None) or empty signals, re-normalising
    weights so the total remains 1.0. After averaging, re-standardises
    to prevent variance collapse from correlated signals.

    Parameters
    ----------
    signals : {name: pd.Series or None}
    weights : {name: float}

    Returns
    -------
    pd.Series  re-standardised pillar score, or empty Series if all missing
    """
    cols, wts = {}, {}
    for name, sig in signals.items():
        w = weights.get(name, 0.0)
        if w == 0.0 or sig is None:
            continue
        if isinstance(sig, pd.Series) and sig.dropna().empty:
            continue
        cols[name] = sig.clip(-OUTLIER_CLIP_Z, OUTLIER_CLIP_Z)
        wts[name] = w

    if not cols:
        return pd.Series(dtype=float)

    df  = pd.DataFrame(cols)
    w_s = pd.Series(wts)
    # Per-row weighted average: NaN columns skip gracefully, weights renormalize.
    num = df.mul(w_s).sum(axis=1, min_count=1)
    den = df.notna().mul(w_s).sum(axis=1).replace(0, np.nan)
    composite = (num / den).clip(-OUTLIER_CLIP_Z, OUTLIER_CLIP_Z)

    # Re-standardise to restore unit variance after signal combination
    return standardise_pillar(composite).clip(-OUTLIER_CLIP_Z, OUTLIER_CLIP_Z)


# ─────────────────────────────────────────────────────────────────────────────
# PILLAR I — FUNDAMENTALS
# ─────────────────────────────────────────────────────────────────────────────

def pillar_fundamentals(asset_class: str, data: dict,
                         ext: dict = None) -> pd.Series:
    """
    Fundamentals pillar: leading economic and earnings indicators.

    All signals in `ext` should already be z-normalised Series.
    When `ext` contains proxy signals (from proxies.py), the system
    uses those. When real Bloomberg series are connected (PMI, CESI, GDP,
    EPS), they replace the proxies automatically in main.py.

    SIGN CONVENTION:
      - Equity, Credit: growth signals are DIRECT (+)
      - FI Duration (STFI, LT Treasuries): growth signals are INVERTED (×-1)
        because growth → higher rates → lower bond prices

    Parameters
    ----------
    asset_class : one of ASSET_CLASSES
    data        : cleaned data dict from data_loader.load_all()
    ext         : {signal_name: pd.Series} — Bloomberg/proxy series
    """
    if ext is None:
        ext = {}

    # Pull from ext — returns None if key missing or series empty
    def _e(key):
        v = ext.get(key)
        if v is None or (isinstance(v, pd.Series) and v.dropna().empty):
            return None
        return v

    pmi_us    = _e("pmi_us")
    pmi_ez    = _e("pmi_ez")
    pmi_china = _e("pmi_china")
    cesi_us   = _e("cesi_us")
    cesi_ez   = _e("cesi_ez")
    cesi_china= _e("cesi_china")
    cesi_em   = _e("cesi_em")
    gdp_us    = _e("gdp_us")
    gdp_em    = _e("gdp_em")
    gdp_dm    = _e("gdp_dm")
    gdp_eu    = _e("gdp_eu")
    gdp_china = _e("gdp_china")
    eps_us    = _e("eps_us")
    eps_em    = _e("eps_em")
    eps_world = _e("eps_world")
    eps_eafe  = _e("eps_eafe")
    eps_china = _e("eps_china")
    bkev_5y   = _e("breakeven_5y")
    bkev_10y  = _e("breakeven_10y")

    fi = data.get("fi_px", pd.DataFrame())
    fed_rate = _get(fi, "fedrate")
    fed_z    = ewma_zscore(fed_rate, span=WINDOWS["long"]) if fed_rate is not None else None

    # ── Equity asset classes ────────────────────────────────────────────────
    if asset_class in ("us_equity", "us_growth", "us_value"):
        signals = {
            "pmi_us":  pmi_us,
            "cesi_us": cesi_us,
            "gdp_us":  gdp_us,
            "eps_us":  eps_us,
            # Inflation proxy: high inflation = ERP compression = slightly bearish
            "bkev":    (-bkev_5y) if bkev_5y is not None else None,
        }
        weights = {"pmi_us": 0.35, "cesi_us": 0.25, "gdp_us": 0.20,
                   "eps_us": 0.15, "bkev": 0.05}

    elif asset_class == "dm_equity":
        signals = {
            "pmi_ez":   pmi_ez,
            "cesi_ez":  cesi_ez,
            "gdp_dm":   gdp_dm,
            "eps_eafe": eps_eafe if eps_eafe is not None else eps_world,
        }
        weights = {"pmi_ez": 0.35, "cesi_ez": 0.30, "gdp_dm": 0.20, "eps_eafe": 0.15}

    elif asset_class in ("em_equity", "em_xchina"):
        signals = {
            "pmi_china": pmi_china,
            "cesi_em":   cesi_em,
            "gdp_em":    gdp_em,
            "eps_em":    eps_em,
        }
        weights = {"pmi_china": 0.30, "cesi_em": 0.25, "gdp_em": 0.25, "eps_em": 0.20}

    elif asset_class == "china_equity":
        signals = {
            "pmi_china":  pmi_china,
            "cesi_china": cesi_china,
            "gdp_china":  gdp_china,
            "eps_china":  eps_china,
        }
        weights = {"pmi_china": 0.40, "cesi_china": 0.25, "gdp_china": 0.20, "eps_china": 0.15}

    # ── Fixed Income (DURATION): all growth signals INVERTED ────────────────
    elif asset_class in ("short_term_fi", "lt_treasuries"):
        # Positive growth → rates rise → bond prices fall → INVERT all
        signals = {
            "pmi":   (-pmi_us)   if pmi_us   is not None else None,
            "cesi":  (-cesi_us)  if cesi_us  is not None else None,
            "gdp":   (-gdp_us)   if gdp_us   is not None else None,
            "bkev":  (-bkev_10y) if bkev_10y is not None else None,
            "fed":   fed_z,   # high Fed rate = restrictive = bearish duration
        }
        weights = {"pmi": 0.30, "cesi": 0.25, "gdp": 0.25, "bkev": 0.20, "fed": 0.00}

    elif asset_class == "money_market":
        # For MM: high rates & tight money = positive carry (DON'T invert)
        signals = {
            "bkev": bkev_5y,   # high inflation = Fed must hold rates high = good for MM
            "fed":  fed_z,     # high Fed rate = high MM yield = positive
        }
        weights = {"bkev": 0.40, "fed": 0.60}

    # ── Fixed Income (CREDIT): growth slightly positive (spread tightening) ─
    elif asset_class == "lt_us_corp":
        signals = {
            "pmi_us":  pmi_us,    # growth = tighter spreads
            "cesi_us": cesi_us,
            "eps_us":  eps_us,    # earnings = corporate health = tighter spreads
            "bkev":    (-bkev_10y) if bkev_10y is not None else None,  # inflation = duration headwind
        }
        weights = {"pmi_us": 0.30, "cesi_us": 0.25, "eps_us": 0.30, "bkev": 0.15}

    elif asset_class == "lt_em_fi":
        signals = {
            "pmi_china": pmi_china,
            "cesi_em":   cesi_em,
            "gdp_em":    gdp_em,
            "eps_em":    eps_em,
        }
        weights = {"pmi_china": 0.30, "cesi_em": 0.25, "gdp_em": 0.25, "eps_em": 0.20}

    else:
        signals, weights = {}, {}

    return _wavg(signals, weights)


# ─────────────────────────────────────────────────────────────────────────────
# PILLAR II — MOMENTUM
# ─────────────────────────────────────────────────────────────────────────────

def pillar_momentum(asset_class: str, data: dict) -> pd.Series:
    """
    Momentum pillar: price trends, spread dynamics.

    CRITICAL: Always uses fi_px (Hoja2 Last Price block, from 1999) for
    equity/FI price momentum — NOT the TR sheet (which has only 1 year).
    The TR sheet is only used for sector rotation analysis.

    For spread momentum (OAS, CDS), uses oas/cds sheets directly.
    """
    tr  = data.get("tr",    pd.DataFrame())   # 261 rows (sectors only)
    fi  = data.get("fi_px", pd.DataFrame())   # 6848 rows (MAIN price source)
    oas = data.get("oas",   pd.DataFrame())
    cds = data.get("cds",   pd.DataFrame())
    tsy = data.get("tsy",   pd.DataFrame())

    # ── Equity price momentum (uses fi_px — full history from 1999) ─────────
    def _eq_mom(price_col: str) -> pd.Series | None:
        """Compute composite momentum for an equity index from fi_px."""
        px = _get(fi, price_col)
        if px is None:
            return None
        return composite_price_momentum(px)

    # ── FI price momentum ───────────────────────────────────────────────────
    def _fi_mom(price_col: str) -> pd.Series | None:
        """Compute composite momentum for a fixed income TR index."""
        px = _get(fi, price_col)
        if px is None:
            return None
        return composite_price_momentum(px)

    # ── Pre-compute spread and yield momentum ────────────────────────────────
    oas_bbb    = _get(oas, "oas_bbb")
    oas_hy     = _get(oas, "oas_hy")
    oas_em     = _get(oas, "oas_em")
    oas_latam  = _get(oas, "oas_latam")
    cdx_ig     = _get(cds, "cdx_ig_spread")
    cdx_hy_p   = _get(cds, "cdx_hy_price")
    gt10       = _get(tsy, "usy_10y")
    gt02       = _get(tsy, "usy_2y")

    # Combined spread momentum helpers (1M + 3M weighted)
    def _oas_mom(oas_s, inv=True):
        if oas_s is None:
            return None
        m1 = spread_momentum(oas_s, 21,  invert=inv)
        m3 = spread_momentum(oas_s, 63,  invert=inv)
        return _wavg({"m1": m1, "m3": m3}, {"m1": 0.40, "m3": 0.60})

    oas_bbb_mom  = _oas_mom(oas_bbb)
    oas_hy_mom   = _oas_mom(oas_hy)
    oas_em_mom   = _oas_mom(oas_em)
    oas_lat_mom  = _oas_mom(oas_latam)
    cdx_ig_mom   = cdx_ig_momentum(cdx_ig)   if cdx_ig  is not None else None
    cdx_hy_mom   = cdx_hy_momentum(cdx_hy_p) if cdx_hy_p is not None else None
    gt10_mom     = (_wavg({"m1": yield_momentum(gt10, 21), "m3": yield_momentum(gt10, 63)},
                          {"m1": 0.40, "m3": 0.60}) if gt10 is not None else None)
    gt02_mom     = (_wavg({"m1": yield_momentum(gt02, 21), "m3": yield_momentum(gt02, 63)},
                          {"m1": 0.40, "m3": 0.60}) if gt02 is not None else None)

    # ── Asset-class combinations ─────────────────────────────────────────────

    if asset_class == "money_market":
        signals = {"fi_mom": _fi_mom("lt03_price"), "gt02_mom": gt02_mom}
        weights = {"fi_mom": 0.60, "gt02_mom": 0.40}

    elif asset_class == "short_term_fi":
        signals = {
            "bfu5_mom":    _fi_mom("bfu5_price"),
            "i132_mom":    _fi_mom("i132_price"),
            "gt02_mom":    gt02_mom,
            "oas_bbb_mom": oas_bbb_mom,
            "cdx_ig_mom":  cdx_ig_mom,
        }
        weights = {"bfu5_mom": 0.35, "i132_mom": 0.20, "gt02_mom": 0.20,
                   "oas_bbb_mom": 0.15, "cdx_ig_mom": 0.10}

    elif asset_class == "lt_treasuries":
        signals = {
            "bsgv_mom":    _fi_mom("bsgv_price"),
            "gt10_mom":    gt10_mom,
            "oas_bbb_mom": oas_bbb_mom,  # credit stress = flight to quality for UST
        }
        weights = {"bsgv_mom": 0.45, "gt10_mom": 0.35, "oas_bbb_mom": 0.20}

    elif asset_class == "lt_us_corp":
        signals = {
            "fi_mom":      _fi_mom("bfu5_price"),  # proxy using STFI TR
            "oas_bbb_mom": oas_bbb_mom,
            "oas_hy_mom":  oas_hy_mom,
            "cdx_ig_mom":  cdx_ig_mom,
            "gt10_mom":    gt10_mom,
        }
        weights = {"fi_mom": 0.20, "oas_bbb_mom": 0.30, "oas_hy_mom": 0.20,
                   "cdx_ig_mom": 0.20, "gt10_mom": 0.10}

    elif asset_class == "lt_em_fi":
        signals = {
            "oas_em_mom":  oas_em_mom,
            "oas_lat_mom": oas_lat_mom,
            "em_eq_mom":   _eq_mom("msci_em_px"),  # EM equity leads EM credit
        }
        weights = {"oas_em_mom": 0.40, "oas_lat_mom": 0.25, "em_eq_mom": 0.35}

    elif asset_class == "us_equity":
        # sp500_tr_px has the longest US equity history (since 1999)
        signals = {
            "price_mom": _eq_mom("sp500_tr_px"),
            "hy_mom":    oas_hy_mom,    # HY tightening = risk appetite = equity bullish
            "cdx_hy":    cdx_hy_mom,
        }
        weights = {"price_mom": 0.55, "hy_mom": 0.25, "cdx_hy": 0.20}

    elif asset_class == "us_growth":
        signals = {
            "price_mom": _eq_mom("sp500_gro_px"),
            "cdx_hy":    cdx_hy_mom,
        }
        weights = {"price_mom": 0.70, "cdx_hy": 0.30}

    elif asset_class == "us_value":
        signals = {
            "price_mom":   _eq_mom("sp500_val_px"),
            "oas_bbb_mom": oas_bbb_mom,  # value benefits from IG tightening
            "cdx_ig_mom":  cdx_ig_mom,
        }
        weights = {"price_mom": 0.55, "oas_bbb_mom": 0.25, "cdx_ig_mom": 0.20}

    elif asset_class == "dm_equity":
        signals = {
            "eafe_mom":  _eq_mom("eafe_px"),
            "acwi_mom":  _eq_mom("msci_acwi_px"),  # global as supplementary
        }
        weights = {"eafe_mom": 0.65, "acwi_mom": 0.35}

    elif asset_class in ("em_equity", "em_xchina"):
        signals = {
            "em_mom":    _eq_mom("msci_em_px"),
            "emx_mom":   _eq_mom("em_xchina_px"),
            "oas_em_mom": oas_em_mom,  # EM credit conditions
        }
        weights = {"em_mom": 0.45, "emx_mom": 0.30, "oas_em_mom": 0.25}

    elif asset_class == "china_equity":
        signals = {
            "cn_mom":    _eq_mom("china_px"),
            "oas_em_mom": oas_em_mom,
        }
        weights = {"cn_mom": 0.70, "oas_em_mom": 0.30}

    else:
        signals, weights = {}, {}

    return _wavg(signals, weights)


# ─────────────────────────────────────────────────────────────────────────────
# PILLAR III — SENTIMENT
# ─────────────────────────────────────────────────────────────────────────────

def pillar_sentiment(asset_class: str, data: dict,
                      ext: dict = None) -> pd.Series:
    """
    Sentiment pillar: volatility regime, positioning, liquidity stress.

    Prefers Bloomberg/FRED signals (VIX, MOVE, TED, DXY, EMBI, PCR)
    passed via `ext`. Falls back to OAS and CDS proxy signals from
    the data dict when external series are unavailable.

    KEY SIGNALS AND THEIR ROLE:
      VIX           : equity vol → contrarian for equity, flight-to-quality for FI
      MOVE          : bond vol  → risk-off for all FI; no proxy available
      TED spread    : funding stress → risk-off for equity/credit, positive for UST
      DXY strength  : USD → negative for EM equity and EM FI
      EMBI          : EM sovereign spreads → negative for EM assets
      PCR / AAII    : contrarian sentiment for equity

    PROXY FALLBACKS (when Bloomberg not connected):
      hy_stress proxy ≈ VIX
      ig_appetite proxy ≈ TED spread
      em_stress proxy ≈ EMBI
    """
    if ext is None:
        ext = {}

    oas = data.get("oas", pd.DataFrame())
    cds = data.get("cds", pd.DataFrame())

    def _e(key):
        v = ext.get(key)
        if v is None or (isinstance(v, pd.Series) and v.dropna().empty):
            return None
        return v

    # External signals (Bloomberg/FRED, may be proxy)
    vix_s  = _e("vix")
    move_s = _e("move")
    ted_s  = _e("ted")
    dxy_s  = _e("dxy")
    embi_s = _e("embi")
    pcr_s  = _e("pcr")

    # Internal fallback proxies from OAS/CDS
    oas_hy   = _get(oas, "oas_hy")
    oas_em   = _get(oas, "oas_em")
    cdx_ig   = _get(cds, "cdx_ig_spread")
    cdx_hy_p = _get(cds, "cdx_hy_price")

    # Pre-compute proxy-based stress signals
    hy_stress_sig   = (oas_stress_proxy(oas_hy,  for_safe_haven=False)
                       if oas_hy  is not None else None)
    em_stress_sig   = (oas_stress_proxy(oas_em,  for_safe_haven=False)
                       if oas_em  is not None else None)
    hy_safe_haven   = (oas_stress_proxy(oas_hy,  for_safe_haven=True)
                       if oas_hy  is not None else None)
    ig_appetite_sig = (-ewma_zscore(cdx_ig, span=WINDOWS["medium"])
                       if cdx_ig  is not None else None)
    cdx_hy_z        = (ewma_zscore(cdx_hy_p.pct_change(21), span=WINDOWS["medium"])
                       if cdx_hy_p is not None else None)

    # Choose best available signal: Bloomberg > proxy
    vix_eq  = vix_s  if vix_s  is not None else (
               vix_score(hy_stress_sig, "equity") if hy_stress_sig is not None else None)
    vix_fi  = vix_s  if vix_s  is not None else (
               vix_score(hy_stress_sig, "fi")     if hy_stress_sig is not None else None)
    ted_sig = ted_s  if ted_s  is not None else ig_appetite_sig
    embi_sig= embi_s if embi_s is not None else (-em_stress_sig if em_stress_sig is not None else None)

    # Invert: negative sentiment = bad for risky assets
    def _inv(s):
        return (-s) if s is not None else None

    # ── Asset-class combinations ─────────────────────────────────────────────

    if asset_class == "money_market":
        signals = {
            "hy_stress": hy_safe_haven,  # stress → demand for cash
            "ted":       ted_sig,         # funding stress → cash attractive
            "vix_fi":    vix_fi,
        }
        weights = {"hy_stress": 0.30, "ted": 0.40, "vix_fi": 0.30}

    elif asset_class == "short_term_fi":
        signals = {
            "vix_fi":  vix_fi,
            "ted":     ted_sig,
            "stress":  hy_safe_haven,   # credit stress → flight to STFI
        }
        weights = {"vix_fi": 0.40, "ted": 0.35, "stress": 0.25}

    elif asset_class == "lt_treasuries":
        signals = {
            "vix_fi":  vix_fi,
            "ted":     ted_sig,
            "stress":  hy_safe_haven,
        }
        weights = {"vix_fi": 0.40, "ted": 0.30, "stress": 0.30}

    elif asset_class == "lt_us_corp":
        # Credit stress is BAD for IG corporate spreads (invert)
        signals = {
            "vix_eq":   _inv(vix_eq),     # risk-off = bad for credit
            "hy_stress": _inv(hy_stress_sig),
            "ted":       _inv(ted_sig),
            "cdx_hy":    cdx_hy_z,        # HY price up = risk appetite = good for IG
        }
        weights = {"vix_eq": 0.30, "hy_stress": 0.25, "ted": 0.20, "cdx_hy": 0.25}

    elif asset_class == "lt_em_fi":
        signals = {
            "dxy":      (-ewma_zscore(dxy_s, span=WINDOWS["medium"])
                         if dxy_s is not None else None),  # strong USD = bad for EM
            "embi":     embi_sig,          # EM sovereign stress
            "em_stress": _inv(em_stress_sig),
            "vix_eq":   _inv(vix_eq),
        }
        weights = {"dxy": 0.30, "embi": 0.30, "em_stress": 0.20, "vix_eq": 0.20}

    elif asset_class in ("us_equity", "us_growth", "us_value"):
        signals = {
            "vix_eq":  vix_eq,      # contrarian: high VIX = buy signal
            "pcr":     pcr_s,       # contrarian: high PCR = fear = buy
            "cdx_hy":  cdx_hy_z,   # HY price momentum = risk appetite
            "ted":     _inv(ted_sig),  # funding stress = bad for equity
        }
        weights = {"vix_eq": 0.40, "pcr": 0.20, "cdx_hy": 0.25, "ted": 0.15}

    elif asset_class == "dm_equity":
        signals = {
            "vix_eq":  vix_eq,
            "cdx_hy":  cdx_hy_z,
            "ted":     _inv(ted_sig),
        }
        weights = {"vix_eq": 0.45, "cdx_hy": 0.35, "ted": 0.20}

    elif asset_class in ("em_equity", "em_xchina"):
        signals = {
            "dxy":      (-ewma_zscore(dxy_s, span=WINDOWS["medium"])
                         if dxy_s is not None else None),
            "embi":     embi_sig,
            "vix_eq":   vix_eq,
            "em_stress": _inv(em_stress_sig),
        }
        weights = {"dxy": 0.30, "embi": 0.25, "vix_eq": 0.25, "em_stress": 0.20}

    elif asset_class == "china_equity":
        signals = {
            "dxy":      (-ewma_zscore(dxy_s, span=WINDOWS["medium"])
                         if dxy_s is not None else None),
            "em_stress": _inv(em_stress_sig),
            "vix_eq":   vix_eq,
        }
        weights = {"dxy": 0.35, "em_stress": 0.35, "vix_eq": 0.30}

    else:
        signals, weights = {}, {}

    return _wavg(signals, weights)


# ─────────────────────────────────────────────────────────────────────────────
# PILLAR IV — VALUATION
# ─────────────────────────────────────────────────────────────────────────────

def pillar_valuation(asset_class: str, data: dict) -> pd.Series:
    """
    Valuation pillar: P/E, ERP, OAS levels, yield levels, term premium.

    This pillar uses:
      - PE sheet (261 rows) → pe_score() with ADAPTIVE window
        (261 obs is enough for short-window relative valuation)
      - yields sheet (6848 rows) → earnings yield for ERP calculation
        (long history = well-anchored ERP z-score)
      - OAS sheet (6937 rows) → credit spread level percentile
      - TSY sheet (6563 rows) → yield levels and term spread
    """
    pe_df   = data.get("pe",     pd.DataFrame())
    oas_df  = data.get("oas",    pd.DataFrame())
    tsy_df  = data.get("tsy",    pd.DataFrame())
    yields  = data.get("yields", pd.DataFrame())

    # P/E series from PE DataFrame (sheet 4, adaptive window in pe_score)
    pe_acwi  = _get(pe_df, "msci_acwi")
    # msci_world not directly available; use msci_eafe or msci_acwi as proxy
    _pe_eafe = _get(pe_df, "msci_eafe")
    pe_world = _pe_eafe if (_pe_eafe is not None and not _pe_eafe.dropna().empty) \
               else _get(pe_df, "msci_acwi")
    pe_em    = _get(pe_df, "msci_em")
    pe_china = _get(pe_df, "msci_china")
    pe_emx   = _get(pe_df, "msci_em_xchina")
    pe_gro   = _get(pe_df, "sp500_growth")
    pe_val   = _get(pe_df, "sp500_value")

    # Earnings yields from yields DataFrame
    sp500_ey = _get(yields, "sp500_ey")
    acwi_ey  = _get(yields, "msci_acwi_ey")
    em_ey    = _get(yields, "msci_em_ey")
    china_ey = _get(yields, "china_ey")
    emx_ey   = _get(yields, "em_xchina_ey")

    # Treasury yields and spreads
    gt10  = _get(tsy_df, "usy_10y")
    gt02  = _get(tsy_df, "usy_2y")
    ts    = _get(tsy_df, "term_spread")
    # Use TIPS 10Y real yield for ERP when available (preferred over nominal GT10)
    tips10 = _get(tsy_df, "tips_10y")
    erp_yield = tips10 if tips10 is not None else gt10  # real yield preferred

    # OAS levels
    oas_bbb   = _get(oas_df, "oas_bbb")
    oas_hy    = _get(oas_df, "oas_hy")
    oas_em    = _get(oas_df, "oas_em")
    oas_latam = _get(oas_df, "oas_latam")

    # Helper shortcuts
    def _pe_s(s): return pe_score(s) if s is not None else None
    def _erp(ey): return equity_risk_premium(ey, erp_yield) if (ey is not None and erp_yield is not None) else None
    def _oas_lv(s): return oas_level_score(s) if s is not None else None
    def _yl(s): return yield_level_score(s) if s is not None else None
    def _ts(ac): return term_spread_score(ts, ac) if ts is not None else None
    def _rel_pe(a, b): return relative_pe(a, b) if (a is not None and b is not None) else None

    # ── Asset-class combinations ─────────────────────────────────────────────

    tips5 = _get(tsy_df, "tips_5y")

    if asset_class == "money_market":
        signals = {
            "gt02":  _yl(gt02),
            "ts":    _ts("money_market"),
            "tips5": _yl(tips5) if tips5 is not None else None,
        }
        weights = {"gt02": 0.50, "ts": 0.25, "tips5": 0.25}

    elif asset_class == "short_term_fi":
        signals = {
            "gt02":    _yl(gt02),
            "oas_bbb": _oas_lv(oas_bbb),
            "ts":      _ts("short_term_fi"),
            "tips5":   _yl(tips5) if tips5 is not None else None,
        }
        weights = {"gt02": 0.35, "oas_bbb": 0.25, "ts": 0.20, "tips5": 0.20}

    elif asset_class == "lt_treasuries":
        signals = {
            "gt10":   _yl(gt10),
            "ts":     _ts("lt_treasuries"),
            "oas_bbb": _oas_lv(oas_bbb),
            "tips10": _yl(tips10) if tips10 is not None else None,
        }
        weights = {"gt10": 0.35, "ts": 0.25, "oas_bbb": 0.10, "tips10": 0.30}

    elif asset_class == "lt_us_corp":
        hy_ig_ratio = (ewma_zscore(oas_hy / oas_bbb.replace(0, np.nan))
                       if oas_hy is not None and oas_bbb is not None else None)
        signals = {
            "oas_bbb":  _oas_lv(oas_bbb),
            "oas_hy":   _oas_lv(oas_hy),
            "hy_ig":    hy_ig_ratio,  # high ratio = HY vs IG cheap = rotate to IG
            "gt10":     _yl(gt10),
        }
        weights = {"oas_bbb": 0.35, "oas_hy": 0.25, "hy_ig": 0.20, "gt10": 0.20}

    elif asset_class == "lt_em_fi":
        signals = {
            "oas_em":    _oas_lv(oas_em),
            "oas_latam": _oas_lv(oas_latam),
            "gt10":      _yl(gt10),
        }
        weights = {"oas_em": 0.45, "oas_latam": 0.25, "gt10": 0.30}

    elif asset_class == "us_equity":
        pe_ref = pe_acwi if pe_acwi is not None else pe_val
        ey_ref = sp500_ey if sp500_ey is not None else acwi_ey
        signals = {
            "pe":        _pe_s(pe_ref),
            "erp":       _erp(ey_ref),
            "rel_vs_em": _rel_pe(pe_ref, pe_em),  # US cheap vs EM = positive
        }
        weights = {"pe": 0.40, "erp": 0.40, "rel_vs_em": 0.20}

    elif asset_class == "us_growth":
        signals = {
            "pe":     _pe_s(pe_gro),
            "erp":    _erp(sp500_ey),
            "rel_gv": _rel_pe(pe_gro, pe_val),  # growth cheap vs value = positive
        }
        weights = {"pe": 0.35, "erp": 0.35, "rel_gv": 0.30}

    elif asset_class == "us_value":
        signals = {
            "pe":     _pe_s(pe_val),
            "erp":    _erp(sp500_ey),
            "rel_vg": _rel_pe(pe_val, pe_gro),  # value cheap vs growth = positive
        }
        weights = {"pe": 0.35, "erp": 0.35, "rel_vg": 0.30}

    elif asset_class == "dm_equity":
        pe_us_ref = pe_acwi if pe_acwi is not None else pe_val
        signals = {
            "pe":         _pe_s(pe_world),
            "erp":        _erp(acwi_ey),
            "rel_vs_us":  _rel_pe(pe_world, pe_us_ref),  # DM cheap vs US = positive
        }
        weights = {"pe": 0.35, "erp": 0.35, "rel_vs_us": 0.30}

    elif asset_class == "em_equity":
        pe_us_ref = pe_acwi if pe_acwi is not None else pe_val
        signals = {
            "pe":        _pe_s(pe_em),
            "erp":       _erp(em_ey),
            "rel_vs_us": _rel_pe(pe_em, pe_us_ref),  # EM cheap vs US = positive
            "oas_em":    _oas_lv(oas_em),             # EM credit cheapness
        }
        weights = {"pe": 0.30, "erp": 0.30, "rel_vs_us": 0.25, "oas_em": 0.15}

    elif asset_class == "em_xchina":
        signals = {
            "pe":     _pe_s(pe_emx),
            "erp":    _erp(emx_ey),
            "oas_em": _oas_lv(oas_em),
        }
        weights = {"pe": 0.35, "erp": 0.35, "oas_em": 0.30}

    elif asset_class == "china_equity":
        pe_us_ref = pe_acwi if pe_acwi is not None else pe_val
        signals = {
            "pe":        _pe_s(pe_china),
            "erp":       _erp(china_ey),
            "rel_vs_us": _rel_pe(pe_china, pe_us_ref),
        }
        weights = {"pe": 0.40, "erp": 0.35, "rel_vs_us": 0.25}

    else:
        signals, weights = {}, {}

    return _wavg(signals, weights)
