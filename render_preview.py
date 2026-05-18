"""Standalone static preview renderer for the CLO Allocation Optimizer.

Replays the notebook's calculations at the provided inputs and writes every
chart into a single self-contained HTML file you can open directly.

Examples:
  python3 render_preview.py                          # defaults
  python3 render_preview.py -o out.html --portfolio 150 \
        --spreads 119 140 165 280 480
"""
from __future__ import annotations

import argparse
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from scipy.optimize import minimize

parser = argparse.ArgumentParser(description="Static preview renderer")
parser.add_argument("-o", "--output", default="preview.html",
                    help="Output HTML path")
parser.add_argument("--portfolio", type=float, default=1000.0,
                    help="Portfolio size in $mm (default: 1000)")
parser.add_argument("--spreads", type=float, nargs=5,
                    metavar=("AAA", "AA", "A", "BBB", "BB"),
                    default=[125, 175, 230, 340, 650],
                    help="Tranche spreads in bps (default: US 125/175/230/340/650)")
parser.add_argument("--equity-spread", type=float, default=1400,
                    help="Equity yield in bps (default: 1400)")
parser.add_argument("--max-capital-pct", type=float, default=5.0,
                    help="Max capital consumed as %% of portfolio (default: 5)")
parser.add_argument("--wal-profile", choices=["5nc2", "3nc1", "0nc6m"],
                    default="5nc2", help="WAL profile (default: 5nc2)")
args = parser.parse_args()

# --- Nationwide theme -------------------------------------------------------
NW = dict(
    blue="#0047BB", dark_blue="#141B4D", new_blue="#002DA2", med_blue="#1F74DB",
    light_blue="#8CC8E9", teal="#009788", mint="#6ECEB2", orange="#FF9800",
    red="#CB333B", charcoal="#171717", dark_grey="#7E7E82", fossil="#AFA9A0",
    pale_grey="#D0D3D4", purple="#890C58", lavender="#D7A9E3",
)
pio.templates["nationwide"] = go.layout.Template(
    layout=go.Layout(
        font=dict(family="Arial", color="#171717"),
        title_font=dict(family="Georgia", size=20, color="#141B4D"),
        colorway=[NW["blue"], NW["dark_blue"], NW["teal"], NW["orange"],
                  NW["red"], NW["med_blue"], NW["light_blue"], NW["mint"],
                  NW["dark_grey"], NW["fossil"]],
        plot_bgcolor="#FAFAFA", paper_bgcolor="white",
        xaxis=dict(gridcolor="#D0D3D4"), yaxis=dict(gridcolor="#D0D3D4"),
    )
)
pio.templates.default = "nationwide"

# --- Inputs (US CLO; spreads/portfolio/profile from CLI args) -------------
REGION = "US CLO"
CAP_FRAMEWORK = "Basel III Standardized"
DEFAULT_RATE_PCT = 2.0
RECOVERY_RATE_PCT = 65.0
SOFR = 3.62
EURIBOR = 2.11
BASIS_SWAP = 32.6
WAL_PROFILE = args.wal_profile
PORTFOLIO_MM = args.portfolio
MAX_CAP_MM = args.portfolio * args.max_capital_pct / 100.0
USER_SPREADS = list(args.spreads) + [args.equity_spread]  # AAA, AA, A, BBB, BB, Equity

eur_defaults = pd.DataFrame({
    "Tranche": ["AAA", "AA", "A", "BBB", "BB", "Equity"],
    "Spread": [127, 185, 240, 350, 650, 1600],
    "Subordination": [38.0, 28.0, 21.0, 13.0, 9.0, 0.0],
    "WAL": [5.0, 6.0, 7.0, 7.0, 7.0, 0.0],
    "Basel III Standardized": [0.56, 0.80, 2.00, 5.00, 12.00, 100.0],
    "Basel III IRB": [0.40, 0.65, 1.60, 4.20, 10.00, 100.0],
    "Solvency II Current": [1.10, 1.60, 3.50, 8.00, 18.00, 100.0],
    "Solvency II Post-Reform (Jan 2027)": [0.22, 0.45, 1.20, 3.50, 10.00, 100.0],
})
us_defaults = pd.DataFrame({
    "Tranche": ["AAA", "AA", "A", "BBB", "BB", "Equity"],
    "Spread": [125, 175, 230, 340, 650, 1400],
    "Subordination": [36.0, 26.0, 18.0, 11.0, 7.0, 0.0],
    "WAL": [5.0, 6.0, 7.0, 7.0, 7.0, 0.0],
    "Basel III Standardized": [0.56, 0.80, 2.00, 5.00, 12.00, 100.0],
    "Basel III IRB": [0.40, 0.65, 1.60, 4.20, 10.00, 100.0],
    "Solvency II Current": [1.10, 1.60, 3.50, 8.00, 18.00, 100.0],
    "Solvency II Post-Reform (Jan 2027)": [0.22, 0.45, 1.20, 3.50, 10.00, 100.0],
})

hedged_pickup_bps = 20.0 + (32.6 - BASIS_SWAP) * 0.4

# Apply WAL profile
_wal_profiles = {
    "5nc2": [5.0, 6.0, 7.0, 7.5, 7.5, 0.0],
    "3nc1": [3.5, 4.5, 5.5, 6.0, 6.0, 0.0],
    "0nc6m": [1.5, 2.5, 3.5, 4.0, 4.0, 0.0],
}
us_defaults["WAL"] = _wal_profiles[WAL_PROFILE]

# Apply user-supplied spreads
us_defaults["Spread"] = USER_SPREADS

# --- Section 1: ROC by tranche (US CLO) ------------------------------------
df = us_defaults.copy()
df["Capital Charge %"] = df[CAP_FRAMEWORK]
base_el_bps = DEFAULT_RATE_PCT * (1.0 - RECOVERY_RATE_PCT / 100.0) * 10_000.0
sub_factor = (1.0 - df["Subordination"] / 100.0).clip(lower=0.05)
df["Expected Loss (bps)"] = (base_el_bps * sub_factor).round(1)
df["ROC"] = (df["Spread"] / df["Capital Charge %"]).round(1)
df["Loss-Adj ROC"] = ((df["Spread"] - df["Expected Loss (bps)"]).clip(lower=0)
                     / df["Capital Charge %"]).round(1)

fig_roc = go.Figure()
fig_roc.add_trace(go.Bar(name="ROC (raw)", x=df["Tranche"], y=df["ROC"],
                         marker_color=NW["blue"], text=df["ROC"], textposition="outside"))
fig_roc.add_trace(go.Bar(name="Loss-Adjusted ROC", x=df["Tranche"], y=df["Loss-Adj ROC"],
                         marker_color=NW["teal"], text=df["Loss-Adj ROC"], textposition="outside"))
_sp = USER_SPREADS
fig_roc.update_layout(
    barmode="group",
    title=(f"Section 1 — Return on Capital by Tranche ({REGION}, {WAL_PROFILE})<br>"
           f"<sub>Spreads: AAA {_sp[0]:.0f} / AA {_sp[1]:.0f} / A {_sp[2]:.0f} / "
           f"BBB {_sp[3]:.0f} / BB {_sp[4]:.0f} bps · Portfolio ${PORTFOLIO_MM:.0f}mm</sub>"),
    yaxis_title="ROC (bps spread per 1% capital)",
    xaxis_title="Tranche", height=460,
)

# --- Section 2: Curve steepness --------------------------------------------
hist = pd.DataFrame({
    "date": pd.to_datetime([
        "2020-03-31", "2020-06-30", "2020-12-31", "2021-06-30", "2021-12-31",
        "2022-06-30", "2022-12-31", "2023-06-30", "2023-12-31", "2024-06-30",
        "2024-12-31", "2025-06-30", "2025-12-31", "2026-03-31",
    ]),
    "AAA": [230, 185, 145, 100,  98, 140, 175, 160, 145, 132, 125, 120, 122, 125],
    "AA":  [370, 295, 230, 150, 140, 210, 270, 245, 215, 195, 185, 170, 172, 175],
    "A":   [520, 420, 320, 215, 200, 300, 375, 345, 300, 270, 250, 230, 235, 230],
    "BBB": [750, 610, 480, 340, 310, 450, 540, 500, 430, 390, 360, 330, 335, 340],
    "BB":  [1150, 1000, 800, 620, 575, 770, 870, 820, 720, 670, 650, 630, 640, 650],
})
tranches_l = ["AAA", "AA", "A", "BBB", "BB"]
current = np.array(USER_SPREADS[:5], dtype=float)  # user-supplied spreads
six_mo = hist[tranches_l].iloc[-3].values
one_yr = hist[tranches_l].iloc[-5].values
mins = hist[tranches_l].min().values
maxs = hist[tranches_l].max().values

fig_curve = go.Figure()
fig_curve.add_trace(go.Scatter(x=tranches_l + tranches_l[::-1],
                               y=list(maxs) + list(mins[::-1]),
                               fill="toself", fillcolor="rgba(140,200,233,0.25)",
                               line=dict(color="rgba(0,0,0,0)"),
                               name="Historical min–max range", hoverinfo="skip"))
fig_curve.add_trace(go.Scatter(x=tranches_l, y=one_yr, mode="lines+markers",
                               name="1yr ago", line=dict(color=NW["fossil"], dash="dot", width=2)))
fig_curve.add_trace(go.Scatter(x=tranches_l, y=six_mo, mode="lines+markers",
                               name="6mo ago", line=dict(color=NW["teal"], dash="dash", width=2)))
fig_curve.add_trace(go.Scatter(x=tranches_l, y=current, mode="lines+markers+text",
                               name="Current", line=dict(color=NW["blue"], width=4),
                               marker=dict(size=10),
                               text=[f"{v:.0f}" for v in current], textposition="top center"))
fig_curve.update_layout(title="Section 2 — Spread Curve: Current vs Historical",
                       xaxis_title="Tranche", yaxis_title="Spread (bps)", height=440)

diff = hist["BB"] - hist["AAA"]
p25, p50, p75 = np.percentile(diff, [25, 50, 75])
fig_steep = go.Figure()
fig_steep.add_trace(go.Scatter(x=hist["date"], y=diff, mode="lines+markers",
                              name="AAA→BB spread", line=dict(color=NW["blue"], width=3)))
for pv, lbl, col in [(p25, "25th pct", NW["red"]), (p50, "Median", NW["dark_grey"]),
                     (p75, "75th pct", NW["teal"])]:
    fig_steep.add_hline(y=pv, line=dict(color=col, dash="dash"),
                       annotation_text=f"{lbl}: {pv:.0f}", annotation_position="right")
fig_steep.update_layout(title="Curve Steepness Through Time (AAA→BB)",
                       yaxis_title="AAA→BB Spread Differential (bps)",
                       xaxis_title="Date", height=380)

# --- Section 3: Optimal allocation pie (US Only, $1bn) ---------------------
tranche_order = ["AAA", "AA", "A", "BBB", "BB", "Equity"]
odf = us_defaults.set_index("Tranche").loc[tranche_order]
spreads = odf["Spread"].values.astype(float)
caps = odf[CAP_FRAMEWORK].values.astype(float)
wals = odf["WAL"].values.astype(float)

def neg_roc(w):
    return -float(np.sum(w * spreads / np.maximum(caps, 1e-6)))

bnds = [(0.0, 1.0)] * 6
# Auto-pick a WAL band that overlaps the chosen profile's WALs
_nzw = wals[wals > 0]
_wal_lo = float(_nzw.min()) if len(_nzw) else 0.0
_wal_hi = float(_nzw.max()) if len(_nzw) else 8.0
cons = [
    {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
    {"type": "ineq", "fun": lambda w: _wal_hi - float(np.sum(w * wals))},
    {"type": "ineq", "fun": lambda w: float(np.sum(w * wals)) - _wal_lo},
    {"type": "ineq", "fun": lambda w: MAX_CAP_MM - float(np.sum(w * caps / 100.0)) * PORTFOLIO_MM},
]
res = minimize(neg_roc, np.array([1/6]*6), method="SLSQP", bounds=bnds, constraints=cons,
               options={"maxiter": 400, "ftol": 1e-8})
opt_w = np.clip(res.x if res.success else np.array([1/6]*6), 0, 1)
opt_w = opt_w / max(opt_w.sum(), 1e-9)

nz = opt_w > 1e-4
fig_pie = go.Figure(data=[go.Pie(
    labels=[t for t, m in zip(tranche_order, nz) if m],
    values=[float(w) for w, m in zip(opt_w, nz) if m],
    hole=0.4,
    marker=dict(colors=[NW["blue"], NW["dark_blue"], NW["teal"], NW["orange"], NW["red"], NW["purple"]]),
)])
port_roc = float(np.sum(opt_w * spreads / np.maximum(caps, 1e-6)))
port_wal = float(np.sum(opt_w * wals))
port_cap = float(np.sum(opt_w * caps / 100.0)) * PORTFOLIO_MM
# Dollar allocation per tranche
alloc_mm = opt_w * PORTFOLIO_MM
fig_pie.update_layout(
    title=(f"Section 3 — Optimal Allocation (${PORTFOLIO_MM:.0f}mm {REGION}, "
           f"{WAL_PROFILE}, ≤${MAX_CAP_MM:.1f}mm capital)<br>"
           f"<sub>Portfolio ROC {port_roc:.1f} | WAL {port_wal:.2f}y | "
           f"Capital consumed ${port_cap:.1f}mm</sub>"),
    height=460,
)

# --- Section 4: Cross-region comparison ------------------------------------
cmp_df = pd.DataFrame({
    "Tranche": eur_defaults["Tranche"],
    "EUR Spread": eur_defaults["Spread"],
    "US Spread": us_defaults["Spread"],
    "EUR Hedged Spread": eur_defaults["Spread"] + hedged_pickup_bps,
})
fig_cmp = go.Figure()
fig_cmp.add_trace(go.Bar(name="EUR (raw)", x=cmp_df["Tranche"], y=cmp_df["EUR Spread"],
                        marker_color=NW["dark_blue"], text=cmp_df["EUR Spread"], textposition="outside"))
fig_cmp.add_trace(go.Bar(name="US (raw)", x=cmp_df["Tranche"], y=cmp_df["US Spread"],
                        marker_color=NW["med_blue"], text=cmp_df["US Spread"], textposition="outside"))
fig_cmp.add_trace(go.Bar(name="EUR (hedged → USD)", x=cmp_df["Tranche"], y=cmp_df["EUR Hedged Spread"],
                        marker_color=NW["orange"], text=cmp_df["EUR Hedged Spread"], textposition="outside"))
fig_cmp.update_layout(barmode="group",
                    title="Section 4 — EUR vs US Spreads (Hedged Equivalent)",
                    yaxis_title="Spread (bps)", xaxis_title="Tranche", height=440)

# --- Section 5: Stress (Mar 2026 replay, US) -------------------------------
cur = us_defaults.set_index("Tranche").loc[tranche_order, "Spread"].values.astype(float)
stressed = np.array([132, 205, 280, 420, 750, cur[5]])
caps_v = us_defaults.set_index("Tranche").loc[tranche_order, CAP_FRAMEWORK].values.astype(float)
base_roc = cur / np.maximum(caps_v, 1e-6)
stressed_roc = stressed / np.maximum(caps_v, 1e-6)

fig_stress = go.Figure()
fig_stress.add_trace(go.Bar(name="Base ROC", x=tranche_order, y=base_roc,
                           marker_color=NW["blue"], text=np.round(base_roc, 1), textposition="outside"))
fig_stress.add_trace(go.Bar(name="Stressed ROC (Mar 2026 replay)", x=tranche_order, y=stressed_roc,
                           marker_color=NW["red"], text=np.round(stressed_roc, 1), textposition="outside"))
fig_stress.update_layout(barmode="group",
                       title="Section 5 — Stress Scenario: Mar 2026 Geopolitical Replay",
                       yaxis_title="ROC (bps per 1% capital)", xaxis_title="Tranche", height=420)

# --- Section 6: Manager scatter + heatmap ----------------------------------
managers = pd.DataFrame({
    "name": ["Redding Ridge (Apollo)", "Blackstone (GSO)", "PGIM", "Tikehau", "Hayfin",
             "Permira", "Ares", "Barings"],
    "warf": [2728, 2979, 2858, 2876, 2846, 2924, 2971, 2855],
    "was_bps": [337, 354, 390, 379, 342, 359, 370, 354],
    "ccc_pct": [1.6, 4.1, 4.7, 1.6, 3.3, 2.4, 2.8, 3.2],
    "jr_oc_pct": [5.78, 4.62, 3.48, 3.31, 3.65, 4.20, 3.68, 2.71],
    "tier": [1, 1, 2, 2, 2, 2, 3, 3],
    "eu_aum_bn": [9.83, 8.14, 6.07, 5.58, 4.62, 4.05, 3.80, 3.28],
})
def norm(x, lo, hi, invert=False):
    v = max(min((x - lo) / (hi - lo), 1.0), 0.0) * 100.0
    return 100.0 - v if invert else v
managers["quality_score"] = [
    round(0.4 * norm(r.jr_oc_pct, 2.5, 6.0)
          + 0.3 * norm(r.ccc_pct, 0.0, 7.5, invert=True)
          + 0.3 * norm(r.warf, 2600, 3100, invert=True), 1)
    for r in managers.itertuples()
]

tier_colors = {1: NW["blue"], 2: NW["teal"], 3: NW["orange"], 4: NW["red"]}
fig_mgr = go.Figure()
for t, sub in managers.groupby("tier"):
    fig_mgr.add_trace(go.Scatter(
        x=sub["quality_score"], y=sub["was_bps"], mode="markers+text",
        marker=dict(size=sub["eu_aum_bn"] * 4.0, color=tier_colors[int(t)],
                    line=dict(width=1, color=NW["charcoal"])),
        name=f"Tier {int(t)}",
        text=sub["name"], textposition="top center", textfont=dict(size=10),
    ))
fig_mgr.update_layout(title="Section 6 — Manager Quality vs Spread (bubble = EU AUM €bn)",
                    xaxis_title="Quality Score (0–100)", yaxis_title="WAS (bps)", height=480)

adj = ((managers["quality_score"] - 50.0) / 500.0).values
spreads_b = us_defaults.set_index("Tranche").loc[tranche_order, "Spread"].values.astype(float)
caps_b = us_defaults.set_index("Tranche").loc[tranche_order, CAP_FRAMEWORK].values.astype(float)
base_roc_v = spreads_b / np.maximum(caps_b, 1e-6)
matrix = np.outer(1.0 + adj, base_roc_v)
fig_hm = go.Figure(data=go.Heatmap(z=matrix, x=tranche_order, y=managers["name"].tolist(),
                                   colorscale="Blues", text=np.round(matrix, 1),
                                   texttemplate="%{text}", colorbar=dict(title="ROC")))
fig_hm.update_layout(title="Manager-Adjusted ROC by Tranche",
                    xaxis_title="Tranche", yaxis_title="Manager", height=440)

# --- Section 7: Correlation + efficient frontier ---------------------------
labels = ["US AAA", "US AA", "US A", "EUR AAA", "EUR AA", "EUR A"]
corr_matrix = np.array([
    [1.00, 0.95, 0.94, 0.87, 0.84, 0.76],
    [0.95, 1.00, 0.97, 0.85, 0.84, 0.72],
    [0.94, 0.97, 1.00, 0.84, 0.81, 0.75],
    [0.87, 0.85, 0.84, 1.00, 0.97, 0.91],
    [0.84, 0.84, 0.81, 0.97, 1.00, 0.91],
    [0.76, 0.72, 0.75, 0.91, 0.91, 1.00],
])
returns = np.array([4.89, 5.45, 5.95, 3.10, 3.80, 4.50]) / 100.0
vols = np.array([1.47, 2.39, 3.09, 1.97, 3.58, 5.86]) / 100.0
cov_matrix = np.outer(vols, vols) * corr_matrix

fig_corr = go.Figure(data=go.Heatmap(z=corr_matrix, x=labels, y=labels,
                                     text=corr_matrix, texttemplate="%{text:.2f}",
                                     colorscale="Blues", zmin=0.6, zmax=1.0))
fig_corr.update_layout(title="Section 7 — US ↔ EUR Tranche Correlation (5yr monthly)", height=440)

rng = np.random.default_rng(42)
weights = rng.dirichlet(np.ones(6), size=5000)
weights = np.clip(weights, 0, 0.5)
weights = weights / weights.sum(axis=1, keepdims=True)
port_ret = weights @ returns
port_vol = np.sqrt(np.einsum("ij,jk,ik->i", weights, cov_matrix, weights))
sharpe = port_ret / np.where(port_vol > 0, port_vol, 1e-6)

fig_ef = go.Figure()
fig_ef.add_trace(go.Scatter(x=port_vol * 100, y=port_ret * 100, mode="markers",
                          marker=dict(size=4, color=sharpe, colorscale="Blues",
                                      colorbar=dict(title="Sharpe"), opacity=0.6),
                          name="Random portfolios", hoverinfo="skip"))
target_rets = np.linspace(returns.min() + 1e-4, returns.max() - 1e-4, 30)
fv, fr = [], []
for tr in target_rets:
    def obj(w):
        return float(w @ cov_matrix @ w)
    c = [{"type": "eq", "fun": lambda w: w.sum() - 1.0},
         {"type": "eq", "fun": lambda w, tr=tr: float(w @ returns) - tr}]
    r = minimize(obj, np.array([1/6]*6), method="SLSQP",
                 bounds=[(0, 0.5)]*6, constraints=c, options={"maxiter": 300})
    if r.success:
        fv.append(float(np.sqrt(r.fun)) * 100)
        fr.append(tr * 100)
fig_ef.add_trace(go.Scatter(x=fv, y=fr, mode="lines",
                          line=dict(color=NW["dark_blue"], width=3),
                          name="Efficient frontier"))
cur_w = np.array([0.70, 0.25, 0.05, 0.0, 0.0, 0.0])
eur_w = np.array([0.0, 0.0, 0.0, 0.70, 0.25, 0.05])
combo_w = (8.5/9.5) * cur_w + (1.0/9.5) * eur_w
for w, name, color in [(cur_w, "Current US-only", NW["orange"]),
                       (eur_w, "Proposed EUR-only", NW["red"]),
                       (combo_w, "Combined US + EUR", NW["teal"])]:
    fig_ef.add_trace(go.Scatter(
        x=[float(np.sqrt(w @ cov_matrix @ w)) * 100],
        y=[float(w @ returns) * 100],
        mode="markers+text",
        marker=dict(size=14, color=color, symbol="diamond",
                    line=dict(width=2, color=NW["charcoal"])),
        text=[name], textposition="top right", name=name,
    ))
fig_ef.update_layout(title="Efficient Frontier (5yr return × vol)",
                   xaxis_title="Volatility (% annualized)",
                   yaxis_title="Return (% annualized)", height=520)

# --- Bundle to single HTML --------------------------------------------------
def render_table_html(df: pd.DataFrame) -> str:
    return df.to_html(index=False, classes="tbl", border=0)

alloc_df = pd.DataFrame({
    "Tranche": tranche_order,
    "Weight %": (opt_w * 100).round(1),
    "Allocation ($mm)": np.round(alloc_mm, 1),
    "Capital ($mm)": np.round(opt_w * caps / 100.0 * PORTFOLIO_MM, 2),
})
alloc_df = alloc_df[alloc_df["Weight %"] > 0.05].reset_index(drop=True)
totals = pd.DataFrame({
    "Tranche": ["TOTAL"],
    "Weight %": [round(alloc_df["Weight %"].sum(), 1)],
    "Allocation ($mm)": [round(alloc_df["Allocation ($mm)"].sum(), 1)],
    "Capital ($mm)": [round(alloc_df["Capital ($mm)"].sum(), 2)],
})
alloc_df = pd.concat([alloc_df, totals], ignore_index=True)

sections = [
    (f"Section 1 — Deal-Level ROC Analysis ({REGION}, {WAL_PROFILE})", [fig_roc],
     [("Tranche ROC table",
       df[["Tranche", "Spread", "Capital Charge %", "Subordination",
           "WAL", "Expected Loss (bps)", "ROC", "Loss-Adj ROC"]])]),
    (f"Section 2 — Curve Steepness Dashboard ({REGION})", [fig_curve, fig_steep], []),
    (f"Section 3 — Allocation Optimizer (${PORTFOLIO_MM:.0f}mm, {WAL_PROFILE}, "
     f"≤${MAX_CAP_MM:.1f}mm capital)", [fig_pie],
     [("Optimal allocation ($mm)", alloc_df)]),
    ("Section 5 — Stress: Mar 2026 Replay", [fig_stress], []),
    ("Section 4 — Cross-Region Comparison (European overlay)", [fig_cmp], []),
    ("Section 6 — Manager Quality Overlay (European overlay)", [fig_mgr, fig_hm], []),
    ("Section 7 — Correlation & Efficient Frontier (European overlay)",
     [fig_corr, fig_ef], []),
]

html_parts = ["""<!doctype html>
<html><head><meta charset="utf-8"><title>CLO Allocation Optimizer — Preview</title>
<style>
  body { font-family: Arial, sans-serif; color:#171717; max-width:1100px; margin:24px auto; padding:0 16px; background:#fafafa;}
  h1 { font-family: Georgia, serif; color:#141B4D; border-bottom:3px solid #0047BB; padding-bottom:6px;}
  h2 { font-family: Georgia, serif; color:#141B4D; margin-top:48px;}
  .note { background:#e8f0fb; border-left:4px solid #0047BB; padding:10px 14px; margin:14px 0; border-radius:4px;}
  .tbl { border-collapse:collapse; margin:14px 0; font-size:13px;}
  .tbl th, .tbl td { padding:6px 10px; border:1px solid #D0D3D4; text-align:right;}
  .tbl th { background:#0047BB; color:white; font-weight:600;}
  .tbl td:first-child, .tbl th:first-child { text-align:left;}
</style></head><body>
<h1>CLO Allocation Optimizer — Static Preview</h1>
<div class="note">
<b>US CLO focus.</b> Region: <b>{REGION}</b> · Capital framework: <b>Basel III Standardized</b> ·
WAL profile: <b>{WAL_PROFILE}</b> · Default rate <b>{DEFAULT_RATE_PCT}%</b> · Recovery <b>{RECOVERY_RATE_PCT}%</b>.
<br>
Portfolio: <b>${PORTFOLIO_MM:.0f}mm</b>, max capital consumed: <b>${MAX_CAP_MM:.1f}mm</b>.
<br>
Spreads (bps): AAA <b>{SP0:.0f}</b> · AA <b>{SP1:.0f}</b> · A <b>{SP2:.0f}</b> · BBB <b>{SP3:.0f}</b> · BB <b>{SP4:.0f}</b>.
<br><br>
Sections 4 (cross-region comparison), 6 (manager quality), and 7 (correlation / efficient frontier)
are <b>European overlay</b> panels — collapsed by default in the live app, shown here for reference.
<br><br>
The live app is fully reactive: spreads, WAL profile, portfolio size, constraint presets all flow
through every chart. Run <code>marimo run clo_allocation_optimizer.py</code> locally.
</div>""".replace("{REGION}", REGION).replace("{WAL_PROFILE}", WAL_PROFILE)
       .replace("{DEFAULT_RATE_PCT}", f"{DEFAULT_RATE_PCT}")
       .replace("{RECOVERY_RATE_PCT}", f"{RECOVERY_RATE_PCT}")
       .replace("{PORTFOLIO_MM}", f"{PORTFOLIO_MM:.0f}")
       .replace("{MAX_CAP_MM}", f"{MAX_CAP_MM:.1f}")
       .replace("{SP0}", f"{USER_SPREADS[0]:.0f}")
       .replace("{SP1}", f"{USER_SPREADS[1]:.0f}")
       .replace("{SP2}", f"{USER_SPREADS[2]:.0f}")
       .replace("{SP3}", f"{USER_SPREADS[3]:.0f}")
       .replace("{SP4}", f"{USER_SPREADS[4]:.0f}")
]

include_js = True
for title, figs, tables in sections:
    html_parts.append(f"<h2>{title}</h2>")
    for f in figs:
        html_parts.append(f.to_html(full_html=False,
                                    include_plotlyjs="cdn" if include_js else False))
        include_js = False
    for tname, tdf in tables:
        html_parts.append(f"<h3 style='font-family:Georgia,serif;color:#141B4D;'>{tname}</h3>")
        html_parts.append(render_table_html(tdf))

html_parts.append("</body></html>")

with open(args.output, "w") as f:
    f.write("\n".join(html_parts))
print(f"wrote {args.output}")
