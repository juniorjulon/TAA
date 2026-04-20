"""
taa_system/config.py
====================
Central configuration for the TAA Signal System.

All tickers, column mappings, window lengths, weights, and thresholds
are defined here. Changing a value in this file propagates everywhere
without touching business logic.

Author: Investment Management
Last updated: April 2026
"""

import os

# ─────────────────────────────────────────────────────────────────────────────
# FILE PATHS
# ─────────────────────────────────────────────────────────────────────────────

_HERE       = os.path.dirname(os.path.abspath(__file__))   # src/
_ROOT       = os.path.dirname(_HERE)                        # project root
EXCEL_PATH  = os.path.join(_ROOT, "data", "Dashboard_TAA_Inputs.xlsx")
OUTPUT_DIR  = os.path.join(_ROOT, "results")                # timestamped subfolder created at runtime


# ─────────────────────────────────────────────────────────────────────────────
# SHEET / COLUMN MAPPINGS
# All dicts: {excel_column_name: internal_short_name}
# ─────────────────────────────────────────────────────────────────────────────

# Sheet "OAS": ICE BofA credit spreads (FRED), long history from 1999 (~6,900 rows).
# Spreads in decimal percent (e.g. 1.53 = 153 bps).
OAS_COLS = {
    "BAMLC0A4CBBB":            "oas_bbb",
    "BAMLH0A0HYM2":            "oas_hy",
    "BAMLEM2BRRBBBCRPIOAS":    "oas_em",
    "BAMLEMRLCRPILAOAS":       "oas_latam",
}

# Sheet "4": PE ratios, Earnings Yields, Total Return indices (~2,686 rows from 2015).
# This is the main source for equity/FI price momentum and equity valuation.
SHEET4_PE_COLS = {
    "NDUEACWF Index PE":  "msci_acwi",
    "SPTRSVX Index PE":   "sp500_value",
    "SPXQUT Index PE":    "sp500_quality",
    "SPTRSGX Index PE":   "sp500_growth",
    "NDDUEAFE Index PE":  "msci_eafe",     # previously all-NaN; now available
    "NDUEEGF Index PE":   "msci_em",
    "M1CXBRV Index PE":   "msci_em_xchina",
    "NDEUCHF Index PE":   "msci_china",
    "SPXT Index PE":      "sp500",
}

# Earnings yields (%) from sheet "4" — used for ERP calculation.
SHEET4_EY_COLS = {
    "NDUEACWF Index EY":  "msci_acwi_ey",
    "SPTRSVX Index EY":   "sp500_val_ey",
    "SPXQUT Index EY":    "sp500_qual_ey",
    "SPTRSGX Index EY":   "sp500_gro_ey",
    "NDDUEAFE Index EY":  "eafe_ey",
    "NDUEEGF Index EY":   "msci_em_ey",
    "M1CXBRV Index EY":   "em_xchina_ey",
    "NDEUCHF Index EY":   "china_ey",
    "SPXT Index EY":      "sp500_ey",
}

# Total Return price levels from sheet "4".
# These replace the old Hoja2 fi_px block as the primary momentum source.
# Note: bfu5_price (Bloomberg 1-5Y Treasury) is not in sheet 4 — i132_price is used as fallback.
SHEET4_TR_COLS = {
    "I26729US Index TR":   "usagg_price",    # Bloomberg US Aggregate
    "NDUEACWF Index TR":   "msci_acwi_px",
    "SPTRSVX Index TR":    "sp500_val_px",
    "SPXQUT Index TR":     "sp500_qual_px",
    "SPTRSGX Index TR":    "sp500_gro_px",
    "NDDUEAFE Index TR":   "eafe_px",
    "NDUEEGF Index TR":    "msci_em_px",
    "M1CXBRV Index TR":    "em_xchina_px",
    "NDEUCHF Index TR":    "china_px",
    "LT03TRUU Index TR":   "lt03_price",
    "I13282US Index TR":   "i132_price",
    "SPXT Index TR":       "sp500_tr_px",
    "BSGVTRUU Index TR":   "bsgv_price",
}

# Sheet "5": Daily market data — VIX, MOVE, CDX, yields, sentiment (~2,669 rows from 2015).
SHEET5_COLS = {
    "IBOXUMAE CBBT Curncy": "cdx_ig_spread",  # CDX NA IG 5Y spread (bps)
    "IBOXHYAE CBBT Curncy": "cdx_hy_price",   # CDX NA HY 5Y price (~100 par)
    "VIX Index":             "vix",
    "MOVE Index":            "move",
    "V2X Index":             "vstoxx",
    "VIX3M Index":           "vix3m",
    "BASPTDSP Index":        "ted",            # Basis swap spread ≈ TED proxy
    "PCRTEQTY Index":        "pcr",            # CBOE equity put/call ratio
    "SKEW Index":            "skew",
    "H15X10YR Index":        "tips_10y",       # TIPS 10Y real yield (%)
    "H15X5YR Index":         "tips_5y",        # TIPS 5Y real yield (%)
    "FDTR Index":            "fedrate",        # Fed Funds effective rate
    "GT10 @BGN Govt":        "usy_10y",
    "GT02 @BGN Govt":        "usy_2y",
    "GB03 @BGN Govt":        "tbill_3m",
}

# Sheet "F1": PMI, CESI surprise indices, GDP forecasts (~2,490 rows from 2016).
SHEET_F1_COLS = {
    "NAPMPMI Index":    "pmi_ism_mfg",       # ISM Manufacturing PMI
    "NAPMNMI Index":    "pmi_ism_svcs",       # ISM Services PMI
    "NAPMEMPL Index":   "pmi_ism_emp",        # ISM Employment sub-index
    "NAPMNEWO Index":   "pmi_ism_exports",    # ISM New Export Orders
    "MPMIEZMA Index":   "pmi_ez_mfg",         # Eurozone Manufacturing PMI
    "MPMIEZSA Index":   "pmi_ez_svcs",        # Eurozone Services PMI
    "CPMINDX Index":    "pmi_china_mfg",      # Caixin China Manufacturing PMI
    "MPMICNSA Index":   "pmi_china_svcs",     # Caixin China Services PMI
    ".ISM G Index":     "ism_new_ord_inv",    # ISM New Orders / Inventories ratio
    "CESIUSD Index":    "cesi_us",
    "CESIEUR Index":    "cesi_ez",
    "CESICNY Index":    "cesi_china",
    "CESIGL Index":     "cesi_global",
    "ECGDUS 26 Index":  "gdp_us_cur",
    "ECGDUS 27 Index":  "gdp_us_nxt",
    "ECGDM1 26 Index":  "gdp_em_cur",
    "ECGDM1 27 Index":  "gdp_em_nxt",
    "ECGDD1 26 Index":  "gdp_dm_cur",
    "ECGDD1 27 Index":  "gdp_dm_nxt",
    "ECGDEU 26 Index":  "gdp_eu_cur",
    "ECGDWO 26 Index":  "gdp_world_cur",
    "ECGDWO 27 Index":  "gdp_world_nxt",
}

# Sheet "F2": Additional regional PMI, CESI, GDP (~2,490 rows from 2016).
SHEET_F2_COLS = {
    "ECGDEU 27 Index":  "gdp_eu_nxt",
    "MPMIJPMA Index":   "pmi_japan_mfg",
    "MPMIGBMA Index":   "pmi_uk_mfg",
    "MPMIGLMA Index":   "pmi_global_mfg",
    "CESIGBP Index":    "cesi_uk",
    "CESIJPY Index":    "cesi_japan",
    "CESIEM Index":     "cesi_em",
    "ECGDJP 26 Index":  "gdp_japan_cur",
    "ECGDJP 27 Index":  "gdp_japan_nxt",
    "ECGDCN 26 Index":  "gdp_china_cur",
    "ECGDCN 27 Index":  "gdp_china_nxt",
    "ECGDR4 26 Index":  "gdp_latam_cur",
    "ECGDR4 27 Index":  "gdp_latam_nxt",
}

# Sheet "F3": Forward EPS, breakeven inflation (~2,490 rows from 2016).
SHEET_F3_COLS = {
    "SPX Index Fwd EPS":   "eps_fwd_us",
    "MXWO Index Fwd EPS":  "eps_fwd_world",
    "MXEM Index Fwd EPS":  "eps_fwd_em",
    "MXCN Index Fwd EPS":  "eps_fwd_china",
    "MXJP Index Fwd EPS":  "eps_fwd_japan",
    "MXEF Index Fwd EPS":  "eps_fwd_eafe",
    "MXLA Index Fwd EPS":  "eps_fwd_latam",
    "USGGBE05 Index":       "breakeven_5y",
    "USGGBE10 Index":       "breakeven_10y",
    "CPI XYOY Index":       "cpi_us",
}

# Sheet "AAII": AAII weekly investor sentiment.
SHEET_AAII_COLS = {
    "Bullish":          "aaii_bull",
    "Bearish":          "aaii_bear",
    "Bull-Bear Spread": "aaii_bull_bear",
}


# ─────────────────────────────────────────────────────────────────────────────
# ASSET CLASS UNIVERSE
# ─────────────────────────────────────────────────────────────────────────────

ASSET_CLASSES = [
    "money_market", "short_term_fi", "lt_treasuries",
    "lt_us_corp", "lt_em_fi",
    "us_equity", "us_growth", "us_value",
    "dm_equity", "em_equity", "em_xchina", "china_equity",
]

ASSET_CLASS_LABELS = {
    "money_market":  "Money Market",       "short_term_fi": "Short-Term FI",
    "lt_treasuries": "LT Treasuries",      "lt_us_corp":    "LT US Corporate",
    "lt_em_fi":      "LT EM Fixed Income", "us_equity":     "US Equity",
    "us_growth":     "US Growth",          "us_value":      "US Value",
    "dm_equity":     "DM ex-US Equity",    "em_equity":     "EM Equity",
    "em_xchina":     "EM ex-China",        "china_equity":  "China Equity",
}

ASSET_CLASS_GROUPS = {
    "money_market": "FI", "short_term_fi": "FI", "lt_treasuries": "FI",
    "lt_us_corp": "FI",   "lt_em_fi": "FI",
    "us_equity": "EQ",    "us_growth": "EQ",  "us_value": "EQ",
    "dm_equity": "EQ",    "em_equity": "EQ",  "em_xchina": "EQ",
    "china_equity": "EQ",
}


# ─────────────────────────────────────────────────────────────────────────────
# PILLAR WEIGHTS  (F=Fundamentals, M=Momentum, S=Sentiment, V=Valuation)
# Each row sums to 1.0
# ─────────────────────────────────────────────────────────────────────────────

PILLAR_WEIGHTS = {
    "money_market":  {"F": 0.10, "M": 0.15, "S": 0.25, "V": 0.50},
    "short_term_fi": {"F": 0.20, "M": 0.25, "S": 0.20, "V": 0.35},
    "lt_treasuries": {"F": 0.25, "M": 0.25, "S": 0.20, "V": 0.30},
    "lt_us_corp":    {"F": 0.20, "M": 0.30, "S": 0.20, "V": 0.30},
    "lt_em_fi":      {"F": 0.25, "M": 0.30, "S": 0.20, "V": 0.25},
    "us_equity":     {"F": 0.25, "M": 0.30, "S": 0.20, "V": 0.25},
    "us_growth":     {"F": 0.20, "M": 0.35, "S": 0.15, "V": 0.30},
    "us_value":      {"F": 0.30, "M": 0.25, "S": 0.20, "V": 0.25},
    "dm_equity":     {"F": 0.25, "M": 0.30, "S": 0.20, "V": 0.25},
    "em_equity":     {"F": 0.25, "M": 0.30, "S": 0.20, "V": 0.25},
    "em_xchina":     {"F": 0.25, "M": 0.30, "S": 0.20, "V": 0.25},
    "china_equity":  {"F": 0.25, "M": 0.30, "S": 0.20, "V": 0.25},
}


# ─────────────────────────────────────────────────────────────────────────────
# WINDOWS (trading days) & QUALITY PARAMETERS
# ─────────────────────────────────────────────────────────────────────────────

WINDOWS = {
    "short":  63,        #  3 months
    "medium": 252,       #  1 year
    "long":   252 * 3,   #  3 years (EWMA span)
    "xlarge": 252 * 5,   #  5 years (spread percentiles)
    "vlong":  252 * 10,  # 10 years (P/E, term premium) — adaptive if shorter
    "pmi":    60,        # 60 months (monthly PMI)
}

EWMA_SPAN        = 252 * 3  # ~3-year effective half-life for EWMA z-scores
MIN_HISTORY_DAYS = 63       # minimum observations before computing any signal

MOM_HORIZONS = {
    "1m": 21, "3m": 63, "6m": 126, "12m": 252,
    "skip": 21,  # skip last month for 12-1M cross-sectional momentum
}

MAX_FFILL_DAYS         = 5      # max consecutive ffill days for price gaps
OUTLIER_CLIP_Z         = 3.0    # winsorise z-scores beyond ±3σ
RETURN_OUTLIER_ZSCORE  = 5.0    # flag daily returns beyond 5σ as data errors


# ─────────────────────────────────────────────────────────────────────────────
# SCORING & CONVICTION
# ─────────────────────────────────────────────────────────────────────────────

# (min_z_threshold, label, tilt_fraction). Checked top-down; None = catch-all.
CONVICTION_THRESHOLDS = [
    (1.50,  "HIGH OW",   +1.0),
    (0.75,  "MEDIUM OW", +0.5),
    (-0.75, "NEUTRAL",    0.0),
    (-1.50, "MEDIUM UW", -0.5),
    (None,  "HIGH UW",   -1.0),
]

MAX_TILT_PCT = {
    "money_market": 2.0, "short_term_fi": 3.0, "lt_treasuries": 4.0,
    "lt_us_corp": 3.0,   "lt_em_fi": 3.0,
    "us_equity": 5.0,    "us_growth": 3.0, "us_value": 3.0,
    "dm_equity": 4.0,    "em_equity": 4.0, "em_xchina": 3.0,
    "china_equity": 3.0,
}

ALPHA_ABS = 0.35  # weight of absolute view; (1-ALPHA) = relative view

PILLAR_AGREEMENT_MULTIPLIERS  = {4: 1.00, 3: 0.80, 2: 0.50, 1: 0.00, 0: 0.00}
PILLAR_AGREEMENT_THRESHOLD    = 0.25  # min |z| for pillar to count as "having signal"
