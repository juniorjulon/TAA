"""
src/hierarchical_scoring.py
============================
Two-level (hierarchical) TAA view system.

Level 1 — Macro / Aggregate
  Six top-level buckets: Money Market, Short-Term FI, LT FI (aggregate),
  US Equity, DM ex-US, EM Equity.  Each produces an overall directional tilt
  (overweight / underweight vs SAA), sized against max_tilt_l1.

Level 2 — Within-Class / Relative
  Within three buckets that have sub-ACs, a zero-sum relative tilt determines
  the internal composition:
    LT FI:      lt_treasuries vs lt_us_corp vs lt_em_fi
    US Equity:  us_value vs us_growth
    EM Equity:  em_xchina vs china_equity
  Sized against max_tilt_l2; sum of L2 tilts within each bucket ≈ 0.

Academic basis
  Maillard, Roncalli & Teïletche (2010) — hierarchical risk parity / orthogonal views
  Wang & Kochard (2012) — z-score TAA with absolute + relative blending
  Lee (2000) — multi-portfolio scaling by risk capacity
"""

import numpy as np
import pandas as pd

from config import (
    AC_HIERARCHY, AC_PARENT, AC_STANDALONE,
    CONVICTION_THRESHOLDS, PILLAR_AGREEMENT_MULTIPLIERS,
    PILLAR_AGREEMENT_THRESHOLD, MAX_TILT_PCT, OUTLIER_CLIP_Z,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _z_to_fraction(z: float) -> float:
    """Map composite z to conviction tilt fraction {-1, -0.5, 0, +0.5, +1}."""
    if pd.isna(z):
        return 0.0
    for threshold, _, fraction in CONVICTION_THRESHOLDS:
        if threshold is None or z >= threshold:
            return fraction
    return -1.0


def _scalar(series_or_float):
    """Safely extract a float from a pd.Series or float."""
    if isinstance(series_or_float, pd.Series):
        clean = series_or_float.dropna()
        return float(clean.iloc[-1]) if len(clean) > 0 else np.nan
    try:
        return float(series_or_float)
    except (TypeError, ValueError):
        return np.nan


# ─────────────────────────────────────────────────────────────────────────────
# HierarchicalViews
# ─────────────────────────────────────────────────────────────────────────────

class HierarchicalViews:
    """
    Compute Level 1 (aggregate) and Level 2 (within-class) views from the
    existing flat scorecard produced by score_snapshot().

    Usage
    -----
    hv  = HierarchicalViews()
    sc2 = hv.enrich(scorecard)   # adds Z_L1, Z_L2, tilt_L1, tilt_L2, tilt_hier columns
    """

    def _aggregate_z(self, scorecard: pd.DataFrame, agg_key: str) -> float:
        """
        Compute the Level-1 z-score for an aggregate bucket.

        For real ACs (us_equity, em_equity) → return their own Z_composite.
        For synthetic (lt_fi_aggregate) → weighted average of children's Z_composite.
        """
        cfg = AC_HIERARCHY[agg_key]
        children = cfg["children"]
        weights  = cfg["model_weights"]

        # Synthetic aggregate: compute weighted average from children
        num, den = 0.0, 0.0
        for child in children:
            if child not in scorecard.index:
                continue
            z = scorecard.loc[child, "Z_composite"]
            if pd.isna(z):
                continue
            w = weights.get(child, 0.0)
            num += float(z) * w
            den += w

        if den < 1e-9:
            # Fall back to agg_key's own row if it exists as a real AC
            if agg_key in scorecard.index:
                return float(scorecard.loc[agg_key, "Z_composite"])
            return np.nan

        return float(np.clip(num / den, -OUTLIER_CLIP_Z, OUTLIER_CLIP_Z))

    def enrich(self, scorecard: pd.DataFrame) -> pd.DataFrame:
        """
        Add hierarchy columns to the existing scorecard DataFrame.

        New columns
        -----------
        Z_L1         : Level-1 (aggregate bucket) composite z-score
        Z_L2         : Level-2 (within-bucket) relative z-score vs parent
                       (0.0 for standalone ACs; approximately zero-sum within each bucket)
        tilt_L1_pct  : tilt from aggregate conviction (L1); applied to all sub-ACs equally
                       as their share of the aggregate
        tilt_L2_pct  : within-bucket redistribution tilt (zero-sum within each bucket)
        tilt_hier_pct: L1_tilt × own_model_weight_share  +  L2_tilt
                       = recommended hierarchical final tilt per AC
        """
        sc = scorecard.copy()

        # Initialise new columns
        sc["Z_L1"]          = np.nan
        sc["Z_L2"]          = 0.0
        sc["tilt_L1_pct"]   = 0.0
        sc["tilt_L2_pct"]   = 0.0
        sc["tilt_hier_pct"] = 0.0

        # ── 1. Standalone ACs — L1 = own z, L2 = 0 ──────────────────────────
        for ac in AC_STANDALONE:
            if ac not in sc.index:
                continue
            z_own = float(sc.loc[ac, "Z_composite"]) if not pd.isna(sc.loc[ac, "Z_composite"]) else np.nan
            sc.loc[ac, "Z_L1"] = z_own
            sc.loc[ac, "Z_L2"] = 0.0

            # Tilt = existing final_tilt (L1 = all of it; no L2)
            sc.loc[ac, "tilt_L1_pct"]   = float(sc.loc[ac, "final_tilt_%"])
            sc.loc[ac, "tilt_hier_pct"] = float(sc.loc[ac, "final_tilt_%"])

        # ── 2. Hierarchical buckets ───────────────────────────────────────────
        for agg_key, cfg in AC_HIERARCHY.items():
            children     = cfg["children"]
            model_wts    = cfg["model_weights"]
            max_tilt_l1  = cfg["max_tilt_l1"]
            max_tilt_l2  = cfg["max_tilt_l2"]

            # Level-1 aggregate z-score
            z_l1 = self._aggregate_z(scorecard, agg_key)

            # Level-1 conviction tilt (same direction for all children)
            frac_l1   = _z_to_fraction(z_l1)
            # Use the average pillar agreement of children as conviction multiplier
            conv_mults = []
            for child in children:
                if child in sc.index:
                    cm = sc.loc[child, "conviction_mult"]
                    try:
                        conv_mults.append(float(cm))
                    except (TypeError, ValueError):
                        pass
            conv_l1  = float(np.mean(conv_mults)) if conv_mults else 0.0
            l1_tilt  = frac_l1 * conv_l1 * max_tilt_l1

            # Also update the parent row itself if it exists as a real AC
            if agg_key in sc.index:
                sc.loc[agg_key, "Z_L1"] = z_l1
                sc.loc[agg_key, "Z_L2"] = 0.0
                sc.loc[agg_key, "tilt_L1_pct"]   = round(l1_tilt, 3)
                sc.loc[agg_key, "tilt_hier_pct"]  = round(l1_tilt, 3)

            # Level-2 relative z-scores and tilts for each child
            for child in children:
                if child not in sc.index:
                    continue

                z_child = float(sc.loc[child, "Z_composite"]) \
                    if not pd.isna(sc.loc[child, "Z_composite"]) else np.nan
                z_l2 = (z_child - z_l1) if (not np.isnan(z_child) and not np.isnan(z_l1)) else 0.0
                z_l2 = float(np.clip(z_l2, -OUTLIER_CLIP_Z, OUTLIER_CLIP_Z))

                frac_l2   = _z_to_fraction(z_l2)
                conv_child = float(sc.loc[child, "conviction_mult"]) \
                    if not pd.isna(sc.loc[child, "conviction_mult"]) else 0.0
                l2_tilt   = frac_l2 * conv_child * max_tilt_l2

                # L1 tilt for this child = aggregate tilt × child's model weight share
                own_w     = model_wts.get(child, 0.0)
                l1_share  = l1_tilt * own_w

                sc.loc[child, "Z_L1"]          = z_l1
                sc.loc[child, "Z_L2"]          = round(z_l2, 4)
                sc.loc[child, "tilt_L1_pct"]   = round(l1_share, 3)
                sc.loc[child, "tilt_L2_pct"]   = round(l2_tilt, 3)
                sc.loc[child, "tilt_hier_pct"]  = round(l1_share + l2_tilt, 3)

        return sc

    def bucket_summary(self, enriched_sc: pd.DataFrame) -> pd.DataFrame:
        """
        Print a compact summary: L1 z-scores, aggregate tilts, L2 decomposition.
        """
        rows = []
        # Standalone
        for ac in AC_STANDALONE:
            if ac not in enriched_sc.index:
                continue
            rows.append({
                "bucket": ac,
                "sub_ac": "",
                "Z_L1":   round(float(enriched_sc.loc[ac, "Z_L1"]), 3),
                "Z_L2":   0.0,
                "tilt_L1": enriched_sc.loc[ac, "tilt_L1_pct"],
                "tilt_L2": 0.0,
                "tilt_hier": enriched_sc.loc[ac, "tilt_hier_pct"],
            })
        # Hierarchical
        for agg_key, cfg in AC_HIERARCHY.items():
            z_l1 = enriched_sc.loc[cfg["children"][0], "Z_L1"] \
                if cfg["children"][0] in enriched_sc.index else np.nan
            rows.append({
                "bucket": agg_key,
                "sub_ac": "[AGGREGATE]",
                "Z_L1":   round(float(z_l1), 3) if not np.isnan(z_l1) else np.nan,
                "Z_L2":   0.0,
                "tilt_L1": "",
                "tilt_L2": "",
                "tilt_hier": "",
            })
            for child in cfg["children"]:
                if child not in enriched_sc.index:
                    continue
                rows.append({
                    "bucket": "",
                    "sub_ac": child,
                    "Z_L1":   enriched_sc.loc[child, "Z_L1"],
                    "Z_L2":   enriched_sc.loc[child, "Z_L2"],
                    "tilt_L1": enriched_sc.loc[child, "tilt_L1_pct"],
                    "tilt_L2": enriched_sc.loc[child, "tilt_L2_pct"],
                    "tilt_hier": enriched_sc.loc[child, "tilt_hier_pct"],
                })
        return pd.DataFrame(rows)
