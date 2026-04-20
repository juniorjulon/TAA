"""
taa_system/scoring.py
=====================
Composite scoring, conviction mapping, and view generation.

Pipeline (called from main.py):
  1. composite_score()      : weighted pillar average → composite z-score
  2. pillar_agreement()     : count aligned pillars → conviction quality
  3. score_snapshot()       : single-date scorecard for all asset classes
  4. apply_crisis_override(): force neutral if VIX+MOVE both in crisis
  5. print_scorecard()      : console display

ABSOLUTE vs RELATIVE VIEWS:
  Absolute: z_composite vs zero → "is this AC attractive in its own history?"
  Relative: cross-sectional ranking → "which AC do I prefer over others?"
  Final:    ALPHA_ABS × absolute + (1-ALPHA) × relative

For details see the TAA_System_Guide.md documentation.
"""

import pandas as pd
import numpy as np

from config import (
    ASSET_CLASSES, ASSET_CLASS_LABELS, ASSET_CLASS_GROUPS,
    PILLAR_WEIGHTS, CONVICTION_THRESHOLDS,
    MAX_TILT_PCT, ALPHA_ABS,
    PILLAR_AGREEMENT_MULTIPLIERS, PILLAR_AGREEMENT_THRESHOLD,
    OUTLIER_CLIP_Z,
)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — COMPOSITE SCORE
# ─────────────────────────────────────────────────────────────────────────────

def composite_score(pillar_scores: dict, asset_class: str) -> pd.Series:
    """
    Combine four pillar z-scores into a single composite z-score.

    Composite = Σ (weight_p × Z_p) for p in {F, M, S, V}
    If a pillar series is missing, its weight is redistributed to present pillars.

    Parameters
    ----------
    pillar_scores : dict {'F': Series, 'M': Series, 'S': Series, 'V': Series}
    asset_class   : string key for PILLAR_WEIGHTS lookup

    Returns
    -------
    pd.Series  composite z-score, clipped ±3σ
    """
    weights = PILLAR_WEIGHTS[asset_class]
    cols, wts = {}, {}

    for pillar, w in weights.items():
        s = pillar_scores.get(pillar)
        if s is None or (isinstance(s, pd.Series) and s.dropna().empty):
            continue
        cols[pillar] = s.clip(-OUTLIER_CLIP_Z, OUTLIER_CLIP_Z)
        wts[pillar]  = w

    if not cols:
        return pd.Series(dtype=float, name=asset_class)

    df  = pd.DataFrame(cols)
    w_s = pd.Series(wts)
    # Per-row weighted average: pillars with missing data on a date skip gracefully.
    num = df.mul(w_s).sum(axis=1, min_count=1)
    den = df.notna().mul(w_s).sum(axis=1).replace(0, np.nan)
    return (num / den).clip(-OUTLIER_CLIP_Z, OUTLIER_CLIP_Z).rename(asset_class)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — CONVICTION MAPPING
# ─────────────────────────────────────────────────────────────────────────────

def z_to_conviction(z: float) -> tuple:
    """
    Map a scalar composite z-score to a (label, tilt_fraction) pair.

    Thresholds (from config.CONVICTION_THRESHOLDS):
      z > +1.50 → HIGH OW    tilt_fraction = +1.0
      z > +0.75 → MEDIUM OW  tilt_fraction = +0.5
      z > -0.75 → NEUTRAL    tilt_fraction =  0.0
      z > -1.50 → MEDIUM UW  tilt_fraction = -0.5
      z ≤ -1.50 → HIGH UW    tilt_fraction = -1.0

    Parameters
    ----------
    z : composite z-score (float, may be NaN)

    Returns
    -------
    (label: str, tilt_fraction: float)
    """
    if pd.isna(z):
        return ("N/A", 0.0)
    for threshold, label, fraction in CONVICTION_THRESHOLDS:
        if threshold is None or z >= threshold:
            return (label, fraction)
    return ("HIGH UW", -1.0)   # fallback (should not reach here)


def pillar_agreement(pillar_z: dict,
                     threshold: float = PILLAR_AGREEMENT_THRESHOLD) -> tuple:
    """
    Count how many pillars agree on the direction of the composite.

    Only pillars where |z| > threshold are counted (filter noise).
    Pillars pointing in the majority direction are "agreeing."

    Returns
    -------
    (n_agree: int, majority_direction: float, conviction_mult: float)
      n_agree         : 0–4 (how many pillars agree)
      majority_dir    : +1.0 (bullish) or -1.0 (bearish)
      conviction_mult : from PILLAR_AGREEMENT_MULTIPLIERS
        4/4 agree → 1.00 (full conviction)
        3/4       → 0.80
        2/4       → 0.50
        1/4       → 0.00 (no tilt even if composite is large)
    """
    directions = []
    for pillar_name, s in pillar_z.items():
        if s is None or (isinstance(s, pd.Series) and s.dropna().empty):
            continue
        val = float(s.dropna().iloc[-1]) if isinstance(s, pd.Series) else float(s)
        if not np.isnan(val) and abs(val) > threshold:
            directions.append(np.sign(val))

    if not directions:
        return (0, 0.0, 0.0)

    majority   = max(set(directions), key=directions.count)
    n_agree    = sum(1 for d in directions if d == majority)
    conv_mult  = PILLAR_AGREEMENT_MULTIPLIERS.get(n_agree, 0.0)
    return (n_agree, majority, conv_mult)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — FULL SCORECARD (single snapshot at latest date)
# ─────────────────────────────────────────────────────────────────────────────

def score_snapshot(pillar_scores_by_ac: dict) -> pd.DataFrame:
    """
    Build the full TAA scorecard for the latest available date.

    For each asset class, extracts the most recent value of each pillar
    series, computes the composite z-score, applies the conviction map,
    generates absolute and relative views, and calculates final tilts.

    Parameters
    ----------
    pillar_scores_by_ac : dict
      {asset_class: {'F': pd.Series, 'M': pd.Series,
                      'S': pd.Series, 'V': pd.Series}}

    Returns
    -------
    pd.DataFrame  one row per asset class, columns:
      label, Z_F, Z_M, Z_S, Z_V, Z_composite,
      n_agree, conviction_mult, conviction,
      abs_tilt_%, Z_relative, rel_tilt_%, final_tilt_%
    """
    rows = {}

    for ac in ASSET_CLASSES:
        if ac not in pillar_scores_by_ac:
            continue

        ps = pillar_scores_by_ac[ac]

        # Extract latest scalar from each pillar series
        def _last(series_or_none):
            if series_or_none is None:
                return np.nan
            if isinstance(series_or_none, pd.Series):
                clean = series_or_none.dropna()
                return float(clean.iloc[-1]) if len(clean) > 0 else np.nan
            return float(series_or_none)

        z_f, z_m, z_s, z_v = (_last(ps.get("F")), _last(ps.get("M")),
                                _last(ps.get("S")), _last(ps.get("V")))

        # Compute weighted composite (reuse scalar math — fast for snapshot)
        weights = PILLAR_WEIGHTS[ac]
        valid   = {p: z for p, z in zip("FMSV", [z_f, z_m, z_s, z_v])
                   if not np.isnan(z)}
        if valid:
            total_w = sum(weights[p] for p in valid)
            z_comp  = sum(weights[p] * valid[p] for p in valid) / total_w
            z_comp  = float(np.clip(z_comp, -OUTLIER_CLIP_Z, OUTLIER_CLIP_Z))
        else:
            z_comp = np.nan

        # Pillar agreement
        n_agree, _, conv_mult = pillar_agreement(
            {"F": z_f, "M": z_m, "S": z_s, "V": z_v})

        # Conviction label + absolute tilt
        conviction, tilt_frac = z_to_conviction(z_comp)
        abs_tilt = tilt_frac * conv_mult * MAX_TILT_PCT[ac]

        rows[ac] = {
            "label":          ASSET_CLASS_LABELS[ac],
            "group":          ASSET_CLASS_GROUPS[ac],
            "Z_F":            round(z_f,    3),
            "Z_M":            round(z_m,    3),
            "Z_S":            round(z_s,    3),
            "Z_V":            round(z_v,    3),
            "Z_composite":    round(z_comp, 3) if not np.isnan(z_comp) else np.nan,
            "n_agree":        n_agree,
            "conviction_mult": conv_mult,
            "conviction":     conviction,
            "abs_tilt_%":     round(abs_tilt, 2),
        }

    df = pd.DataFrame(rows).T

    # ── Relative view: cross-sectional normalisation ─────────────────────────
    z_series = pd.to_numeric(df["Z_composite"], errors="coerce")
    mu_cs    = z_series.mean()
    std_cs   = z_series.std()
    if std_cs > 0:
        df["Z_relative"] = ((z_series - mu_cs) / std_cs).round(3)
    else:
        df["Z_relative"] = 0.0

    # Relative tilt from Z_relative (same conviction map)
    def _rel_tilt(row):
        z_r = row.get("Z_relative", np.nan)
        if pd.isna(z_r):
            return 0.0
        _, frac  = z_to_conviction(z_r)
        cm       = row.get("conviction_mult", 0.0)
        max_t    = MAX_TILT_PCT.get(row.name, 3.0)
        return round(frac * cm * max_t, 2)

    df["rel_tilt_%"] = df.apply(_rel_tilt, axis=1)

    # Final tilt: blend absolute and relative
    df["final_tilt_%"] = (
        ALPHA_ABS        * pd.to_numeric(df["abs_tilt_%"],  errors="coerce").fillna(0)
      + (1 - ALPHA_ABS)  * pd.to_numeric(df["rel_tilt_%"],  errors="coerce").fillna(0)
    ).round(2)

    return df


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — CRISIS OVERRIDE
# ─────────────────────────────────────────────────────────────────────────────

def apply_crisis_override(scorecard: pd.DataFrame,
                           vix_pctile: float = None,
                           move_pctile: float = None,
                           threshold: float = 0.80) -> pd.DataFrame:
    """
    Force all tilts to zero when both VIX and MOVE exceed threshold simultaneously.

    Rationale: when both equity vol (VIX) and bond vol (MOVE) are in crisis
    territory, the signal engine's normal outputs are unreliable. Sitting flat
    (zero tilt) is the correct risk-managed response.

    Override lifts when both return below 70th percentile.

    Parameters
    ----------
    scorecard    : scorecard DataFrame from score_snapshot()
    vix_pctile   : current VIX percentile [0, 1] or None (skips override)
    move_pctile  : current MOVE percentile [0, 1] or None (skips override)
    threshold    : percentile threshold above which crisis is declared (0.80)
    """
    if vix_pctile is None or move_pctile is None:
        return scorecard   # can't evaluate, skip override

    if vix_pctile > threshold and move_pctile > threshold:
        print(f"\n  ⚠  CRISIS OVERRIDE ACTIVE: VIX={vix_pctile:.0%}  MOVE={move_pctile:.0%}")
        print(  "     All tilts set to zero. Override lifts when both < 70th pctile.\n")
        sc = scorecard.copy()
        for col in ["abs_tilt_%", "rel_tilt_%", "final_tilt_%"]:
            if col in sc.columns:
                sc[col] = 0.0
        return sc

    return scorecard


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — CONSOLE DISPLAY
# ─────────────────────────────────────────────────────────────────────────────

def print_scorecard(df: pd.DataFrame, date: str = "Latest") -> None:
    """
    Pretty-print the TAA scorecard to console.

    Output columns: Asset Class | Z_F | Z_M | Z_S | Z_V | Z_Comp | Agree | Conviction | Tilt
    """
    W = 112
    print(f"\n{'='*W}")
    print(f"  TAA SCORECARD -- {date}")
    print(f"{'='*W}")
    print(f"  {'Asset Class':<22} {'Z_F':>6} {'Z_M':>6} {'Z_S':>6} {'Z_V':>6} "
          f"{'Z_Comp':>8} {'Agree':>6} {'Conviction':<16} {'AbsTilt%':>9} {'RelZ':>7} {'FinalTilt%':>11}")
    print(f"  {'-'*108}")

    GROUPS = {
        "Fixed Income": ["money_market","short_term_fi","lt_treasuries","lt_us_corp","lt_em_fi"],
        "Equity":       ["us_equity","us_growth","us_value","dm_equity","em_equity","em_xchina","china_equity"],
    }

    for group_label, acs in GROUPS.items():
        print(f"\n  -- {group_label} --")
        for ac in acs:
            if ac not in df.index:
                continue
            row = df.loc[ac]

            def _f(v, d=2):
                """Format a float with leading sign, or n/a if NaN."""
                try:
                    fv = float(v)
                    if np.isnan(fv):
                        return "  n/a"
                    return f"{fv:+.{d}f}"
                except (TypeError, ValueError):
                    return "  n/a"

            conv  = str(row.get("conviction", ""))
            icon  = ("++ " if "HIGH OW"   in conv else
                     "+  " if "MEDIUM OW" in conv else
                     "=  " if "NEUTRAL"   in conv else
                     "-  " if "MEDIUM UW" in conv else
                     "-- " if "HIGH UW"   in conv else "?  ")
            ft    = float(row.get("final_tilt_%", 0))
            tilt_s= f"{ft:+.1f}%"

            print(f"  {row['label']:<22} "
                  f"{_f(row['Z_F']):>6} {_f(row['Z_M']):>6} "
                  f"{_f(row['Z_S']):>6} {_f(row['Z_V']):>6} "
                  f"{_f(row['Z_composite']):>8} "
                  f"{str(row.get('n_agree','?')):>6} "
                  f"{icon} {conv:<14} "
                  f"{_f(row.get('abs_tilt_%',0)):>9} "
                  f"{_f(row.get('Z_relative',0)):>7} "
                  f"{tilt_s:>11}")

    print(f"\n  {'-'*108}")

    # Portfolio summary
    fi_acs  = ["money_market","short_term_fi","lt_treasuries","lt_us_corp","lt_em_fi"]
    eq_acs  = ["us_equity","us_growth","us_value","dm_equity","em_equity","em_xchina","china_equity"]
    fi_net  = sum(float(df.loc[ac,"final_tilt_%"]) for ac in fi_acs if ac in df.index)
    eq_net  = sum(float(df.loc[ac,"final_tilt_%"]) for ac in eq_acs if ac in df.index)
    tot_abs = sum(abs(float(df.loc[ac,"final_tilt_%"]))
                  for ac in fi_acs + eq_acs if ac in df.index)

    print(f"\n  Portfolio checks:")
    print(f"    FI net tilt:      {fi_net:+.1f}%")
    print(f"    Equity net tilt:  {eq_net:+.1f}%")
    print(f"    Total |tilts|:    {tot_abs:.1f}%  "
          f"(tracking error ~{tot_abs * 0.16:.0f} bps)")
    print(f"    View mix:         {ALPHA_ABS:.0%} absolute / {1-ALPHA_ABS:.0%} relative")
    print(f"{'='*W}\n")
