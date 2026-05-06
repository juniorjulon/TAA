"""
src/generate_dashboard.py
=========================
Generates index.html by injecting live pipeline data into docs/model_design.html.

Template  : docs/model_design.html  (CSS / HTML / JS design — owned by user)
Live data :
  SCORECARD, COMPOSITES → results/RUN_*/  (CSV outputs of main.py)
  CB                    → results/chartbook_data.json  (chartbook_data.py output)
  SIG_MATRIX, FI/EQ_BLUEPRINT, AC_ORDER, AC_LABEL_FULL, PW
                        → config/taa_config.xlsx  (via build_dashboard.py functions)

Output    : index.html

Run:
  python src/generate_dashboard.py
"""

import os, sys, json, re, glob
import pandas as pd
import numpy as np

_SRC  = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SRC)
sys.path.insert(0, _SRC)

TEMPLATE_PATH = os.path.join(_ROOT, "docs", "model_design.html")
CB_PATH       = os.path.join(_ROOT, "results", "chartbook_data.json")
OUT_PATH      = os.path.join(_ROOT, "index.html")


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


# ── fundamentals heatmap JS ───────────────────────────────────────────────────
# Injected before cbFundBuilt — uses CB.fundamentals_heatmap (in CB data object)

HEATMAP_JS = r"""
function heatColor(z){
  if(z===null||z===undefined) return 'var(--bg3)';
  if(z> 1.5)  return 'rgba(0,169,104,.55)';
  if(z> 0.75) return 'rgba(0,169,104,.28)';
  if(z>-0.75) return 'var(--bg4)';
  if(z>-1.5)  return 'rgba(225,29,72,.25)';
  return 'rgba(225,29,72,.5)';
}
function heatTextColor(z){
  if(z===null||z===undefined) return 'var(--text3)';
  if(Math.abs(z)>0.75) return 'var(--text)';
  return 'var(--text2)';
}
function buildFundamentalsHeatmap(el){
  const HM=CB.fundamentals_heatmap;
  if(!HM||!HM.dates||!HM.series_meta) return;
  const N=Math.min(HM.dates.length,18);
  const dates=HM.dates.slice(-N);
  const meta=HM.series_meta;
  function fmtMonth(ym){const[y,m]=ym.split('-');const mn=['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];return mn[parseInt(m)]+" '"+y.slice(2);}
  let t=`<div class="card mb16" style="overflow-x:auto">
  <div class="card-title" style="display:flex;align-items:center;gap:12px">
    US Fundamentals Heatmap — Monthly z-scores
    <span style="font-size:9px;font-weight:400;color:var(--text3);font-family:'JetBrains Mono',monospace">
      <span style="background:rgba(0,169,104,.55);padding:1px 6px;border-radius:3px;color:var(--text);margin-right:4px">Strong</span>
      <span style="background:rgba(0,169,104,.28);padding:1px 6px;border-radius:3px;color:var(--text);margin-right:4px">Positive</span>
      <span style="background:var(--bg4);padding:1px 6px;border-radius:3px;color:var(--text2);margin-right:4px">Neutral</span>
      <span style="background:rgba(225,29,72,.25);padding:1px 6px;border-radius:3px;color:var(--text);margin-right:4px">Negative</span>
      <span style="background:rgba(225,29,72,.5);padding:1px 6px;border-radius:3px;color:var(--text)">Weak</span>
    </span>
  </div>
  <table class="heat-table"><thead><tr>
    <th style="text-align:left;min-width:200px">Series</th>`;
  dates.forEach(d=>{t+=`<th>${fmtMonth(d)}</th>`;});
  t+=`</tr></thead><tbody>`;
  meta.forEach(s=>{
    const z=( HM.zscores[s.id]||[]).slice(-N);
    const raw=(HM.raw[s.id]||[]).slice(-N);
    const lastZ=z.filter(v=>v!==null).at(-1);
    let badge='';
    if(lastZ!=null){
      const col=lastZ>0.75?'rgba(0,169,104,.55)':lastZ<-0.75?'rgba(225,29,72,.5)':'var(--bg4)';
      const tc=Math.abs(lastZ)>0.75?'var(--text)':'var(--text2)';
      badge=`<span style="margin-left:6px;padding:1px 5px;border-radius:3px;background:${col};color:${tc};font-size:9px;font-family:'JetBrains Mono',monospace">${lastZ>0?'+':''}${lastZ.toFixed(1)}</span>`;
    }
    t+=`<tr><td style="color:var(--text)">${s.label}${badge}</td>`;
    z.forEach((zv,i)=>{
      const rv=raw[i];
      const bg=heatColor(zv);
      const tc=heatTextColor(zv);
      const tip=zv!=null?`z=${zv>0?'+':''}${zv.toFixed(2)}${rv!=null?' | '+rv.toFixed(2):''}`:'-';
      t+=`<td style="background:${bg};color:${tc};text-align:center;cursor:default;border:1px solid var(--bg);border-radius:3px" title="${tip}">${zv!=null?(zv>0?'+':'')+zv.toFixed(1):'—'}</td>`;
    });
    t+=`</tr>`;
  });
  t+=`</tbody></table></div>`;
  el.insertAdjacentHTML('afterbegin',t);
}
"""


# ── main build ────────────────────────────────────────────────────────────────

def build_html(sc: pd.DataFrame, comp: pd.DataFrame, cb: dict, run: str) -> str:
    # Read design template
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

    # ── 3. Build COMPOSITES (last 252 days) ───────────────────────────────────
    tail = comp.tail(252)
    comp_obj = {"dates": [d.strftime("%Y-%m-%d") for d in tail.index]}
    for col in tail.columns:
        comp_obj[col] = [
            round(float(v), 4) if not (np.isnan(v) or np.isinf(v)) else None
            for v in tail[col]
        ]

    # ── 4. CB: sample to 252 rows per series to keep file manageable ─────────
    cb_sampled = _sample(cb, n=252)

    # ── 5. Replace data constants ─────────────────────────────────────────────
    # Use lambda replacements to avoid backslash interpretation in re.sub
    _sc_js   = _js_const("SCORECARD",  sc_rows)
    _comp_js = _js_const("COMPOSITES", comp_obj)
    _cb_js   = _js_const("CB",         cb_sampled)
    html = re.sub(r"const SCORECARD\s*=\s*\[.*?\];",  lambda _: _sc_js,   html, flags=re.DOTALL)
    html = re.sub(r"const COMPOSITES\s*=\s*\{.*?\};", lambda _: _comp_js, html, flags=re.DOTALL)
    html = re.sub(r"const CB\s*=\s*\{.*?\};",         lambda _: _cb_js,   html, flags=re.DOTALL)

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
        raise FileNotFoundError(f"Template not found: {TEMPLATE_PATH}\nExpected docs/model_design.html")

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
