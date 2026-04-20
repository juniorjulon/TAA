"""
taa_system/test_system.py
=========================
Automated tests for the TAA system.
Run: python test_system.py
Expected output: ALL TESTS PASSED
"""
import sys, os, traceback, warnings
import pandas as pd, numpy as np
warnings.filterwarnings("ignore")
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_TESTS_DIR, "..", "src"))  # src/ on path

PASS, FAIL = 0, 0

def test(name, fn):
    global PASS, FAIL
    try:
        fn()
        print(f"  OK  {name}")
        PASS += 1
    except Exception as e:
        print(f"  FAIL  {name}  ->  {e}")
        traceback.print_exc()
        FAIL += 1

# ── import tests ──────────────────────────────────────────────────────────────
print("\n=== IMPORTS ===")
def t_config():
    from config import ASSET_CLASSES, PILLAR_WEIGHTS, EXCEL_PATH, OUTPUT_DIR
    assert len(ASSET_CLASSES) == 12
    assert os.path.exists(EXCEL_PATH), f"Excel not found: {EXCEL_PATH}"

def t_loader():   from data_loader import load_all, get_series
def t_signals():  from signals import rolling_zscore, ewma_zscore, composite_price_momentum
def t_proxies():  from proxies import build_proxy_ext
def t_pillars():  from pillars import pillar_fundamentals, pillar_momentum, pillar_sentiment, pillar_valuation
def t_scoring():  from scoring import composite_score, score_snapshot, z_to_conviction, print_scorecard

for nm, fn in [("config",      t_config),
               ("data_loader", t_loader),
               ("signals",     t_signals),
               ("proxies",     t_proxies),
               ("pillars",     t_pillars),
               ("scoring",     t_scoring)]:
    test(nm, fn)

# ── data loading ──────────────────────────────────────────────────────────────
print("\n=== DATA LOADING ===")
from data_loader import load_all
data = load_all(verbose=False)

def t_sheets_present():
    for k in ["oas", "pe", "yields", "fi_px", "tsy", "cds", "mkt", "f1", "f3", "aaii"]:
        df = data.get(k)
        assert df is not None and not df.empty, f"Sheet '{k}' is empty or missing"

def t_dates_ascending():
    for k, df in data.items():
        if isinstance(df, pd.DataFrame) and not df.empty:
            assert df.index.is_monotonic_increasing, f"{k} index not sorted ascending"

def t_oas_long_history():
    oas = data["oas"]
    assert oas.index.min().year <= 2001, f"OAS should start from ~1999/2000, got {oas.index.min()}"
    assert oas.shape[0] > 6000, f"OAS should have >6000 rows, got {oas.shape[0]}"
    assert "oas_bbb" in oas.columns

def t_fi_px_present():
    fi = data["fi_px"]
    assert "sp500_tr_px" in fi.columns, "sp500_tr_px missing from fi_px"
    assert fi.index.min().year <= 2016, f"fi_px should start from 2015/2016, got {fi.index.min()}"
    assert fi.shape[0] > 1000

def t_yields_present():
    y = data["yields"]
    assert "sp500_ey" in y.columns, "sp500_ey missing"
    assert y["sp500_ey"].dropna().shape[0] > 500

def t_tsy_computed():
    tsy = data["tsy"]
    assert "term_spread" in tsy.columns, "term_spread not computed"
    assert "usy_10y" in tsy.columns
    assert "usy_2y" in tsy.columns

def t_mkt_signals():
    mkt = data["mkt"]
    for col in ["vix", "move"]:
        assert col in mkt.columns, f"{col} missing from mkt"
    assert mkt["vix"].dropna().shape[0] > 500

def t_f1_fundamentals():
    f1 = data["f1"]
    for col in ["pmi_ism_mfg", "cesi_us"]:
        assert col in f1.columns, f"{col} missing from f1"
    assert f1["pmi_ism_mfg"].dropna().shape[0] > 100

def t_f3_eps():
    f3 = data["f3"]
    assert "eps_fwd_us" in f3.columns, "eps_fwd_us missing from f3"

def t_no_zero_prices():
    fi = data["fi_px"]
    assert (fi == 0).sum().sum() == 0, "fi_px contains zero prices"

for nm, fn in [("all sheets present",     t_sheets_present),
               ("dates ascending",         t_dates_ascending),
               ("OAS long history",        t_oas_long_history),
               ("fi_px present",           t_fi_px_present),
               ("yields present",          t_yields_present),
               ("tsy with term_spread",    t_tsy_computed),
               ("mkt VIX/MOVE present",    t_mkt_signals),
               ("f1 fundamentals present", t_f1_fundamentals),
               ("f3 EPS present",          t_f3_eps),
               ("no zero prices",          t_no_zero_prices)]:
    test(nm, fn)

# ── signal functions ──────────────────────────────────────────────────────────
print("\n=== SIGNALS ===")
from signals import (rolling_zscore, ewma_zscore, pctile_rank,
                     composite_price_momentum, spread_momentum,
                     yield_momentum, pe_score, equity_risk_premium,
                     oas_level_score, relative_pe)

fi   = data["fi_px"]
oas  = data["oas"]
tsy  = data["tsy"]
ylds = data["yields"]

price = fi["sp500_tr_px"].dropna()
oa    = oas["oas_bbb"].dropna()
gt10  = tsy["usy_10y"].dropna()
ey    = ylds["sp500_ey"].dropna()

def t_rolling_zscore_output():
    z = rolling_zscore(price.pct_change(21), 252)
    assert z.dropna().shape[0] > 0
    assert z.dropna().abs().max() <= 3.0 + 1e-6, f"winsorise failed: max={z.dropna().abs().max()}"

def t_ewma_zscore_output():
    z = ewma_zscore(price.pct_change(21))
    assert z.dropna().shape[0] > 0
    assert z.dropna().abs().max() <= 3.0 + 1e-6

def t_pctile_range():
    p = pctile_rank(oa, 252 * 5)
    assert p.dropna().min() >= 0.0
    assert p.dropna().max() <= 1.0

def t_composite_momentum():
    m = composite_price_momentum(price)
    assert m.dropna().shape[0] > 200, f"Expected >200 obs, got {m.dropna().shape[0]}"

def t_spread_momentum_sign():
    tight = pd.Series(np.linspace(5.0, 2.0, 200),
                      index=pd.date_range("2020-01-01", periods=200))
    z = spread_momentum(tight, 21, invert=True)
    assert z.dropna().iloc[-1] > 0, "Tightening should give positive signal"

def t_pe_score_cheap():
    vals = list(np.linspace(30, 8, 80))
    pe_s = pd.Series(vals, index=pd.date_range("2014-01-01", periods=80, freq="ME"))
    scores = pe_score(pe_s)
    nona = scores.dropna()
    assert len(nona) > 0, "pe_score returned all NaN"
    assert nona.iloc[-1] > nona.iloc[0], "Score should increase as P/E falls"

def t_erp_signal():
    z = equity_risk_premium(ey, gt10)
    assert z.dropna().shape[0] > 200

def t_oas_level_score_high():
    w = pd.Series([0.8, 1.0, 1.5, 2.0, 3.0, 4.5, 6.0],
                  index=pd.date_range("2020-01-01", periods=7, freq="ME"))
    s = oas_level_score(w)
    if s.dropna().shape[0] >= 2:
        assert s.dropna().iloc[-1] > s.dropna().iloc[0], "Widening OAS should increase score"

for nm, fn in [("rolling_zscore winsorised",  t_rolling_zscore_output),
               ("ewma_zscore winsorised",      t_ewma_zscore_output),
               ("pctile in [0,1]",             t_pctile_range),
               ("composite_mom",               t_composite_momentum),
               ("spread_mom sign convention",  t_spread_momentum_sign),
               ("pe_score cheap = positive",   t_pe_score_cheap),
               ("erp signal",                  t_erp_signal),
               ("oas_level wide = positive",   t_oas_level_score_high)]:
    test(nm, fn)

# ── proxies ───────────────────────────────────────────────────────────────────
print("\n=== PROXIES ===")
from proxies import build_proxy_ext

ext_proxy = build_proxy_ext(data, verbose=False)

def t_proxy_keys():
    required = ["pmi_us", "pmi_ez", "pmi_china", "cesi_us", "cesi_em",
                "gdp_us", "gdp_em", "eps_us", "eps_em",
                "breakeven_5y", "breakeven_10y",
                "vix", "move", "ted", "dxy", "embi", "pcr"]
    for k in required:
        assert k in ext_proxy, f"Proxy key '{k}' missing"

def t_proxy_winsorised():
    for k, v in ext_proxy.items():
        if isinstance(v, pd.Series) and v.dropna().shape[0] > 0:
            assert v.dropna().abs().max() <= 3.0 + 1e-6, f"Proxy {k} not winsorised"

for nm, fn in [("proxy keys present", t_proxy_keys),
               ("proxies winsorised", t_proxy_winsorised)]:
    test(nm, fn)

# ── build_bloomberg_series (real Excel data) ──────────────────────────────────
print("\n=== BLOOMBERG SERIES (from Excel) ===")
from main import build_bloomberg_series

bbg = build_bloomberg_series(data)

def t_bbg_pmi_live():
    s = bbg.get("pmi_us")
    assert s is not None and isinstance(s, pd.Series), "pmi_us missing"
    assert s.dropna().shape[0] > 100, f"pmi_us too few obs: {s.dropna().shape[0]}"

def t_bbg_vix_live():
    s = bbg.get("vix")
    assert s is not None and isinstance(s, pd.Series), "vix missing"
    assert s.dropna().shape[0] > 500

def t_bbg_eps_live():
    s = bbg.get("eps_us")
    assert s is not None and isinstance(s, pd.Series), "eps_us missing"
    assert s.dropna().shape[0] > 100

for nm, fn in [("pmi_us from Excel", t_bbg_pmi_live),
               ("vix from Excel",    t_bbg_vix_live),
               ("eps_us from Excel", t_bbg_eps_live)]:
    test(nm, fn)

# ── pillars ───────────────────────────────────────────────────────────────────
print("\n=== PILLARS ===")
from pillars import pillar_fundamentals, pillar_momentum, pillar_sentiment, pillar_valuation
from config import ASSET_CLASSES

# Build full ext dict (bbg overrides proxies)
from proxies import build_proxy_ext
ext = {}
for key, proxy_val in ext_proxy.items():
    if key.startswith("_"):
        ext[key] = proxy_val
        continue
    bbg_val = bbg.get(key)
    is_live = (bbg_val is not None and isinstance(bbg_val, pd.Series)
               and bbg_val.dropna().shape[0] > 0)
    ext[key] = bbg_val if is_live else proxy_val
for key, val in bbg.items():
    if key not in ext:
        ext[key] = val

def t_all_pillars_run():
    for ac in ASSET_CLASSES:
        for fn, nm in [(pillar_fundamentals, "F"), (pillar_momentum, "M"),
                       (pillar_sentiment,    "S"), (pillar_valuation, "V")]:
            kw = dict(ext=ext) if fn in (pillar_fundamentals, pillar_sentiment) else {}
            result = fn(ac, data, **kw) if kw else fn(ac, data)
            assert isinstance(result, pd.Series), f"{ac} pillar {nm} not a Series"

def t_pillar_winsorised():
    for ac in ASSET_CLASSES:
        for fn, nm in [(pillar_momentum, "M"), (pillar_valuation, "V")]:
            s = fn(ac, data)
            if isinstance(s, pd.Series) and s.dropna().shape[0] > 0:
                assert s.dropna().abs().max() <= 3.0 + 1e-6, f"{ac} pillar {nm} not winsorised"

def t_12_of_12_active():
    for ac in ASSET_CLASSES:
        active = 0
        for fn in [pillar_fundamentals, pillar_momentum,
                   pillar_sentiment, pillar_valuation]:
            kw = dict(ext=ext) if fn in (pillar_fundamentals, pillar_sentiment) else {}
            s = fn(ac, data, **kw) if kw else fn(ac, data)
            if isinstance(s, pd.Series) and s.dropna().shape[0] > 0:
                active += 1
        assert active >= 2, f"{ac} has only {active} active pillars"

for nm, fn in [("all pillars run without error", t_all_pillars_run),
               ("pillar outputs winsorised",      t_pillar_winsorised),
               ("12/12 ACs active",               t_12_of_12_active)]:
    test(nm, fn)

# ── scoring ───────────────────────────────────────────────────────────────────
print("\n=== SCORING ===")
from scoring import composite_score, score_snapshot, z_to_conviction, pillar_agreement

pillar_scores = {}
for ac in ASSET_CLASSES:
    pillar_scores[ac] = {
        "F": pillar_fundamentals(ac, data, ext),
        "M": pillar_momentum(ac, data),
        "S": pillar_sentiment(ac, data, ext),
        "V": pillar_valuation(ac, data),
    }

def t_composite_runs():
    for ac in ASSET_CLASSES:
        c = composite_score(pillar_scores[ac], ac)
        assert isinstance(c, pd.Series)

def t_z_to_conviction():
    assert z_to_conviction(+2.0) == ("HIGH OW",  +1.0)
    assert z_to_conviction(+1.0) == ("MEDIUM OW", +0.5)
    assert z_to_conviction( 0.0) == ("NEUTRAL",    0.0)
    assert z_to_conviction(-1.0) == ("MEDIUM UW", -0.5)
    assert z_to_conviction(-2.0) == ("HIGH UW",   -1.0)
    assert z_to_conviction(float("nan")) == ("N/A", 0.0)

def t_pillar_agreement():
    n, d, m = pillar_agreement({"F": +1.5, "M": +0.8, "S": +1.2, "V": +0.9})
    assert n == 4 and d == 1.0 and m == 1.0
    n2, _, m2 = pillar_agreement({"F": -1.0, "M": +1.0, "S": -1.5, "V": -0.8})
    assert n2 == 3
    n3, _, m3 = pillar_agreement({"F": 0.1, "M": -0.1, "S": 0.05, "V": -0.05})
    assert n3 == 0 and m3 == 0.0

def t_scorecard_shape():
    sc = score_snapshot(pillar_scores)
    assert sc.shape[0] == 12, f"Expected 12 rows, got {sc.shape[0]}"
    for col in ["label", "Z_composite", "conviction", "final_tilt_%", "Z_relative"]:
        assert col in sc.columns, f"Missing column '{col}'"

def t_scorecard_tilts_bounded():
    from config import MAX_TILT_PCT
    sc = score_snapshot(pillar_scores)
    for ac in ASSET_CLASSES:
        if ac in sc.index:
            tilt  = float(sc.loc[ac, "final_tilt_%"])
            max_t = MAX_TILT_PCT[ac]
            assert abs(tilt) <= max_t + 1e-6, f"{ac}: tilt {tilt:.2f}% > max {max_t:.1f}%"

def t_relative_z_zero_mean():
    sc = score_snapshot(pillar_scores)
    rel = pd.to_numeric(sc["Z_relative"], errors="coerce").dropna()
    assert abs(rel.mean()) < 0.01, f"Relative z mean ≠ 0: {rel.mean():.4f}"

for nm, fn in [("composite_score runs",        t_composite_runs),
               ("z_to_conviction thresholds",   t_z_to_conviction),
               ("pillar_agreement logic",        t_pillar_agreement),
               ("scorecard shape 12xN",          t_scorecard_shape),
               ("tilts within bounds",           t_scorecard_tilts_bounded),
               ("relative z mean=0",             t_relative_z_zero_mean)]:
    test(nm, fn)

# ── summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
total = PASS + FAIL
print(f"  {PASS}/{total} tests passed  {'ALL PASSED' if FAIL == 0 else f'{FAIL} FAILED'}")
print(f"{'='*50}\n")
if FAIL > 0:
    sys.exit(1)
