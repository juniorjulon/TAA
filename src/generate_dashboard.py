"""
src/generate_dashboard.py
=========================
Generates dashboard.html with all data embedded inline.
Run from project root:  python src/generate_dashboard.py
"""
import os, sys, json, textwrap
import pandas as pd
import numpy as np

_SRC  = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SRC)
sys.path.insert(0, _SRC)

LATEST_RUN = "RUN_20260417_1016"
SC_PATH    = os.path.join(_ROOT, "results", LATEST_RUN, "taa_scorecard.csv")
COMP_PATH  = os.path.join(_ROOT, "results", LATEST_RUN, "taa_composite_series.csv")
CB_PATH    = os.path.join(_ROOT, "results", "chartbook_data.json")
OUT_PATH   = os.path.join(_ROOT, "dashboard.html")


# ── helpers ──────────────────────────────────────────────────────────────────

def _sample(obj, n=252):
    if isinstance(obj, dict):
        if "dates" in obj:
            d = obj.get("dates", [])[-n:]
            r = {"dates": d}
            for k, v in obj.items():
                if k != "dates":
                    r[k] = v[-n:] if isinstance(v, list) else v
            return r
        return {k: _sample(v, n) for k, v in obj.items()}
    return obj


def load_data():
    sc   = pd.read_csv(SC_PATH, index_col=0)
    comp = pd.read_csv(COMP_PATH, index_col=0, parse_dates=True)
    comp = comp.tail(252).dropna(how="all")

    with open(CB_PATH, "r") as f:
        cb = json.load(f)
    cb_s = _sample(cb, 252)

    AC_COLS = ["money_market","short_term_fi","lt_treasuries","lt_us_corp","lt_em_fi",
               "us_equity","us_growth","us_value","dm_equity","em_equity","em_xchina","china_equity"]

    sc_rows = []
    for ac in AC_COLS:
        if ac in sc.index:
            r = sc.loc[ac].to_dict()
            r["ac"] = ac
            sc_rows.append(r)

    comp_js = {"dates": [d.strftime("%Y-%m-%d") for d in comp.index]}
    for col in AC_COLS:
        if col in comp.columns:
            comp_js[col] = [round(v,4) if not pd.isna(v) else None for v in comp[col]]

    return sc_rows, comp_js, cb_s


def js_const(name, val):
    return f"const {name} = {json.dumps(val, allow_nan=False)};\n"


# ── HTML builder ─────────────────────────────────────────────────────────────

def build_html(sc_rows, comp_js, cb):
    sc_js   = js_const("SCORECARD", sc_rows)
    comp_js_str = js_const("COMPOSITES", comp_js)
    cb_js   = js_const("CB", cb)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TAA Dashboard · Apr 2026</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
{CSS}
</style>
</head>
<body>
<div class="layout">
{SIDEBAR_HTML}
<main class="main" id="main">
{SECTION_SIGNALS}
{SECTION_METHODOLOGY}
{SECTION_CHARTBOOK}
</main>
</div>
<script>
{sc_js}
{comp_js_str}
{cb_js}
{JS}
</script>
</body>
</html>"""


# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0B1220;--bg2:#111C2E;--bg3:#162236;--bg4:#1E2E47;
  --text:#E2E8F0;--text2:#8B9CC0;--text3:#556070;
  --brand:#C41230;--blue:#3A7BD5;--teal:#14B8A6;--amber:#F59E0B;
  --purple:#A855F7;--green:#22C55E;--red:#E8354A;--orange:#F97316;
  --pos:#22C55E;--neg:#E8354A;--neut:#556070;
  --pf:#14B8A6;--pm:#F59E0B;--ps:#A855F7;--pv:#3A7BD5;
  --border:#1E2E47;--radius:8px;--sidebar:220px
}
body{font-family:'Space Grotesk',sans-serif;background:var(--bg);color:var(--text);font-size:13px;line-height:1.4;overflow:hidden}
.layout{display:flex;height:100vh}

/* Sidebar */
.sidebar{width:var(--sidebar);background:var(--bg2);border-right:1px solid var(--border);
  display:flex;flex-direction:column;flex-shrink:0;overflow-y:auto}
.sidebar-header{padding:18px 16px 14px;border-bottom:1px solid var(--border)}
.sidebar-logo{font-size:14px;font-weight:700;color:var(--text);letter-spacing:-.3px}
.sidebar-logo span{color:var(--brand)}
.sidebar-sub{font-size:10px;color:var(--text3);margin-top:3px;font-family:'JetBrains Mono',monospace}
.sidebar-section{padding:14px 12px 6px;font-size:9px;letter-spacing:.8px;text-transform:uppercase;
  color:var(--text3);font-weight:600}
.sidebar a{display:block;padding:7px 16px;color:var(--text2);text-decoration:none;font-size:12px;
  border-left:2px solid transparent;transition:.15s}
.sidebar a:hover{color:var(--text);background:var(--bg3)}
.sidebar a.active{color:var(--text);background:var(--bg3);border-left-color:var(--brand)}
.sidebar-footer{margin-top:auto;padding:12px 16px;border-top:1px solid var(--border);
  font-size:10px;color:var(--text3);font-family:'JetBrains Mono',monospace}

/* Main */
.main{flex:1;overflow-y:auto;background:var(--bg)}
.section{display:none;min-height:100vh}
.section.active{display:block}
.page-header{padding:20px 24px 14px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:12px}
.page-title{font-size:16px;font-weight:700;letter-spacing:-.3px}
.page-title span{color:var(--brand)}
.page-date{font-size:10px;color:var(--text3);font-family:'JetBrains Mono',monospace;margin-left:auto}
.content{padding:20px 24px}

/* Cards */
.card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:14px}
.card-title{font-size:11px;font-weight:600;color:var(--text2);text-transform:uppercase;
  letter-spacing:.6px;margin-bottom:10px}
.card-accent-f{border-top:2px solid var(--pf)}
.card-accent-m{border-top:2px solid var(--pm)}
.card-accent-s{border-top:2px solid var(--ps)}
.card-accent-v{border-top:2px solid var(--pv)}
.card-accent-b{border-top:2px solid var(--brand)}

/* KPI row */
.kpi-row{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}
.kpi{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);
  padding:14px 16px}
.kpi-label{font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.6px;margin-bottom:6px}
.kpi-value{font-size:22px;font-weight:700;font-family:'JetBrains Mono',monospace;line-height:1}
.kpi-sub{font-size:10px;color:var(--text3);margin-top:4px}
.kpi-pos{color:var(--pos)}.kpi-neg{color:var(--neg)}.kpi-neut{color:var(--text2)}

/* Grids */
.g2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.g3{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.gap{gap:16px}
.mb12{margin-bottom:12px}.mb16{margin-bottom:16px}.mb20{margin-bottom:20px}

/* Section group headers */
.group-header{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;
  color:var(--text3);padding:16px 0 8px;display:flex;align-items:center;gap:8px}
.group-header::after{content:'';flex:1;height:1px;background:var(--border)}

/* Chart card */
.chart-card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);
  padding:12px}
.chart-card-header{display:flex;align-items:flex-start;justify-content:space-between;
  margin-bottom:8px;gap:8px}
.chart-card-label{font-size:10px;font-weight:600;color:var(--text2);text-transform:uppercase;
  letter-spacing:.5px;line-height:1.3}
.chart-card-name{font-size:12px;font-weight:500;color:var(--text);margin-top:2px}
.tf-btns{display:flex;gap:3px;flex-shrink:0}
.tf-btn{font-size:9px;font-weight:600;padding:2px 6px;border-radius:3px;cursor:pointer;
  background:var(--bg4);border:1px solid var(--border);color:var(--text3);font-family:'JetBrains Mono',monospace}
.tf-btn.active{background:var(--brand);border-color:var(--brand);color:#fff}
.chart-wrap{position:relative}
.chart-footer{display:flex;gap:12px;margin-top:6px;font-size:10px;color:var(--text3);
  font-family:'JetBrains Mono',monospace}
.chart-footer .val{color:var(--text);font-weight:500}

/* Metric toggles (momentum) */
.metric-toggles{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px}
.mtog{font-size:9px;padding:2px 7px;border-radius:3px;cursor:pointer;
  border:1px solid var(--border);background:var(--bg4);color:var(--text3);font-family:'JetBrains Mono',monospace}
.mtog.active{color:#fff}
.mtog[data-m="ret_1m"].active{background:#3A7BD5;border-color:#3A7BD5}
.mtog[data-m="ret_3m"].active{background:#14B8A6;border-color:#14B8A6}
.mtog[data-m="ret_6m"].active{background:#F59E0B;border-color:#F59E0B}
.mtog[data-m="ret_12_1m"].active{background:#A855F7;border-color:#A855F7}
.mtog[data-m="ma_dist"].active{background:#F97316;border-color:#F97316}
.mtog[data-m="rsi"].active{background:#22C55E;border-color:#22C55E}

/* Scorecard table */
.sc-table{width:100%;border-collapse:collapse;font-size:12px}
.sc-table th{font-size:9px;text-transform:uppercase;letter-spacing:.7px;color:var(--text3);
  padding:6px 10px;text-align:left;border-bottom:1px solid var(--border);white-space:nowrap}
.sc-table td{padding:7px 10px;border-bottom:1px solid rgba(255,255,255,.04);vertical-align:middle}
.sc-table tr:hover td{background:rgba(255,255,255,.02)}
.sc-table .group-row td{background:var(--bg3);font-size:10px;font-weight:600;
  text-transform:uppercase;letter-spacing:.6px;color:var(--text3);padding:5px 10px}
.zchip{display:inline-block;padding:2px 6px;border-radius:4px;font-family:'JetBrains Mono',monospace;
  font-size:11px;font-weight:500;min-width:44px;text-align:center}
.conv{display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600;
  letter-spacing:.3px;white-space:nowrap}
.conv-how{background:rgba(34,197,94,.15);color:#22C55E}
.conv-how2{background:rgba(34,197,94,.25);color:#4ADE80}
.conv-neu{background:rgba(85,96,112,.2);color:var(--text3)}
.conv-luw{background:rgba(232,53,74,.15);color:#F87171}
.conv-huw{background:rgba(232,53,74,.25);color:#EF4444}
.tilt-bar-wrap{display:flex;align-items:center;gap:6px;min-width:100px}
.tilt-bar-bg{flex:1;height:6px;background:var(--bg4);border-radius:3px;overflow:hidden;position:relative}
.tilt-bar-fill{height:100%;border-radius:3px;position:absolute;top:0}
.tilt-val{font-family:'JetBrains Mono',monospace;font-size:11px;width:36px;text-align:right}

/* Heatmap table */
.heat-table{width:100%;border-collapse:collapse;font-size:11px}
.heat-table th{font-size:9px;text-transform:uppercase;letter-spacing:.7px;color:var(--text3);
  padding:6px 10px;text-align:center;border-bottom:1px solid var(--border)}
.heat-table th:first-child{text-align:left}
.heat-table td{padding:6px 10px;border-bottom:1px solid rgba(255,255,255,.03);
  font-family:'JetBrains Mono',monospace;text-align:center}
.heat-table td:first-child{text-align:left;font-family:'Space Grotesk',sans-serif;font-size:12px}
.heat-table .group-row td{background:var(--bg3);font-size:9px;font-weight:600;
  text-transform:uppercase;color:var(--text3);padding:4px 10px}

/* Signal matrix table */
.sig-table{width:100%;border-collapse:collapse;font-size:11px}
.sig-table th{font-size:9px;text-transform:uppercase;letter-spacing:.6px;color:var(--text3);
  padding:6px 8px;white-space:nowrap;border-bottom:1px solid var(--border)}
.sig-table td{padding:5px 8px;border-bottom:1px solid rgba(255,255,255,.03);vertical-align:middle}
.sig-table .row-head{font-size:11px;color:var(--text);min-width:160px}
.sig-table .row-sub{font-size:9px;color:var(--text3)}
.sign{display:inline-block;padding:1px 5px;border-radius:3px;font-size:10px;font-weight:700;
  font-family:'JetBrains Mono',monospace;min-width:20px;text-align:center}
.s-pp{background:rgba(34,197,94,.2);color:#4ADE80}
.s-p {background:rgba(34,197,94,.12);color:#22C55E}
.s-n {background:rgba(232,53,74,.12);color:#F87171}
.s-nn{background:rgba(232,53,74,.2);color:#EF4444}
.s-c {background:rgba(168,85,247,.15);color:#C084FC}
.s-na{background:rgba(85,96,112,.1);color:var(--text3)}
.chip{display:inline-block;padding:2px 6px;border-radius:3px;font-size:9px;font-weight:500}
.chip-teal{background:rgba(20,184,166,.15);color:#2DD4BF}
.chip-blue{background:rgba(58,123,213,.15);color:#60A5FA}
.chip-amber{background:rgba(245,158,11,.15);color:#FCD34D}
.chip-purple{background:rgba(168,85,247,.15);color:#C084FC}
.chip-red{background:rgba(232,53,74,.15);color:#F87171}
.chip-gray{background:rgba(85,96,112,.2);color:var(--text3)}

/* Pillar bar */
.pillar-bar{display:flex;align-items:center;gap:6px;margin-bottom:6px}
.pillar-bar-label{font-size:10px;color:var(--text3);width:20px;text-align:right}
.pillar-bar-track{flex:1;height:6px;background:var(--bg4);border-radius:3px;overflow:hidden;position:relative}
.pillar-bar-fill{height:100%;border-radius:3px;position:absolute;top:0}
.pillar-bar-val{font-size:10px;font-family:'JetBrains Mono',monospace;width:32px}

/* Relative PE selector */
.rel-pe-controls{display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap}
.rel-pe-controls select{background:var(--bg3);border:1px solid var(--border);color:var(--text);
  padding:4px 8px;border-radius:4px;font-size:11px;font-family:'Space Grotesk',sans-serif}
.rel-pe-controls label{font-size:10px;color:var(--text3)}
.rel-pe-zscore{font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:600;margin-left:auto}

/* Scatter label */
canvas{display:block}
</style>"""


SIDEBAR_HTML = """
<nav class="sidebar">
  <div class="sidebar-header">
    <div class="sidebar-logo">TAA <span>Dashboard</span></div>
    <div class="sidebar-sub">Apr 2026 · 12 AC · 4 Pillars</div>
  </div>
  <div class="sidebar-section">1. Chartbook</div>
  <a href="#" onclick="nav('cb-fund')" id="nav-cb-fund">I. Fundamentals</a>
  <a href="#" onclick="nav('cb-mom')"  id="nav-cb-mom">II. Momentum</a>
  <a href="#" onclick="nav('cb-sent')" id="nav-cb-sent">III. Sentiment</a>
  <a href="#" onclick="nav('cb-val')"  id="nav-cb-val">IV. Valuation</a>
  <div class="sidebar-section">2. TAA Methodology</div>
  <a href="#" onclick="nav('meth-matrix')" id="nav-meth-matrix">Full Signal Matrix</a>
  <a href="#" onclick="nav('meth-fi')"     id="nav-meth-fi">Fixed Income</a>
  <a href="#" onclick="nav('meth-eq')"     id="nav-meth-eq">Equity</a>
  <div class="sidebar-section">3. TAA Signals</div>
  <a href="#" onclick="nav('sig-score')"  id="nav-sig-score" class="active">Composite Scorecard</a>
  <a href="#" onclick="nav('sig-heat')"   id="nav-sig-heat">Signal Heatmap</a>
  <div class="sidebar-footer">v1.0 · Rimac Group<br>Signal ref: TAA_Signal_Reference.html</div>
</nav>"""


# ─────────────────────────────────────── SECTION 3: SIGNALS ──────────────────

SECTION_SIGNALS = """
<!-- ========== SECTION: Composite Scorecard ========== -->
<section class="section active" id="sec-sig-score">
<div class="page-header">
  <div class="page-title">TAA <span>Signals</span> · Composite Scorecard</div>
  <div class="page-date" id="sc-date">Apr 2026</div>
</div>
<div class="content">
  <div class="kpi-row" id="kpi-row"></div>
  <div class="card mb16">
    <div class="card-title">Composite Scorecard — All Asset Classes</div>
    <table class="sc-table" id="sc-table"></table>
  </div>
  <div class="g2 mb16">
    <div class="card">
      <div class="card-title">Pillar Z-Scores by Asset Class</div>
      <div class="chart-wrap"><canvas id="ch-pillar-bars" height="220"></canvas></div>
    </div>
    <div class="card">
      <div class="card-title">Composite Z-Score Ranking</div>
      <div class="chart-wrap"><canvas id="ch-comp-rank" height="220"></canvas></div>
    </div>
  </div>
  <div class="g2">
    <div class="card">
      <div class="card-title">FI Composite Z-Scores — 1Y History</div>
      <div class="chart-wrap"><canvas id="ch-fi-ts" height="180"></canvas></div>
    </div>
    <div class="card">
      <div class="card-title">Equity Composite Z-Scores — 1Y History</div>
      <div class="chart-wrap"><canvas id="ch-eq-ts" height="180"></canvas></div>
    </div>
  </div>
</div>
</section>

<!-- ========== SECTION: Signal Heatmap ========== -->
<section class="section" id="sec-sig-heat">
<div class="page-header">
  <div class="page-title">TAA <span>Signals</span> · Signal Heatmap</div>
  <div class="page-date">Apr 2026</div>
</div>
<div class="content">
  <div class="card mb16">
    <div class="card-title">Pillar Z-Score Heatmap — All Asset Classes × Pillars</div>
    <table class="heat-table" id="heat-table"></table>
  </div>
  <div class="g2 mb16">
    <div class="card">
      <div class="card-title">Fundamentals vs Valuation</div>
      <div class="chart-wrap"><canvas id="ch-sc-fv" height="200"></canvas></div>
    </div>
    <div class="card">
      <div class="card-title">Momentum vs Sentiment</div>
      <div class="chart-wrap"><canvas id="ch-sc-ms" height="200"></canvas></div>
    </div>
  </div>
</div>
</section>"""


# ─────────────────────────────────────── SECTION 2: METHODOLOGY ──────────────

SECTION_METHODOLOGY = """
<!-- ========== SECTION: Full Signal Matrix ========== -->
<section class="section" id="sec-meth-matrix">
<div class="page-header">
  <div class="page-title">TAA <span>Methodology</span> · Full Signal Matrix</div>
</div>
<div class="content">
  <div class="card mb16">
    <div class="card-title">Signal Universe × Asset Class Coverage</div>
    <table class="sig-table" id="sig-matrix-table"></table>
  </div>
</div>
</section>

<!-- ========== SECTION: FI Signals ========== -->
<section class="section" id="sec-meth-fi">
<div class="page-header">
  <div class="page-title">TAA <span>Methodology</span> · Fixed Income Signals</div>
</div>
<div class="content">
  <div id="fi-pillar-cards"></div>
</div>
</section>

<!-- ========== SECTION: EQ Signals ========== -->
<section class="section" id="sec-meth-eq">
<div class="page-header">
  <div class="page-title">TAA <span>Methodology</span> · Equity Signals</div>
</div>
<div class="content">
  <div id="eq-pillar-cards"></div>
</div>
</section>"""


# ─────────────────────────────────────── SECTION 1: CHARTBOOK ────────────────

SECTION_CHARTBOOK = """
<!-- ========== CHARTBOOK: Fundamentals ========== -->
<section class="section" id="sec-cb-fund">
<div class="page-header">
  <div class="page-title">Chartbook · <span>I. Fundamentals</span></div>
</div>
<div class="content" id="cb-fund-content"></div>
</section>

<!-- ========== CHARTBOOK: Momentum ========== -->
<section class="section" id="sec-cb-mom">
<div class="page-header">
  <div class="page-title">Chartbook · <span>II. Momentum</span></div>
</div>
<div class="content" id="cb-mom-content"></div>
</section>

<!-- ========== CHARTBOOK: Sentiment ========== -->
<section class="section" id="sec-cb-sent">
<div class="page-header">
  <div class="page-title">Chartbook · <span>III. Sentiment</span></div>
</div>
<div class="content" id="cb-sent-content"></div>
</section>

<!-- ========== CHARTBOOK: Valuation ========== -->
<section class="section" id="sec-cb-val">
<div class="page-header">
  <div class="page-title">Chartbook · <span>IV. Valuation</span></div>
</div>
<div class="content" id="cb-val-content"></div>
</section>"""


# ─────────────────────────────────────── JAVASCRIPT ──────────────────────────

JS = r"""
// ── Navigation ──────────────────────────────────────────────────────────────
const SECTION_MAP = {
  'cb-fund':'sec-cb-fund','cb-mom':'sec-cb-mom','cb-sent':'sec-cb-sent','cb-val':'sec-cb-val',
  'meth-matrix':'sec-meth-matrix','meth-fi':'sec-meth-fi','meth-eq':'sec-meth-eq',
  'sig-score':'sec-sig-score','sig-heat':'sec-sig-heat'
};
let currentNav = 'sig-score';
function nav(id){
  document.querySelectorAll('.sidebar a').forEach(a=>a.classList.remove('active'));
  document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
  document.getElementById('nav-'+id)?.classList.add('active');
  document.getElementById(SECTION_MAP[id])?.classList.add('active');
  currentNav = id;
  if(id==='sig-score' && !scorecardBuilt) buildScorecard();
  if(id==='sig-heat'  && !heatmapBuilt)  buildHeatmap();
  if(id.startsWith('meth') && !methBuilt) buildMethodology();
  if(id==='cb-fund'   && !cbFundBuilt)   buildCBFund();
  if(id==='cb-mom'    && !cbMomBuilt)    buildCBMom();
  if(id==='cb-sent'   && !cbSentBuilt)   buildCBSent();
  if(id==='cb-val'    && !cbValBuilt)    buildCBVal();
  return false;
}

// ── Colour helpers ───────────────────────────────────────────────────────────
function zColor(z,alpha=1){
  if(z===null||z===undefined||isNaN(z)) return `rgba(85,96,112,${alpha})`;
  const a=Math.min(Math.abs(z)/2,1);
  return z>0 ? `rgba(34,197,94,${a*alpha})` : `rgba(232,53,74,${a*alpha})`;
}
function zText(z){
  if(z===null||z===undefined||isNaN(z)) return '#556070';
  return z>0.25?'#22C55E':z<-0.25?'#E8354A':'#8B9CC0';
}
function zFmt(v){return v===null||v===undefined?'—':(v>=0?'+':'')+v.toFixed(2)}
function pctFmt(v){return v===null?'—':(v>=0?'+':'')+v.toFixed(2)+'%'}

// ── Chart.js defaults ────────────────────────────────────────────────────────
Chart.defaults.color = '#8B9CC0';
Chart.defaults.borderColor = '#1E2E47';
Chart.defaults.font.family = "'Space Grotesk', sans-serif";
Chart.defaults.font.size = 11;

function makeLineChart(id, labels, datasets, opts={}){
  const el = document.getElementById(id);
  if(!el) return null;
  return new Chart(el, {
    type:'line',
    data:{labels, datasets},
    options:{
      responsive:true, maintainAspectRatio:false,
      animation:{duration:200},
      plugins:{legend:{display:opts.legend??false,
        labels:{boxWidth:10,padding:10,font:{size:10}}},
        tooltip:{mode:'index',intersect:false,
          callbacks:{label:ctx=>`${ctx.dataset.label}: ${ctx.parsed.y?.toFixed(2)}`}}},
      scales:{
        x:{grid:{color:'rgba(30,46,71,.6)'},ticks:{maxTicksLimit:6,font:{size:9}}},
        y:{grid:{color:'rgba(30,46,71,.6)'},ticks:{font:{size:9}},
          ...(opts.yMin!==undefined?{min:opts.yMin}:{}),
          ...(opts.yMax!==undefined?{max:opts.yMax}:{})
        }
      },
      ...(opts.extra||{})
    }
  });
}
function ds(label,data,color,opts={}){
  return {label,data,borderColor:color,backgroundColor:opts.fill?color+'22':'transparent',
    borderWidth:opts.bw??1.5,pointRadius:0,pointHoverRadius:3,fill:opts.fill??false,tension:.3,...opts};
}
function sliceTF(arr,n){return arr?arr.slice(-n):arr}
function sliceLast(dates,vals,n){return{d:sliceTF(dates,n),v:sliceTF(vals,n)}}

// ── TF toggle helper ─────────────────────────────────────────────────────────
function tfSetup(chartRef, serFn){
  // serFn(n) returns {labels, datasets}
  return function(n, btn){
    btn.closest('.chart-card').querySelectorAll('.tf-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    const {labels,datasets}=serFn(n);
    chartRef.data.labels=labels;
    chartRef.data.datasets=datasets;
    chartRef.update();
  };
}

// ── Scorecard ────────────────────────────────────────────────────────────────
let scorecardBuilt=false;
function convClass(c){
  return c==='HIGH OW'?'conv-how2':c==='MEDIUM OW'?'conv-how':c==='NEUTRAL'?'conv-neu':
         c==='MEDIUM UW'?'conv-luw':'conv-huw';
}
function tiltBar(v,max){
  const pct=Math.min(Math.abs(v)/max*50,50);
  const color=v>=0?'#22C55E':'#E8354A';
  const left=v>=0?50:50-pct;
  return `<div class="tilt-bar-wrap">
    <div class="tilt-bar-bg"><div class="tilt-bar-fill" style="width:${pct}%;left:${left}%;background:${color}"></div></div>
    <span class="tilt-val" style="color:${color}">${pctFmt(v)}</span>
  </div>`;
}
function buildScorecard(){
  scorecardBuilt=true;
  // KPIs
  const fi   = SCORECARD.filter(r=>r.group==='FI');
  const eq   = SCORECARD.filter(r=>r.group==='EQ');
  const fiTilt = fi.reduce((s,r)=>s+(r['final_tilt_%']||0),0);
  const eqTilt = eq.reduce((s,r)=>s+(r['final_tilt_%']||0),0);
  const agree  = SCORECARD.filter(r=>r.n_agree>=3).length;
  const teBudget = SCORECARD.reduce((s,r)=>s+Math.abs(r['final_tilt_%']||0),0);
  const kpis = [
    {label:'FI Net Tilt',    value:pctFmt(fiTilt),  sub:'5 asset classes', cls:fiTilt>=0?'kpi-pos':'kpi-neg'},
    {label:'Equity Net Tilt',value:pctFmt(eqTilt),  sub:'7 asset classes', cls:eqTilt>=0?'kpi-pos':'kpi-neg'},
    {label:'Pillars Agree',  value:agree+'/'+SCORECARD.length, sub:'≥3 pillars aligned', cls:'kpi-neut'},
    {label:'TE Budget Used', value:teBudget.toFixed(1)+'%', sub:'sum |final tilt|', cls:'kpi-neut'},
  ];
  document.getElementById('kpi-row').innerHTML = kpis.map(k=>
    `<div class="kpi"><div class="kpi-label">${k.label}</div>
     <div class="kpi-value ${k.cls}">${k.value}</div>
     <div class="kpi-sub">${k.sub}</div></div>`).join('');

  // Table
  const AC_LABEL={money_market:'Money Market',short_term_fi:'Short-Term FI',lt_treasuries:'LT Treasuries',
    lt_us_corp:'LT US Corp',lt_em_fi:'LT EM FI',us_equity:'US Equity',us_growth:'US Growth',
    us_value:'US Value',dm_equity:'DM ex-US',em_equity:'EM Equity',em_xchina:'EM ex-China',
    china_equity:'China Equity'};
  let html=`<thead><tr>
    <th>Asset Class</th><th style="color:var(--pf)">F</th><th style="color:var(--pm)">M</th>
    <th style="color:var(--ps)">S</th><th style="color:var(--pv)">V</th>
    <th>Composite</th><th>Agree</th><th>Conviction</th>
    <th>Abs Tilt</th><th>Rel Tilt</th><th>Final Tilt</th></tr></thead><tbody>`;
  let lastGroup='';
  SCORECARD.forEach(r=>{
    const g=r.group==='FI'?'Fixed Income':'Equity';
    if(g!==lastGroup){
      html+=`<tr class="group-row"><td colspan="11">${g}</td></tr>`;
      lastGroup=g;
    }
    const zc=z=>
      `<span class="zchip" style="background:${zColor(z,.18)};color:${zText(z)}">${zFmt(z)}</span>`;
    html+=`<tr>
      <td>${AC_LABEL[r.ac]||r.ac}</td>
      <td>${zc(r.Z_F)}</td><td>${zc(r.Z_M)}</td>
      <td>${zc(r.Z_S)}</td><td>${zc(r.Z_V)}</td>
      <td>${zc(r.Z_composite)}</td>
      <td style="font-family:'JetBrains Mono',monospace;color:var(--text2)">${r.n_agree}/4</td>
      <td><span class="conv ${convClass(r.conviction)}">${r.conviction}</span></td>
      <td>${tiltBar(r['abs_tilt_%'],5)}</td>
      <td>${tiltBar(r['rel_tilt_%'],5)}</td>
      <td>${tiltBar(r['final_tilt_%'],5)}</td>
    </tr>`;
  });
  html+='</tbody>';
  document.getElementById('sc-table').innerHTML=html;

  // Pillar bars chart
  const acLabels=SCORECARD.map(r=>r.label||r.ac);
  const pillars=[
    {key:'Z_F',label:'Fundamentals',color:'rgba(20,184,166,.85)'},
    {key:'Z_M',label:'Momentum',   color:'rgba(245,158,11,.85)'},
    {key:'Z_S',label:'Sentiment',  color:'rgba(168,85,247,.85)'},
    {key:'Z_V',label:'Valuation',  color:'rgba(58,123,213,.85)'},
  ];
  makeLineChart('ch-pillar-bars', acLabels,
    pillars.map(p=>({type:'bar',label:p.label,
      data:SCORECARD.map(r=>r[p.key]),
      backgroundColor:p.color,borderRadius:2,maxBarThickness:10})),
    {legend:true,extra:{plugins:{legend:{position:'top'}}}});

  // Composite ranking
  const ranked=[...SCORECARD].sort((a,b)=>b.Z_composite-a.Z_composite);
  new Chart(document.getElementById('ch-comp-rank'),{
    type:'bar',
    data:{labels:ranked.map(r=>r.label||r.ac),
      datasets:[{label:'Composite Z',data:ranked.map(r=>r.Z_composite),
        backgroundColor:ranked.map(r=>r.Z_composite>=0?'rgba(34,197,94,.8)':'rgba(232,53,74,.8)'),
        borderRadius:2}]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false}},animation:{duration:200},
      scales:{x:{grid:{color:'rgba(30,46,71,.6)'}},y:{grid:{display:false},ticks:{font:{size:9}}}}}
  });

  // Time series: FI
  const fiAC =['money_market','short_term_fi','lt_treasuries','lt_us_corp','lt_em_fi'];
  const eqAC =['us_equity','us_growth','us_value','dm_equity','em_equity','em_xchina','china_equity'];
  const fiColors=['#60A5FA','#3A7BD5','#14B8A6','#2DD4BF','#0EA5E9'];
  const eqColors=['#4ADE80','#22C55E','#F59E0B','#F97316','#A855F7','#C084FC','#E879F9'];
  const AC_LABEL2={money_market:'Money Mkt',short_term_fi:'ST FI',lt_treasuries:'LT Tsy',
    lt_us_corp:'LT Corp',lt_em_fi:'LT EM FI',us_equity:'US Eq',us_growth:'US Gro',
    us_value:'US Val',dm_equity:'DM',em_equity:'EM Eq',em_xchina:'EM xCN',china_equity:'China'};
  const n=252;
  makeLineChart('ch-fi-ts', sliceTF(COMPOSITES.dates,n),
    fiAC.map((ac,i)=>ds(AC_LABEL2[ac],sliceTF(COMPOSITES[ac],n),fiColors[i])),
    {legend:true});
  makeLineChart('ch-eq-ts', sliceTF(COMPOSITES.dates,n),
    eqAC.map((ac,i)=>ds(AC_LABEL2[ac],sliceTF(COMPOSITES[ac],n),eqColors[i])),
    {legend:true});
}

// ── Heatmap ──────────────────────────────────────────────────────────────────
let heatmapBuilt=false;
function buildHeatmap(){
  heatmapBuilt=true;
  const AC_LABEL={money_market:'Money Market',short_term_fi:'Short-Term FI',lt_treasuries:'LT Treasuries',
    lt_us_corp:'LT US Corp',lt_em_fi:'LT EM FI',us_equity:'US Equity',us_growth:'US Growth',
    us_value:'US Value',dm_equity:'DM ex-US',em_equity:'EM Equity',em_xchina:'EM ex-China',
    china_equity:'China Equity'};
  let html=`<thead><tr><th>Asset Class</th>
    <th style="color:var(--pf)">Fundamentals</th><th style="color:var(--pm)">Momentum</th>
    <th style="color:var(--ps)">Sentiment</th><th style="color:var(--pv)">Valuation</th>
    <th>Composite</th></tr></thead><tbody>`;
  let lastG='';
  SCORECARD.forEach(r=>{
    const g=r.group==='FI'?'Fixed Income':'Equity';
    if(g!==lastG){html+=`<tr class="group-row"><td colspan="6">${g}</td></tr>`;lastG=g;}
    const cell=z=>{
      const bg=zColor(z,.22),col=zText(z);
      return `<td style="background:${bg};color:${col}">${zFmt(z)}</td>`;
    };
    html+=`<tr><td>${AC_LABEL[r.ac]||r.ac}</td>${cell(r.Z_F)}${cell(r.Z_M)}${cell(r.Z_S)}${cell(r.Z_V)}${cell(r.Z_composite)}</tr>`;
  });
  document.getElementById('heat-table').innerHTML=html+'</tbody>';

  // Scatter plots
  const scatterAC=SCORECARD.map(r=>({
    label:r.label||r.ac,x:r.Z_F,y:r.Z_V,
    ms:r.Z_M,ss:r.Z_S,
    color:r.group==='FI'?'rgba(58,123,213,.8)':'rgba(34,197,94,.8)'
  }));
  [
    {id:'ch-sc-fv',xk:'x',yk:'y',xl:'Fundamentals (Z)',yl:'Valuation (Z)'},
    {id:'ch-sc-ms',xk:'ms',yk:'ss',xl:'Momentum (Z)',yl:'Sentiment (Z)'}
  ].forEach(cfg=>{
    new Chart(document.getElementById(cfg.id),{
      type:'scatter',
      data:{datasets:scatterAC.map(p=>({
        label:p.label,data:[{x:p[cfg.xk],y:p[cfg.yk]}],
        backgroundColor:p.color,pointRadius:7,pointHoverRadius:9
      }))},
      options:{responsive:true,maintainAspectRatio:false,animation:{duration:200},
        plugins:{legend:{display:false},
          tooltip:{callbacks:{label:c=>`${c.dataset.label}: (${c.parsed.x?.toFixed(2)}, ${c.parsed.y?.toFixed(2)})`}}},
        scales:{
          x:{title:{display:true,text:cfg.xl,font:{size:10}},
             grid:{color:'rgba(30,46,71,.6)'},
             ticks:{font:{size:9}}},
          y:{title:{display:true,text:cfg.yl,font:{size:10}},
             grid:{color:'rgba(30,46,71,.6)'},ticks:{font:{size:9}}}
        }}
    });
  });
}

// ── Methodology ──────────────────────────────────────────────────────────────
let methBuilt=false;
const SIG_MATRIX=[
  {pillar:'F',name:'ISM Mfg PMI',source:'BBG',freq:'Monthly',
   signs:{money_market:'—',short_term_fi:'-',lt_treasuries:'-',lt_us_corp:'+',lt_em_fi:'—',
          us_equity:'++',us_growth:'++',us_value:'+',dm_equity:'+',em_equity:'+',em_xchina:'+',china_equity:'—'}},
  {pillar:'F',name:'ISM Svcs PMI',source:'BBG',freq:'Monthly',
   signs:{us_equity:'+',us_growth:'+',us_value:'+',lt_treasuries:'-',
          dm_equity:'—',em_equity:'—',em_xchina:'—',china_equity:'—',money_market:'—',short_term_fi:'-',lt_us_corp:'+',lt_em_fi:'—'}},
  {pillar:'F',name:'Eurozone PMI Mfg',source:'BBG',freq:'Monthly',
   signs:{dm_equity:'++',em_equity:'+',em_xchina:'+',china_equity:'—',us_equity:'—',
          money_market:'—',short_term_fi:'—',lt_treasuries:'—',lt_us_corp:'—',lt_em_fi:'—',us_growth:'—',us_value:'—'}},
  {pillar:'F',name:'China PMI (Caixin)',source:'BBG',freq:'Monthly',
   signs:{china_equity:'++',em_equity:'+',em_xchina:'+',lt_em_fi:'+',
          us_equity:'—',dm_equity:'—',money_market:'—',short_term_fi:'—',lt_treasuries:'—',lt_us_corp:'—',us_growth:'—',us_value:'—'}},
  {pillar:'F',name:'CESI United States',source:'BBG',freq:'Daily',
   signs:{us_equity:'+',us_growth:'+',us_value:'+',lt_treasuries:'-',short_term_fi:'-',
          lt_us_corp:'+',dm_equity:'—',em_equity:'—',em_xchina:'—',china_equity:'—',money_market:'+',lt_em_fi:'—'}},
  {pillar:'F',name:'CESI Emerging Mkts',source:'BBG',freq:'Daily',
   signs:{em_equity:'+',em_xchina:'+',china_equity:'+',lt_em_fi:'+',
          us_equity:'—',dm_equity:'—',money_market:'—',short_term_fi:'—',lt_treasuries:'—',lt_us_corp:'—',us_growth:'—',us_value:'—'}},
  {pillar:'F',name:'US GDP Revision',source:'BBG',freq:'Daily',
   signs:{us_equity:'+',us_growth:'+',us_value:'+',lt_treasuries:'-',short_term_fi:'-',
          lt_us_corp:'+',dm_equity:'—',em_equity:'—',em_xchina:'—',china_equity:'—',money_market:'+',lt_em_fi:'—'}},
  {pillar:'F',name:'US Fwd EPS Growth',source:'BBG',freq:'Daily',
   signs:{us_equity:'+',us_growth:'+',us_value:'+',lt_us_corp:'+',
          dm_equity:'—',em_equity:'—',em_xchina:'—',china_equity:'—',money_market:'—',short_term_fi:'—',lt_treasuries:'—',lt_em_fi:'—'}},
  {pillar:'M',name:'Price Momentum (12-1M)',source:'BBG',freq:'Daily',
   signs:{us_equity:'++',us_growth:'++',us_value:'+',dm_equity:'++',em_equity:'++',em_xchina:'++',china_equity:'++',
          lt_treasuries:'+',lt_us_corp:'+',lt_em_fi:'+',short_term_fi:'+',money_market:'+'}},
  {pillar:'M',name:'MA 50/200 Distance',source:'BBG',freq:'Daily',
   signs:{us_equity:'+',us_growth:'+',us_value:'+',dm_equity:'+',em_equity:'+',em_xchina:'+',china_equity:'+',
          lt_treasuries:'+',lt_us_corp:'+',lt_em_fi:'+',short_term_fi:'+',money_market:'—'}},
  {pillar:'M',name:'OAS BBB Momentum',source:'FRED',freq:'Daily',
   signs:{lt_us_corp:'++',short_term_fi:'+',lt_em_fi:'+',
          us_equity:'—',dm_equity:'—',em_equity:'—',em_xchina:'—',china_equity:'—',money_market:'—',lt_treasuries:'+',us_growth:'—',us_value:'+'}},
  {pillar:'M',name:'HY OAS Momentum',source:'FRED',freq:'Daily',
   signs:{lt_us_corp:'++',us_equity:'+',
          dm_equity:'—',em_equity:'+',em_xchina:'+',china_equity:'—',money_market:'—',short_term_fi:'+',lt_treasuries:'—',lt_em_fi:'+',us_growth:'—',us_value:'+'}},
  {pillar:'S',name:'VIX Level',source:'FRED',freq:'Daily',
   signs:{us_equity:'C',us_growth:'C',us_value:'C',dm_equity:'C',em_equity:'C',em_xchina:'C',china_equity:'C',
          lt_treasuries:'+',short_term_fi:'+',money_market:'+',lt_us_corp:'-',lt_em_fi:'-'}},
  {pillar:'S',name:'MOVE Index',source:'BBG',freq:'Daily',
   signs:{lt_treasuries:'+',short_term_fi:'+',
          us_equity:'-',dm_equity:'-',em_equity:'-',em_xchina:'-',china_equity:'-',
          lt_us_corp:'-',lt_em_fi:'-',money_market:'+',us_growth:'-',us_value:'-'}},
  {pillar:'S',name:'AAII Bull-Bear',source:'AAII',freq:'Weekly',
   signs:{us_equity:'C',us_growth:'C',us_value:'C',
          dm_equity:'—',em_equity:'—',em_xchina:'—',china_equity:'—',money_market:'—',short_term_fi:'—',lt_treasuries:'—',lt_us_corp:'—',lt_em_fi:'—'}},
  {pillar:'S',name:'CBOE PCR (10d)',source:'FRED',freq:'Daily',
   signs:{us_equity:'C',us_growth:'C',us_value:'C',
          dm_equity:'—',em_equity:'—',em_xchina:'—',china_equity:'—',money_market:'—',short_term_fi:'—',lt_treasuries:'—',lt_us_corp:'—',lt_em_fi:'—'}},
  {pillar:'V',name:'Forward P/E',source:'BBG',freq:'Daily',
   signs:{us_equity:'-',us_growth:'-',us_value:'-',dm_equity:'-',em_equity:'-',em_xchina:'-',china_equity:'-',
          money_market:'—',short_term_fi:'—',lt_treasuries:'—',lt_us_corp:'—',lt_em_fi:'—'}},
  {pillar:'V',name:'Relative P/E',source:'BBG',freq:'Daily',
   signs:{us_equity:'+',us_growth:'+',us_value:'+',dm_equity:'+',em_equity:'+',em_xchina:'+',china_equity:'+',
          money_market:'—',short_term_fi:'—',lt_treasuries:'—',lt_us_corp:'—',lt_em_fi:'—'}},
  {pillar:'V',name:'OAS Level (pctile)',source:'FRED',freq:'Daily',
   signs:{lt_us_corp:'++',short_term_fi:'+',lt_em_fi:'++',
          us_equity:'—',dm_equity:'—',em_equity:'+',em_xchina:'+',china_equity:'—',money_market:'—',lt_treasuries:'+',us_growth:'—',us_value:'+'}},
  {pillar:'V',name:'Yield Level (pctile)',source:'BBG',freq:'Daily',
   signs:{lt_treasuries:'++',short_term_fi:'+',money_market:'++',lt_us_corp:'+',lt_em_fi:'+',
          us_equity:'—',dm_equity:'—',em_equity:'—',em_xchina:'—',china_equity:'—',us_growth:'—',us_value:'—'}},
  {pillar:'V',name:'Equity Risk Premium',source:'BBG',freq:'Daily',
   signs:{us_equity:'++',us_growth:'+',us_value:'+',dm_equity:'+',em_equity:'++',em_xchina:'+',china_equity:'+',
          money_market:'—',short_term_fi:'—',lt_treasuries:'—',lt_us_corp:'—',lt_em_fi:'—'}},
];
const AC_ORDER=['money_market','short_term_fi','lt_treasuries','lt_us_corp','lt_em_fi',
                'us_equity','us_growth','us_value','dm_equity','em_equity','em_xchina','china_equity'];
const AC_SHORT={money_market:'MM',short_term_fi:'STFI',lt_treasuries:'LT Tsy',lt_us_corp:'IG Corp',
  lt_em_fi:'EM FI',us_equity:'US Eq',us_growth:'US Gro',us_value:'US Val',
  dm_equity:'DM',em_equity:'EM Eq',em_xchina:'EM xCN',china_equity:'China'};
const PSIGN_CLASS={'++':'s-pp','+':'s-p','-':'s-n','--':'s-nn','C':'s-c','—':'s-na'};
const PILLAR_COLOR={F:'var(--pf)',M:'var(--pm)',S:'var(--ps)',V:'var(--pv)'};

function buildMethodology(){
  methBuilt=true;
  let h=`<thead><tr><th>Signal</th><th>Src</th><th>Freq</th>`;
  AC_ORDER.forEach(a=>h+=`<th style="font-size:8px">${AC_SHORT[a]}</th>`);
  h+=`</tr></thead><tbody>`;
  let lastP='';
  SIG_MATRIX.forEach(s=>{
    if(s.pillar!==lastP){
      h+=`<tr class="group-row"><td colspan="${3+AC_ORDER.length}" style="color:${PILLAR_COLOR[s.pillar]}">
        Pillar ${s.pillar} — ${s.pillar==='F'?'Fundamentals':s.pillar==='M'?'Momentum':s.pillar==='S'?'Sentiment':'Valuation'}
      </td></tr>`;
      lastP=s.pillar;
    }
    h+=`<tr><td class="row-head">${s.name}</td>
      <td><span class="chip chip-gray">${s.source}</span></td>
      <td><span class="chip ${s.freq==='Daily'?'chip-blue':s.freq==='Monthly'?'chip-amber':'chip-teal'}">${s.freq}</span></td>`;
    AC_ORDER.forEach(a=>{
      const sg=s.signs[a]||'—';
      h+=`<td><span class="sign ${PSIGN_CLASS[sg]||'s-na'}">${sg}</span></td>`;
    });
    h+=`</tr>`;
  });
  document.getElementById('sig-matrix-table').innerHTML=h+'</tbody>';

  // FI/EQ pillar cards
  buildPillarCards('fi-pillar-cards',['money_market','short_term_fi','lt_treasuries','lt_us_corp','lt_em_fi']);
  buildPillarCards('eq-pillar-cards',['us_equity','us_growth','us_value','dm_equity','em_equity','em_xchina','china_equity']);
}

const AC_LABEL_FULL={money_market:'Money Market',short_term_fi:'Short-Term FI',lt_treasuries:'LT Treasuries',
  lt_us_corp:'LT US Corp',lt_em_fi:'LT EM FI',us_equity:'US Equity',us_growth:'US Growth',
  us_value:'US Value',dm_equity:'DM ex-US',em_equity:'EM Equity',em_xchina:'EM ex-China',
  china_equity:'China Equity'};
const PW={money_market:{F:0.10,M:0.15,S:0.25,V:0.50},short_term_fi:{F:0.20,M:0.25,S:0.20,V:0.35},
  lt_treasuries:{F:0.25,M:0.25,S:0.20,V:0.30},lt_us_corp:{F:0.20,M:0.30,S:0.20,V:0.30},
  lt_em_fi:{F:0.25,M:0.30,S:0.20,V:0.25},us_equity:{F:0.25,M:0.30,S:0.20,V:0.25},
  us_growth:{F:0.20,M:0.35,S:0.15,V:0.30},us_value:{F:0.30,M:0.25,S:0.20,V:0.25},
  dm_equity:{F:0.25,M:0.30,S:0.20,V:0.25},em_equity:{F:0.25,M:0.30,S:0.20,V:0.25},
  em_xchina:{F:0.25,M:0.30,S:0.20,V:0.25},china_equity:{F:0.25,M:0.30,S:0.20,V:0.25}};

function buildPillarCards(containerId, acs){
  const sc=Object.fromEntries(SCORECARD.map(r=>[r.ac,r]));
  let h='<div class="g3 gap mb16">';
  acs.forEach(ac=>{
    const r=sc[ac]||{};
    const w=PW[ac]||{F:.25,M:.25,S:.25,V:.25};
    const pills=['F','M','S','V'].map(p=>{
      const z=r['Z_'+p];
      return `<div class="pillar-bar">
        <span class="pillar-bar-label" style="color:var(--p${p.toLowerCase()})">${p}</span>
        <div class="pillar-bar-track">
          <div class="pillar-bar-fill" style="width:${Math.min(Math.abs(z||0)/3*100,100)}%;
            left:${(z||0)>=0?50:50-Math.min(Math.abs(z||0)/3*50,50)}%;
            background:${(z||0)>=0?'var(--pos)':'var(--neg)'}"></div>
        </div>
        <span class="pillar-bar-val" style="color:${zText(z)}">${zFmt(z)}</span>
        <span style="font-size:9px;color:var(--text3);width:28px;text-align:right">${Math.round(w[p]*100)}%</span>
      </div>`;
    }).join('');
    h+=`<div class="card">
      <div class="card-title">${AC_LABEL_FULL[ac]}</div>
      ${pills}
      <div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border);
        display:flex;align-items:center;gap:8px">
        <span style="font-size:10px;color:var(--text3)">Composite</span>
        <span class="zchip" style="background:${zColor(r.Z_composite,.2)};color:${zText(r.Z_composite)}">${zFmt(r.Z_composite)}</span>
        <span class="conv ${convClass(r.conviction)}" style="margin-left:auto">${r.conviction}</span>
      </div>
    </div>`;
  });
  h+='</div>';
  document.getElementById(containerId).innerHTML=h;
}

// ── CHARTBOOK HELPERS ────────────────────────────────────────────────────────
function mkChartCard(id, label, name, accent, height=160){
  return `<div class="chart-card">
    <div class="chart-card-header">
      <div><div class="chart-card-label" style="color:${accent}">${label}</div>
        <div class="chart-card-name">${name}</div></div>
      <div class="tf-btns">
        <button class="tf-btn" onclick="tfClick(this,'${id}',21)">1M</button>
        <button class="tf-btn" onclick="tfClick(this,'${id}',63)">3M</button>
        <button class="tf-btn active" onclick="tfClick(this,'${id}',252)">1Y</button>
      </div>
    </div>
    <div class="chart-wrap" style="height:${height}px"><canvas id="${id}"></canvas></div>
    <div class="chart-footer" id="${id}-footer"></div>
  </div>`;
}
const CHARTS={};
function tfClick(btn,id,n){
  const c=CHARTS[id];
  if(!c) return;
  btn.closest('.chart-card').querySelectorAll('.tf-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  const full=c._fullData;
  if(!full) return;
  c.data.labels=sliceTF(full.dates,n);
  c.data.datasets.forEach((ds,i)=>{
    if(full.series && full.series[i]) ds.data=sliceTF(full.series[i],n);
  });
  c.update();
}
function registerChart(id,chart,dates,series){
  chart._fullData={dates,series};
  CHARTS[id]=chart;
}
function footer(id,val,trend,z){
  const el=document.getElementById(id+'-footer');
  if(!el) return;
  el.innerHTML=`<span>Latest: <span class="val">${val??'—'}</span></span>`+
    (trend!==undefined?`<span>Trend: <span class="val">${trend}</span></span>`:'')+
    (z!==undefined?`<span>Z: <span class="val" style="color:${zText(z)}">${zFmt(z)}</span></span>`:'');
}
function lastVal(arr){return arr?arr.filter(v=>v!==null).slice(-1)[0]:null}
function trendArrow(arr){const v=arr?arr.filter(v=>v!==null):[];if(v.length<2)return'—';return v.at(-1)>v.at(-21)?'↑':'↓';}

// ── CHARTBOOK: Fundamentals ──────────────────────────────────────────────────
let cbFundBuilt=false;
function buildCBFund(){
  cbFundBuilt=true;
  const el=document.getElementById('cb-fund-content');
  const F=CB.fundamentals;
  let h='';

  // Group: US PMI
  h+=`<div class="group-header" style="color:var(--pf)">United States · PMI & Surprise</div>`;
  h+=`<div class="g3 mb16">`;
  h+=mkChartCard('f-ism-mfg','US','ISM Manufacturing PMI','var(--pf)');
  h+=mkChartCard('f-ism-svc','US','ISM Services PMI','var(--pf)');
  h+=mkChartCard('f-cesi-us','US','CESI United States','var(--pf)');
  h+=`</div>`;

  // Group: US Macro
  h+=`<div class="group-header" style="color:var(--pf)">United States · GDP & Earnings</div>`;
  h+=`<div class="g3 mb16">`;
  h+=mkChartCard('f-gdp-us','US','GDP Forecast Revision (1M)','var(--pf)');
  h+=mkChartCard('f-eps-us','US','Forward EPS (S&P 500)','var(--pf)');
  h+=mkChartCard('f-bk5','US','5Y Breakeven Inflation','var(--pf)');
  h+=`</div>`;

  // Group: Eurozone
  h+=`<div class="group-header" style="color:var(--pf)">Eurozone</div>`;
  h+=`<div class="g3 mb16">`;
  h+=mkChartCard('f-ez-mfg','Eurozone','Manufacturing PMI','var(--pf)');
  h+=mkChartCard('f-ez-svc','Eurozone','Services PMI','var(--pf)');
  h+=mkChartCard('f-cesi-ez','Eurozone','CESI Eurozone','var(--pf)');
  h+=`</div>`;

  // Group: China
  h+=`<div class="group-header" style="color:var(--pf)">China</div>`;
  h+=`<div class="g3 mb16">`;
  h+=mkChartCard('f-cn-mfg','China','Caixin Manufacturing PMI','var(--pf)');
  h+=mkChartCard('f-cesi-cn','China','CESI China','var(--pf)');
  h+=mkChartCard('f-eps-cn','China','Fwd EPS — China','var(--pf)');
  h+=`</div>`;

  // Group: Japan / EM / Global
  h+=`<div class="group-header" style="color:var(--pf)">Japan & EM / Global</div>`;
  h+=`<div class="g3 mb16">`;
  h+=mkChartCard('f-jp-mfg','Japan','Manufacturing PMI','var(--pf)');
  h+=mkChartCard('f-cesi-em','Emerging Mkts','CESI EM','var(--pf)');
  h+=mkChartCard('f-eps-em','EM','Fwd EPS — EM Equity','var(--pf)');
  h+=`</div>`;

  el.innerHTML=h;

  // PMI charts (show raw level with 50-line)
  function pmiChart(id, ser){
    if(!ser||!ser.dates||!ser.dates.length) return;
    const c=new Chart(document.getElementById(id),{
      type:'line',
      data:{labels:ser.dates,
        datasets:[{data:ser.values,borderColor:'var(--pf)',backgroundColor:'rgba(20,184,166,.08)',
          borderWidth:1.5,pointRadius:0,fill:true,tension:.3}]},
      options:{responsive:true,maintainAspectRatio:false,animation:{duration:200},
        plugins:{legend:{display:false},
          annotation:{annotations:{line50:{type:'line',yMin:50,yMax:50,
            borderColor:'rgba(255,255,255,.3)',borderWidth:1,borderDash:[4,4]}}}},
        scales:{x:{grid:{color:'rgba(30,46,71,.6)'},ticks:{maxTicksLimit:6,font:{size:9}}},
          y:{grid:{color:'rgba(30,46,71,.6)'},ticks:{font:{size:9}}}}}
    });
    registerChart(id,c,ser.dates,[ser.values]);
    const v=lastVal(ser.values);
    footer(id,v?.toFixed(1),trendArrow(ser.values),lastVal(ser.z));
  }

  function lineZChart(id,ser,color='var(--blue)'){
    if(!ser||!ser.dates||!ser.dates.length) return;
    const c=makeLineChart(id,ser.dates,[ds('Value',ser.values,color,{fill:true})]);
    registerChart(id,c,ser.dates,[ser.values]);
    const v=lastVal(ser.values);
    footer(id,v?.toFixed(2),trendArrow(ser.values),lastVal(ser.z));
  }

  pmiChart('f-ism-mfg',F.pmi.ism_mfg);
  pmiChart('f-ism-svc',F.pmi.ism_svc);
  lineZChart('f-cesi-us',F.cesi.cesi_us,'var(--pf)');
  lineZChart('f-gdp-us',F.gdp_revision.us,'var(--amber)');
  lineZChart('f-eps-us',F.earnings.eps_fwd_us,'var(--blue)');
  lineZChart('f-bk5',F.inflation.breakeven_5y,'var(--orange)');
  pmiChart('f-ez-mfg',F.pmi.ez_mfg);
  pmiChart('f-ez-svc',F.pmi.ez_svc);
  lineZChart('f-cesi-ez',F.cesi.cesi_ez,'var(--pf)');
  pmiChart('f-cn-mfg',F.pmi.china_mfg);
  lineZChart('f-cesi-cn',F.cesi.cesi_china,'var(--pf)');
  lineZChart('f-eps-cn',F.earnings.eps_fwd_china,'var(--blue)');
  pmiChart('f-jp-mfg',F.pmi.japan_mfg);
  lineZChart('f-cesi-em',F.cesi.cesi_em,'var(--pf)');
  lineZChart('f-eps-em',F.earnings.eps_fwd_em,'var(--blue)');
}

// ── CHARTBOOK: Momentum ──────────────────────────────────────────────────────
let cbMomBuilt=false;
const MOM_COLORS={ret_1m:'#3A7BD5',ret_3m:'#14B8A6',ret_6m:'#F59E0B',ret_12_1m:'#A855F7',ma_dist:'#F97316',rsi:'#22C55E'};
const MOM_LABELS={ret_1m:'Ret 1M',ret_3m:'Ret 3M',ret_6m:'Ret 6M',ret_12_1m:'12-1M',ma_dist:'MA Dist',rsi:'RSI'};

function buildMomCard(id,region,name){
  return `<div class="chart-card" id="card-${id}">
    <div class="chart-card-header">
      <div><div class="chart-card-label" style="color:var(--pm)">${region}</div>
        <div class="chart-card-name">${name}</div></div>
      <div class="tf-btns">
        <button class="tf-btn" onclick="tfClick(this,'${id}',21)">1M</button>
        <button class="tf-btn" onclick="tfClick(this,'${id}',63)">3M</button>
        <button class="tf-btn active" onclick="tfClick(this,'${id}',252)">1Y</button>
      </div>
    </div>
    <div class="metric-toggles" id="mt-${id}">
      ${Object.keys(MOM_COLORS).map(m=>`<button class="mtog active" data-m="${m}" onclick="toggleMom('${id}',this)">${MOM_LABELS[m]}</button>`).join('')}
    </div>
    <div class="chart-wrap" style="height:150px"><canvas id="${id}"></canvas></div>
    <div class="chart-footer" id="${id}-footer"></div>
  </div>`;
}

function buildMomChart(id, momData){
  if(!momData||!Object.keys(momData).length) return;
  const keys=Object.keys(MOM_COLORS);
  const dates=momData[keys.find(k=>momData[k]?.dates?.length)]?.dates||[];
  const datasets=keys.filter(k=>momData[k]?.dates?.length)
    .map(k=>ds(MOM_LABELS[k],momData[k].values,MOM_COLORS[k]));
  const c=makeLineChart(id,dates,datasets,{legend:false});
  if(!c) return;
  const series=keys.filter(k=>momData[k]?.dates?.length).map(k=>momData[k].values);
  registerChart(id,c,dates,series);
  c._momKeys=keys.filter(k=>momData[k]?.dates?.length);
  c._momDates=dates;
  footer(id, null, null, null);
}

function toggleMom(id, btn){
  const m=btn.dataset.m;
  btn.classList.toggle('active');
  const c=CHARTS[id];
  if(!c) return;
  const idx=c._momKeys?.indexOf(m)??-1;
  if(idx>=0){c.data.datasets[idx].hidden=!c.data.datasets[idx].hidden; c.update();}
}

function buildCBMom(){
  cbMomBuilt=true;
  const el=document.getElementById('cb-mom-content');
  const M=CB.momentum;
  let h='';

  h+=`<div class="group-header" style="color:var(--pm)">US Equity</div><div class="g3 mb16">`;
  h+=buildMomCard('m-us-eq','US Equity','S&P 500');
  h+=buildMomCard('m-us-gro','US Growth','S&P 500 Growth');
  h+=buildMomCard('m-us-val','US Value','S&P 500 Value');
  h+=`</div>`;

  h+=`<div class="group-header" style="color:var(--pm)">Developed Markets</div><div class="g2 mb16">`;
  h+=buildMomCard('m-dm','DM ex-US','MSCI EAFE');
  h+=buildMomCard('m-world','Global','MSCI ACWI');
  h+=`</div>`;

  h+=`<div class="group-header" style="color:var(--pm)">Emerging Markets</div><div class="g3 mb16">`;
  h+=buildMomCard('m-em','EM Equity','MSCI EM');
  h+=buildMomCard('m-emx','EM ex-China','MSCI EM ex-China');
  h+=buildMomCard('m-cn','China Equity','MSCI China');
  h+=`</div>`;

  h+=`<div class="group-header" style="color:var(--pm)">Fixed Income</div><div class="g3 mb16">`;
  h+=buildMomCard('m-lttsy','LT Treasuries','Bloomberg Gov TR');
  h+=buildMomCard('m-corp','LT US Corp','Bloomberg US Agg');
  h+=buildMomCard('m-stfi','Short-Term FI','1-3Y Treasury');
  h+=`</div>`;

  h+=`<div class="group-header" style="color:var(--pm)">Credit Spread Momentum</div><div class="g2 mb16">`;
  h+=mkChartCard('m-oas-bbb','Credit','BBB OAS Momentum (sign-inv)','var(--pm)');
  h+=mkChartCard('m-oas-hy','Credit','HY OAS Momentum (sign-inv)','var(--pm)');
  h+=`</div><div class="g2 mb16">`;
  h+=mkChartCard('m-oas-em','EM Credit','EM BBB OAS Momentum','var(--pm)');
  h+=mkChartCard('m-oas-la','EM Credit','LatAm OAS Momentum','var(--pm)');
  h+=`</div>`;

  el.innerHTML=h;

  buildMomChart('m-us-eq',  M.equity.us_equity);
  buildMomChart('m-us-gro', M.equity.us_growth);
  buildMomChart('m-us-val', M.equity.us_value);
  buildMomChart('m-dm',     M.equity.dm_equity);
  buildMomChart('m-world',  M.equity.msci_world);
  buildMomChart('m-em',     M.equity.em_equity);
  buildMomChart('m-emx',    M.equity.em_xchina);
  buildMomChart('m-cn',     M.equity.china_equity);
  buildMomChart('m-lttsy',  M.fi.lt_treasuries);
  buildMomChart('m-corp',   M.fi.lt_us_corp);
  buildMomChart('m-stfi',   M.fi.short_term_fi);

  function spreadMomChart(id, ser1, ser2, c1, c2, l1, l2){
    if(!ser1&&!ser2) return;
    const dates=(ser1||ser2)?.dates||[];
    const dss=[];
    if(ser1?.dates?.length) dss.push(ds(l1,ser1.spread_mom_1m||ser1.values,c1));
    if(ser2?.dates?.length) dss.push(ds(l2,ser2.spread_mom_3m||ser2.values,c2));
    const c=makeLineChart(id,dates,dss);
    registerChart(id,c,dates,dss.map(d=>d.data));
  }
  const S=M.spreads;
  spreadMomChart('m-oas-bbb',S.oas_bbb,null,'var(--blue)',null,'1M','3M');
  spreadMomChart('m-oas-hy', S.oas_hy, null,'var(--amber)',null,'1M','3M');
  spreadMomChart('m-oas-em', S.oas_em, null,'var(--purple)',null,'1M','3M');
  spreadMomChart('m-oas-la', S.oas_latam,null,'var(--orange)',null,'1M','3M');
}

// ── CHARTBOOK: Sentiment ─────────────────────────────────────────────────────
let cbSentBuilt=false;
function buildCBSent(){
  cbSentBuilt=true;
  const el=document.getElementById('cb-sent-content');
  const S=CB.sentiment;
  let h='';

  h+=`<div class="group-header" style="color:var(--ps)">Volatility Indices</div>`;
  h+=`<div class="g3 mb16">`;
  h+=mkChartCard('s-vix','Volatility','VIX — Equity Fear Gauge','var(--ps)');
  h+=mkChartCard('s-move','Volatility','MOVE — Bond Volatility','var(--ps)');
  h+=mkChartCard('s-vstoxx','Eurozone','VSTOXX','var(--ps)');
  h+=`</div>`;

  h+=`<div class="group-header" style="color:var(--ps)">Financial Conditions & Funding</div>`;
  h+=`<div class="g2 mb16">`;
  h+=mkChartCard('s-ted','Funding Stress','TED Spread (Basis Swap Proxy)','var(--ps)');
  h+=mkChartCard('s-embi','EM Stress','EM BBB OAS (EMBI Proxy)','var(--ps)');
  h+=`</div>`;

  h+=`<div class="group-header" style="color:var(--ps)">Investor Positioning & Options</div>`;
  h+=`<div class="g2 mb16">`;
  h+=mkChartCard('s-aaii','Positioning','AAII Bull-Bear Spread','var(--ps)');
  h+=mkChartCard('s-pcr','Options','CBOE Equity PCR (10d MA)','var(--ps)');
  h+=`</div>`;

  el.innerHTML=h;

  function volChart(id, ser, thresholds=[], color='var(--ps)'){
    if(!ser||!ser.dates?.length) return;
    const c=makeLineChart(id, ser.dates,
      [ds('Value',ser.values,color,{fill:true,bw:1.5})]);
    registerChart(id,c,ser.dates,[ser.values]);
    const v=lastVal(ser.values);
    const pct=ser.pctile?lastVal(ser.pctile):null;
    footer(id, v?.toFixed(1), null, null);
    const fl=document.getElementById(id+'-footer');
    if(fl&&pct!==null) fl.innerHTML+=`<span>Pctile: <span class="val">${(pct*100).toFixed(0)}th</span></span>`;
  }

  volChart('s-vix',   S.volatility.vix,  [],'var(--ps)');
  volChart('s-move',  S.volatility.move, [],'var(--ps)');
  volChart('s-vstoxx',S.volatility.vstoxx,[],'var(--ps)');
  volChart('s-ted',   S.funding.ted,     [],'var(--orange)');
  volChart('s-embi',  S.funding.embi,    [],'var(--red)');
  volChart('s-aaii',  S.positioning.aaii_bull_bear,[],'var(--amber)');
  volChart('s-pcr',   S.positioning.pcr, [],'var(--purple)');
}

// ── CHARTBOOK: Valuation ─────────────────────────────────────────────────────
let cbValBuilt=false;
const REL_PE_OPTIONS={
  'Growth vs Value':'growth_vs_value','Value vs Growth':'value_vs_growth',
  'US vs EM':'us_vs_em','EM vs US':'em_vs_us',
  'DM vs US':'dm_vs_us','China vs EM':'china_vs_em','EM vs DM':'em_vs_dm'
};
let relPeChart=null;

function buildCBVal(){
  cbValBuilt=true;
  const el=document.getElementById('cb-val-content');
  const V=CB.valuation;
  let h='';

  // P/E Absolute
  h+=`<div class="group-header" style="color:var(--pv)">Equity P/E — Absolute (Forward P/E level)</div>`;
  h+=`<div class="g3 mb16">`;
  h+=mkChartCard('v-pe-sp500','US','S&P 500 Forward P/E','var(--pv)');
  h+=mkChartCard('v-pe-eafe','DM','MSCI EAFE Forward P/E','var(--pv)');
  h+=mkChartCard('v-pe-em','EM','MSCI EM Forward P/E','var(--pv)');
  h+=`</div><div class="g3 mb16">`;
  h+=mkChartCard('v-pe-china','China','MSCI China Forward P/E','var(--pv)');
  h+=mkChartCard('v-pe-gro','US Growth','S&P 500 Growth P/E','var(--pv)');
  h+=mkChartCard('v-pe-val','US Value','S&P 500 Value P/E','var(--pv)');
  h+=`</div>`;

  // P/E Relative
  h+=`<div class="group-header" style="color:var(--pv)">Equity P/E — Relative (Ratio + Z-Score)</div>`;
  h+=`<div class="g2 mb16">`;
  // Interactive selector
  h+=`<div class="card" style="grid-column:span 2">
    <div class="card-title">Relative P/E — Interactive</div>
    <div class="rel-pe-controls">
      <label>Pair:</label>
      <select id="rel-pe-sel" onchange="updateRelPE()">
        ${Object.keys(REL_PE_OPTIONS).map(k=>`<option value="${REL_PE_OPTIONS[k]}">${k}</option>`).join('')}
      </select>
      <div class="tf-btns">
        <button class="tf-btn" onclick="relPeTf(this,21)">1M</button>
        <button class="tf-btn" onclick="relPeTf(this,63)">3M</button>
        <button class="tf-btn active" onclick="relPeTf(this,252)">1Y</button>
      </div>
      <span class="rel-pe-zscore" id="rel-pe-z">Z: —</span>
    </div>
    <div class="g2">
      <div class="chart-wrap" style="height:160px"><canvas id="ch-rel-pe-ratio"></canvas></div>
      <div class="chart-wrap" style="height:160px"><canvas id="ch-rel-pe-z"></canvas></div>
    </div>
  </div>`;
  h+=`</div>`;

  // Static relative P/E cards
  h+=`<div class="g3 mb16">`;
  h+=mkChartCard('v-rel-gv','Style','Growth vs Value P/E Ratio','var(--pv)',140);
  h+=mkChartCard('v-rel-usem','Cross-Region','US vs EM P/E Ratio','var(--pv)',140);
  h+=mkChartCard('v-rel-dmvs','Cross-Region','DM vs US P/E Ratio','var(--pv)',140);
  h+=`</div>`;

  // ERP
  h+=`<div class="group-header" style="color:var(--pv)">Equity Risk Premium (ERP = Earnings Yield − TIPS 10Y)</div>`;
  h+=`<div class="g2 mb16">`;
  h+=mkChartCard('v-erp-us','US Equity','Equity Risk Premium — US','var(--pv)',160);
  h+=mkChartCard('v-erp-em','EM Equity','Equity Risk Premium — EM','var(--pv)',160);
  h+=`</div>`;

  // OAS
  h+=`<div class="group-header" style="color:var(--pv)">Credit Spreads (OAS) — Absolute Level</div>`;
  h+=`<div class="g2 mb16">`;
  h+=mkChartCard('v-oas-bbb','IG Credit','ICE BofA BBB OAS','var(--pv)');
  h+=mkChartCard('v-oas-hy','HY Credit','ICE BofA HY OAS','var(--pv)');
  h+=`</div><div class="g2 mb16">`;
  h+=mkChartCard('v-oas-em','EM Credit','EM BBB OAS','var(--pv)');
  h+=mkChartCard('v-oas-la','LatAm','LatAm Corp OAS','var(--pv)');
  h+=`</div>`;

  // Yield curve
  h+=`<div class="group-header" style="color:var(--pv)">Yield Curve & Real Rates</div>`;
  h+=`<div class="g3 mb16">`;
  h+=mkChartCard('v-y10','US Yields','US 10Y Treasury Yield','var(--pv)');
  h+=mkChartCard('v-y2','US Yields','US 2Y Treasury Yield','var(--pv)');
  h+=mkChartCard('v-term','Yield Curve','10Y − 2Y Term Spread','var(--pv)');
  h+=`</div><div class="g2 mb16">`;
  h+=mkChartCard('v-tips10','Real Rates','TIPS 10Y Real Yield','var(--pv)');
  h+=mkChartCard('v-tips5','Real Rates','TIPS 5Y Real Yield','var(--pv)');
  h+=`</div>`;

  el.innerHTML=h;

  // Render P/E absolute charts
  function peChart(id, ser){
    if(!ser||!ser.dates?.length) return;
    const c=makeLineChart(id,ser.dates,[ds('P/E',ser.values,'var(--pv)',{fill:false})]);
    registerChart(id,c,ser.dates,[ser.values]);
    const v=lastVal(ser.values);
    const p=ser.pctile?lastVal(ser.pctile):null;
    const fl=document.getElementById(id+'-footer');
    if(fl) fl.innerHTML=`<span>Latest: <span class="val">${v?.toFixed(1)}x</span></span>`+
      (p!==null?`<span>Pctile: <span class="val">${(p*100).toFixed(0)}th</span></span>`:'');
  }
  peChart('v-pe-sp500',V.pe_absolute.sp500);
  peChart('v-pe-eafe', V.pe_absolute.msci_eafe);
  peChart('v-pe-em',   V.pe_absolute.msci_em);
  peChart('v-pe-china',V.pe_absolute.msci_china);
  peChart('v-pe-gro',  V.pe_absolute.sp500_growth);
  peChart('v-pe-val',  V.pe_absolute.sp500_value);

  // Relative P/E interactive
  let relPeTfN=252;
  relPeChart=null;
  window.updateRelPE=function(){
    const key=document.getElementById('rel-pe-sel').value;
    const ser=V.pe_relative[key];
    if(!ser||!ser.dates?.length) return;
    const n=relPeTfN;
    const dates=sliceTF(ser.dates,n), ratio=sliceTF(ser.ratio,n), z=sliceTF(ser.z,n);
    // Rolling mean of ratio
    const mean=ratio.map((_,i)=>{if(i<20)return null;const w=ratio.slice(Math.max(0,i-63),i+1).filter(v=>v!==null);return w.length?w.reduce((a,b)=>a+b,0)/w.length:null;});
    if(!relPeChart){
      const c1=new Chart(document.getElementById('ch-rel-pe-ratio'),{
        type:'line',data:{labels:dates,datasets:[
          ds('Ratio',ratio,'#3A7BD5',{bw:2}),
          ds('Mean',mean,'#F59E0B',{bw:1,borderDash:[4,3]}),
        ]},options:{responsive:true,maintainAspectRatio:false,animation:{duration:0},
          plugins:{legend:{display:true,labels:{boxWidth:8,font:{size:9}}}},
          scales:{x:{grid:{color:'rgba(30,46,71,.6)'},ticks:{maxTicksLimit:5,font:{size:9}}},
            y:{grid:{color:'rgba(30,46,71,.6)'},ticks:{font:{size:9}}}}}});
      const c2=new Chart(document.getElementById('ch-rel-pe-z'),{
        type:'line',data:{labels:dates,datasets:[ds('Z-score',z,'var(--purple)',{fill:true})]},
        options:{responsive:true,maintainAspectRatio:false,animation:{duration:0},
          plugins:{legend:{display:false}},
          scales:{x:{grid:{color:'rgba(30,46,71,.6)'},ticks:{maxTicksLimit:5,font:{size:9}}},
            y:{grid:{color:'rgba(30,46,71,.6)'},ticks:{font:{size:9}}}}}});
      relPeChart={c1,c2};
    } else {
      relPeChart.c1.data.labels=dates;
      relPeChart.c1.data.datasets[0].data=ratio;
      relPeChart.c1.data.datasets[1].data=mean;
      relPeChart.c1.update();
      relPeChart.c2.data.labels=dates;
      relPeChart.c2.data.datasets[0].data=z;
      relPeChart.c2.update();
    }
    const zv=lastVal(z);
    const zEl=document.getElementById('rel-pe-z');
    if(zEl) zEl.textContent=`Z: ${zFmt(zv)}`;
    if(zEl) zEl.style.color=zText(zv);
  };
  window.relPeTf=function(btn,n){
    btn.closest('.card').querySelectorAll('.tf-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    relPeTfN=n;
    updateRelPE();
  };
  updateRelPE();

  // Static relative P/E cards
  function relPeStatic(id, key){
    const ser=V.pe_relative[key];
    if(!ser||!ser.dates?.length) return;
    const c=makeLineChart(id, ser.dates,[
      ds('Ratio',ser.ratio,'#3A7BD5',{bw:2}),
      ds('Z',ser.z,'var(--purple)',{bw:1.2}),
    ],{legend:true});
    registerChart(id,c,ser.dates,[ser.ratio,ser.z]);
    const zv=lastVal(ser.z);
    footer(id,lastVal(ser.ratio)?.toFixed(2),null,zv);
  }
  relPeStatic('v-rel-gv',  'growth_vs_value');
  relPeStatic('v-rel-usem','us_vs_em');
  relPeStatic('v-rel-dmvs','dm_vs_us');

  // ERP charts
  function erpChart(id, ser){
    if(!ser||!ser.dates?.length) return;
    const c=makeLineChart(id, ser.dates,[
      ds('ERP %',ser.values,'var(--green)',{fill:true,bw:2}),
    ]);
    registerChart(id,c,ser.dates,[ser.values]);
    const v=lastVal(ser.values);
    const fl=document.getElementById(id+'-footer');
    if(fl) fl.innerHTML=`<span>ERP: <span class="val">${v?.toFixed(2)}%</span></span>`+
      `<span style="font-size:9px;color:var(--text3)">4%=cheap · 2%=fair · <1%=expensive</span>`;
  }
  erpChart('v-erp-us',V.erp.us_equity);
  erpChart('v-erp-em',V.erp.em_equity);

  // OAS charts
  function oasChart(id, ser){
    if(!ser||!ser.dates?.length) return;
    const vals=ser.values.map(v=>v!==null?v*100:null); // decimal to bps
    const c=makeLineChart(id, ser.dates,[ds('OAS (bps)',vals,'var(--blue)',{fill:true})]);
    registerChart(id,c,ser.dates,[vals]);
    const v=lastVal(vals);
    const p=ser.pctile?lastVal(ser.pctile):null;
    const fl=document.getElementById(id+'-footer');
    if(fl) fl.innerHTML=`<span>OAS: <span class="val">${v?.toFixed(0)} bps</span></span>`+
      (p!==null?`<span>Pctile: <span class="val">${(p*100).toFixed(0)}th</span></span>`:'');
  }
  oasChart('v-oas-bbb',V.oas.bbb);
  oasChart('v-oas-hy', V.oas.hy);
  oasChart('v-oas-em', V.oas.em);
  oasChart('v-oas-la', V.oas.latam);

  // Yield charts
  function yldChart(id, ser, color='var(--blue)'){
    if(!ser||!ser.dates?.length) return;
    const c=makeLineChart(id, ser.dates,[ds('Yield %',ser.values,color)]);
    registerChart(id,c,ser.dates,[ser.values]);
    const v=lastVal(ser.values);
    const p=ser.pctile?lastVal(ser.pctile):null;
    const fl=document.getElementById(id+'-footer');
    if(fl) fl.innerHTML=`<span>Latest: <span class="val">${v?.toFixed(2)}%</span></span>`+
      (p!==null?`<span>Pctile: <span class="val">${(p*100).toFixed(0)}th</span></span>`:'');
  }
  yldChart('v-y10',   V.yields.usy_10y,  '#3A7BD5');
  yldChart('v-y2',    V.yields.usy_2y,   '#14B8A6');
  yldChart('v-term',  V.yields.term_spread,'#F59E0B');
  yldChart('v-tips10',V.yields.tips_10y, '#A855F7');
  yldChart('v-tips5', V.yields.tips_5y,  '#F97316');
}

// ── INIT ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded',()=>{
  nav('sig-score');
});
"""


# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("Loading data...")
    sc_rows, comp_js, cb = load_data()
    print(f"  Scorecard: {len(sc_rows)} rows")
    print(f"  Composite series: {len(comp_js.get('dates',[]))} dates")

    # inject template pieces
    import types
    mod = types.ModuleType("_tpl")
    mod.CSS = CSS
    mod.SIDEBAR_HTML = SIDEBAR_HTML
    mod.SECTION_SIGNALS = SECTION_SIGNALS
    mod.SECTION_METHODOLOGY = SECTION_METHODOLOGY
    mod.SECTION_CHARTBOOK = SECTION_CHARTBOOK
    mod.JS = JS

    html = build_html(sc_rows, comp_js, cb)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    size = os.path.getsize(OUT_PATH) / 1024
    print(f"  dashboard.html -> {OUT_PATH}")
    print(f"  File size: {size:.0f} KB")


if __name__ == "__main__":
    main()
