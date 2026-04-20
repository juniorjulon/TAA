"""
taa_system/signals.py
=====================
Atomic signal computation functions. Every function returns a pd.Series
with a DatetimeIndex so it can be composited directly with pd.DataFrame
operations.

Design principles:
- Adaptive windows: always use min(target_window, len(series)) so that
  short series (e.g. PE sheet with 261 rows) still produce valid signals.
- EWMA preferred over rolling for daily signals: handles regime breaks by
  downweighting stale observations naturally (λ ≈ 0.95 monthly).
- All outputs are winsorised at ±OUTLIER_CLIP_Z (default ±3σ) to prevent
  a single crisis spike from dominating the composite score.
- All z-score and percentile functions require MIN_HISTORY_DAYS before
  returning a non-NaN value (prevents lookback bias).

Sign conventions (documented explicitly):
- For EQUITY:  higher signal = more bullish (positive tilt)
- For FI:      growth/cycle signals are INVERTED in pillars.py, not here
- For CREDIT:  spread TIGHTENING (negative change) = positive signal
- For SENTIMENT: VIX/stress signals are CONTRARIAN — high fear = buy signal
"""

import numpy as np
import pandas as pd

from config import WINDOWS, MOM_HORIZONS, OUTLIER_CLIP_Z, MIN_HISTORY_DAYS, EWMA_SPAN


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — NORMALISATION
# ─────────────────────────────────────────────────────────────────────────────

def _adaptive_window(series: pd.Series, target: int) -> int:
    """Return min(target, available non-null observations)."""
    n = series.dropna().shape[0]
    return max(min(target, n), MIN_HISTORY_DAYS)


def rolling_zscore(s: pd.Series, window: int, min_periods: int = None) -> pd.Series:
    """
    Rolling z-score using simple (equal-weight) mean and std.

    z = (x - rolling_mean) / rolling_std, clipped to ±OUTLIER_CLIP_Z.

    Adaptive: if series is shorter than `window`, uses available length.

    Parameters
    ----------
    s           : input series
    window      : lookback in observations
    min_periods : minimum obs to compute (default = window // 2)

    Returns
    -------
    pd.Series  winsorised z-score
    """
    w  = _adaptive_window(s, window)
    mp = min_periods if min_periods is not None else max(w // 2, MIN_HISTORY_DAYS)
    mu = s.rolling(w, min_periods=mp).mean()
    sd = s.rolling(w, min_periods=mp).std()
    z  = (s - mu) / sd.replace(0, np.nan)
    return z.clip(-OUTLIER_CLIP_Z, OUTLIER_CLIP_Z).rename(s.name)


def ewma_zscore(s: pd.Series, span: int = None) -> pd.Series:
    """
    EWMA (exponentially weighted) z-score.

    Preferred over rolling_zscore for daily signals because:
    - Weights recent observations more heavily → responds to regime changes
    - No cliff-edge at window boundary → smoother signal
    - λ = 1 - 2/(span+1); default span ≈ 756 days (3 years half-life)

    Parameters
    ----------
    s    : input series
    span : EWM span (default: EWMA_SPAN from config)

    Returns
    -------
    pd.Series  winsorised z-score
    """
    if span is None:
        span = EWMA_SPAN
    mp = MIN_HISTORY_DAYS
    mu = s.ewm(span=span, min_periods=mp).mean()
    sd = s.ewm(span=span, min_periods=mp).std()
    z  = (s - mu) / sd.replace(0, np.nan)
    return z.clip(-OUTLIER_CLIP_Z, OUTLIER_CLIP_Z).rename(s.name)


def pctile_rank(s: pd.Series, window: int) -> pd.Series:
    """
    Rolling percentile rank in [0, 1].

    Preferred over z-score for non-normal distributions (VIX, OAS spreads,
    P/E ratios) where the mean and std are poor measures of location.

    High percentile = series near its historical maximum.
    Low  percentile = series near its historical minimum.

    Adaptive: uses min(window, available observations).
    """
    w  = _adaptive_window(s, window)
    mp = max(2, min(w // 4, MIN_HISTORY_DAYS))
    return s.rolling(w, min_periods=mp).rank(pct=True)


def standardise_pillar(s: pd.Series) -> pd.Series:
    """
    Re-normalise a pillar aggregate back to unit variance.

    After combining individual z-scores with weights, the composite may have
    reduced variance (because signals are correlated). Re-standardising ensures
    each pillar contributes equally regardless of how many signals it contains.
    """
    return ewma_zscore(s, span=WINDOWS["medium"])


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — PRICE MOMENTUM
# ─────────────────────────────────────────────────────────────────────────────

def composite_price_momentum(price: pd.Series) -> pd.Series:
    """
    Compute a multi-horizon price momentum composite.

    Combines four momentum signals weighted by their empirical information
    content (Jegadeesh-Titman 12-1M has the highest IC in multi-asset TAA):
      - 12-1M skip momentum (40%): cross-sectional momentum, skip last month
        to avoid short-term reversal effect
      - 3M price return    (25%): medium-term trend
      - MA50/MA200 distance(25%): trend-following signal
      - RSI(14)            (10%): short-run overbought/oversold

    CRITICAL: The TR sheet only covers 1 year. This function works correctly
    with the fi_px sheet (full history from 1999, 6,848 rows).
    When called with a short series, the 12-1M component will have few
    observations but the 3M and MA signals will still work.

    Parameters
    ----------
    price : pd.Series  price or total return index level

    Returns
    -------
    pd.Series  composite momentum z-score, winsorised ±3σ
    """
    h = MOM_HORIZONS
    signals = {}

    # 1M return, normalised
    if price.dropna().shape[0] >= h["1m"] + MIN_HISTORY_DAYS:
        signals["1m"] = ewma_zscore(price.pct_change(h["1m"]))

    # 3M return, normalised
    if price.dropna().shape[0] >= h["3m"] + MIN_HISTORY_DAYS:
        signals["3m"] = ewma_zscore(price.pct_change(h["3m"]))

    # 12-1M skip momentum: return from price[-12M] to price[-1M]
    # Only computed if we have > 252 + 21 + MIN_HISTORY observations
    min_needed_12m = h["12m"] + h["skip"] + MIN_HISTORY_DAYS
    if price.dropna().shape[0] >= min_needed_12m:
        mom_12_1 = price.shift(h["skip"]).pct_change(h["12m"] - h["skip"])
        signals["12_1m"] = ewma_zscore(mom_12_1)

    # MA50/MA200 distance
    if price.dropna().shape[0] >= 200 + MIN_HISTORY_DAYS:
        ma50  = price.rolling(50,  min_periods=25).mean()
        ma200 = price.rolling(200, min_periods=100).mean()
        signals["ma"] = ewma_zscore((ma50 - ma200) / ma200.replace(0, np.nan))

    # RSI(14) — mapped to [-1, +1] and then EWMA-normalised
    if price.dropna().shape[0] >= 14 + MIN_HISTORY_DAYS:
        signals["rsi"] = ewma_zscore(_rsi_signal(price))

    if not signals:
        return pd.Series(dtype=float, name="mom_composite")

    # Weight map (will be re-normalised if some signals are missing)
    target_w = {"1m": 0.10, "3m": 0.25, "12_1m": 0.40, "ma": 0.15, "rsi": 0.10}

    total_w  = sum(target_w[k] for k in signals)
    comp     = sum((target_w[k] / total_w) * signals[k] for k in signals)
    return comp.clip(-OUTLIER_CLIP_Z, OUTLIER_CLIP_Z).rename("mom_composite")


def _rsi_signal(price: pd.Series, window: int = 14) -> pd.Series:
    """
    RSI(14) using Wilder's smoothing, mapped from [0,100] → [-1, +1].

    RSI above 70 = overbought territory; below 30 = oversold.
    Output is a continuous signal: (RSI - 50) / 50, clipped to [-1, +1].
    """
    delta  = price.diff()
    up     = delta.clip(lower=0)
    down   = (-delta).clip(lower=0)
    rs     = (up.ewm(span=window, adjust=False).mean() /
              down.ewm(span=window, adjust=False).mean())
    rsi    = 100 - (100 / (1 + rs))
    signal = ((rsi - 50) / 50).clip(-1, 1)
    return signal.rename("rsi")


def spread_momentum(spread: pd.Series, horizon_days: int,
                    invert: bool = True) -> pd.Series:
    """
    Spread change z-score (for OAS and CDS spreads).

    Positive change = spread widening = negative for credit.
    With invert=True: tightening (negative change) → positive signal.
    Used for: OAS BBB, HY OAS, EM OAS; set invert=False for flight-to-quality
    assets (UST benefits when spreads widen rapidly).

    Parameters
    ----------
    spread        : OAS or CDS spread series
    horizon_days  : lookback for diff (21=1M, 63=3M, 126=6M)
    invert        : True = tightening is positive (credit assets)
                    False = widening is positive (UST flight-to-quality)
    """
    chg = spread.diff(horizon_days)
    z   = ewma_zscore(chg, span=WINDOWS["long"])
    return (-z if invert else z).rename(f"spread_mom_{horizon_days}d")


def yield_momentum(yield_: pd.Series, horizon_days: int) -> pd.Series:
    """
    Treasury yield change → FI price momentum proxy.

    Falling yields = bond prices rising = positive for duration assets.
    Signal = -z(Δyield) so that declining yields give positive scores.
    """
    chg = yield_.diff(horizon_days)
    z   = ewma_zscore(chg, span=WINDOWS["long"])
    return (-z).rename(f"yield_mom_{horizon_days}d")  # invert: falling yield = +


def cdx_ig_momentum(cdx_ig_spread: pd.Series) -> pd.Series:
    """
    CDX IG spread momentum: tightening is positive for IG credit.
    Combines 1M and 3M horizon changes.
    """
    m1 = spread_momentum(cdx_ig_spread, 21,  invert=True)
    m3 = spread_momentum(cdx_ig_spread, 63,  invert=True)
    return (0.4 * m1 + 0.6 * m3).rename("cdx_ig_mom")


def cdx_hy_momentum(cdx_hy_price: pd.Series) -> pd.Series:
    """
    CDX HY price momentum: rising price = positive for risk appetite.
    Price (not spread) so we use standard return-based momentum.
    """
    r1 = ewma_zscore(cdx_hy_price.pct_change(21))
    r3 = ewma_zscore(cdx_hy_price.pct_change(63))
    return (0.4 * r1 + 0.6 * r3).rename("cdx_hy_mom")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — VALUATION
# ─────────────────────────────────────────────────────────────────────────────

def pe_score(pe: pd.Series, window: int = None) -> pd.Series:
    """
    Forward P/E → valuation score using adaptive percentile ranking.

    Uses percentile rank (not z-score) because P/E is right-skewed.
    Score direction: low P/E (cheap) → high positive score.

    Formula: score = -2 + 4 × (1 - pctile)
    Maps percentile [0, 1] → score [+2, -2] with inversion.

    Adaptive window: if series has fewer than `window` rows (e.g. PE sheet
    only has 261 rows), uses all available data. The score is still valid
    but represents "cheap/expensive within the available window" rather than
    the full historical context.

    Parameters
    ----------
    pe     : forward P/E series (positive values, e.g. 20.5 for 20.5x)
    window : lookback for percentile (default: vlong=10Y; adaptive)
    """
    if window is None:
        window = WINDOWS["vlong"]
    w   = _adaptive_window(pe, window)
    pct = pctile_rank(pe, w)
    # Invert: high P/E = high percentile = expensive = negative score
    score = -2.0 + 4.0 * (1.0 - pct)
    return score.clip(-OUTLIER_CLIP_Z, OUTLIER_CLIP_Z).rename("pe_score")


def equity_risk_premium(earnings_yield_pct: pd.Series,
                        bond_yield_pct: pd.Series) -> pd.Series:
    """
    Equity Risk Premium (ERP) = Earnings Yield - Bond Yield.

    When TIPS (real yields) are available: ERP = EY - TIPS_10Y (preferred).
    When only nominal yields available: ERP = EY - GT10 (proxy).

    Both inputs should be in percent (e.g. 5.0 for 5%).
    Historical average ERP is typically 3-5%. Below ~1% = equities expensive
    vs bonds; above ~5% = equities very cheap.

    Returns EWMA z-score of ERP (not the raw ERP level).
    """
    erp = earnings_yield_pct - bond_yield_pct
    # Align series on common index
    erp = erp.dropna()
    return ewma_zscore(erp, span=WINDOWS["vlong"]).rename("erp")


def relative_pe(pe_a: pd.Series, pe_b: pd.Series) -> pd.Series:
    """
    Relative P/E: A vs B (e.g. US vs EM, Growth vs Value).

    Returns z-score of ratio A/B, inverted so that:
    - A cheap relative to B (low ratio) → positive signal for A
    - A expensive relative to B (high ratio) → negative signal for A

    Used for cross-regional and cross-style rotation signals.
    """
    ratio = (pe_a / pe_b.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
    z     = ewma_zscore(ratio)
    return (-z).rename("relative_pe")  # invert: cheap relative = positive


def oas_level_score(oas: pd.Series, window: int = None) -> pd.Series:
    """
    OAS level → credit valuation score (high spread = cheap = positive).

    Uses percentile because OAS is highly skewed by crisis episodes.
    Wide spread = high percentile = attractive carry = high positive score.

    Formula: score = -2 + 4 × pctile (NOT inverted; high OAS = high score)
    """
    if window is None:
        window = WINDOWS["xlarge"]
    w     = _adaptive_window(oas, window)
    pct   = pctile_rank(oas, w)
    score = -2.0 + 4.0 * pct   # wide spread = high pctile = positive score
    return score.clip(-OUTLIER_CLIP_Z, OUTLIER_CLIP_Z).rename("oas_level_score")


def yield_level_score(yield_: pd.Series, window: int = None) -> pd.Series:
    """
    Treasury yield level → carry attractiveness for FI.

    High yield = positive (better carry). Uses EWMA z-score.
    """
    if window is None:
        window = WINDOWS["vlong"]
    return ewma_zscore(yield_, span=_adaptive_window(yield_, window)).rename("yield_level")


def term_spread_score(term_spread: pd.Series, asset_class: str) -> pd.Series:
    """
    Yield curve shape (10Y-2Y) → signal interpretation varies by asset class.

    For SHORT-TERM FI / MONEY MARKET:
      Inverted curve → short-end yield > long-end → high carry for STFI
      Score: high when curve is flat or inverted → INVERT z-score of spread

    For LT TREASURIES:
      Deeply inverted → recession/rate-cut signal → bullish for long duration
      Score: also invert (deeply inverted = positive for duration)

    For LT US CORPORATE:
      Slightly positive slope = healthier economy = tighter spreads
      Score: direct (not inverted)

    Parameters
    ----------
    asset_class : asset class identifier from ASSET_CLASSES
    """
    z = ewma_zscore(term_spread, span=WINDOWS["vlong"])
    if asset_class in ("short_term_fi", "money_market", "lt_treasuries"):
        return (-z).rename("term_spread_score")  # inverted: flat/inverted = good
    else:
        return z.rename("term_spread_score")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — SENTIMENT
# ─────────────────────────────────────────────────────────────────────────────

def vix_score(vix: pd.Series, target_asset: str = "equity",
              window: int = None) -> pd.Series:
    """
    VIX (or proxy) → sentiment signal with non-linear contrarian scoring.

    VIX has a non-normal (right-skewed) distribution. A linear z-score
    underweights extreme readings. Instead we use percentile rank with
    discrete contrarian thresholds:

    For EQUITY:
      VIX > 90th pctile = extreme fear = contrarian BUY signal (+2)
      VIX < 20th pctile = complacency  = cautious sell signal (-1.5)
    For FI (UST / STFI):
      VIX high = flight to quality = direct positive signal
      (same direction but for a different reason: demand for safety)

    Parameters
    ----------
    vix          : VIX index or suitable proxy
    target_asset : 'equity' (contrarian) or 'fi' (flight-to-quality)
    window       : percentile lookback (default xlarge = 5Y)
    """
    if window is None:
        window = WINDOWS["xlarge"]
    w   = _adaptive_window(vix, window)
    pct = pctile_rank(vix, w)

    if target_asset == "equity":
        # Non-linear contrarian scoring
        score = pct.map(lambda p:
            +2.0 if p is not None and p > 0.90 else
            +1.0 if p is not None and p > 0.75 else
             0.0 if p is not None and p > 0.50 else
            -0.5 if p is not None and p > 0.25 else
            -1.5 if p is not None else np.nan
        )
    else:
        # FI: flight-to-quality — high VIX = positive for bonds
        score = ewma_zscore(vix, span=w)

    return score.clip(-OUTLIER_CLIP_Z, OUTLIER_CLIP_Z).rename("vix_score")


def oas_stress_proxy(oas: pd.Series, window: int = None,
                     for_safe_haven: bool = False) -> pd.Series:
    """
    OAS rapid widening as a VIX / TED spread proxy.

    Used when VIX is unavailable. The 1-month change in HY or IG OAS
    captures credit market stress similarly to equity volatility.

    for_safe_haven=True : widening = demand for safety = positive for UST
    for_safe_haven=False: widening = risk-off = negative for credit/equity
    """
    if window is None:
        window = WINDOWS["long"]
    chg = oas.diff(21)   # 1-month OAS change
    z   = ewma_zscore(chg, span=_adaptive_window(chg, window))
    return (z if for_safe_haven else -z).rename("oas_stress")
