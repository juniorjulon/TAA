"""
taa_system/main.py
==================
Entry point for the TAA Signal System.

Run:
  cd "9_TAA Dashboard"
  python main.py

OUTPUT FILES (written to the project folder):
  taa_scorecard.csv          : latest snapshot (one row per asset class)
  taa_composite_series.csv   : full time series of composite z-scores
  pillars_{ac}.csv           : per-pillar time series for each asset class

DATA SOURCES (all from Dashboard_TAA_Inputs.xlsx):
  OAS     : ICE BofA credit spreads, long history from 1999
  Sheet 4 : PE, earnings yields, TR price levels, from 2015
  Sheet 5 : VIX, MOVE, CDX, Treasury yields, sentiment, from 2015
  F1/F2   : PMI, CESI, GDP forecasts, from 2016
  F3      : Forward EPS, breakeven inflation, from 2016
  AAII    : Weekly investor sentiment

HOW TO ADD LIVE BLOOMBERG/FRED OVERRIDES:
  In build_bloomberg_series() below, replace the empty pd.Series() placeholders
  with real live data. Non-empty series override the Excel data automatically.
"""

import os
import sys
import warnings
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # src/ on path

from data_loader          import load_all
from proxies              import build_proxy_ext
from pillars              import (pillar_fundamentals, pillar_momentum,
                                   pillar_sentiment,    pillar_valuation,
                                   build_all_pillars)
from signal_engine        import SignalEngine
from scoring              import (composite_score, score_snapshot,
                                   print_scorecard, apply_crisis_override)
from hierarchical_scoring import HierarchicalViews
from portfolio            import (load_portfolio_configs, build_multi_portfolio_report)
from config               import ASSET_CLASSES, OUTPUT_DIR, MAX_FFILL_DAYS, CONFIG_XLSX
from signals              import ewma_zscore, rolling_zscore, pctile_rank, WINDOWS


# ─────────────────────────────────────────────────────────────────────────────
# BUILD REAL SIGNALS FROM EXCEL DATA
# Returns an ext dict populated from the already-loaded data dict.
# If you connect live Bloomberg/FRED, return non-empty series to override.
# ─────────────────────────────────────────────────────────────────────────────

def build_bloomberg_series(data: dict) -> dict:
    """
    Build the external signals dict from data in the Excel workbook (H1-H6 structure).

    All signals now sourced from Excel — no Bloomberg API required:
      Fundamentals   : PMI, CESI, GDP, Forward EPS                → H1/H2/H3
      Inflation      : Breakeven 5Y/10Y, PCE YoY, CPI             → H5
      Sentiment vol  : VIX, MOVE, VSTOXX, VIX3M, PCR, SKEW       → H5
      Sentiment new  : DXY (USD Index, from 2011)                  → H5
                       BFCIUS (Bloomberg US FCI, from 2011)        → H5
                       Modern TED = 3M T-bill − SOFR (from 2018)  → H5 (computed in tsy)
                       AAII Bull-Bear Spread (from 1987)           → AAII
      EMBI proxy     : EM BBB OAS from OAS sheet (unchanged)

    New signals wired in v2:
      dxy        → EM FI, EM equity, EM ex-China, China equity sentiment
      modern_ted → all AC sentiment (replaces dead BASPTDSP)
      fci        → US equity/credit sentiment (FCI tight = headwind)
      real_ff    → money market and STFI fundamentals (FDTR - PCE)
      vstoxx     → DM equity sentiment (now wired, was loaded but unused)
      aaii       → US equity sentiment (contrarian, now wired)
      pmi_japan  → DM equity fundamentals (now wired)
      gdp_japan  → DM equity fundamentals (now wired)
      eps_japan  → DM equity fundamentals (now wired)

    Returns: dict of {signal_name: pd.Series} ready for pillar functions.
    """
    f1   = data.get("f1",   pd.DataFrame())
    f3   = data.get("f3",   pd.DataFrame())
    mkt  = data.get("mkt",  pd.DataFrame())
    tsy  = data.get("tsy",  pd.DataFrame())
    aaii = data.get("aaii", pd.DataFrame())
    oas  = data.get("oas",  pd.DataFrame())

    def _s(df, col):
        if not df.empty and col in df.columns:
            s = df[col].dropna()
            return s if len(s) > 0 else pd.Series(dtype=float)
        return pd.Series(dtype=float)

    # ── Fundamentals ─────────────────────────────────────────────────────────

    def _pmi_composite(mfg_col, svcs_col=None):
        mfg  = _s(f1, mfg_col)
        if svcs_col:
            svcs = _s(f1, svcs_col)
            if not svcs.dropna().empty and not mfg.dropna().empty:
                return mfg.add(svcs, fill_value=np.nan) / 2
        return mfg

    pmi_us    = _pmi_composite("pmi_ism_mfg", "pmi_ism_svcs")
    pmi_ez    = _pmi_composite("pmi_ez_mfg",  "pmi_ez_svcs")
    pmi_china = _pmi_composite("pmi_china_mfg", "pmi_china_svcs")
    pmi_japan = _s(f1, "pmi_japan_mfg")   # now wired into dm_equity fundamentals
    pmi_uk    = _s(f1, "pmi_uk_mfg")
    pmi_global= _s(f1, "pmi_global_mfg")

    cesi_us    = _s(f1, "cesi_us")
    cesi_ez    = _s(f1, "cesi_ez")
    cesi_china = _s(f1, "cesi_china")
    cesi_em    = _s(f1, "cesi_em")
    cesi_japan = _s(f1, "cesi_japan")

    def _blended_gdp(cur_col, nxt_col):
        cur = _s(f1, cur_col)
        nxt = _s(f1, nxt_col)
        if cur.dropna().empty:
            return nxt
        if nxt.dropna().empty:
            return cur
        idx   = cur.index.union(nxt.index)
        cur   = cur.reindex(idx).ffill()
        nxt   = nxt.reindex(idx).ffill()
        w_cur = pd.Series(idx.month / 12, index=idx)
        return w_cur * cur + (1 - w_cur) * nxt

    gdp_us    = _blended_gdp("gdp_us_cur",    "gdp_us_nxt")
    gdp_em    = _blended_gdp("gdp_em_cur",    "gdp_em_nxt")
    gdp_dm    = _blended_gdp("gdp_dm_cur",    "gdp_dm_nxt")
    gdp_eu    = _blended_gdp("gdp_eu_cur",    "gdp_eu_nxt")
    gdp_japan = _blended_gdp("gdp_japan_cur", "gdp_japan_nxt")  # now wired
    gdp_china = _blended_gdp("gdp_china_cur", "gdp_china_nxt")
    gdp_latam = _blended_gdp("gdp_latam_cur", "gdp_latam_nxt")

    def _eps_revision(col):
        s = _s(f3, col)
        if s.dropna().empty:
            return pd.Series(dtype=float)
        return ewma_zscore(s.pct_change(21), span=WINDOWS["medium"])

    eps_us    = _eps_revision("eps_fwd_us")
    eps_em    = _eps_revision("eps_fwd_em")
    eps_world = _eps_revision("eps_fwd_world")
    eps_china = _eps_revision("eps_fwd_china")
    eps_japan = _eps_revision("eps_fwd_japan")  # now wired into dm_equity
    eps_eafe  = _eps_revision("eps_fwd_eafe")
    eps_latam = _eps_revision("eps_fwd_latam")

    # Breakeven inflation: now in mkt (H5), not f3
    def _bkev(col):
        s = _s(mkt, col)
        if s.dropna().empty:
            return pd.Series(dtype=float)
        return ewma_zscore(s, span=WINDOWS["vlong"])

    bkev_5y  = _bkev("breakeven_5y")
    bkev_10y = _bkev("breakeven_10y")

    # ── Real Fed Funds Rate (new) ─────────────────────────────────────────────
    # PCE is monthly (ffilled), FDTR daily. real_ff = FDTR - PCE_YoY.
    # When real_ff > 0: restrictive. Used in MM and STFI fundamentals.
    fedrate = _s(tsy, "fedrate")
    pce_yoy = _s(tsy, "pce_yoy")
    real_ff = pd.Series(dtype=float)
    if not fedrate.dropna().empty and not pce_yoy.dropna().empty:
        idx = fedrate.index.union(pce_yoy.index)
        ff  = fedrate.reindex(idx).ffill(limit=MAX_FFILL_DAYS)
        pce = pce_yoy.reindex(idx).ffill(limit=35)  # monthly → ffill up to 35 days
        real_ff = (ff - pce).clip(lower=-10, upper=15)

    # ── Sentiment ─────────────────────────────────────────────────────────────

    vix    = _s(mkt, "vix")
    move   = _s(mkt, "move")
    vstoxx = _s(mkt, "vstoxx")   # now wired into dm_equity sentiment
    pcr    = _s(mkt, "pcr")

    # Modern TED = 3M T-bill − SOFR (computed in load_tsy); fallback: empty before 2018
    modern_ted = _s(tsy, "modern_ted")

    # DXY (USD Index): now in H5 from 2011. Positive = USD strong = EM headwind.
    dxy_raw = _s(mkt, "dxy")
    dxy_z   = (ewma_zscore(dxy_raw, span=WINDOWS["medium"])
               if not dxy_raw.dropna().empty else pd.Series(dtype=float))

    # Bloomberg US FCI (BFCIUS): positive = tight conditions = risk headwind.
    fci_raw = _s(mkt, "fci")
    fci_z   = (ewma_zscore(fci_raw, span=WINDOWS["medium"])
               if not fci_raw.dropna().empty else pd.Series(dtype=float))

    # AAII Bull-Bear Spread: z-scored, contrarian. High = euphoria = bearish equity.
    aaii_bb = _s(aaii, "aaii_bull_bear")
    aaii_z  = (ewma_zscore(aaii_bb, span=WINDOWS["xlarge"])
               if not aaii_bb.dropna().empty else pd.Series(dtype=float))

    # EMBI proxy: EM BBB OAS. High EM OAS = EM stress = negative for EM assets.
    embi_proxy = pd.Series(dtype=float)
    if not oas.empty and "oas_em" in oas.columns:
        em_oas = oas["oas_em"].dropna()
        if len(em_oas) > 0:
            embi_proxy = -ewma_zscore(em_oas, span=WINDOWS["xlarge"])

    return {
        # PMI composites
        "pmi_us":        pmi_us,
        "pmi_ez":        pmi_ez,
        "pmi_china":     pmi_china,
        "pmi_japan":     pmi_japan,
        "pmi_uk":        pmi_uk,
        "pmi_global":    pmi_global,
        # CESI
        "cesi_us":       cesi_us,
        "cesi_ez":       cesi_ez,
        "cesi_china":    cesi_china,
        "cesi_em":       cesi_em,
        "cesi_japan":    cesi_japan,
        # GDP blends
        "gdp_us":        gdp_us,
        "gdp_em":        gdp_em,
        "gdp_dm":        gdp_dm,
        "gdp_eu":        gdp_eu,
        "gdp_japan":     gdp_japan,
        "gdp_china":     gdp_china,
        "gdp_latam":     gdp_latam,
        # EPS revisions
        "eps_us":        eps_us,
        "eps_em":        eps_em,
        "eps_world":     eps_world,
        "eps_china":     eps_china,
        "eps_japan":     eps_japan,
        "eps_eafe":      eps_eafe,
        "eps_latam":     eps_latam,
        # Inflation
        "breakeven_5y":  bkev_5y,
        "breakeven_10y": bkev_10y,
        # Fundamentals — rate environment
        "real_ff":       real_ff,        # Real Fed Funds = FDTR - PCE (new)
        # Sentiment — volatility (raw levels, pillar_sentiment normalises)
        "vix":           vix,
        "move":          move,
        "vstoxx":        vstoxx,         # now wired into dm_equity
        # Sentiment — positioning / contrarian
        "pcr":           pcr,
        "aaii":          aaii_z,         # now wired into us_equity (contrarian)
        # Sentiment — macro stress (new/restored)
        "dxy":           dxy_z,          # USD strength z-score (new — was empty)
        "fci":           fci_z,          # Bloomberg FCI z-score (new)
        "ted":           modern_ted,     # Modern TED = tbill_3m - SOFR (replaces dead BASPTDSP)
        "embi":          embi_proxy,     # EM BBB OAS proxy (unchanged)
    }


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(verbose: bool = True) -> dict:
    """
    Execute the full TAA scoring pipeline (Excel-driven via SignalEngine).

    Returns
    -------
    dict:
      'pillar_scores' : {ac: {'F','M','S','V'} → pd.Series}
      'composites'    : {ac: pd.Series}  full time series
      'scorecard'     : pd.DataFrame     latest snapshot
      'data'          : dict             cleaned raw data
    """
    print("=" * 60)
    print("  TAA SIGNAL SYSTEM")
    print("=" * 60)

    # STEP 1: Load raw data (needed for crisis override + proxy fallbacks)
    data = load_all(verbose=verbose)

    # Data freshness check — OAS often lags H5 by several weeks
    _oas = data.get("oas", pd.DataFrame())
    _mkt = data.get("mkt", pd.DataFrame())
    if not _oas.empty and not _mkt.empty:
        _oas_lag = (_mkt.index.max() - _oas.index.max()).days
        if _oas_lag > 7:
            print(f"  WARNING: OAS data is {_oas_lag} days behind H5 "
                  f"({_oas.index.max().date()} vs {_mkt.index.max().date()}). "
                  f"Credit signals (oas_bbb, oas_em, hy_stress) may be stale.")

    # STEP 2: Load all signals via SignalEngine (reads DataSeries from taa_config.xlsx)
    if verbose:
        print("\nLoading signals via SignalEngine...")
    engine  = SignalEngine()
    signals = engine.load_all(verbose=verbose)

    # STEP 3: Proxy fallbacks for signals not loaded by engine
    proxies = build_proxy_ext(data, verbose=verbose)
    for key, proxy_val in proxies.items():
        if key.startswith("_"):
            continue
        sig = signals.get(key)
        if sig is None or (isinstance(sig, pd.Series) and sig.dropna().empty):
            signals[key] = proxy_val

    if verbose:
        print(f"\n  Total signals available: {len(signals)}")

    # STEP 4: Get SignalMapping and build pillar scores
    signal_mapping = engine.get_signal_mapping()

    if verbose:
        print("\nBuilding pillar scores...")

    pillar_scores = {}
    for ac in ASSET_CLASSES:
        try:
            ps = build_all_pillars(ac, signals, signal_mapping)
            pillar_scores[ac] = ps

            if verbose:
                live = sum(1 for s in ps.values()
                           if isinstance(s, pd.Series) and s.dropna().shape[0] > 0)
                print(f"  {ac:<22} {live}/4 pillars active")

        except Exception as exc:
            import traceback
            print(f"  {ac:<22} ERROR: {exc}")
            traceback.print_exc()
            pillar_scores[ac] = {"F": None, "M": None, "S": None, "V": None}

    # STEP 5: Composite scores
    if verbose:
        print("\nComposite z-scores (latest):")

    composites = {}
    for ac in ASSET_CLASSES:
        comp = composite_score(pillar_scores[ac], ac)
        composites[ac] = comp
        if verbose:
            if comp.dropna().shape[0] > 0:
                last = comp.dropna().iloc[-1]
                print(f"  {ac:<22} {last:+.3f}")
            else:
                print(f"  {ac:<22} no data")

    # STEP 6: Scorecard snapshot
    scorecard = score_snapshot(pillar_scores)

    # STEP 7: Hierarchical views (Level 1 aggregate + Level 2 within-class)
    hv = HierarchicalViews()
    hierarchy_scorecard = hv.enrich(scorecard)
    bucket_summary      = hv.bucket_summary(hierarchy_scorecard)

    if verbose:
        print("\nHierarchical views (L1 aggregate | L2 within-class):")
        print(f"  {'Bucket':<20} {'Z_L1':>7}  {'Sub-AC':<22} {'Z_L2':>7} {'tilt_L1':>8} {'tilt_L2':>8} {'tilt_hier':>10}")
        print(f"  {'-'*88}")
        for _, brow in bucket_summary.iterrows():
            if brow["sub_ac"] == "[AGGREGATE]":
                z1 = f"{brow['Z_L1']:+.3f}" if not pd.isna(brow['Z_L1']) else " n/a"
                print(f"  {brow['bucket']:<20} {z1:>7}  {'[aggregate L1]':<22}")
            elif brow["sub_ac"] == "":
                z1 = f"{brow['Z_L1']:+.3f}" if not pd.isna(brow['Z_L1']) else " n/a"
                print(f"  {brow['bucket']:<20} {z1:>7}")
            else:
                z2  = f"{float(brow['Z_L2']):+.3f}" if brow['Z_L2'] != "" else "    -"
                tl1 = f"{float(brow['tilt_L1']):+.2f}%" if brow['tilt_L1'] != "" else "    -"
                tl2 = f"{float(brow['tilt_L2']):+.2f}%" if brow['tilt_L2'] != "" else "    -"
                th  = f"{float(brow['tilt_hier']):+.2f}%" if brow['tilt_hier'] != "" else "    -"
                print(f"  {'':20} {'':>7}  {brow['sub_ac']:<22} {z2:>7} {tl1:>8} {tl2:>8} {th:>10}")

    # Crisis override: VIX and MOVE from mkt sheet
    mkt = data.get("mkt", pd.DataFrame())
    vix_pctile = move_pctile = None
    if not mkt.empty:
        if "vix" in mkt.columns:
            vp = pctile_rank(mkt["vix"].dropna(), WINDOWS["xlarge"])
            if len(vp.dropna()) > 0:
                vix_pctile = float(vp.dropna().iloc[-1])
        if "move" in mkt.columns:
            mp = pctile_rank(mkt["move"].dropna(), WINDOWS["xlarge"])
            if len(mp.dropna()) > 0:
                move_pctile = float(mp.dropna().iloc[-1])

    scorecard = apply_crisis_override(scorecard, vix_pctile, move_pctile)

    dates_avail = [composites[ac].dropna().index[-1]
                   for ac in ASSET_CLASSES
                   if ac in composites and composites[ac].dropna().shape[0] > 0]
    latest_date = str(max(dates_avail).date()) if dates_avail else "Unknown"

    print_scorecard(scorecard, date=latest_date)

    # Build current signal z-score snapshot: latest value for each series_id
    sig_z_snapshot = {}
    for sid, s in signals.items():
        if s is None or not isinstance(s, pd.Series):
            continue
        clean = s.dropna()
        if len(clean) > 0:
            sig_z_snapshot[sid] = round(float(clean.iloc[-1]), 4)

    return {
        "pillar_scores":      pillar_scores,
        "composites":         composites,
        "scorecard":          scorecard,
        "hierarchy_scorecard": hierarchy_scorecard,
        "bucket_summary":     bucket_summary,
        "data":               data,
        "sig_z_snapshot":     sig_z_snapshot,
    }


def export_results(results: dict, out_dir: str = None) -> None:
    """Export all outputs to results/RUN_YYYYMMDD_HHMM/."""
    import os as _os
    import json as _json
    from datetime import datetime
    timestamp = datetime.now().strftime("RUN_%Y%m%d_%H%M%S")
    base      = out_dir if out_dir is not None else OUTPUT_DIR
    run_dir   = _os.path.join(base, timestamp)
    _os.makedirs(run_dir, exist_ok=True)

    # ── Signal z-score snapshot (series_id -> latest z-score) ────────────────
    sig_z = results.get("sig_z_snapshot", {})
    if sig_z:
        sig_z_path = _os.path.join(run_dir, "signal_z_snapshot.json")
        with open(sig_z_path, "w") as _f:
            _json.dump(sig_z, _f, indent=2)
        # Also write to results/ root so generate_dashboard.py can find latest
        sig_z_root = _os.path.join(base, "signal_z_snapshot.json")
        with open(sig_z_root, "w") as _f:
            _json.dump(sig_z, _f, indent=2)
        print(f"  Signal Z snap    -> {sig_z_path}")

    # ── Standard outputs ─────────────────────────────────────────────────────
    sc_path = _os.path.join(run_dir, "taa_scorecard.csv")
    results["scorecard"].to_csv(sc_path)
    print(f"  Scorecard        -> {sc_path}")

    comp_df = pd.DataFrame(results["composites"])
    ts_path = _os.path.join(run_dir, "taa_composite_series.csv")
    comp_df.to_csv(ts_path)
    print(f"  Composite series -> {ts_path}")

    for ac, ps in results["pillar_scores"].items():
        rows = {p: s for p, s in ps.items()
                if isinstance(s, pd.Series) and s.dropna().shape[0] > 0}
        if rows:
            pd.DataFrame(rows).to_csv(
                _os.path.join(run_dir, f"pillars_{ac}.csv"))
    print(f"  Pillar series    -> {run_dir}/pillars_*.csv")

    # ── Hierarchical scorecard ────────────────────────────────────────────────
    hier_sc = results.get("hierarchy_scorecard")
    if hier_sc is not None:
        hier_path = _os.path.join(run_dir, "taa_hierarchy_scorecard.csv")
        hier_sc.to_csv(hier_path)
        print(f"  Hierarchy views  -> {hier_path}")

        bucket_path = _os.path.join(run_dir, "taa_bucket_summary.csv")
        results.get("bucket_summary", pd.DataFrame()).to_csv(bucket_path, index=False)
        print(f"  Bucket summary   -> {bucket_path}")

    # ── Multi-portfolio views ─────────────────────────────────────────────────
    ptf_path = _os.path.join(run_dir, "multi_portfolio_views.xlsx")
    portfolios_file = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)),
                                    "config", "portfolios.xlsx")
    if _os.path.exists(portfolios_file):
        try:
            portfolios = load_portfolio_configs(portfolios_file)
            build_multi_portfolio_report(results["scorecard"], portfolios, ptf_path)
        except Exception as exc:
            print(f"  Multi-portfolio  -> SKIPPED ({exc})")
    else:
        print(f"  Multi-portfolio  -> SKIPPED (config/portfolios.xlsx not found)")

    print(f"\n  All outputs in: {run_dir}")


if __name__ == "__main__":
    results = run_pipeline(verbose=True)
    export_results(results)
