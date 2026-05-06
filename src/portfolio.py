"""
src/portfolio.py
================
Multi-portfolio TAA application layer.

Applies a single house-view scorecard (z-scores + convictions) to N portfolios,
each with a different Strategic Asset Allocation and active risk budget.

Methodology (Lee 2000; BlackRock BGRI; AQR Systematic)
-------------------------------------------------------
One signal engine → one set of z-scores → N scaled implementations.
Tilt size = signal_fraction × conviction_mult × portfolio_specific_max_tilt
          where portfolio_specific_max_tilt = config_default × (TE_budget / 100)

This ensures:
  - Same direction for all portfolios (signal coherence)
  - Size proportional to each portfolio's active risk budget (risk-adjusted fairness)
  - Optional zero-sum enforcement for Solvency II / UCITS mandates

Usage
-----
portfolios = load_portfolio_configs("config/portfolios.xlsx")
for p in portfolios:
    ptf_sc = apply_house_view(scorecard, p)
    # ptf_sc has columns: saa_weight, scaled_max_tilt, portfolio_tilt, portfolio_weight
"""

from __future__ import annotations

import os
import numpy as np
import pandas as pd
from dataclasses import dataclass, field

from config import (
    ASSET_CLASSES, MAX_TILT_PCT, ALPHA_ABS,
    CONVICTION_THRESHOLDS, OUTLIER_CLIP_Z,
)


# ─────────────────────────────────────────────────────────────────────────────
# PortfolioConfig
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PortfolioConfig:
    """
    Per-portfolio parameters that govern how the house view is scaled.

    Parameters
    ----------
    portfolio_id      : unique key, e.g. "portfolio_01"
    label             : human-readable name
    saa               : dict {ac_id: weight_pct} (weights in %, sum to 100)
    te_budget_bps     : total active risk budget in basis points (e.g. 100 = 100bps)
    alpha_abs         : weight for absolute vs relative view (default 0.35)
    max_tilt_overrides: optional per-AC max tilt overrides (% of portfolio)
    force_zero_sum    : if True, scale tilts to sum to zero (Solvency II / UCITS)
    risk_profile      : "conservative" | "moderate" | "aggressive"
    """
    portfolio_id:       str
    label:              str
    saa:                dict   # {ac_id: float}  — weights in percent
    te_budget_bps:      float  = 100.0
    alpha_abs:          float  = 0.35
    max_tilt_overrides: dict   = field(default_factory=dict)
    force_zero_sum:     bool   = False
    risk_profile:       str    = "moderate"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _z_to_fraction(z: float) -> float:
    """Map composite z-score to conviction tilt fraction {-1, -0.5, 0, +0.5, +1}."""
    if pd.isna(z):
        return 0.0
    for threshold, _, fraction in CONVICTION_THRESHOLDS:
        if threshold is None or z >= threshold:
            return fraction
    return -1.0


# ─────────────────────────────────────────────────────────────────────────────
# apply_house_view
# ─────────────────────────────────────────────────────────────────────────────

def apply_house_view(
    scorecard: pd.DataFrame,
    portfolio: PortfolioConfig,
    reference_te_bps: float = 100.0,
) -> pd.DataFrame:
    """
    Scale the central TAA house view to a specific portfolio's risk constraints.

    Parameters
    ----------
    scorecard        : output of score_snapshot() — one row per AC
    portfolio        : PortfolioConfig for the target portfolio
    reference_te_bps : TE budget that corresponds to the default max_tilt_pct
                       values in config.py (100 bps by convention)

    Returns
    -------
    pd.DataFrame with columns:
      ac, label, saa_weight, Z_composite, Z_relative, conviction,
      scaled_max_tilt, portfolio_tilt, portfolio_weight
    """
    te_scale = portfolio.te_budget_bps / reference_te_bps

    rows = []
    for ac in ASSET_CLASSES:
        if ac not in scorecard.index:
            continue

        row = scorecard.loc[ac]

        saa_w   = portfolio.saa.get(ac, 0.0)
        # Portfolio-specific max tilt: scaled by TE budget
        cfg_max = (portfolio.max_tilt_overrides or {}).get(ac, MAX_TILT_PCT.get(ac, 3.0))
        max_t   = cfg_max * te_scale

        # Blend z-scores with portfolio-specific alpha_abs
        z_abs = float(row.get("Z_composite",  np.nan))
        z_rel = float(row.get("Z_relative",   np.nan))

        if pd.isna(z_abs):
            z_blend = np.nan
        else:
            if pd.isna(z_rel):
                z_rel = 0.0
            z_blend = portfolio.alpha_abs * z_abs + (1 - portfolio.alpha_abs) * z_rel
            z_blend = float(np.clip(z_blend, -OUTLIER_CLIP_Z, OUTLIER_CLIP_Z))

        tilt_frac  = _z_to_fraction(z_blend)
        conv_mult  = float(row.get("conviction_mult", 0.0))
        tilt       = round(tilt_frac * conv_mult * max_t, 2)

        rows.append({
            "ac":             ac,
            "label":          str(row.get("label", ac)),
            "saa_weight":     saa_w,
            "Z_composite":    round(z_abs, 3) if not pd.isna(z_abs) else np.nan,
            "Z_relative":     round(z_rel, 3) if not pd.isna(z_rel) else np.nan,
            "conviction":     str(row.get("conviction", "")),
            "scaled_max_tilt": round(max_t, 2),
            "portfolio_tilt": tilt,
            "portfolio_weight": round(saa_w + tilt, 2),
        })

    result = pd.DataFrame(rows).set_index("ac")

    # Optional: enforce zero-sum by pro-rata reduction of excess
    if portfolio.force_zero_sum:
        excess = result["portfolio_tilt"].sum()
        if abs(excess) > 0.01:
            result["portfolio_tilt"] = (result["portfolio_tilt"] - excess / len(result)).round(2)
            result["portfolio_weight"] = (
                result["saa_weight"] + result["portfolio_tilt"]).round(2)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# load_portfolio_configs  (reads config/portfolios.xlsx)
# ─────────────────────────────────────────────────────────────────────────────

def load_portfolio_configs(path: str) -> list[PortfolioConfig]:
    """
    Load portfolio definitions from portfolios.xlsx.

    Sheet "Portfolios" columns:
      portfolio_id | label | te_budget_bps | alpha_abs | force_zero_sum | risk_profile
      + one column per AC (e.g. "money_market", "us_equity", ...) for SAA weights.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"portfolios.xlsx not found: {path}")

    df = pd.read_excel(path, sheet_name="Portfolios")
    df.columns = [str(c).strip() for c in df.columns]

    portfolios = []
    for _, row in df.iterrows():
        pid    = str(row.get("portfolio_id", "")).strip()
        label  = str(row.get("label", pid))
        te     = float(row.get("te_budget_bps", 100))
        alpha  = float(row.get("alpha_abs", ALPHA_ABS))
        fzs    = bool(row.get("force_zero_sum", False))
        rp     = str(row.get("risk_profile", "moderate")).strip()

        saa = {}
        for ac in ASSET_CLASSES:
            if ac in row and not pd.isna(row[ac]):
                saa[ac] = float(row[ac])

        portfolios.append(PortfolioConfig(
            portfolio_id=pid, label=label, saa=saa,
            te_budget_bps=te, alpha_abs=alpha,
            force_zero_sum=fzs, risk_profile=rp,
        ))

    return portfolios


# ─────────────────────────────────────────────────────────────────────────────
# build_multi_portfolio_report
# ─────────────────────────────────────────────────────────────────────────────

def build_multi_portfolio_report(
    scorecard:  pd.DataFrame,
    portfolios: list[PortfolioConfig],
    out_path:   str,
) -> None:
    """
    Apply the house view to each portfolio and write multi_portfolio_views.xlsx.

    One sheet per portfolio; a summary sheet "Summary" shows final_tilt_% side-by-side.
    """
    summary_rows = {}

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        for p in portfolios:
            df = apply_house_view(scorecard, p)
            sheet = p.portfolio_id[:31]   # Excel sheet name max 31 chars
            df.to_excel(writer, sheet_name=sheet)
            summary_rows[p.label] = df["portfolio_tilt"]

        # Summary sheet: AC × portfolio tilt
        summary = pd.DataFrame(summary_rows)
        summary.index.name = "asset_class"
        summary.to_excel(writer, sheet_name="Tilt_Summary")

    print(f"  Multi-portfolio views  -> {out_path}")
