"""
src/generate_dashboard.py
=========================
Updates index.html in-place by injecting live pipeline data.

Source / Output : index.html  (single dashboard file — read and written back each run)
Live data :
  SCORECARD, COMPOSITES → results/RUN_*/  (CSV outputs of main.py)
  CB                    → results/chartbook_data.json  (chartbook_data.py output)
  SIG_MATRIX, FI/EQ_BLUEPRINT, AC_ORDER, AC_LABEL_FULL, PW
                        → config/taa_config.xlsx  (via build_dashboard.py functions)

Note: docs/model_design.html is a design reference only — it is NOT read by this script.
      index.html is the only dashboard file; it contains the full CSS/JS/layout plus the
      live data constants that this script replaces on each run.

Run:
  python src/generate_dashboard.py
"""

import os, sys, json, re, glob
import pandas as pd
import numpy as np

_SRC  = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SRC)
sys.path.insert(0, _SRC)

TEMPLATE_PATH  = os.path.join(_ROOT, "index.html")   # index.html is both source and output
CB_PATH        = os.path.join(_ROOT, "results", "chartbook_data.json")
SIG_Z_PATH     = os.path.join(_ROOT, "results", "signal_z_snapshot.json")
OUT_PATH       = os.path.join(_ROOT, "index.html")


# ── helpers ──────────────────────────────────────────────────────────────────

def _latest_run() -> str:
    runs = sorted(glob.glob(os.path.join(_ROOT, "results", "RUN_*")))
    return os.path.basename(runs[-1]) if runs else ""


def _js_const(name: str, obj) -> str:
    return f"const {name} = {json.dumps(obj, allow_nan=False, separators=(',', ':'))};"


def _sample(obj, n=252):
    """Keep last n dates in a CB sub-object."""
    if isinstance(obj, dict) and "dates" in obj:
        d = obj.get("dates", [])[-n:]
        r = {"dates": d}
        for k, v in obj.items():
            if k == "dates":
                continue
            if isinstance(v, list):
                r[k] = v[-n:]
            elif isinstance(v, dict):
                r[k] = _sample(v, n)
            else:
                r[k] = v
        return r
    if isinstance(obj, dict):
        return {k: _sample(v, n) for k, v in obj.items()}
    return obj


# ── data loading ─────────────────────────────────────────────────────────────

def load_data():
    run = _latest_run()
    if not run:
        raise FileNotFoundError("No RUN_* folders in results/")

    sc_path   = os.path.join(_ROOT, "results", run, "taa_scorecard.csv")
    comp_path = os.path.join(_ROOT, "results", run, "taa_composite_series.csv")

    sc   = pd.read_csv(sc_path,   index_col=0)
    comp = pd.read_csv(comp_path, index_col=0, parse_dates=True)

    with open(CB_PATH, encoding="utf-8") as f:
        cb = json.load(f)

    return sc, comp, cb, run


# ── methodology blocks from taa_config.xlsx ──────────────────────────────────

def _live_methodology_overrides() -> dict:
    """Generate fresh methodology JS from taa_config.xlsx via build_dashboard.py."""
    try:
        import build_dashboard as _bd
        cfg = _bd.load_config()
        return {
            "SIG_MATRIX":   _bd.render_sig_matrix(cfg),
            "AC_META":      _bd.render_ac_meta(cfg),
            "FI_BLUEPRINT": _bd.render_fi_blueprint(cfg),
            "EQ_BLUEPRINT": _bd.render_eq_blueprint(cfg),
            "AC_LABEL_PW":  _bd.render_ac_label_pw(cfg),
        }
    except Exception as exc:
        print(f"  [warn] live methodology blocks skipped: {exc}")
        return {}


def _patch_methodology(html: str, overrides: dict) -> str:
    """Replace hardcoded methodology constants in the HTML with live versions."""
    def _sub(pattern, replacement, text):
        r = replacement  # capture in closure
        new, _ = re.subn(pattern, lambda _: r, text, flags=re.DOTALL)
        return new

    if overrides.get("SIG_MATRIX"):
        html = _sub(r"const SIG_MATRIX\s*=\s*\[.*?\];", overrides["SIG_MATRIX"], html)

    if overrides.get("AC_META"):
        m = re.search(r"(const AC_ORDER\s*=\s*\[.*?\];)", overrides["AC_META"], re.DOTALL)
        if m:
            html = _sub(r"const AC_ORDER\s*=\s*\[.*?\];", m.group(1), html)

    if overrides.get("FI_BLUEPRINT"):
        html = _sub(r"const FI_BLUEPRINT\s*=\s*\[.*?\];", overrides["FI_BLUEPRINT"], html)

    if overrides.get("EQ_BLUEPRINT"):
        html = _sub(r"const EQ_BLUEPRINT\s*=\s*\[.*?\];", overrides["EQ_BLUEPRINT"], html)

    if overrides.get("AC_LABEL_PW"):
        lp = overrides["AC_LABEL_PW"]
        m_lf = re.search(r"(const AC_LABEL_FULL\s*=\s*\{.*?\};)", lp, re.DOTALL)
        if m_lf:
            html = _sub(r"const AC_LABEL_FULL\s*=\s*\{.*?\};", m_lf.group(1), html)
        m_pw = re.search(r"(const PW\s*=\s*\{.*?\};)", lp, re.DOTALL)
        if m_pw:
            html = _sub(r"const PW\s*=\s*\{.*?\};", m_pw.group(1), html)

    return html


# ── PMI heatmap JS ───────────────────────────────────────────────────────────
# Injected before cbFundBuilt — uses CB.fundamentals_heatmap (quarterly PMI data).
# Design: LGT Capital Partners style — real values, quarterly, green=expansion, red=contraction.

HEATMAP_JS = r"""
// ── PMI / Leading Indicators Heatmap ─────────────────────────────────────────
// Format: monthly columns, grouped by Quarter then Year (LGT Capital Partners style)
// Colors: INDEPENDENT per row — PMI rows use 50-threshold; macro rows use percentile rank

function _hmBg(alpha, isGreen){
  return isGreen
    ? `rgba(0,169,104,${alpha.toFixed(2)})`
    : `rgba(225,29,72,${alpha.toFixed(2)})`;
}
function _hmTc(alpha){
  return alpha > 0.45 ? 'var(--text)' : 'var(--text2)';
}

// For PMI rows: color based on fixed threshold (50 or 1.0)
function hmThresholdStyle(val, threshold, invert){
  if(val===null||val===undefined) return {bg:'var(--bg3)',tc:'var(--text3)'};
  const diff = invert ? threshold - val : val - threshold;
  const absD = Math.abs(val - threshold);
  if(absD < (threshold===50 ? 0.5 : 0.02)) return {bg:'var(--bg3)',tc:'var(--text2)'};
  const scale = threshold===50 ? 7 : 0.18;
  const alpha = Math.min(0.12 + (absD / scale) * 0.76, 0.88);
  return {bg: _hmBg(alpha, diff > 0), tc: _hmTc(alpha)};
}

// For non-PMI rows: color based on percentile rank within own row (independent scale)
function hmPercentileStyle(pct, invert){
  if(pct===null||pct===undefined) return {bg:'var(--bg3)',tc:'var(--text3)'};
  const p = invert ? 1 - pct : pct;
  // 0-0.2: strong red, 0.2-0.4: light red, 0.4-0.6: neutral, 0.6-0.8: light green, 0.8-1: strong green
  if(p >= 0.5){
    const alpha = Math.min(0.10 + (p - 0.5) / 0.5 * 0.78, 0.88);
    return {bg: _hmBg(alpha, true), tc: _hmTc(alpha)};
  } else {
    const alpha = Math.min(0.10 + (0.5 - p) / 0.5 * 0.78, 0.88);
    return {bg: _hmBg(alpha, false), tc: _hmTc(alpha)};
  }
}

function buildFundamentalsHeatmap(el){
  const HM=CB.fundamentals_heatmap;
  if(!HM||!HM.rows||!HM.col_meta) return;

  const cols    = HM.col_meta;   // [{year,quarter,month_idx,month_short,month_full}]
  const years   = HM.years;      // [{year,start_idx,count}]
  const quarters= HM.quarters;   // [{year,quarter,label,start_idx,count}]
  const rows    = HM.rows;
  const nCols   = cols.length;
  const YB      = '2px solid var(--border-strong)';   // year separator — CSS var = visible in dark/light
  const QB      = '1px solid var(--border)';           // quarter separator

  // Helper: is column ci the first of a new year?
  function isYearStart(ci){ return ci>0 && years.some(y=>y.start_idx===ci); }
  function isQtrStart(ci) { return ci>0 && quarters.some(q=>q.start_idx===ci); }
  function colLeftBorder(ci){
    if(isYearStart(ci)) return 'border-left:'+YB+';';
    if(isQtrStart(ci))  return 'border-left:'+QB+';';
    return '';
  }

  let t=`<div style="overflow-x:auto;margin-bottom:20px">
  <div style="margin-bottom:8px">
    <div style="font-size:13px;font-weight:700;color:var(--text);letter-spacing:-.2px">
      Global Industry Growth Heatmap</div>
    <div style="font-size:10px;color:var(--text3);margin-top:2px;font-style:italic">${HM.subtitle||''}</div>
  </div>
  <!-- Legend -->
  <div style="display:flex;align-items:center;gap:5px;margin-bottom:10px;flex-wrap:wrap">
    <span style="font-size:9px;color:var(--text3);font-weight:600;text-transform:uppercase;letter-spacing:.04em">Color:</span>
    <span style="background:rgba(0,169,104,.85);padding:2px 8px;border-radius:3px;color:#fff;font-size:9px">Expansion / Positive</span>
    <span style="background:rgba(0,169,104,.30);padding:2px 8px;border-radius:3px;color:var(--text);font-size:9px">Slightly above</span>
    <span style="background:var(--bg3);padding:2px 8px;border-radius:3px;color:var(--text2);font-size:9px;border:1px solid var(--border)">Neutral</span>
    <span style="background:rgba(225,29,72,.30);padding:2px 8px;border-radius:3px;color:var(--text);font-size:9px">Slightly below</span>
    <span style="background:rgba(225,29,72,.85);padding:2px 8px;border-radius:3px;color:#fff;font-size:9px">Contraction / Negative</span>
    <span style="font-size:9px;color:var(--text3);margin-left:6px">PMI: absolute 50 threshold · Other series: independent per-row scale</span>
  </div>
  <table style="border-collapse:collapse;font-size:10px">
  <thead>
  <!-- Row 1: Year groups -->
  <tr>
    <th style="min-width:195px;padding:4px 10px 3px 0"></th>`;

  years.forEach((yr,yi)=>{
    const lb=yi===0?'':'border-left:'+YB+';';
    t+=`<th colspan="${yr.count}" style="text-align:center;padding:3px 4px;
      font-weight:700;font-size:12px;color:var(--text);letter-spacing:-.2px;${lb}">${yr.year}</th>`;
  });

  t+=`</tr>
  <!-- Row 2: Quarter groups -->
  <tr>
    <th></th>`;

  quarters.forEach((qr,qi)=>{
    const lb=qr.start_idx>0?'border-left:'+(qr.quarter===1?YB:QB)+';':'';
    t+=`<th colspan="${qr.count}" style="text-align:center;padding:2px 3px;
      font-size:10px;font-weight:600;color:var(--text2);${lb}">${qr.label}</th>`;
  });

  t+=`</tr>
  <!-- Row 3: Month labels -->
  <tr>
    <th style="border-bottom:2px solid var(--border-strong)"></th>`;

  cols.forEach((cm,ci)=>{
    const lb=colLeftBorder(ci);
    t+=`<th style="text-align:center;padding:2px 2px 3px;font-size:9px;font-weight:500;
      color:var(--text3);border-bottom:2px solid var(--border-strong);
      min-width:22px;${lb}">${cm.month_short}</th>`;
  });

  t+=`</tr></thead><tbody>`;

  // Data rows
  rows.forEach(row=>{
    if(row.type==='header'){
      t+=`<tr><td colspan="${nCols+1}" style="padding:7px 0 3px;font-size:10px;
        font-weight:700;color:var(--text);letter-spacing:-.1px;
        border-top:1px solid var(--border);border-bottom:1px solid var(--border)">${row.label}</td></tr>`;
      return;
    }

    const vals=row.values||[];
    const pcts=row.percentiles||[];
    const isThresh=row.color_mode==='threshold';
    const thr=row.threshold||50;
    const inv=row.invert||false;

    // No badge next to series name — clean label only
    t+=`<tr><td style="padding:3px 10px 3px 0;color:var(--text2);font-size:10.5px;
      border-bottom:1px solid var(--border);white-space:nowrap">${row.label}</td>`;

    vals.forEach((v,ci)=>{
      const lb=colLeftBorder(ci);
      const pct=pcts[ci];
      if(v===null||v===undefined){
        t+=`<td style="background:var(--bg3);color:var(--text3);text-align:center;
          padding:4px 1px;font-size:8px;border-bottom:1px solid var(--border);${lb}"></td>`;
      } else {
        const cs = isThresh ? hmThresholdStyle(v,thr,inv) : hmPercentileStyle(pct,inv);
        const dp = thr===1||thr===1.0?2:(Math.abs(v)>9?1:2);
        const tip=`${row.label} (${cols[ci].month_full} ${cols[ci].year}): ${v.toFixed(dp)}`;
        t+=`<td style="text-align:center;padding:4px 1px;background:${cs.bg};color:${cs.tc};
          font-size:9px;font-family:'JetBrains Mono',monospace;
          border-bottom:1px solid var(--border);cursor:default;${lb}"
          title="${tip}">${v.toFixed(dp)}</td>`;
      }
    });
    t+=`</tr>`;
  });

  t+=`</tbody></table>
  <div style="font-size:9px;color:var(--text3);margin-top:6px;line-height:1.5">
    Color legend: White = neutral/50 · Green = expansion/positive · Red = contraction/negative.
    PMI threshold = 50 · ISM N.O./Inventories threshold = 1.0 · FCI/NFCI: high = tight = red.
    Non-PMI series: color scaled independently per row using historical percentile rank.
  </div></div>`;

  el.insertAdjacentHTML('afterbegin',t);
}
"""


# ── main build ────────────────────────────────────────────────────────────────

def build_html(sc: pd.DataFrame, comp: pd.DataFrame, cb: dict, run: str) -> str:
    # Read index.html (source of truth — updated in place on each run)
    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        html = f.read()

    # ── 1. Run date and sidebar text ──────────────────────────────────────────
    run_date = cb.get("meta", {}).get("run_date", run[:10] if run else "")
    n_acs    = len(sc)

    # Replace sidebar-sub content (dynamic AC count + date)
    html = re.sub(
        r'(<div class="sidebar-sub">)[^<]*(</div>)',
        rf'\g<1>{run_date} · {n_acs} AC · 4 Pillars\g<2>',
        html
    )

    # Replace date in injectHeaderControls (the lu-val span)
    html = re.sub(
        r"(<span class=\"header-lu-val\">)[^<]*(</span>)",
        rf"\g<1>{run_date}\g<2>",
        html
    )

    # ── 2. Build SCORECARD rows ───────────────────────────────────────────────
    sc_rows = []
    for ac, row in sc.iterrows():
        d = {"ac": ac}
        for col in row.index:
            v = row[col]
            if hasattr(v, "item"):
                v = v.item()
            if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                v = None
            d[col] = v
        sc_rows.append(d)

    # ── 3. Build COMPOSITES (last 756 days = 3Y for Design 4 charts) ─────────
    tail = comp.tail(756)
    comp_obj = {"dates": [d.strftime("%Y-%m-%d") for d in tail.index]}
    for col in tail.columns:
        comp_obj[col] = [
            round(float(v), 4) if not (np.isnan(v) or np.isinf(v)) else None
            for v in tail[col]
        ]

    # ── 4. CB: pass full history (MAX_ROWS removed in chartbook_data.py) ─────
    cb_sampled = cb  # full history; client-side TF slicing handles windowing

    # ── 5. Replace data constants ─────────────────────────────────────────────
    # Use lambda replacements to avoid backslash interpretation in re.sub
    _sc_js   = _js_const("SCORECARD",  sc_rows)
    _comp_js = _js_const("COMPOSITES", comp_obj)
    _cb_js   = _js_const("CB",         cb_sampled)
    html = re.sub(r"const SCORECARD\s*=\s*\[.*?\];",  lambda _: _sc_js,   html, flags=re.DOTALL)
    html = re.sub(r"const COMPOSITES\s*=\s*\{.*?\};", lambda _: _comp_js, html, flags=re.DOTALL)
    html = re.sub(r"const CB\s*=\s*\{.*?\};",         lambda _: _cb_js,   html, flags=re.DOTALL)

    # ── 5b. Inject SIG_Z: real signal z-scores from latest pipeline run ───────
    sig_z = {}
    if os.path.exists(SIG_Z_PATH):
        try:
            with open(SIG_Z_PATH, encoding="utf-8") as f:
                sig_z = json.load(f)
        except Exception as exc:
            print(f"  [warn] signal_z_snapshot.json not loaded: {exc}")
    _sigz_js = _js_const("SIG_Z", sig_z)
    html = re.sub(r"const SIG_Z\s*=\s*\{.*?\};", lambda _: _sigz_js, html, flags=re.DOTALL)

    # ── 6. Patch live methodology constants from taa_config.xlsx ─────────────
    overrides = _live_methodology_overrides()
    html = _patch_methodology(html, overrides)

    # ── 7. Inject heatmap JS before cbFundBuilt ───────────────────────────────
    html = html.replace(
        "let cbFundBuilt=false;",
        HEATMAP_JS + "\nlet cbFundBuilt=false;"
    )

    # ── 8. Add buildFundamentalsHeatmap(el) call at start of buildCBFund ──────
    html = html.replace(
        "function buildCBFund(){\n  cbFundBuilt=true;\n  const el=document.getElementById('cb-fund-content');\n  const F=CB.fundamentals;\n  let h='';\n",
        "function buildCBFund(){\n  cbFundBuilt=true;\n  const el=document.getElementById('cb-fund-content');\n  const F=CB.fundamentals;\n  let h='';\n  // heatmap injected after charts render:\n"
    )
    # Add call at the end of buildCBFund (before the final closing of the function)
    # We find "el.innerHTML=h;" and add the heatmap call after chart setup
    html = html.replace(
        "  el.innerHTML=h;\n\n  // PMI charts",
        "  el.innerHTML=h;\n  buildFundamentalsHeatmap(el);\n\n  // PMI charts"
    )

    return html


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(f"index.html not found: {TEMPLATE_PATH}")

    print("Loading data...")
    sc, comp, cb, run = load_data()
    print(f"  Run:      {run}")
    print(f"  Scorecard: {len(sc)} rows")
    print(f"  Composite: {len(comp)} dates")

    html = build_html(sc, comp, cb, run)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    size_kb = os.path.getsize(OUT_PATH) // 1024
    print(f"  index.html -> {OUT_PATH}  ({size_kb} KB)")


if __name__ == "__main__":
    main()
    # Optional: run economic sanity report
    try:
        ans = input("\nRun economic sanity report? [y/N] ").strip().lower()
    except EOFError:
        ans = "n"
    if ans in ("y", "yes"):
        import sys as _sys
        _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from economic_sanity import main as _sanity_main
        _sanity_main()
