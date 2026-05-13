"use strict";
const pptxgen = require("pptxgenjs");

// ─── THEME ────────────────────────────────────────────────────────────────────
const C = {
  red:        "C41230",
  darkRed:    "8B0000",
  black:      "1A1A1A",
  white:      "FFFFFF",
  offWhite:   "F7F7F7",
  lightGrey:  "EBEBEB",
  midGrey:    "888888",
  darkGrey:   "444444",
  redLight:   "F5D0D7",
};

const FONT_HEADER = "Calibri";
const FONT_BODY   = "Calibri";

let pres = new pptxgen();
pres.layout  = "LAYOUT_16x9";   // 10" × 5.625"
pres.author  = "Rimac Group";
pres.title   = "TAA System — Investment Committee";

// ─── HELPERS ─────────────────────────────────────────────────────────────────
const makeShadow = () => ({ type: "outer", blur: 5, offset: 2, angle: 135, color: "000000", opacity: 0.12 });

function addRedHeader(slide, text, y = 0, h = 0.52) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y, w: 10, h,
    fill: { color: C.red },
  });
  slide.addText(text, {
    x: 0.4, y: y + 0.04, w: 9.2, h: h - 0.08,
    fontSize: 20, bold: true, color: C.white,
    fontFace: FONT_HEADER, valign: "middle", margin: 0,
  });
}

function addSlideNum(slide, n) {
  slide.addText(`${n} / 10`, {
    x: 8.8, y: 5.3, w: 1.0, h: 0.25,
    fontSize: 9, color: C.midGrey, align: "right", fontFace: FONT_BODY, margin: 0,
  });
}

function addFooter(slide, text = "Rimac Group — Investment Committee | May 2026 | CONFIDENTIAL") {
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.42, w: 10, h: 0.21, fill: { color: C.black } });
  slide.addText(text, {
    x: 0.3, y: 5.43, w: 9.4, h: 0.19,
    fontSize: 8, color: "AAAAAA", fontFace: FONT_BODY, valign: "middle", margin: 0,
  });
}

function sectionLabel(slide, text, x, y) {
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.06, h: 0.28, fill: { color: C.red } });
  slide.addText(text, {
    x: x + 0.12, y, w: 4, h: 0.28,
    fontSize: 11, bold: true, color: C.red, fontFace: FONT_HEADER, valign: "middle", margin: 0,
  });
}

// ─── SLIDE 1 — TITLE ─────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.red };

  // Decorative geometry
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.35, h: 5.625, fill: { color: C.darkRed } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.35, y: 3.6, w: 9.65, h: 0.06, fill: { color: C.white } });

  s.addText("TACTICAL ASSET ALLOCATION", {
    x: 0.6, y: 1.3, w: 8.8, h: 0.8,
    fontSize: 38, bold: true, color: C.white, fontFace: FONT_HEADER,
    charSpacing: 3, align: "left", margin: 0,
  });
  s.addText("System Methodology & Signal Architecture", {
    x: 0.6, y: 2.2, w: 8.8, h: 0.55,
    fontSize: 22, bold: false, color: "FFD0D8", fontFace: FONT_HEADER, align: "left", margin: 0,
  });
  s.addText("Investment Committee Presentation", {
    x: 0.6, y: 3.8, w: 6, h: 0.35,
    fontSize: 13, color: C.white, fontFace: FONT_BODY, align: "left", margin: 0,
  });
  s.addText("Rimac Group  |  May 2026  |  CONFIDENTIAL", {
    x: 0.6, y: 4.2, w: 6, h: 0.28,
    fontSize: 10, color: "FFB0C0", fontFace: FONT_BODY, align: "left", margin: 0,
  });
}

// ─── SLIDE 2 — SYSTEM OVERVIEW ───────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  addRedHeader(s, "TAA SYSTEM AT A GLANCE");

  // Left column — what it does
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.3, y: 0.65, w: 4.35, h: 4.5,
    fill: { color: C.offWhite }, shadow: makeShadow(),
  });
  s.addText("What the System Does", {
    x: 0.45, y: 0.72, w: 4.0, h: 0.3,
    fontSize: 11, bold: true, color: C.red, fontFace: FONT_HEADER, margin: 0,
  });
  const bullets = [
    "Scores 10 active asset classes across 4 signal pillars (F · M · S · V)",
    "Maps composite z-scores to conviction-based tilts around SAA benchmarks",
    "Enforces no short positions — Solvency II / insurance mandate",
    "Serves 4 real portfolios with TE budgets of 50–125 bps",
    "97 active signals · 170 data series · weekly refresh cycle",
    "Single source of truth: taa_config.xlsx + Dashboard_TAA_Inputs.xlsx",
  ];
  s.addText(bullets.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < bullets.length - 1, paraSpaceAfter: 4 } })), {
    x: 0.45, y: 1.1, w: 4.1, h: 3.8,
    fontSize: 10.5, color: C.black, fontFace: FONT_BODY, valign: "top",
  });

  // Right column — 10 ACs table
  const tableRows = [
    [{ text: "Asset Class", options: { bold: true, color: C.white, fill: { color: C.red } } },
     { text: "Group", options: { bold: true, color: C.white, fill: { color: C.red } } },
     { text: "Hierarchy Role", options: { bold: true, color: C.white, fill: { color: C.red } } }],
    ["Money Market",        "Fixed Income", "Standalone (L1)"],
    ["Short-Term FI (USD)", "Fixed Income", "Standalone (L1)"],
    ["LT US Treasuries",    "Fixed Income", "L2 within LT FI"],
    ["LT US Corporate",     "Fixed Income", "L2 within LT FI"],
    ["LT EM Corp (CEMBI)",  "Fixed Income", "L2 within LT FI"],
    ["US Equity (Broad)",   "Equity",       "L1 Parent"],
    ["US Growth",           "Equity",       "L2 within US Equity"],
    ["US Value",            "Equity",       "L2 within US Equity"],
    ["DM ex-US Equity",     "Equity",       "Standalone (L1)"],
    ["EM Equity",           "Equity",       "Standalone (L1)"],
  ].map((row, i) => {
    if (i === 0) return row;
    const bg = i % 2 === 0 ? C.lightGrey : C.white;
    return row.map(cell => ({ text: String(cell), options: { fill: { color: bg }, color: C.black } }));
  });
  s.addTable(tableRows, {
    x: 4.85, y: 0.65, w: 4.85, h: 4.5,
    fontSize: 9.5, fontFace: FONT_BODY,
    border: { type: "solid", pt: 0.5, color: "CCCCCC" },
    colW: [2.2, 1.2, 1.45],
    rowH: 0.37,
    align: "left",
  });

  addFooter(s);
  addSlideNum(s, 2);
}

// ─── SLIDE 3 — THE FOUR PILLARS ───────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  addRedHeader(s, "THE FOUR SIGNAL PILLARS");

  s.addText("Every asset class is scored across four independent dimensions — each anchored to a distinct economic mechanism", {
    x: 0.3, y: 0.6, w: 9.4, h: 0.32,
    fontSize: 10.5, color: C.darkGrey, fontFace: FONT_BODY, italic: true, margin: 0,
  });

  const pillars = [
    {
      letter: "F", label: "FUNDAMENTALS",
      q: "Does the macro backdrop support this AC?",
      items: [
        "PMI composites (mfg + svcs / 2)",
        "GDP consensus forecasts — blended current/next year",
        "CESI economic surprise indices",
        "Forward EPS revisions (1M · 3M+6M composite)",
        "Real Fed Funds rate & inflation breakevens",
        "Sign logic: growth signals INVERTED for duration ACs",
      ],
    },
    {
      letter: "M", label: "MOMENTUM",
      q: "Is the price trend constructive?",
      items: [
        "Composite price momentum: 12-1M (40%) + 3M (25%) + MA cross (25%) + RSI (10%)",
        "OAS spread momentum — 1M + 3M weighted, inverted (tightening = positive)",
        "Yield momentum (inverted: falling yields = positive)",
        "CDX IG / HY synthetic index momentum",
        "Covers all 10 ACs via total return price indices",
      ],
    },
    {
      letter: "S", label: "SENTIMENT",
      q: "What does positioning & stress signalling tell us?",
      items: [
        "VIX — contrarian for equity; flight-to-quality for FI",
        "MOVE (bond vol) · VSTOXX (European vol)",
        "CBOE Put/Call Ratio (PCR) — contrarian",
        "AAII Bull-Bear — contrarian, inverted",
        "Bloomberg US/EZ FCI — tight FCI = headwind",
        "Modern TED spread (SOFR-based, gated 2018+)",
        "Crisis override: all tilts = 0 if VIX & MOVE both > 80th pctile",
      ],
    },
    {
      letter: "V", label: "VALUATION",
      q: "Is the AC cheap or expensive?",
      items: [
        "PE Score — rolling percentile of forward P/E",
        "Equity Risk Premium = EY% − TIPS 10Y%",
        "Relative PE — log(PE_AC / PE_peer)",
        "OAS level percentile (1260-day window since 1999)",
        "Yield level & term spread percentile",
        "HY/IG OAS ratio",
        "Philosophy: mean-reversion anchor, paired with Momentum",
      ],
    },
  ];

  const boxW = 2.3, boxH = 4.35, startX = 0.2, startY = 0.98, gapX = 0.17;

  pillars.forEach((p, i) => {
    const x = startX + i * (boxW + gapX);
    // Card background
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: startY, w: boxW, h: boxH,
      fill: { color: C.offWhite }, shadow: makeShadow(),
    });
    // Red top accent
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: startY, w: boxW, h: 0.52,
      fill: { color: C.red },
    });
    // Letter
    s.addText(p.letter, {
      x: x + 0.1, y: startY + 0.04, w: 0.4, h: 0.44,
      fontSize: 22, bold: true, color: C.white, fontFace: FONT_HEADER,
      valign: "middle", align: "center", margin: 0,
    });
    // Label
    s.addText(p.label, {
      x: x + 0.52, y: startY + 0.04, w: boxW - 0.6, h: 0.44,
      fontSize: 10, bold: true, color: C.white, fontFace: FONT_HEADER,
      valign: "middle", margin: 0, charSpacing: 1,
    });
    // Question
    s.addText(p.q, {
      x: x + 0.1, y: startY + 0.58, w: boxW - 0.2, h: 0.5,
      fontSize: 9, italic: true, color: C.darkGrey, fontFace: FONT_BODY, margin: 0,
    });
    // Divider
    s.addShape(pres.shapes.RECTANGLE, { x: x + 0.1, y: startY + 1.1, w: boxW - 0.2, h: 0.02, fill: { color: C.lightGrey } });
    // Bullets
    s.addText(p.items.map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < p.items.length - 1, paraSpaceAfter: 3 } })), {
      x: x + 0.08, y: startY + 1.18, w: boxW - 0.16, h: boxH - 1.24,
      fontSize: 8.5, color: C.black, fontFace: FONT_BODY, valign: "top",
    });
  });

  addFooter(s);
  addSlideNum(s, 3);
}

// ─── SLIDE 4 — SIGNAL CONSTRUCTION ───────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  addRedHeader(s, "SIGNAL NORMALISATION FRAMEWORK");

  s.addText("All 97 signals output a z-score clipped to ±3σ before pillar aggregation. Six transform codes standardise raw series into dimensionless z-scores.", {
    x: 0.3, y: 0.6, w: 9.4, h: 0.32,
    fontSize: 10.5, italic: true, color: C.darkGrey, fontFace: FONT_BODY, margin: 0,
  });

  const hdr = { color: C.white, fill: { color: C.red }, bold: true };
  const tbl = [
    [{ text: "Code", options: { ...hdr } }, { text: "Formula", options: { ...hdr } }, { text: "Window", options: { ...hdr } }, { text: "Primary Use", options: { ...hdr } }],
    ["ewma_z",    "EWMA(x, span) → (x − μ) / σ",                   "756 trading days (~3Y)",          "VIX, DXY, FCI, PMI composites, TED spread"],
    ["rolling_z", "Rolling mean & std → z-score",                    "Per series (config-driven)",       "Breakevens, ERP, term spread"],
    ["pctile",    "Percentile rank → (p − 0.5) × 4",                "Per series (e.g. 1260d for OAS)",  "OAS levels, yield levels — mean-reversion signals"],
    ["mom_z",     "pct_change(window) → ewma_z",                     "21d or 63d + 756d EWMA",          "EPS revisions, GDP revisions"],
    ["price_mom", "40%×12-1M + 25%×3M + 25%×MA cross + 10%×RSI",   "252d / 63d / 50d / 14d",          "All equity & FI total return price indices"],
    ["inv_mom_z", "−ewma_z(diff(window)) — falling series = positive", "21d or 63d + 756d EWMA",       "OAS spreads, yields (spread/yield falling = bullish)"],
  ].map((row, i) => {
    if (i === 0) return row;
    const bg = i % 2 === 0 ? C.lightGrey : C.white;
    return row.map(cell => ({ text: String(cell), options: { fill: { color: bg }, color: C.black } }));
  });
  s.addTable(tbl, {
    x: 0.3, y: 0.98, w: 9.4, h: 2.72,
    fontSize: 9.5, fontFace: FONT_BODY,
    border: { type: "solid", pt: 0.5, color: "CCCCCC" },
    colW: [1.3, 3.0, 2.0, 3.1],
    rowH: 0.38,
    align: "left",
  });

  // Quality rules grid
  sectionLabel(s, "KEY DATA QUALITY RULES", 0.3, 3.82);

  const rules = [
    ["Signal floor", "MIN_DATE_FOR_SIGNALS = 2013-02-01. EWMA span=756 trading days (~3Y). Data starts 2010-12-31. Signals only reliable after full warm-up period."],
    ["Outlier protection", "Returns > 5σ set to NaN before momentum computation (prevents flash-crash contamination). All z-scores hard-clipped at ±3.0 before pillar aggregation."],
    ["modern_ted", "Gated at 2018-04-01 (SOFR inception). Before 2018 entirely NaN — gating prevents EWMA distortion. Reliable from ~2020-12."],
    ["Forward-fill limits", "Daily prices: max 5 days (weekends + 1 holiday). Monthly PMI/CESI: max 31 days. AAII weekly: 7 days spread to business days."],
  ];

  rules.forEach(([title, body], i) => {
    const x = 0.3 + (i % 2) * 4.8, y = 4.1 + Math.floor(i / 2) * 0.72;
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 4.55, h: 0.62, fill: { color: C.offWhite }, shadow: makeShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.07, h: 0.62, fill: { color: C.red } });
    s.addText(title, { x: x + 0.14, y: y + 0.04, w: 4.3, h: 0.2, fontSize: 9, bold: true, color: C.red, fontFace: FONT_HEADER, margin: 0 });
    s.addText(body, { x: x + 0.14, y: y + 0.24, w: 4.3, h: 0.34, fontSize: 8, color: C.black, fontFace: FONT_BODY, margin: 0 });
  });

  addFooter(s);
  addSlideNum(s, 4);
}

// ─── SLIDE 5 — FUNDAMENTALS & MOMENTUM BY AC ─────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  addRedHeader(s, "PILLAR DETAIL — FUNDAMENTALS (F) AND MOMENTUM (M)");

  const hdr = { color: C.white, fill: { color: C.red }, bold: true };

  // Fundamentals table
  sectionLabel(s, "F · FUNDAMENTALS  —  Key signals & weights by asset class", 0.2, 0.6);
  const fRows = [
    [{ text: "Asset Class", options: { ...hdr } }, { text: "Key Signals & Weights", options: { ...hdr } }],
    ["Money Market",      "Real Fed Funds Rate (50%) · Breakeven 5Y (25%) · Nominal Fed Rate (25%)"],
    ["Short-Term FI",     "−PMI US (30%) · −CESI US (25%) · −GDP US Blended (25%) · −Breakeven 10Y (20%)   [growth signals INVERTED]"],
    ["LT Treasuries",     "−PMI US (30%) · −CESI US (25%) · −GDP US Blended (25%) · −Breakeven 10Y (20%)   [growth signals INVERTED]"],
    ["LT US Corporate",   "PMI US (30%) · CESI US (25%) · EPS Revision US (30%) · −Breakeven 10Y (15%)"],
    ["LT EM FI (CEMBI)",  "PMI China (30%) · CESI EM (25%) · GDP EM Blended (25%) · EPS Revision EM (20%)"],
    ["US Equity",         "PMI US (35%) · CESI US (25%) · GDP US Blended (20%) · EPS Revision US (15%) · −Breakeven 5Y (5%)"],
    ["US Growth",         "Same as US Equity (signal set identical — pillar weights differ)"],
    ["US Value",          "PMI US (30%) · CESI US (25%) · EPS Revision US (30%) · −Breakeven 10Y (15%)"],
    ["DM ex-US Equity",   "PMI EZ (25%) · CESI EZ (25%) · GDP DM (15%) · EPS EAFE (15%) · PMI Japan (10%) · GDP Japan (5%) · EPS Japan (5%)"],
    ["EM Equity",         "PMI China (30%) · CESI EM (25%) · GDP EM Blended (25%) · EPS Revision EM (20%)"],
  ].map((row, i) => {
    if (i === 0) return row;
    const bg = i % 2 === 0 ? C.lightGrey : C.white;
    return row.map(cell => ({ text: String(cell), options: { fill: { color: bg }, color: C.black } }));
  });
  s.addTable(fRows, {
    x: 0.2, y: 0.9, w: 9.6, h: 3.0,
    fontSize: 8.5, fontFace: FONT_BODY,
    border: { type: "solid", pt: 0.5, color: "CCCCCC" },
    colW: [1.95, 7.65],
    align: "left",
  });

  // Momentum table
  sectionLabel(s, "M · MOMENTUM  —  Key signals & weights by asset class", 0.2, 3.98);
  const mRows = [
    [{ text: "Asset Class", options: { ...hdr } }, { text: "Key Signals & Weights", options: { ...hdr } }],
    ["Money Market",     "ST FI Price Mom (60%) · GT02 Yield Mom (40%)"],
    ["Short-Term FI",    "Bloomberg FI TR Mom (35%) · USD Corp TR Mom (20%) · GT02 Yield Mom (20%) · BBB OAS Mom (15%) · CDX IG Mom (10%)"],
    ["LT Treasuries",    "Bloomberg Gov TR Mom (45%) · GT10 Yield Mom (35%) · BBB OAS Mom (20%) [credit stress = flight to quality for UST]"],
    ["LT US Corporate",  "BBB OAS Mom (30%) · CDX IG Mom (20%) · HY OAS Mom (20%) · FI Price Mom (20%) · GT10 Mom (10%)"],
    ["LT EM FI (CEMBI)", "EM OAS Mom (40%) · MSCI EM Price Mom (35%) · LatAm OAS Mom (25%) [EM equity leads EM credit]"],
    ["US Equity",        "S&P 500 TR Price Mom (55%) · HY OAS Mom (25%) · CDX HY Mom (20%)"],
    ["US Growth",        "S&P 500 Growth TR Price Mom (70%) · CDX HY Mom (30%)"],
    ["US Value",         "S&P 500 Value TR Price Mom (55%) · BBB OAS Mom (25%) · CDX IG Mom (20%)"],
    ["DM ex-US Equity",  "MSCI EAFE Price Mom (65%) · MSCI ACWI Price Mom (35%)"],
    ["EM Equity",        "MSCI EM Price Mom (60%) · EM OAS Mom (40%)"],
  ].map((row, i) => {
    if (i === 0) return row;
    const bg = i % 2 === 0 ? C.lightGrey : C.white;
    return row.map(cell => ({ text: String(cell), options: { fill: { color: bg }, color: C.black } }));
  });
  s.addTable(mRows, {
    x: 0.2, y: 4.27, w: 9.6, h: 0.87,
    fontSize: 8.5, fontFace: FONT_BODY,
    border: { type: "solid", pt: 0.5, color: "CCCCCC" },
    colW: [1.95, 7.65],
    align: "left",
  });

  addFooter(s);
  addSlideNum(s, 5);
}

// ─── SLIDE 6 — SENTIMENT & VALUATION BY AC ───────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  addRedHeader(s, "PILLAR DETAIL — SENTIMENT (S) AND VALUATION (V)");

  const hdr = { color: C.white, fill: { color: C.red }, bold: true };

  sectionLabel(s, "S · SENTIMENT  —  Key signals & weights by asset class", 0.2, 0.6);
  const sRows = [
    [{ text: "Asset Class", options: { ...hdr } }, { text: "Key Signals & Weights", options: { ...hdr } }],
    ["Money Market",     "TED Spread (40%) · HY Stress safe-haven (30%) · VIX flight-to-quality (30%)"],
    ["Short-Term FI",    "VIX flight-to-quality (40%) · TED Spread (35%) · HY Stress safe-haven (25%)"],
    ["LT Treasuries",    "VIX flight-to-quality (35%) · TED Spread (25%) · HY Stress safe-haven (20%) · MOVE bond vol (20%)"],
    ["LT US Corporate",  "VIX inverted/risk-off (30%) · CDX HY price (25%) · HY Stress inverted (25%) · TED inverted (20%)"],
    ["LT EM FI (CEMBI)", "DXY inverted/USD headwind (30%) · EMBI inverted (30%) · EM Stress inverted (20%) · VIX inverted (20%)"],
    ["US Equity",        "VIX contrarian (30%) · AAII Bull-Bear inverted (20%) · PCR contrarian (15%) · FCI inverted (15%) · CDX HY (15%) · TED inverted (5%)"],
    ["US Growth",        "Same as US Equity (VIX 30% · AAII 20% · PCR 15% · FCI 15% · CDX HY 15% · TED 5%)"],
    ["US Value",         "Same as US Equity (VIX 30% · AAII 20% · PCR 15% · FCI 15% · CDX HY 15% · TED 5%)"],
    ["DM ex-US Equity",  "VIX contrarian (30%) · VSTOXX European vol contrarian (25%) · CDX HY (30%) · TED inverted (15%)"],
    ["EM Equity",        "DXY inverted (30%) · EMBI inverted (25%) · VIX contrarian (25%) · EM Stress inverted (20%)"],
  ].map((row, i) => {
    if (i === 0) return row;
    const bg = i % 2 === 0 ? C.lightGrey : C.white;
    return row.map(cell => ({ text: String(cell), options: { fill: { color: bg }, color: C.black } }));
  });
  s.addTable(sRows, {
    x: 0.2, y: 0.9, w: 9.6, h: 3.0,
    fontSize: 8.5, fontFace: FONT_BODY,
    border: { type: "solid", pt: 0.5, color: "CCCCCC" },
    colW: [1.95, 7.65],
    align: "left",
  });

  sectionLabel(s, "V · VALUATION  —  Key signals & weights by asset class", 0.2, 3.98);
  const vRows = [
    [{ text: "Asset Class", options: { ...hdr } }, { text: "Key Signals & Weights", options: { ...hdr } }],
    ["Money Market",     "GT02 Yield Level pctile (50%) · Term Spread (25%) · TIPS 5Y Level (25%)"],
    ["Short-Term FI",    "GT02 Yield Level (35%) · BBB OAS Level pctile (25%) · Term Spread (20%) · TIPS 5Y Level (20%)"],
    ["LT Treasuries",    "GT10 Yield Level pctile (35%) · TIPS 10Y Level (30%) · Term Spread (25%) · BBB OAS Level (10%)"],
    ["LT US Corporate",  "BBB OAS Level pctile (35%) · HY OAS Level pctile (25%) · HY/IG OAS Ratio (20%) · GT10 Level (20%)"],
    ["LT EM FI (CEMBI)", "EM OAS Level pctile (45%) · GT10 Yield Level (30%) · LatAm OAS Level pctile (25%)"],
    ["US Equity",        "PE Score (40%) · ERP = EY − TIPS 10Y% (40%) · Relative PE vs EM (20%)"],
    ["US Growth",        "PE Score Growth Index (35%) · ERP (35%) · Relative PE Growth vs Value (30%)"],
    ["US Value",         "PE Score Value Index (35%) · ERP (35%) · Relative PE Value vs Growth (30%)"],
    ["DM ex-US Equity",  "PE Score DM (35%) · ERP ACWI (35%) · Relative PE DM vs US (30%)"],
    ["EM Equity",        "PE Score EM (30%) · ERP EM = EY − TIPS 10Y (30%) · Relative PE EM vs US (25%) · EM OAS Level (15%)"],
  ].map((row, i) => {
    if (i === 0) return row;
    const bg = i % 2 === 0 ? C.lightGrey : C.white;
    return row.map(cell => ({ text: String(cell), options: { fill: { color: bg }, color: C.black } }));
  });
  s.addTable(vRows, {
    x: 0.2, y: 4.27, w: 9.6, h: 0.87,
    fontSize: 8.5, fontFace: FONT_BODY,
    border: { type: "solid", pt: 0.5, color: "CCCCCC" },
    colW: [1.95, 7.65],
    align: "left",
  });

  addFooter(s);
  addSlideNum(s, 6);
}

// ─── SLIDE 7 — COMPOSITE SCORE PIPELINE ──────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  addRedHeader(s, "STEP-BY-STEP: FROM SIGNALS TO COMPOSITE Z-SCORE");

  // Three pipeline steps
  const steps = [
    {
      n: "01", label: "SIGNAL NORMALISATION",
      formula: "z_i = transform_code(raw_series_i)   →   clip(z_i, −3, +3)",
      desc: "Each of 97 raw series → z-score via its assigned transform code. Outlier returns > 5σ set to NaN before momentum computation. Output: 97 normalised z-score time series.",
    },
    {
      n: "02", label: "PILLAR SCORE (per AC, per pillar)",
      formula: "Z_pillar = [ Σ (w_i × sign_i × z_i) / Σ w_i(present) ]   →   standardise_pillar()",
      desc: "For each AC and each pillar {F, M, S, V}: weighted average of assigned signals (sign from SignalMapping). Missing signals skip gracefully with weight redistribution. Re-standardised post-aggregation to restore unit variance. Output: 4 pillar z-score series per AC (40 total).",
    },
    {
      n: "03", label: "COMPOSITE Z-SCORE",
      formula: "Z_composite = Σ (W_p × Z_p) / Σ W_p(present)   →   clip(−3, +3)",
      desc: "Pillar scores combined with AC-specific pillar weights (see table). Missing pillars skip with weight redistribution. Clipped at ±3σ. Output: one composite z-score series per AC (10 total).",
    },
  ];

  steps.forEach((step, i) => {
    const y = 0.65 + i * 1.3;
    // Step number badge
    s.addShape(pres.shapes.RECTANGLE, { x: 0.2, y, w: 0.52, h: 0.52, fill: { color: C.red } });
    s.addText(step.n, { x: 0.2, y, w: 0.52, h: 0.52, fontSize: 16, bold: true, color: C.white, align: "center", valign: "middle", fontFace: FONT_HEADER, margin: 0 });
    // Step label
    s.addText(step.label, { x: 0.82, y: y + 0.02, w: 6.5, h: 0.25, fontSize: 10, bold: true, color: C.red, fontFace: FONT_HEADER, margin: 0 });
    // Formula box
    s.addShape(pres.shapes.RECTANGLE, { x: 0.82, y: y + 0.28, w: 6.8, h: 0.3, fill: { color: C.black } });
    s.addText(step.formula, { x: 0.9, y: y + 0.28, w: 6.65, h: 0.3, fontSize: 8.5, color: C.white, fontFace: "Consolas", valign: "middle", margin: 0 });
    // Description
    s.addText(step.desc, { x: 0.82, y: y + 0.62, w: 6.8, h: 0.55, fontSize: 9, color: C.darkGrey, fontFace: FONT_BODY, margin: 0 });
    // Arrow
    if (i < 2) s.addShape(pres.shapes.RECTANGLE, { x: 0.37, y: y + 0.56, w: 0.04, h: 0.72, fill: { color: C.red } });
  });

  // Pillar weights table (right side)
  const hdr = { color: C.white, fill: { color: C.red }, bold: true };
  const pwRows = [
    [{ text: "Asset Class", options: { ...hdr } }, { text: "F", options: { ...hdr, align: "center" } }, { text: "M", options: { ...hdr, align: "center" } }, { text: "S", options: { ...hdr, align: "center" } }, { text: "V", options: { ...hdr, align: "center" } }],
    ["Money Market",    "10%","15%","25%","50%"],
    ["Short-Term FI",   "20%","25%","20%","35%"],
    ["LT Treasuries",   "25%","25%","20%","30%"],
    ["LT US Corporate", "20%","30%","20%","30%"],
    ["LT EM FI",        "25%","30%","20%","25%"],
    ["US Equity",       "25%","30%","25%","20%"],
    ["US Growth",       "20%","35%","15%","30%"],
    ["US Value",        "30%","25%","20%","25%"],
    ["DM Equity",       "25%","30%","20%","25%"],
    ["EM Equity",       "25%","30%","20%","25%"],
  ].map((row, i) => {
    if (i === 0) return row;
    const bg = i % 2 === 0 ? C.lightGrey : C.white;
    return row.map((cell, j) => ({ text: String(cell), options: { fill: { color: bg }, color: C.black, align: j > 0 ? "center" : "left" } }));
  });
  sectionLabel(s, "PILLAR WEIGHTS BY ASSET CLASS", 7.75, 0.64);
  s.addTable(pwRows, {
    x: 7.75, y: 0.94, w: 2.0, h: 4.3,
    fontSize: 8.5, fontFace: FONT_BODY,
    border: { type: "solid", pt: 0.5, color: "CCCCCC" },
    colW: [1.0, 0.25, 0.25, 0.25, 0.25],
    align: "center",
  });

  addFooter(s);
  addSlideNum(s, 7);
}

// ─── SLIDE 8 — CONVICTION FRAMEWORK ──────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  addRedHeader(s, "CONVICTION FRAMEWORK: Z-SCORE → TILT SIZING");

  // Formula box at top
  s.addShape(pres.shapes.RECTANGLE, { x: 0.3, y: 0.62, w: 9.4, h: 0.36, fill: { color: C.black } });
  s.addText("Raw Tilt (%)  =  Tilt_Fraction  ×  Conviction_Multiplier  ×  MAX_TILT_PCT[AC]", {
    x: 0.5, y: 0.62, w: 9.0, h: 0.36,
    fontSize: 12, bold: true, color: C.white, fontFace: "Consolas", valign: "middle", margin: 0,
  });

  // Left: conviction map table
  sectionLabel(s, "A · CONVICTION MAP (from Z_composite)", 0.3, 1.1);
  const hdr = { color: C.white, fill: { color: C.red }, bold: true };
  const convRows = [
    [{ text: "Z_composite Range", options: { ...hdr } }, { text: "Conviction Label", options: { ...hdr } }, { text: "Tilt Fraction", options: { ...hdr, align: "center" } }],
    [{ text: "Z ≥ +1.50", options: { fill: { color: "FFDDE2" }, color: C.black } }, { text: "HIGH Overweight", options: { fill: { color: "FFDDE2" }, bold: true, color: C.red } }, { text: "+100%", options: { fill: { color: "FFDDE2" }, color: C.red, bold: true, align: "center" } }],
    [{ text: "+0.75 ≤ Z < +1.50", options: { fill: { color: "FFF0F2" }, color: C.black } }, { text: "MEDIUM Overweight", options: { fill: { color: "FFF0F2" }, bold: false, color: C.darkGrey } }, { text: "+50%", options: { fill: { color: "FFF0F2" }, color: C.darkGrey, align: "center" } }],
    [{ text: "−0.75 ≤ Z < +0.75", options: { fill: { color: C.lightGrey }, color: C.black } }, { text: "NEUTRAL", options: { fill: { color: C.lightGrey }, bold: false, color: C.darkGrey } }, { text: "0%", options: { fill: { color: C.lightGrey }, color: C.darkGrey, align: "center" } }],
    [{ text: "−1.50 ≤ Z < −0.75", options: { fill: { color: "E8E8F8" }, color: C.black } }, { text: "MEDIUM Underweight", options: { fill: { color: "E8E8F8" }, bold: false, color: C.darkGrey } }, { text: "−50%", options: { fill: { color: "E8E8F8" }, color: C.darkGrey, align: "center" } }],
    [{ text: "Z < −1.50", options: { fill: { color: "D0D0EC" }, color: C.black } }, { text: "HIGH Underweight", options: { fill: { color: "D0D0EC" }, bold: true, color: C.darkGrey } }, { text: "−100%", options: { fill: { color: "D0D0EC" }, color: C.darkGrey, bold: true, align: "center" } }],
  ];
  s.addTable(convRows, {
    x: 0.3, y: 1.38, w: 4.5, h: 2.0,
    fontSize: 10, fontFace: FONT_BODY,
    border: { type: "solid", pt: 0.5, color: "CCCCCC" },
    colW: [1.9, 1.7, 0.9],
    rowH: 0.32,
    align: "left",
  });

  // Right: pillar agreement multiplier table
  sectionLabel(s, "B · PILLAR AGREEMENT MULTIPLIER", 5.1, 1.1);
  const agreRows = [
    [{ text: "Pillars Agreeing", options: { ...hdr, align: "center" } }, { text: "Multiplier", options: { ...hdr, align: "center" } }, { text: "Interpretation", options: { ...hdr } }],
    [{ text: "4 / 4", options: { fill: { color: "FFDDE2" }, color: C.red, bold: true, align: "center" } }, { text: "1.00 ×", options: { fill: { color: "FFDDE2" }, color: C.red, bold: true, align: "center" } }, { text: "Full conviction — all pillars aligned", options: { fill: { color: "FFDDE2" }, color: C.black } }],
    [{ text: "3 / 4", options: { fill: { color: "FFF0F2" }, color: C.black, align: "center" } }, { text: "0.80 ×", options: { fill: { color: "FFF0F2" }, color: C.black, align: "center" } }, { text: "High conviction — one dissenting pillar", options: { fill: { color: "FFF0F2" }, color: C.black } }],
    [{ text: "2 / 4", options: { fill: { color: C.lightGrey }, color: C.black, align: "center" } }, { text: "0.50 ×", options: { fill: { color: C.lightGrey }, color: C.black, align: "center" } }, { text: "Moderate conviction — mixed signals", options: { fill: { color: C.lightGrey }, color: C.black } }],
    [{ text: "1 / 4", options: { fill: { color: "EEEEEE" }, color: C.black, align: "center" } }, { text: "0.00 ×", options: { fill: { color: "EEEEEE" }, color: C.black, align: "center" } }, { text: "No tilt — no actionable consensus", options: { fill: { color: "EEEEEE" }, color: C.black } }],
    [{ text: "0 / 4", options: { fill: { color: "EEEEEE" }, color: C.black, align: "center" } }, { text: "0.00 ×", options: { fill: { color: "EEEEEE" }, color: C.black, align: "center" } }, { text: "No tilt — no signal", options: { fill: { color: "EEEEEE" }, color: C.black } }],
  ];
  s.addTable(agreRows, {
    x: 5.1, y: 1.38, w: 4.65, h: 2.0,
    fontSize: 10, fontFace: FONT_BODY,
    border: { type: "solid", pt: 0.5, color: "CCCCCC" },
    colW: [1.1, 1.1, 2.45],
    rowH: 0.32,
    align: "left",
  });

  // Note
  s.addText("Note: A pillar is counted as having signal only when |Z_pillar| > 0.25 (noise filter). Pillars pointing in the majority direction are 'agreeing'.", {
    x: 0.3, y: 3.46, w: 9.4, h: 0.3,
    fontSize: 9, italic: true, color: C.darkGrey, fontFace: FONT_BODY, margin: 0,
  });

  // Max tilts table
  sectionLabel(s, "C · MAXIMUM TILT BUDGET BY ASSET CLASS  (before TE portfolio scaling)", 0.3, 3.82);
  const hdr2 = { color: C.white, fill: { color: C.red }, bold: true, align: "center" };
  const maxTiltRows = [
    ["Money Market", "Short-Term FI", "LT Treasuries", "LT US Corp", "LT EM FI", "US Equity", "US Growth", "US Value", "DM Equity", "EM Equity"].map(t => ({ text: t, options: { ...hdr2 } })),
    ["±2%", "±3%", "±4%", "±3%", "±3%", "±3%", "±3%", "±3%", "±4%", "±4%"].map(t => ({ text: t, options: { fill: { color: C.offWhite }, color: C.black, align: "center", bold: true } })),
  ];
  s.addTable(maxTiltRows, {
    x: 0.3, y: 4.1, w: 9.4, h: 0.72,
    fontSize: 9, fontFace: FONT_BODY,
    border: { type: "solid", pt: 0.5, color: "CCCCCC" },
    colW: Array(10).fill(0.94),
    rowH: 0.36,
    align: "center",
  });

  addFooter(s);
  addSlideNum(s, 8);
}

// ─── SLIDE 9 — ABSOLUTE VS RELATIVE VIEWS ────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  addRedHeader(s, "VIEW CONSTRUCTION: ABSOLUTE + RELATIVE → FINAL TILT");

  // Three side-by-side sections
  const sections = [
    {
      label: "A · ABSOLUTE VIEW  (35% weight)",
      ref: "Wang & Kochard (2012)",
      color: C.red,
      formula: "abs_tilt = Tilt_Frac(Z_composite) × Conv_Mult × MAX_TILT[AC]",
      desc: "Compares each AC to its own historical z-score distribution.\n\"Is this AC cheap/expensive/bullish vs its own history?\"\nCaptures regime-level attractiveness independent of peers.",
    },
    {
      label: "B · RELATIVE VIEW  (65% weight)",
      ref: "Cross-sectional ranking",
      color: "1A3A6A",
      formula: "Z_rel = (Z_comp − μ_cs) / σ_cs     rel_tilt = Tilt_Frac(Z_rel) × Conv_Mult × MAX_TILT[AC]",
      desc: "Ranks each AC vs all other ACs on the same date.\nμ and σ computed cross-sectionally across all 10 ACs.\n\"Which AC do I prefer over others today?\"\nForces discipline — avoids being overweight everything in bull markets.",
    },
    {
      label: "C · FINAL TILT BLEND",
      ref: "Validated blend",
      color: C.black,
      formula: "final_tilt = 0.35 × abs_tilt  +  0.65 × rel_tilt",
      desc: "Absolute view provides regime anchor (35%).\nRelative view enforces ranking discipline (65%).\nBoth views share the same conviction multiplier.\nResult: final_tilt (%) per AC before portfolio constraints.",
    },
  ];

  sections.forEach((sec, i) => {
    const x = 0.2 + i * 3.27, y = 0.63;
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 3.1, h: 3.05, fill: { color: C.offWhite }, shadow: makeShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 3.1, h: 0.38, fill: { color: sec.color } });
    s.addText(sec.label, { x: x + 0.1, y: y + 0.04, w: 2.9, h: 0.3, fontSize: 9.5, bold: true, color: C.white, fontFace: FONT_HEADER, valign: "middle", margin: 0 });
    // Formula
    s.addShape(pres.shapes.RECTANGLE, { x: x + 0.1, y: y + 0.46, w: 2.9, h: 0.38, fill: { color: C.black } });
    s.addText(sec.formula, { x: x + 0.12, y: y + 0.46, w: 2.87, h: 0.38, fontSize: 7, color: C.white, fontFace: "Consolas", valign: "middle", margin: 0 });
    s.addText(sec.ref, { x: x + 0.1, y: y + 0.9, w: 2.9, h: 0.2, fontSize: 8, italic: true, color: C.midGrey, fontFace: FONT_BODY, margin: 0 });
    s.addText(sec.desc, { x: x + 0.1, y: y + 1.12, w: 2.9, h: 1.85, fontSize: 9, color: C.black, fontFace: FONT_BODY, valign: "top", margin: 0 });
  });

  // Portfolio constraints
  sectionLabel(s, "PORTFOLIO CONSTRAINTS  (applied after blending, in order)", 0.2, 3.76);
  const constraints = [
    ["1. ZERO-SUM", "Σ tilts = 0 across all ACs (no net leverage). Excess redistributed proportionally among positive-SAA ACs. Money Market absorbs any residual."],
    ["2. NO SHORTS", "portfolio_weight = SAA_weight + tilt ≥ 0% at all times. Weight hard-clipped at 0%. Solvency II / insurance mandate — no short positions ever."],
    ["3. TE SCALING", "Each portfolio scales tilts by (TE_budget / 100 bps): IGCON 0.5× · IGMOD 0.75× · IGDIN 1.0× · IGEQUS 1.25×"],
    ["4. CRISIS OVERRIDE", "VIX > 80th pctile AND MOVE > 80th pctile simultaneously → all tilts forced to 0. Override lifts when both return below 70th pctile."],
  ];

  constraints.forEach(([title, body], i) => {
    const x = 0.2 + (i % 2) * 4.88, y = 4.04 + Math.floor(i / 2) * 0.72;
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 4.62, h: 0.62, fill: { color: C.offWhite }, shadow: makeShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.07, h: 0.62, fill: { color: C.red } });
    s.addText(title, { x: x + 0.14, y: y + 0.04, w: 4.38, h: 0.2, fontSize: 9, bold: true, color: C.red, fontFace: FONT_HEADER, margin: 0 });
    s.addText(body, { x: x + 0.14, y: y + 0.25, w: 4.38, h: 0.34, fontSize: 8.5, color: C.black, fontFace: FONT_BODY, margin: 0 });
  });

  addFooter(s);
  addSlideNum(s, 9);
}

// ─── SLIDE 10 — HIERARCHICAL VIEWS & PORTFOLIOS ───────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  addRedHeader(s, "HIERARCHICAL STRUCTURE AND PORTFOLIO IMPLEMENTATION");

  // L1/L2 explanation
  sectionLabel(s, "HIERARCHICAL VIEWS — Two layers of decision-making", 0.2, 0.62);

  const hierCols = [
    {
      label: "L1 · ALLOCATION",
      color: C.red,
      items: [
        "Operates across all 10 ACs — decides WHERE to allocate",
        "US Equity, DM, EM, MM, STFI: own composite z IS the L1 view",
        "LT FI bucket uses SYNTHETIC aggregate z-score:",
        "   Z_lt_fi = 0.40 × Z_lt_tsy + 0.35 × Z_lt_corp + 0.25 × Z_lt_em",
        "L1 tilts determine the size of the FI/EQ allocation shift",
      ],
    },
    {
      label: "L2 · ROTATION (within bucket)",
      color: C.black,
      items: [
        "Within-bucket zero-sum rotation — decides WHICH child to prefer",
        "Within LT FI: Z_L2 = Z_child − Z_lt_fi_agg",
        "Within US Equity: Z_L2 = Z_child − Z_us_equity",
        "L2 tilts are independent of L1 sizing",
        "Growth vs Value rotation driven entirely by L2 z-scores",
      ],
    },
  ];
  hierCols.forEach((col, i) => {
    const x = 0.2 + i * 4.85, y = 0.9;
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 4.6, h: 1.7, fill: { color: C.offWhite }, shadow: makeShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 4.6, h: 0.34, fill: { color: col.color } });
    s.addText(col.label, { x: x + 0.1, y: y + 0.04, w: 4.4, h: 0.26, fontSize: 10, bold: true, color: C.white, fontFace: FONT_HEADER, valign: "middle", margin: 0 });
    s.addText(col.items.map((t, j) => ({ text: t, options: { bullet: j < 2 || j > 3, breakLine: j < col.items.length - 1, paraSpaceAfter: 2 } })), {
      x: x + 0.1, y: y + 0.38, w: 4.4, h: 1.28,
      fontSize: 8.5, color: C.black, fontFace: FONT_BODY, valign: "top",
    });
  });

  // Portfolios table
  sectionLabel(s, "FOUR REAL PORTFOLIOS — Rimac Group Insurance Mandates", 0.2, 2.72);
  const hdr = { color: C.white, fill: { color: C.red }, bold: true };
  const portRows = [
    [
      { text: "Portfolio", options: { ...hdr } },
      { text: "Label", options: { ...hdr } },
      { text: "TE Budget", options: { ...hdr, align: "center" } },
      { text: "Risk Profile", options: { ...hdr, align: "center" } },
      { text: "SAA: MM / STFI / LT EM / US Eq / DM / EM", options: { ...hdr, align: "center" } },
      { text: "Tilt Scale", options: { ...hdr, align: "center" } },
    ],
    [
      { text: "IGCON_USD",  options: { fill: { color: C.white }, color: C.black, bold: true } },
      { text: "IG Conservador",  options: { fill: { color: C.white }, color: C.black } },
      { text: "50 bps", options: { fill: { color: C.white }, color: C.black, align: "center" } },
      { text: "Conservative",   options: { fill: { color: C.white }, color: C.black, align: "center" } },
      { text: "15% / 25% / 30% / 19.2% / 7.5% / 3.3%", options: { fill: { color: C.white }, color: C.black, align: "center" } },
      { text: "0.5×", options: { fill: { color: C.white }, color: C.black, align: "center" } },
    ],
    [
      { text: "IGMOD_USD",  options: { fill: { color: C.lightGrey }, color: C.black, bold: true } },
      { text: "IG Moderado",     options: { fill: { color: C.lightGrey }, color: C.black } },
      { text: "75 bps", options: { fill: { color: C.lightGrey }, color: C.black, align: "center" } },
      { text: "Moderate",        options: { fill: { color: C.lightGrey }, color: C.black, align: "center" } },
      { text: "10% / 15% / 25% / 32.0% / 12.5% / 5.5%", options: { fill: { color: C.lightGrey }, color: C.black, align: "center" } },
      { text: "0.75×", options: { fill: { color: C.lightGrey }, color: C.black, align: "center" } },
    ],
    [
      { text: "IGDIN_USD",  options: { fill: { color: C.white }, color: C.black, bold: true } },
      { text: "IG Dinámico",     options: { fill: { color: C.white }, color: C.black } },
      { text: "100 bps", options: { fill: { color: C.white }, color: C.black, align: "center" } },
      { text: "Aggressive",      options: { fill: { color: C.white }, color: C.black, align: "center" } },
      { text: "5% / 10% / 15% / 44.8% / 17.5% / 7.7%", options: { fill: { color: C.white }, color: C.black, align: "center" } },
      { text: "1.0×", options: { fill: { color: C.white }, color: C.black, align: "center" } },
    ],
    [
      { text: "IGEQUS_USD", options: { fill: { color: C.lightGrey }, color: C.black, bold: true } },
      { text: "IG Acciones EE.UU.", options: { fill: { color: C.lightGrey }, color: C.black } },
      { text: "125 bps", options: { fill: { color: C.lightGrey }, color: C.black, align: "center" } },
      { text: "Aggressive",      options: { fill: { color: C.lightGrey }, color: C.black, align: "center" } },
      { text: "5% / 0% / 0% / 95.0% / 0% / 0%", options: { fill: { color: C.lightGrey }, color: C.black, align: "center" } },
      { text: "1.25×", options: { fill: { color: C.lightGrey }, color: C.black, align: "center" } },
    ],
  ];
  s.addTable(portRows, {
    x: 0.2, y: 3.0, w: 9.6, h: 1.62,
    fontSize: 9.5, fontFace: FONT_BODY,
    border: { type: "solid", pt: 0.5, color: "CCCCCC" },
    colW: [1.4, 1.7, 0.85, 1.2, 2.95, 0.7],
    rowH: 0.32,
    align: "left",
  });

  s.addText("All four portfolios have force_zero_sum = True — no leverage, no short positions at any time.", {
    x: 0.3, y: 4.68, w: 9.2, h: 0.22,
    fontSize: 8.5, italic: true, bold: true, color: C.darkGrey, fontFace: FONT_BODY, margin: 0,
  });

  // Academic references
  s.addShape(pres.shapes.RECTANGLE, { x: 0.2, y: 4.9, w: 9.6, h: 0.28, fill: { color: C.lightGrey } });
  s.addText(
    "Academic foundations:  Brinson/Hood/Beebower (1986) — allocation explains 80–90% of variance  ·  Wang & Kochard (2012) — 35/65 abs/rel blend  ·  Asness/Moskowitz/Pedersen (2013) — value + momentum everywhere  ·  Maillard/Roncalli/Teïletche (2010) — hierarchical risk parity  ·  Chan/Jegadeesh/Lakonishok (1996) — earnings revision momentum at 3–6M",
    { x: 0.3, y: 4.91, w: 9.4, h: 0.26, fontSize: 7, color: C.darkGrey, fontFace: FONT_BODY, italic: true, valign: "middle", margin: 0 }
  );

  addFooter(s);
  addSlideNum(s, 10);
}

// ─── WRITE FILE ───────────────────────────────────────────────────────────────
pres.writeFile({ fileName: "docs/TAA_IC_Presentation.pptx" })
  .then(() => console.log("✅  docs/TAA_IC_Presentation.pptx written successfully"))
  .catch(err => { console.error("❌  Error:", err); process.exit(1); });
