"""
src/economic_sanity.py
======================
Generates an economic sanity report for the latest (or specified) TAA run.

Reads:
  results/RUN_YYYYMMDD_HHMMSS/taa_scorecard.csv
  results/RUN_YYYYMMDD_HHMMSS/signal_z_snapshot.json
  results/RUN_YYYYMMDD_HHMMSS/multi_portfolio_views.xlsx

Compares with the previous run's signal_z_snapshot.json to show largest movers.

Output:
  results/economic_sanity/ESR_YYYYMMDD_HHMMSS.md

Run:
  python src/economic_sanity.py           # uses latest RUN
  python src/economic_sanity.py RUN_20260520_114858   # specific run
"""

import os
import sys
import glob
import json
import math
import pandas as pd
import numpy as np
from datetime import datetime

_SRC  = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SRC)
sys.path.insert(0, _SRC)


# ── helpers ───────────────────────────────────────────────────────────────────

def _latest_run() -> str:
    runs = sorted(glob.glob(os.path.join(_ROOT, "results", "RUN_*")))
    if not runs:
        raise SystemExit("No RUN_* folders found in results/")
    return os.path.basename(runs[-1])


def _prev_run(current: str) -> str | None:
    runs = sorted(glob.glob(os.path.join(_ROOT, "results", "RUN_*")))
    names = [os.path.basename(r) for r in runs]
    try:
        idx = names.index(current)
        return names[idx - 1] if idx > 0 else None
    except ValueError:
        return None


def _load_snap(run_id: str) -> dict | None:
    p = os.path.join(_ROOT, "results", run_id, "signal_z_snapshot.json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _z_bar(z: float, width: int = 8) -> str:
    if z is None or (isinstance(z, float) and math.isnan(z)):
        return ""
    filled = min(int(abs(z) * 2), width)
    return "+" * filled if z >= 0 else "-" * filled


def _flag(z: float, warn: float = 2.0, strong: float = 2.5) -> str:
    if z is None or (isinstance(z, float) and math.isnan(z)):
        return ""
    if abs(z) >= strong:
        return " **[!!]**"
    if abs(z) >= warn:
        return " **[!]**"
    return ""


# ── signal groupings for the report ──────────────────────────────────────────

SIGNAL_GROUPS = {
    "Growth / Macro": [
        "pmi_us", "pmi_ez", "pmi_china", "pmi_japan_mfg",
        "cesi_us", "cesi_ez", "cesi_em", "cesi_china", "cesi_japan",
        "gdp_us", "gdp_eu", "gdp_em", "gdp_china", "gdpnow", "ism_no_inv",
    ],
    "Inflation / Rates": [
        "core_pce", "real_ff", "breakeven_1y", "breakeven_5y", "breakeven_10y",
        "term_spread", "gt02", "gt10", "gt02_mom", "gt10_mom",
    ],
    "Credit Spreads": [
        "oas_bbb", "oas_hy", "oas_em", "oas_latam",
        "oas_bbb_mom", "oas_hy_mom", "oas_em_mom",
        "cdx_ig_mom", "cdx_hy_mom", "hy_ig_ratio",
    ],
    "Equity Valuation": [
        "erp_us", "erp_em", "erp_acwi",
        "pe_score_sp500", "pe_score_eafe", "pe_score_em", "pe_score_gro", "pe_score_val",
        "rel_pe_dm_us", "rel_pe_em_us", "rel_pe_gro_val",
    ],
    "Equity Momentum": [
        "sp500_tr", "sp500_gro_tr", "sp500_val_tr", "eafe_tr", "msci_em_tr", "msci_acwi_tr",
    ],
    "FI Momentum": [
        "bfu5_price", "i132_price", "lt03_price", "bsgv_price",
    ],
    "Sentiment": [
        "vix", "move_z", "vstoxx_z", "skew_z", "pcr",
        "aaii_z", "fci_z", "fci_ez", "nfci", "modern_ted", "dxy_z",
    ],
    "Earnings Revisions": [
        "eps_us", "eps_em", "eps_eafe", "eps_china", "eps_japan",
        "eps_rev_us", "eps_rev_em", "eps_rev_eafe", "eps_rev_china",
    ],
    "Stress Proxies": [
        "hy_stress", "hy_safe_haven", "em_stress", "embi",
    ],
}

# AC-level assessment rules (pillar thresholds for auto-text)
def _ac_verdict(row: dict, ac: str) -> str:
    """Generate a one-line verdict based on pillar z-scores."""
    zf = row.get("Z_F", 0.0) or 0.0
    zm = row.get("Z_M", 0.0) or 0.0
    zs = row.get("Z_S", 0.0) or 0.0
    zv = row.get("Z_V", 0.0) or 0.0
    zc = row.get("Z_composite", 0.0) or 0.0
    conv = str(row.get("conviction", "NEUTRAL"))
    tilt = float(row.get("final_tilt_%", 0.0) or 0.0)

    # Identify dominant drivers (|z| > 0.8)
    drivers = []
    if abs(zf) > 0.8:
        drivers.append(f"F{'(+)' if zf > 0 else '(-)'} {abs(zf):.1f}")
    if abs(zm) > 0.8:
        drivers.append(f"M{'(+)' if zm > 0 else '(-)'} {abs(zm):.1f}")
    if abs(zs) > 0.8:
        drivers.append(f"S{'(+)' if zs > 0 else '(-)'} {abs(zs):.1f}")
    if abs(zv) > 0.8:
        drivers.append(f"V{'(+)' if zv > 0 else '(-)'} {abs(zv):.1f}")

    driver_str = ", ".join(drivers) if drivers else "all pillars near neutral"
    tilt_str = f"{tilt:+.1f}%" if tilt != 0.0 else "0.0%"

    return f"Composite {zc:+.2f} ({conv}), tilt {tilt_str}. Drivers: {driver_str}."


def _macro_flags(snap: dict) -> list[str]:
    """Extract auto-generated macro warning flags from signal z-scores."""
    flags = []

    bk10 = snap.get("breakeven_10y", 0)
    if isinstance(bk10, float) and bk10 > 2.0:
        flags.append(f"INFLATION EXPECTATIONS: `breakeven_10y` = {bk10:+.2f} (>{2.0} sigma) — very elevated long-run inflation pricing.")

    oas_em = snap.get("oas_em", 0)
    if isinstance(oas_em, float) and oas_em < -1.8:
        flags.append(f"CREDIT EXTREME: `oas_em` = {oas_em:+.2f} (<-1.8 sigma) — EM credit spreads at historical tights, asymmetric downside.")

    oas_bbb = snap.get("oas_bbb", 0)
    if isinstance(oas_bbb, float) and oas_bbb < -1.8:
        flags.append(f"CREDIT EXTREME: `oas_bbb` = {oas_bbb:+.2f} (<-1.8 sigma) — IG BBB spreads at historical tights.")

    stfi_v = snap.get("lt_em_fi_V", None)  # placeholder; use oas_em as proxy
    for sid, threshold, label in [
        ("erp_us",   -1.5, "US ERP compressed"),
        ("erp_em",   -1.5, "EM ERP compressed"),
        ("erp_acwi", -1.5, "Global ERP compressed"),
    ]:
        z = snap.get(sid)
        if isinstance(z, float) and z < threshold:
            flags.append(f"EQUITY RISK PREMIUM: `{sid}` = {z:+.2f} — {label}, equity valuation stretched vs bonds.")

    real_ff = snap.get("real_ff", 0)
    if isinstance(real_ff, float) and real_ff < -1.5:
        flags.append(f"POLICY STANCE: `real_ff` = {real_ff:+.2f} — highly restrictive real rates, headwind for risk assets.")

    gdp_eu = snap.get("gdp_eu", 0)
    cesi_ez = snap.get("cesi_ez", 0)
    if isinstance(gdp_eu, float) and gdp_eu < -1.0 and isinstance(cesi_ez, float) and cesi_ez < -1.0:
        flags.append(f"EZ DETERIORATION: `gdp_eu` = {gdp_eu:+.2f}, `cesi_ez` = {cesi_ez:+.2f} — European fundamentals double negative confirmation.")

    return flags


# ── report builder ────────────────────────────────────────────────────────────

def build_report(run_id: str) -> str:
    run_dir = os.path.join(_ROOT, "results", run_id)

    # Load scorecard
    sc_path = os.path.join(run_dir, "taa_scorecard.csv")
    if not os.path.exists(sc_path):
        raise FileNotFoundError(f"Scorecard not found: {sc_path}")
    sc = pd.read_csv(sc_path, index_col=0)

    # Load current signal snapshot
    cur_snap = _load_snap(run_id)
    if cur_snap is None:
        raise FileNotFoundError(f"signal_z_snapshot.json not found in {run_id}")

    # Load previous snapshot for delta comparison
    prev_id = _prev_run(run_id)
    prev_snap = _load_snap(prev_id) if prev_id else None

    # Load multi-portfolio views
    mp_path = os.path.join(run_dir, "multi_portfolio_views.xlsx")
    mp = {}
    if os.path.exists(mp_path):
        xl = pd.ExcelFile(mp_path)
        for sheet in xl.sheet_names:
            if sheet != "Tilt_Summary":
                mp[sheet] = pd.read_excel(xl, sheet, index_col=0)
        if "Tilt_Summary" in xl.sheet_names:
            tilt_summary = pd.read_excel(xl, "Tilt_Summary", index_col=0)
        else:
            tilt_summary = None
    else:
        tilt_summary = None

    # Extract run timestamp
    ts = run_id.replace("RUN_", "")
    try:
        dt = datetime.strptime(ts, "%Y%m%d_%H%M%S")
        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        data_date_str = dt.strftime("%Y-%m-%d")
    except ValueError:
        dt_str = ts
        data_date_str = ts

    lines = []

    # ── Header ────────────────────────────────────────────────────────────────
    lines.append(f"# Economic Sanity Report")
    lines.append(f"**Run:** {run_id}  ")
    lines.append(f"**Data through:** {data_date_str}  ")
    lines.append(f"**Generated:** {dt_str}  ")
    if prev_id:
        lines.append(f"**Previous run:** {prev_id}  ")
    lines.append("")

    # ── Signal Movers ─────────────────────────────────────────────────────────
    if prev_snap:
        lines.append("---")
        lines.append("")
        lines.append("## Largest Signal Changes vs Previous Run")
        lines.append("")
        deltas = []
        for k in cur_snap:
            if k in prev_snap:
                cv, pv = cur_snap[k], prev_snap[k]
                if isinstance(cv, (int, float)) and isinstance(pv, (int, float)):
                    d = cv - pv
                    if abs(d) > 0.25:
                        deltas.append((abs(d), k, pv, cv, d))
        deltas.sort(reverse=True)

        lines.append("| Signal | Prev | Current | Change | Interpretation |")
        lines.append("|---|---|---|---|---|")
        for _, k, old, new, d in deltas[:20]:
            sign = "+" if d > 0 else ""
            flag = _flag(new)
            interp = ""
            if k == "breakeven_10y" and abs(d) > 1.0:
                interp = "Inflation expectations surge" if d > 0 else "Inflation expectations easing"
            elif k == "breakeven_5y" and abs(d) > 0.8:
                interp = "5Y inflation expectation shift"
            elif k in ("oas_bbb", "oas_hy", "oas_em", "oas_latam") and d < -0.5:
                interp = "Credit spreads tightened further"
            elif k in ("oas_bbb", "oas_hy", "oas_em", "oas_latam") and d > 0.5:
                interp = "Credit spreads widened"
            elif k.startswith("cesi_") and d > 0.8:
                interp = f"Economic data beat consensus ({k[5:].upper()})"
            elif k.startswith("cesi_") and d < -0.8:
                interp = f"Economic data disappointed ({k[5:].upper()})"
            elif k.startswith("gdp_") and d < -0.8:
                interp = "GDP forecast cut"
            elif k.startswith("gdp_") and d > 0.8:
                interp = "GDP forecast revised up"
            elif k.startswith("eps_rev") and abs(d) > 0.5:
                interp = "EPS revisions " + ("upgraded" if d > 0 else "downgraded")
            elif k == "pcr" and d > 1.0:
                interp = "Put/call flipped — market more hedged (contrarian +)"
            elif k == "pcr" and d < -1.0:
                interp = "Put/call eased — market less hedged"
            elif k == "gdpnow" and abs(d) > 1.0:
                interp = "GDPNow tracking " + ("surged" if d > 0 else "fell")
            elif k in ("vix", "vstoxx_z", "move_z") and d > 1.0:
                interp = "Volatility spike — risk-off"
            elif k in ("vix", "vstoxx_z", "move_z") and d < -1.0:
                interp = "Volatility eased"
            elif k.endswith("_tr") or k.endswith("_price"):
                interp = "Price momentum " + ("improved" if d > 0 else "deteriorated")
            lines.append(f"| `{k}` | {old:+.2f} | {new:+.2f}{flag} | **{sign}{d:.2f}** | {interp} |")
        lines.append("")

    # ── Scorecard ──────────────────────────────────────────────────────────────
    lines.append("---")
    lines.append("")
    lines.append("## TAA Scorecard")
    lines.append("")
    lines.append("| Asset Class | Z_F | Z_M | Z_S | Z_V | Z_Comp | Conviction | Tilt |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for ac in sc.index:
        row = sc.loc[ac]
        label = str(row.get("label", ac))
        zf = row.get("Z_F", float("nan"))
        zm = row.get("Z_M", float("nan"))
        zs = row.get("Z_S", float("nan"))
        zv = row.get("Z_V", float("nan"))
        zc = row.get("Z_composite", float("nan"))
        conv = str(row.get("conviction", "NEUTRAL"))
        tilt = float(row.get("final_tilt_%", 0.0) or 0.0)
        tilt_str = f"**{tilt:+.1f}%**" if abs(tilt) > 0.05 else "0%"
        lines.append(
            f"| {label} | {zf:+.2f} | {zm:+.2f} | {zs:+.2f} | {zv:+.2f} | "
            f"{zc:+.2f} | {conv} | {tilt_str} |"
        )
    lines.append("")

    # ── AC Verdicts ────────────────────────────────────────────────────────────
    lines.append("---")
    lines.append("")
    lines.append("## AC-Level Assessment")
    lines.append("")
    for ac in sc.index:
        row = sc.loc[ac].to_dict()
        label = str(row.get("label", ac))
        tilt = float(row.get("final_tilt_%", 0.0) or 0.0)
        conv = str(row.get("conviction", "NEUTRAL"))
        zc = float(row.get("Z_composite", 0.0) or 0.0)
        zf = float(row.get("Z_F", 0.0) or 0.0)
        zm = float(row.get("Z_M", 0.0) or 0.0)
        zs = float(row.get("Z_S", 0.0) or 0.0)
        zv = float(row.get("Z_V", 0.0) or 0.0)

        tilt_display = f"{tilt:+.1f}%"
        conv_icon = {"HIGH OW": "++", "MEDIUM OW": "+", "NEUTRAL": "=",
                     "MEDIUM UW": "-", "HIGH UW": "--"}.get(conv, "=")
        lines.append(f"### {label} — {conv_icon} {conv} ({tilt_display})")
        lines.append("")

        # Pillar breakdown
        lines.append(f"| Pillar | Z-score | Signal |")
        lines.append(f"|---|---|---|")
        for p_label, z_val in [("Fundamentals (F)", zf), ("Momentum (M)", zm),
                                ("Sentiment (S)", zs), ("Valuation (V)", zv)]:
            bar = _z_bar(z_val)
            flag = _flag(z_val)
            lines.append(f"| {p_label} | {z_val:+.2f}{flag} | `{bar}` |")
        lines.append("")

        # Auto interpretation
        if ac in ("money_market", "short_term_fi"):
            lines.append("*Structural position — no tactical tilt generated. "
                         "Absorbs zero-sum redistribution from active ACs.*")
        else:
            # Identify strongest driver
            pillars = {"F": zf, "M": zm, "S": zs, "V": zv}
            strongest = max(pillars, key=lambda k: abs(pillars[k]))
            sv = pillars[strongest]

            # Generate auto-comment
            if abs(zc) < 0.3:
                lines.append("Mixed signals — pillars pulling in different directions. "
                             "No clear directional conviction.")
            elif zc > 0.5:
                lines.append(f"Positive composite driven primarily by {strongest} ({sv:+.2f}). "
                             f"Signal direction is bullish.")
            else:
                lines.append(f"Negative composite driven primarily by {strongest} ({sv:+.2f}). "
                             f"Signal direction is bearish.")

            # Specific pillar flags
            if zv < -2.5:
                lines.append(f"  - **VALUATION FLAG**: V = {zv:+.2f} — asset class priced at historical extreme (expensive). Single-pillar signal; no conviction without corroboration.")
            if zv > 2.0:
                lines.append(f"  - **VALUATION FLAG**: V = {zv:+.2f} — historically cheap on valuation metrics.")
            if zf < -1.5:
                lines.append(f"  - **FUNDAMENTALS FLAG**: F = {zf:+.2f} — fundamentals significantly below trend.")
            if zm < -1.5:
                lines.append(f"  - **MOMENTUM FLAG**: M = {zm:+.2f} — strong negative price/spread momentum.")
            if zm > 1.5:
                lines.append(f"  - **MOMENTUM FLAG**: M = {zm:+.2f} — strong positive momentum.")

        lines.append("")

    # ── Signal Environment ─────────────────────────────────────────────────────
    lines.append("---")
    lines.append("")
    lines.append("## Signal Environment")
    lines.append("")
    for group, sids in SIGNAL_GROUPS.items():
        lines.append(f"### {group}")
        lines.append("")
        lines.append("| Signal | Z-score | Direction |")
        lines.append("|---|---|---|")
        for sid in sids:
            z = cur_snap.get(sid)
            if z is None:
                continue
            if not isinstance(z, (int, float)):
                continue
            flag = _flag(z)
            bar = _z_bar(z)
            lines.append(f"| `{sid}` | {z:+.2f}{flag} | `{bar}` |")
        lines.append("")

    # ── Macro Flags ───────────────────────────────────────────────────────────
    flags = _macro_flags(cur_snap)
    if flags:
        lines.append("---")
        lines.append("")
        lines.append("## Macro Warning Flags")
        lines.append("")
        for f in flags:
            lines.append(f"- **{f}**")
        lines.append("")

    # ── Portfolio Tilts ────────────────────────────────────────────────────────
    if tilt_summary is not None:
        lines.append("---")
        lines.append("")
        lines.append("## Portfolio Tilt Summary")
        lines.append("")
        cols = tilt_summary.columns.tolist()
        lines.append("| Asset Class | " + " | ".join(cols) + " |")
        lines.append("|---" * (len(cols) + 1) + "|")
        for ac in tilt_summary.index:
            vals = []
            for col in cols:
                v = tilt_summary.loc[ac, col]
                try:
                    v = float(v)
                    vals.append(f"**{v:+.1f}%**" if abs(v) > 0.05 else "0%")
                except (TypeError, ValueError):
                    vals.append(str(v))
            lines.append(f"| {ac} | " + " | ".join(vals) + " |")
        lines.append("")
        lines.append("*Tilts scale with TE budget. force_zero_sum=True. MM/STFI absorb residual.*")
        lines.append("")

    # ── Overall Verdict ────────────────────────────────────────────────────────
    lines.append("---")
    lines.append("")
    lines.append("## Overall Verdict")
    lines.append("")

    # Identify the highest conviction call
    high_conv = []
    for ac in sc.index:
        row = sc.loc[ac]
        conv = str(row.get("conviction", "NEUTRAL"))
        tilt = float(row.get("final_tilt_%", 0.0) or 0.0)
        if abs(tilt) > 0.5 or "HIGH" in conv or "MEDIUM" in conv:
            high_conv.append((abs(tilt), ac, conv, tilt))
    high_conv.sort(reverse=True)

    if high_conv:
        lines.append("**Active conviction calls (|tilt| > 0.5% or non-neutral conviction):**")
        lines.append("")
        for _, ac, conv, tilt in high_conv:
            label = str(sc.loc[ac].get("label", ac))
            lines.append(f"- **{label}**: {conv} ({tilt:+.1f}%)")
        lines.append("")

    total_abs = sum(abs(float(sc.loc[ac].get("final_tilt_%", 0) or 0)) for ac in sc.index)
    lines.append(f"Total |tilts| across all ACs: **{total_abs:.1f}%**")
    lines.append("")
    lines.append("---")
    lines.append(f"*Generated by `src/economic_sanity.py` | Run: {run_id}*")

    return "\n".join(lines)


# ── main ──────────────────────────────────────────────────────────────────────

def main(run_id: str = None):
    if run_id is None:
        run_id = _latest_run()

    print(f"Economic sanity report for: {run_id}")

    report = build_report(run_id)

    # Output directory
    out_dir = os.path.join(_ROOT, "results", "economic_sanity")
    os.makedirs(out_dir, exist_ok=True)

    ts = run_id.replace("RUN_", "")
    out_path = os.path.join(out_dir, f"ESR_{ts}.md")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"  Report -> {out_path}")
    return out_path


if __name__ == "__main__":
    run_arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(run_arg)
