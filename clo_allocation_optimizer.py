import marimo

__generated_with = "0.23.6"
app = marimo.App(width="medium", app_title="CLO Allocation Optimizer")


@app.cell
def _():
    import marimo as mo
    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go
    import plotly.express as px
    import plotly.io as pio
    from scipy.optimize import minimize, linprog
    return go, linprog, minimize, mo, np, pd, pio, px


@app.cell
def _(go, pio):
    nw_template = go.layout.Template(
        layout=go.Layout(
            font=dict(family="Arial", color="#171717"),
            title_font=dict(family="Georgia", size=20, color="#141B4D"),
            colorway=[
                "#0047BB", "#141B4D", "#009788", "#FF9800", "#CB333B",
                "#1F74DB", "#8CC8E9", "#6ECEB2", "#7E7E82", "#AFA9A0",
            ],
            plot_bgcolor="#FAFAFA",
            paper_bgcolor="white",
            xaxis=dict(gridcolor="#D0D3D4"),
            yaxis=dict(gridcolor="#D0D3D4"),
            legend=dict(bgcolor="rgba(255,255,255,0.8)"),
        )
    )
    pio.templates["nationwide"] = nw_template
    pio.templates.default = "nationwide"

    NW = dict(
        blue="#0047BB",
        dark_blue="#141B4D",
        new_blue="#002DA2",
        med_blue="#1F74DB",
        light_blue="#8CC8E9",
        teal="#009788",
        mint="#6ECEB2",
        orange="#FF9800",
        red="#CB333B",
        charcoal="#171717",
        dark_grey="#7E7E82",
        fossil="#AFA9A0",
        pale_grey="#D0D3D4",
        purple="#890C58",
        lavender="#D7A9E3",
    )
    return (NW,)


@app.cell
def _(mo):
    mo.md(
        """
        # CLO Allocation Optimizer
        ### US-focused ROC, curve-steepness, and portfolio optimization
        *European tranches, managers, and cross-region analytics are available via the "European overlay" toggles inside the relevant sections.*

        ---
        """
    )
    return


@app.cell
def _(mo):
    mo.md("## Section 1 — Deal-Level ROC Analysis")
    return


@app.cell
def _(mo):
    region = mo.ui.dropdown(
        options=["US CLO", "EUR CLO", "Combined"],
        value="US CLO",
        label="Region (drives historical curve, equity yield, etc.)",
    )
    capital_framework = mo.ui.dropdown(
        options=[
            "Basel III Standardized",
            "Basel III IRB",
            "Solvency II Current",
            "Solvency II Post-Reform (Jan 2027)",
            "Custom",
        ],
        value="Basel III Standardized",
        label="Capital Framework",
    )
    default_rate = mo.ui.slider(
        start=0.0, stop=10.0, step=0.1, value=2.0,
        label="Annual Default Rate (%)",
        show_value=True,
    )
    recovery_rate = mo.ui.slider(
        start=0.0, stop=100.0, step=1.0, value=65.0,
        label="Recovery Rate (%)",
        show_value=True,
    )

    # Deal-specific spreads (defaults are current US CLO market)
    spread_aaa = mo.ui.number(value=125, step=1, label="AAA")
    spread_aa = mo.ui.number(value=175, step=1, label="AA")
    spread_a = mo.ui.number(value=230, step=1, label="A")
    spread_bbb = mo.ui.number(value=340, step=1, label="BBB")
    spread_bb = mo.ui.number(value=650, step=1, label="BB")
    spread_eq = mo.ui.number(value=1400, step=10, label="Equity")

    # Subordination and WAL — defaults are US; user can override
    sub_aaa = mo.ui.number(value=36.0, step=0.5, label="AAA")
    sub_aa = mo.ui.number(value=26.0, step=0.5, label="AA")
    sub_a = mo.ui.number(value=18.0, step=0.5, label="A")
    sub_bbb = mo.ui.number(value=11.0, step=0.5, label="BBB")
    sub_bb = mo.ui.number(value=7.0, step=0.5, label="BB")

    wal_profile = mo.ui.dropdown(
        options=[
            "5nc2 (new-issue, full 5y reinvest / 2y non-call)",
            "3nc1 (shorter 3y reinvest / 1y non-call)",
            "0nc6m (post-reinvest, 6mo to call — short/amortizing)",
            "Custom (use inputs below)",
        ],
        value="5nc2 (new-issue, full 5y reinvest / 2y non-call)",
        label="WAL profile",
    )

    wal_aaa = mo.ui.number(value=5.0, step=0.25, label="AAA")
    wal_aa = mo.ui.number(value=6.0, step=0.25, label="AA")
    wal_a = mo.ui.number(value=7.0, step=0.25, label="A")
    wal_bbb = mo.ui.number(value=7.0, step=0.25, label="BBB")
    wal_bb = mo.ui.number(value=7.0, step=0.25, label="BB")

    # EUR-specific cross-currency inputs (collapsed by default)
    sofr = mo.ui.number(value=3.62, step=0.01, label="3mo SOFR (%)")
    euribor = mo.ui.number(value=2.11, step=0.01, label="3mo Euribor (%)")
    basis_swap = mo.ui.number(value=32.6, step=0.1, label="2yr basis swap (bps)")

    mo.vstack([
        mo.md("**Region, capital framework, and credit assumptions**"),
        mo.hstack([region, capital_framework], justify="start", gap=1.0),
        mo.hstack([default_rate, recovery_rate], justify="start", gap=1.0),
        mo.md("**Tranche spreads (bps over reference rate) — edit to match your deal**"),
        mo.hstack([spread_aaa, spread_aa, spread_a, spread_bbb, spread_bb, spread_eq],
                  justify="start", gap=0.5),
        mo.md("**WAL profile** — pick a CLO structure or use Custom to enter tranche-by-tranche WALs below"),
        wal_profile,
        mo.accordion({
            "Override subordination & WAL (per tranche)": mo.vstack([
                mo.md("*Subordination % (credit enhancement below each tranche)*"),
                mo.hstack([sub_aaa, sub_aa, sub_a, sub_bbb, sub_bb], justify="start", gap=0.5),
                mo.md("*Per-tranche WAL (yr) — only used when WAL profile = Custom*"),
                mo.hstack([wal_aaa, wal_aa, wal_a, wal_bbb, wal_bb], justify="start", gap=0.5),
            ]),
            "European overlay — cross-currency basis (for hedged EUR ROC)": mo.vstack([
                mo.md("*Only used when region = EUR CLO or Combined*"),
                mo.hstack([sofr, euribor, basis_swap], justify="start", gap=1.0),
            ]),
        }),
    ])
    return (
        basis_swap, capital_framework, default_rate, euribor, recovery_rate, region, sofr,
        spread_aaa, spread_aa, spread_a, spread_bbb, spread_bb, spread_eq,
        sub_aaa, sub_aa, sub_a, sub_bbb, sub_bb,
        wal_aaa, wal_aa, wal_a, wal_bbb, wal_bb, wal_profile,
    )


@app.cell
def _(pd):
    eur_defaults = pd.DataFrame({
        "Tranche": ["AAA", "AA", "A", "BBB", "BB", "Equity"],
        "Spread": [127, 185, 240, 350, 650, 1600],
        "Subordination": [38.0, 28.0, 21.0, 13.0, 9.0, 0.0],
        "WAL": [5.0, 6.0, 7.0, 7.0, 7.0, 0.0],
        "Basel III Standardized": [0.56, 0.80, 2.00, 5.00, 12.00, 100.0],
        "Basel III IRB": [0.40, 0.65, 1.60, 4.20, 10.00, 100.0],
        "Solvency II Current": [1.10, 1.60, 3.50, 8.00, 18.00, 100.0],
        "Solvency II Post-Reform (Jan 2027)": [0.22, 0.45, 1.20, 3.50, 10.00, 100.0],
        "Custom": [0.56, 0.80, 2.00, 5.00, 12.00, 100.0],
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
        "Custom": [0.56, 0.80, 2.00, 5.00, 12.00, 100.0],
    })
    return eur_defaults, us_defaults


@app.cell
def _(
    eur_defaults, region, us_defaults,
    spread_aaa, spread_aa, spread_a, spread_bbb, spread_bb, spread_eq,
    sub_aaa, sub_aa, sub_a, sub_bbb, sub_bb,
    wal_aaa, wal_aa, wal_a, wal_bbb, wal_bb,
    wal_profile,
):
    # Start from the region's capital-charge columns / equity defaults
    if region.value == "EUR CLO":
        base_df = eur_defaults.copy()
    elif region.value == "US CLO":
        base_df = us_defaults.copy()
    else:
        base_df = eur_defaults.copy()
        for _col in ["Spread", "Subordination", "WAL"]:
            base_df[_col] = (eur_defaults[_col] + us_defaults[_col]) / 2

    # WAL profile presets (AAA, AA, A, BBB, BB, Equity)
    if wal_profile.value.startswith("5nc2"):
        effective_wals = [5.0, 6.0, 7.0, 7.5, 7.5, 0.0]
    elif wal_profile.value.startswith("3nc1"):
        effective_wals = [3.5, 4.5, 5.5, 6.0, 6.0, 0.0]
    elif wal_profile.value.startswith("0nc6m"):
        effective_wals = [1.5, 2.5, 3.5, 4.0, 4.0, 0.0]
    else:  # Custom
        effective_wals = [wal_aaa.value, wal_aa.value, wal_a.value,
                          wal_bbb.value, wal_bb.value, 0.0]

    user_spreads = [spread_aaa.value, spread_aa.value, spread_a.value,
                    spread_bbb.value, spread_bb.value, spread_eq.value]
    user_subs = [sub_aaa.value, sub_aa.value, sub_a.value,
                 sub_bbb.value, sub_bb.value, 0.0]
    base_df["Spread"] = user_spreads
    base_df["Subordination"] = user_subs
    base_df["WAL"] = effective_wals
    return (base_df,)


@app.cell
def _(basis_swap, euribor, sofr):
    rate_diff_bps = (sofr.value - euribor.value) * 100.0
    # ~20 bps base pickup at neutral basis (32.6 bps), with sensitivity to current basis
    hedged_pickup_bps = 20.0 + (32.6 - basis_swap.value) * 0.4
    return hedged_pickup_bps, rate_diff_bps


@app.cell
def _(base_df, capital_framework, default_rate, hedged_pickup_bps, recovery_rate, region):
    cap_col = capital_framework.value
    df = base_df.copy()
    df["Capital Charge %"] = df[cap_col]

    # Subordination-adjusted expected loss (bps):
    # ann default rate × (1 - recovery) × notional, scaled by how much subordination absorbs.
    # We treat anything below subordination as zero EL up to subordination, then linear above.
    base_el_bps = default_rate.value * (1.0 - recovery_rate.value / 100.0) * 10_000.0
    sub_factor = (1.0 - (df["Subordination"] / 100.0)).clip(lower=0.05)
    df["Expected Loss (bps)"] = (base_el_bps * sub_factor).round(1)

    # Hedged spread (EUR only adds pickup)
    if region.value == "EUR CLO":
        df["Hedged Spread"] = df["Spread"] + hedged_pickup_bps
    elif region.value == "Combined":
        df["Hedged Spread"] = df["Spread"] + hedged_pickup_bps / 2.0
    else:
        df["Hedged Spread"] = df["Spread"]

    # ROC = Spread (bps) / Capital Charge (%). Result is bps per 1% capital.
    df["ROC"] = (df["Spread"] / df["Capital Charge %"]).round(1)
    df["Loss-Adj ROC"] = (
        (df["Spread"] - df["Expected Loss (bps)"]).clip(lower=0) / df["Capital Charge %"]
    ).round(1)
    df["Hedged ROC"] = (df["Hedged Spread"] / df["Capital Charge %"]).round(1)

    roc_df = df[
        ["Tranche", "Spread", "Hedged Spread", "Capital Charge %", "Subordination",
         "WAL", "Expected Loss (bps)", "ROC", "Loss-Adj ROC", "Hedged ROC"]
    ]
    return cap_col, df, roc_df


@app.cell
def _(NW, df, go, region):
    fig_roc = go.Figure()
    fig_roc.add_trace(go.Bar(
        name="ROC (raw)", x=df["Tranche"], y=df["ROC"],
        marker_color=NW["blue"], text=df["ROC"], textposition="outside",
    ))
    fig_roc.add_trace(go.Bar(
        name="Loss-Adjusted ROC", x=df["Tranche"], y=df["Loss-Adj ROC"],
        marker_color=NW["teal"], text=df["Loss-Adj ROC"], textposition="outside",
    ))
    if region.value in ("EUR CLO", "Combined"):
        fig_roc.add_trace(go.Bar(
            name="Hedged ROC", x=df["Tranche"], y=df["Hedged ROC"],
            marker_color=NW["orange"], text=df["Hedged ROC"], textposition="outside",
        ))
    fig_roc.update_layout(
        barmode="group",
        title=f"Return on Capital by Tranche — {region.value}",
        yaxis_title="ROC (bps spread per 1% capital)",
        xaxis_title="Tranche",
        height=460,
    )
    return (fig_roc,)


@app.cell
def _(fig_roc, mo, roc_df):
    mo.vstack([
        mo.ui.plotly(fig_roc),
        mo.md("**Tranche metrics (reactive)**"),
        mo.ui.table(roc_df, selection=None, page_size=10),
    ])
    return


@app.cell
def _(cap_col, hedged_pickup_bps, mo, region, roc_df):
    # Highlight best tranche
    best = roc_df.loc[roc_df["Loss-Adj ROC"].idxmax()]
    msg_pieces = [
        f"**Highest loss-adjusted ROC:** {best['Tranche']} at "
        f"{best['Loss-Adj ROC']:.1f} bps per 1% capital ",
        f"(spread {best['Spread']:.0f} bps, capital charge {best['Capital Charge %']:.2f}%, "
        f"framework: {cap_col}).",
    ]
    if region.value in ("EUR CLO", "Combined"):
        msg_pieces.append(
            f" Hedged pickup applied: **+{hedged_pickup_bps:.1f} bps** on EUR spreads."
        )
    mo.callout(mo.md(" ".join(msg_pieces)), kind="success")
    return


@app.cell
def _(mo):
    mo.md("---\n## Section 2 — Curve Steepness Dashboard")
    return


@app.cell
def _(pd):
    hist_spreads_eur = pd.DataFrame({
        "date": pd.to_datetime([
            "2020-03-31", "2020-06-30", "2020-12-31", "2021-06-30", "2021-12-31",
            "2022-06-30", "2022-12-31", "2023-06-30", "2023-12-31", "2024-06-30",
            "2024-12-31", "2025-06-30", "2025-12-31", "2026-03-31",
        ]),
        "AAA": [250, 200, 160, 110, 105, 150, 190, 175, 155, 140, 130, 125, 128, 127],
        "AA":  [400, 320, 250, 165, 155, 225, 290, 260, 230, 210, 195, 180, 185, 185],
        "A":   [550, 450, 350, 235, 220, 325, 400, 370, 320, 290, 265, 245, 250, 240],
        "BBB": [800, 650, 520, 370, 340, 480, 570, 530, 460, 420, 380, 350, 355, 350],
        "BB":  [1200, 1050, 850, 650, 600, 800, 900, 850, 750, 700, 670, 650, 660, 650],
    })

    hist_spreads_us = pd.DataFrame({
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
    return hist_spreads_eur, hist_spreads_us


@app.cell
def _(hist_spreads_eur, hist_spreads_us, region):
    hist = hist_spreads_eur if region.value != "US CLO" else hist_spreads_us
    return (hist,)


@app.cell
def _(NW, df, go, hist):
    tranches_l = ["AAA", "AA", "A", "BBB", "BB"]
    current = hist[tranches_l].iloc[-1].values
    six_mo = hist[tranches_l].iloc[-3].values  # ~6mo prior (semi-annual data)
    one_yr = hist[tranches_l].iloc[-5].values
    mins = hist[tranches_l].min().values
    maxs = hist[tranches_l].max().values

    fig_curve = go.Figure()
    # Min/max band
    fig_curve.add_trace(go.Scatter(
        x=tranches_l + tranches_l[::-1],
        y=list(maxs) + list(mins[::-1]),
        fill="toself", fillcolor="rgba(140,200,233,0.25)",
        line=dict(color="rgba(0,0,0,0)"),
        name="Historical min–max range",
        hoverinfo="skip",
    ))
    fig_curve.add_trace(go.Scatter(
        x=tranches_l, y=one_yr, mode="lines+markers",
        name="1yr ago", line=dict(color=NW["fossil"], dash="dot", width=2),
    ))
    fig_curve.add_trace(go.Scatter(
        x=tranches_l, y=six_mo, mode="lines+markers",
        name="6mo ago", line=dict(color=NW["teal"], dash="dash", width=2),
    ))
    # Use deal inputs for current (so Section 1 inputs flow here)
    cur_from_inputs = df.set_index("Tranche").loc[tranches_l, "Spread"].values
    fig_curve.add_trace(go.Scatter(
        x=tranches_l, y=cur_from_inputs, mode="lines+markers+text",
        name="Current (from inputs)", line=dict(color=NW["blue"], width=4),
        marker=dict(size=10),
        text=[f"{v:.0f}" for v in cur_from_inputs], textposition="top center",
    ))
    fig_curve.update_layout(
        title="Spread Curve — Current vs Historical",
        xaxis_title="Tranche",
        yaxis_title="Spread (bps)",
        height=440,
    )
    return current, fig_curve, tranches_l


@app.cell
def _(NW, go, hist, np):
    diff_aaa_aa = hist["AA"] - hist["AAA"]
    diff_aaa_a = hist["A"] - hist["AAA"]
    diff_aaa_bb = hist["BB"] - hist["AAA"]

    fig_steep = go.Figure()
    fig_steep.add_trace(go.Scatter(
        x=hist["date"], y=diff_aaa_aa, mode="lines+markers",
        name="AAA→AA (senior steepness)",
        line=dict(color=NW["blue"], width=3),
    ))
    fig_steep.add_trace(go.Scatter(
        x=hist["date"], y=diff_aaa_a, mode="lines+markers",
        name="AAA→A",
        line=dict(color=NW["teal"], width=3),
    ))
    fig_steep.add_trace(go.Scatter(
        x=hist["date"], y=diff_aaa_bb, mode="lines",
        name="AAA→BB (reference)",
        line=dict(color=NW["fossil"], width=1, dash="dot"),
        opacity=0.55,
    ))

    # Percentile lines for the primary senior measure (AAA→AA)
    p25_aa, p50_aa, p75_aa = np.percentile(diff_aaa_aa, [25, 50, 75])
    for _pct_v, _lbl, _col in [(p25_aa, "AAA→AA 25th", NW["red"]),
                               (p50_aa, "AAA→AA median", NW["dark_grey"]),
                               (p75_aa, "AAA→AA 75th", NW["teal"])]:
        fig_steep.add_hline(y=_pct_v, line=dict(color=_col, dash="dash"),
                            annotation_text=f"{_lbl}: {_pct_v:.0f}",
                            annotation_position="right")
    fig_steep.update_layout(
        title="Curve Steepness Through Time — senior focus (AAA→AA, AAA→A)",
        yaxis_title="Spread Differential (bps)",
        xaxis_title="Date",
        height=420,
    )
    # Keep the AAA→BB diff returned for other cells that consume it
    diff = diff_aaa_bb
    p25, p50, p75 = np.percentile(diff_aaa_bb, [25, 50, 75])
    return diff, fig_steep, p25, p50, p75


@app.cell
def _(hist):
    def pct_rank(series, value):
        return float((series < value).sum()) / len(series) * 100.0

    cur_aaa = hist["AAA"].iloc[-1]
    cur_aa = hist["AA"].iloc[-1]
    cur_a = hist["A"].iloc[-1]
    cur_bbb = hist["BBB"].iloc[-1]
    cur_bb = hist["BB"].iloc[-1]

    aaa_aa_cur = cur_aa - cur_aaa
    aaa_a_cur = cur_a - cur_aaa
    aaa_bbb_cur = cur_bbb - cur_aaa
    aaa_bb_cur = cur_bb - cur_aaa

    aaa_aa_pct = pct_rank(hist["AA"] - hist["AAA"], aaa_aa_cur)
    aaa_a_pct = pct_rank(hist["A"] - hist["AAA"], aaa_a_cur)
    aaa_bbb_pct = pct_rank(hist["BBB"] - hist["AAA"], aaa_bbb_cur)
    aaa_bb_pct = pct_rank(hist["BB"] - hist["AAA"], aaa_bb_cur)

    aa_a_pct = pct_rank(hist["A"] - hist["AA"], cur_a - cur_aa)
    steepness_ratio = cur_aa / cur_aaa  # senior steepness ratio
    return (
        aa_a_pct, aaa_a_cur, aaa_a_pct, aaa_aa_cur, aaa_aa_pct,
        aaa_bb_cur, aaa_bb_pct, aaa_bbb_cur, aaa_bbb_pct, steepness_ratio,
    )


@app.cell
def _(
    aa_a_pct, aaa_a_cur, aaa_a_pct, aaa_aa_cur, aaa_aa_pct,
    aaa_bb_cur, aaa_bb_pct, aaa_bbb_cur, aaa_bbb_pct, mo, steepness_ratio,
):
    metrics_md = mo.md(f"""
    **Senior-curve focus**

    | Metric | Current | Percentile (vs 5yr history) |
    |---|---|---|
    | **AAA → AA spread** | **{aaa_aa_cur:.0f} bps** | **{aaa_aa_pct:.0f}%** |
    | **AAA → A spread** | **{aaa_a_cur:.0f} bps** | **{aaa_a_pct:.0f}%** |
    | AA → A spread | — | {aa_a_pct:.0f}% |
    | Senior steepness ratio (AA / AAA) | **{steepness_ratio:.2f}x** | — |

    *Reference (mezz / lower)*

    | Metric | Current | Percentile |
    |---|---|---|
    | AAA → BBB spread | {aaa_bbb_cur:.0f} bps | {aaa_bbb_pct:.0f}% |
    | AAA → BB spread | {aaa_bb_cur:.0f} bps | {aaa_bb_pct:.0f}% |
    """)
    return (metrics_md,)


@app.cell
def _(aaa_a_pct, aaa_aa_pct, mo):
    # Signal driven by the senior curve (AAA→AA primary, AAA→A confirming)
    primary = aaa_aa_pct
    if primary > 75:
        signal = mo.callout(
            mo.md(
                f"**Senior curve steep — AAA→AA at {primary:.0f}th percentile, AAA→A at "
                f"{aaa_a_pct:.0f}th.** Moving AAA→AA or AAA→A picks up above-average compensation "
                f"for the incremental subordination loss."
            ),
            kind="success",
        )
    elif primary < 25:
        signal = mo.callout(
            mo.md(
                f"**Senior curve flat — AAA→AA at {primary:.0f}th percentile, AAA→A at "
                f"{aaa_a_pct:.0f}th.** AAA offers better risk-adjusted value than AA or A "
                f"at these levels."
            ),
            kind="warn",
        )
    else:
        signal = mo.callout(
            mo.md(
                f"**Senior curve near median — AAA→AA at {primary:.0f}th percentile, "
                f"AAA→A at {aaa_a_pct:.0f}th.** No strong relative-value signal in the senior stack."
            ),
            kind="neutral",
        )
    return (signal,)


@app.cell
def _(fig_curve, fig_steep, metrics_md, mo, signal):
    mo.vstack([
        mo.ui.plotly(fig_curve),
        mo.ui.plotly(fig_steep),
        metrics_md,
        signal,
    ])
    return


@app.cell
def _(mo):
    mo.md("---\n## Section 3 — Allocation Optimizer")
    return


@app.cell
def _(mo):
    portfolio_size = mo.ui.number(value=1000.0, step=50.0, label="Portfolio Size ($mm)")
    max_capital = mo.ui.number(value=50.0, step=5.0, label="Max Capital Consumption ($mm)")
    wal_range = mo.ui.range_slider(
        start=0.0, stop=8.0, step=0.25, value=(4.5, 7.0),
        label="Target WAL Range (yr) — widen for 3nc1 / 0nc6m profiles",
        show_value=True,
    )
    opt_region = mo.ui.dropdown(
        options=["US Only", "EUR Only", "Combined (hedged)"],
        value="US Only",
        label="Optimization Region",
    )

    preset = mo.ui.dropdown(
        options=[
            "Custom (use sliders below)",
            "AAA Only (100% AAA)",
            "Senior-Heavy (≥70% AAA, no BBB/BB)",
            "IG Only (AAA/AA/A, no BBB/BB)",
            "No Mezz (0% BBB, 0% BB)",
            "Conservative (≥80% AAA, ≤20% AA/A)",
            "Balanced (max 40% any tranche)",
            "Down-in-credit (max 30% AAA, force ≥10% BBB)",
        ],
        value="Custom (use sliders below)",
        label="Constraint Preset",
    )
    min_rating = mo.ui.dropdown(
        options=["AAA", "AA", "A", "BBB", "BB"],
        value="BB",
        label="Lowest acceptable rating",
    )
    max_concentration = mo.ui.slider(
        start=10, stop=100, step=5, value=100,
        label="Max single-tranche concentration (%)", show_value=True,
    )

    min_aaa = mo.ui.range_slider(start=0, stop=100, step=5, value=(0, 100), label="AAA min/max %", show_value=True)
    min_aa = mo.ui.range_slider(start=0, stop=100, step=5, value=(0, 100), label="AA min/max %", show_value=True)
    min_a = mo.ui.range_slider(start=0, stop=100, step=5, value=(0, 100), label="A min/max %", show_value=True)
    min_bbb = mo.ui.range_slider(start=0, stop=100, step=5, value=(0, 100), label="BBB min/max %", show_value=True)
    min_bb = mo.ui.range_slider(start=0, stop=100, step=5, value=(0, 100), label="BB min/max %", show_value=True)
    min_eq = mo.ui.range_slider(start=0, stop=100, step=5, value=(0, 0), label="Equity min/max %", show_value=True)

    mo.vstack([
        mo.hstack([portfolio_size, max_capital, opt_region], justify="start", gap=1.0),
        wal_range,
        mo.md(
            "**How constraints work** — pick a **preset** below for a one-click profile, "
            "or use the per-tranche **min/max sliders** to set hard bounds directly "
            "(e.g. set BBB max = 0 to exclude BBB entirely; set AAA min = 50 to require ≥50% AAA). "
            "**Lowest acceptable rating** zeros-out everything below it. "
            "**Max single-tranche concentration** caps the largest position for diversification."
        ),
        mo.hstack([preset, min_rating, max_concentration], justify="start", gap=1.0),
        mo.md("**Per-tranche bounds** (used when preset = Custom; otherwise preset overrides)"),
        mo.hstack([min_aaa, min_aa, min_a], justify="start", gap=1.0),
        mo.hstack([min_bbb, min_bb, min_eq], justify="start", gap=1.0),
    ])
    return (
        max_capital,
        max_concentration,
        min_a,
        min_aa,
        min_aaa,
        min_bb,
        min_bbb,
        min_eq,
        min_rating,
        opt_region,
        portfolio_size,
        preset,
        wal_range,
    )


@app.cell
def _(
    max_concentration,
    min_a,
    min_aa,
    min_aaa,
    min_bb,
    min_bbb,
    min_eq,
    min_rating,
    pd,
    preset,
):
    tranche_names = ["AAA", "AA", "A", "BBB", "BB", "Equity"]
    rating_idx = {"AAA": 0, "AA": 1, "A": 2, "BBB": 3, "BB": 4, "Equity": 5}

    # 1) Start from per-tranche sliders (used in Custom)
    bounds = {
        "AAA": list(min_aaa.value),
        "AA": list(min_aa.value),
        "A": list(min_a.value),
        "BBB": list(min_bbb.value),
        "BB": list(min_bb.value),
        "Equity": list(min_eq.value),
    }

    # 2) Preset overrides
    p = preset.value
    if p == "AAA Only (100% AAA)":
        bounds = {"AAA": [100, 100], "AA": [0, 0], "A": [0, 0],
                  "BBB": [0, 0], "BB": [0, 0], "Equity": [0, 0]}
    elif p == "Senior-Heavy (≥70% AAA, no BBB/BB)":
        bounds = {"AAA": [70, 100], "AA": [0, 30], "A": [0, 30],
                  "BBB": [0, 0], "BB": [0, 0], "Equity": [0, 0]}
    elif p == "IG Only (AAA/AA/A, no BBB/BB)":
        bounds = {"AAA": [0, 100], "AA": [0, 100], "A": [0, 100],
                  "BBB": [0, 0], "BB": [0, 0], "Equity": [0, 0]}
    elif p == "No Mezz (0% BBB, 0% BB)":
        bounds = {"AAA": [0, 100], "AA": [0, 100], "A": [0, 100],
                  "BBB": [0, 0], "BB": [0, 0], "Equity": [0, 0]}
    elif p == "Conservative (≥80% AAA, ≤20% AA/A)":
        bounds = {"AAA": [80, 100], "AA": [0, 20], "A": [0, 20],
                  "BBB": [0, 0], "BB": [0, 0], "Equity": [0, 0]}
    elif p == "Balanced (max 40% any tranche)":
        bounds = {"AAA": [0, 40], "AA": [0, 40], "A": [0, 40],
                  "BBB": [0, 40], "BB": [0, 40], "Equity": [0, 0]}
    elif p == "Down-in-credit (max 30% AAA, force ≥10% BBB)":
        bounds = {"AAA": [0, 30], "AA": [0, 40], "A": [0, 40],
                  "BBB": [10, 50], "BB": [0, 30], "Equity": [0, 0]}

    # 3) Apply minimum rating (zero-out anything below)
    cutoff = rating_idx[min_rating.value]
    for t, idx in rating_idx.items():
        if idx > cutoff:
            bounds[t] = [0, 0]

    # 4) Apply max concentration cap to every tranche
    for t in tranche_names:
        if t == "Equity":
            continue
        bounds[t][1] = min(bounds[t][1], max_concentration.value)
        bounds[t][0] = min(bounds[t][0], bounds[t][1])

    effective_bounds = bounds
    bounds_df = pd.DataFrame({
        "Tranche": tranche_names,
        "Min %": [bounds[t][0] for t in tranche_names],
        "Max %": [bounds[t][1] for t in tranche_names],
    })
    sum_min = bounds_df["Min %"].sum()
    sum_max = bounds_df["Max %"].sum()
    return bounds_df, effective_bounds, sum_max, sum_min


@app.cell
def _(bounds_df, mo, preset, sum_max, sum_min):
    feasible = (sum_min <= 100) and (sum_max >= 100)
    if not feasible:
        _kind, _msg = "danger", (
            f"⚠ **Infeasible bounds:** mins sum to {sum_min:.0f}% (must be ≤ 100) "
            f"and maxes sum to {sum_max:.0f}% (must be ≥ 100). Optimizer will relax."
        )
    else:
        _kind, _msg = "info", (
            f"**Effective bounds** (preset: *{preset.value}*) — "
            f"Σmin = {sum_min:.0f}%, Σmax = {sum_max:.0f}%."
        )
    mo.vstack([
        mo.callout(mo.md(_msg), kind=_kind),
        mo.ui.table(bounds_df, selection=None, page_size=10),
    ])
    return


@app.cell
def _(base_df, cap_col, eur_defaults, hedged_pickup_bps, opt_region, region, us_defaults):
    def opt_inputs():
        if opt_region.value == "US Only":
            d = us_defaults.copy()
            match = (region.value == "US CLO")
        elif opt_region.value == "EUR Only":
            d = eur_defaults.copy()
            match = (region.value == "EUR CLO")
        else:  # Combined (hedged)
            d = eur_defaults.copy()
            d["Spread"] = (eur_defaults["Spread"] + us_defaults["Spread"]) / 2.0
            d["Subordination"] = (eur_defaults["Subordination"] + us_defaults["Subordination"]) / 2.0
            match = False

        # If opt_region matches Section 1's region, use user-edited spreads / sub
        if match:
            d["Spread"] = base_df["Spread"].values
            d["Subordination"] = base_df["Subordination"].values
        # WAL always comes from base_df (the WAL profile dropdown is global)
        d["WAL"] = base_df["WAL"].values

        if opt_region.value == "EUR Only":
            d["EffSpread"] = d["Spread"] + hedged_pickup_bps
        elif opt_region.value == "Combined (hedged)":
            d["EffSpread"] = d["Spread"] + hedged_pickup_bps / 2.0
        else:
            d["EffSpread"] = d["Spread"]
        d["Capital"] = d[cap_col]
        return d
    opt_df = opt_inputs()
    return (opt_df,)


@app.cell
def _(mo):
    objective_mode = mo.ui.radio(
        options=["Pure ROC", "Pure Total Return", "Blend (Pareto)"],
        value="Pure ROC",
        label="Optimization objective",
        inline=True,
    )
    roc_weight = mo.ui.slider(
        start=0, stop=100, step=5, value=50,
        label="Blend: ROC weight % (0 = pure TR, 100 = pure ROC)",
        show_value=True,
    )
    mo.vstack([
        mo.md(
            "**Objective** — *Pure ROC* maximizes spread per unit of capital "
            "(loads on AAA). *Pure Total Return* maximizes portfolio-weighted "
            "spread income in bps (loads on BB / mezz). *Blend* finds the "
            "Pareto-efficient point at your chosen weight."
        ),
        mo.hstack([objective_mode, roc_weight], justify="start", gap=1.0),
    ])
    return objective_mode, roc_weight


@app.cell
def _(
    effective_bounds,
    max_capital,
    minimize,
    np,
    objective_mode,
    opt_df,
    portfolio_size,
    roc_weight,
    wal_range,
):
    tranche_order = ["AAA", "AA", "A", "BBB", "BB", "Equity"]
    odf = opt_df.set_index("Tranche").loc[tranche_order]

    spreads = odf["EffSpread"].values.astype(float)
    caps = odf["Capital"].values.astype(float)
    wals = odf["WAL"].values.astype(float)

    # Effective bounds come from preset + min-rating + max-concentration + per-tranche sliders
    _bnds = [(effective_bounds[t][0] / 100.0, effective_bounds[t][1] / 100.0)
             for t in tranche_order]
    _sum_min = sum(lo for lo, _ in _bnds)
    _sum_max = sum(hi for _, hi in _bnds)
    if _sum_min > 1.0 or _sum_max < 1.0:
        _bnds = [(0.0, 1.0) for _ in _bnds]

    # Per-tranche ROC and TR for normalization
    _per_roc = spreads / np.maximum(caps, 1e-6)
    _max_roc = float(np.max(_per_roc)) if np.max(_per_roc) > 0 else 1.0
    _max_tr = float(np.max(spreads)) if np.max(spreads) > 0 else 1.0
    _alpha = roc_weight.value / 100.0  # only used in Blend

    def _portfolio_roc(w):
        return float(np.sum(w * _per_roc))

    def _portfolio_tr(w):
        return float(np.sum(w * spreads))

    if objective_mode.value == "Pure ROC":
        def _objective(w):
            return -_portfolio_roc(w)
    elif objective_mode.value == "Pure Total Return":
        def _objective(w):
            return -_portfolio_tr(w)
    else:  # Blend (Pareto)
        def _objective(w):
            return -(_alpha * _portfolio_roc(w) / _max_roc
                     + (1.0 - _alpha) * _portfolio_tr(w) / _max_tr)

    _nz_wals = wals[wals > 0]
    _wal_floor = float(_nz_wals.min()) if len(_nz_wals) else 0.0
    _wal_ceil = float(_nz_wals.max()) if len(_nz_wals) else 8.0
    _wal_lo = max(wal_range.value[0], _wal_floor)
    _wal_hi = min(wal_range.value[1], _wal_ceil)
    if _wal_lo > _wal_hi:
        _wal_lo, _wal_hi = _wal_floor, _wal_ceil
    wal_relaxed = (_wal_lo != wal_range.value[0]) or (_wal_hi != wal_range.value[1])
    effective_wal_band = (_wal_lo, _wal_hi)

    _cons = [
        {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        {"type": "ineq", "fun": lambda w: _wal_hi - float(np.sum(w * wals))},
        {"type": "ineq", "fun": lambda w: float(np.sum(w * wals)) - _wal_lo},
        {"type": "ineq", "fun": lambda w: max_capital.value - float(np.sum(w * caps / 100.0)) * portfolio_size.value},
    ]

    _x0 = np.array([max(lo, min(hi, 1.0 / 6.0)) for (lo, hi) in _bnds])
    _x0 = _x0 / max(_x0.sum(), 1e-9)

    _result = minimize(
        _objective, _x0,
        method="SLSQP", bounds=_bnds, constraints=_cons,
        options={"maxiter": 400, "ftol": 1e-8},
    )

    optimal_w = _result.x if _result.success else _x0
    optimal_w = np.clip(optimal_w, 0, 1)
    optimal_w = optimal_w / max(optimal_w.sum(), 1e-9)
    return caps, effective_wal_band, odf, optimal_w, spreads, tranche_order, wal_relaxed, wals


@app.cell
def _(caps, np, optimal_w, pd, portfolio_size, spreads, tranche_order, wals):
    def summarize(w):
        port_roc = float(np.sum(w * spreads / np.maximum(caps, 1e-6)))
        port_tr = float(np.sum(w * spreads))
        port_wal = float(np.sum(w * wals))
        port_cap = float(np.sum(w * caps / 100.0)) * portfolio_size.value
        return port_roc, port_tr, port_wal, port_cap

    optimal_roc, optimal_tr, optimal_wal, optimal_cap = summarize(optimal_w)
    current_w = np.array([0.70, 0.25, 0.05, 0.0, 0.0, 0.0])
    equal_w = np.array([1, 1, 1, 1, 1, 0]) / 5.0  # exclude equity by default

    cur_roc, cur_tr, cur_wal, cur_cap = summarize(current_w)
    eq_roc, eq_tr, eq_wal, eq_cap = summarize(equal_w)

    compare_df = pd.DataFrame({
        "Allocation": ["Optimal", "Current (70/25/5)", "Equal-Weight (5 tranches)"],
        "Portfolio ROC": [round(optimal_roc, 1), round(cur_roc, 1), round(eq_roc, 1)],
        "Portfolio TR (bps)": [round(optimal_tr, 1), round(cur_tr, 1), round(eq_tr, 1)],
        "Portfolio WAL": [round(optimal_wal, 2), round(cur_wal, 2), round(eq_wal, 2)],
        "Capital ($mm)": [round(optimal_cap, 1), round(cur_cap, 1), round(eq_cap, 1)],
    })
    for _i, _t in enumerate(tranche_order):
        compare_df[_t + " %"] = [
            round(optimal_w[_i] * 100, 1),
            round(current_w[_i] * 100, 1),
            round(equal_w[_i] * 100, 1),
        ]
    return compare_df, optimal_cap, optimal_roc, optimal_tr, optimal_wal


@app.cell
def _(
    NW, caps, effective_wal_band, go, max_capital, minimize, np,
    optimal_roc, optimal_tr, portfolio_size, roc_weight, spreads, wals,
):
    # Compute Pareto frontier by sweeping alpha across [0, 1]
    _max_roc_asset = float(np.max(spreads / np.maximum(caps, 1e-6)))
    _max_tr_asset = float(np.max(spreads))
    _wal_lo, _wal_hi = effective_wal_band

    def _solve(alpha):
        def _obj(w):
            return -(alpha * float(np.sum(w * spreads / np.maximum(caps, 1e-6))) / _max_roc_asset
                     + (1.0 - alpha) * float(np.sum(w * spreads)) / _max_tr_asset)
        _cons = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            {"type": "ineq", "fun": lambda w: _wal_hi - float(np.sum(w * wals))},
            {"type": "ineq", "fun": lambda w: float(np.sum(w * wals)) - _wal_lo},
            {"type": "ineq", "fun": lambda w: max_capital.value - float(np.sum(w * caps / 100.0)) * portfolio_size.value},
        ]
        _x0 = np.array([1.0 / 6.0] * 6)
        _r = minimize(_obj, _x0, method="SLSQP", bounds=[(0.0, 1.0)] * 6,
                      constraints=_cons, options={"maxiter": 300, "ftol": 1e-7})
        _w = _r.x if _r.success else _x0
        _w = np.clip(_w, 0, 1)
        _w = _w / max(_w.sum(), 1e-9)
        return _w

    _alphas = np.linspace(0.0, 1.0, 21)
    _pts = []
    for _a in _alphas:
        _w = _solve(float(_a))
        _pts.append((float(np.sum(_w * spreads)),
                     float(np.sum(_w * spreads / np.maximum(caps, 1e-6))),
                     float(_a)))
    _tr_arr = [p[0] for p in _pts]
    _roc_arr = [p[1] for p in _pts]

    fig_pareto = go.Figure()
    fig_pareto.add_trace(go.Scatter(
        x=_tr_arr, y=_roc_arr, mode="lines+markers",
        line=dict(color=NW["dark_blue"], width=3),
        marker=dict(size=7, color=NW["med_blue"]),
        name="Pareto frontier (sweep α)",
        hovertemplate="TR %{x:.0f} bps · ROC %{y:.1f}<extra></extra>",
    ))
    # Mark the user's current selection
    fig_pareto.add_trace(go.Scatter(
        x=[optimal_tr], y=[optimal_roc],
        mode="markers+text",
        marker=dict(size=18, color=NW["orange"], symbol="star",
                    line=dict(width=2, color=NW["charcoal"])),
        text=[f"  Your selection (α={roc_weight.value}%)"],
        textposition="middle right",
        name="Your selection",
    ))
    # Anchor labels for the two extremes
    fig_pareto.add_annotation(
        x=_tr_arr[0], y=_roc_arr[0], text="Pure TR (max spread income)",
        showarrow=True, arrowhead=2, ax=40, ay=20, font=dict(size=10),
    )
    fig_pareto.add_annotation(
        x=_tr_arr[-1], y=_roc_arr[-1], text="Pure ROC (max spread/capital)",
        showarrow=True, arrowhead=2, ax=-40, ay=-20, font=dict(size=10),
    )
    fig_pareto.update_layout(
        title="Pareto Frontier — Total Return vs Return on Capital<br>"
              "<sub>Each point is the best achievable ROC at that Total Return level "
              "(subject to your WAL, capital, and bound constraints).</sub>",
        xaxis_title="Portfolio Total Return (bps spread income)",
        yaxis_title="Portfolio ROC (bps per 1% capital)",
        height=460,
    )
    return (fig_pareto,)


@app.cell
def _(NW, go, np, optimal_w, tranche_order):
    nz = optimal_w > 1e-4
    fig_pie = go.Figure(data=[go.Pie(
        labels=[t for t, m in zip(tranche_order, nz) if m],
        values=[float(w) for w, m in zip(optimal_w, nz) if m],
        hole=0.4,
        marker=dict(colors=[NW["blue"], NW["dark_blue"], NW["teal"], NW["orange"], NW["red"], NW["purple"]]),
    )])
    fig_pie.update_layout(
        title=f"Optimal Allocation — Portfolio ROC {float(np.sum(optimal_w * 1)):.2f}",
        height=420,
    )
    return (fig_pie,)


@app.cell
def _(NW, caps, go, minimize, np, opt_df, optimal_w, spreads, tranche_order, wals):
    _shifts = [0, 50, 100, 200]
    _sens_weights = {}

    def _reoptimize(shift):
        _s = spreads + shift
        def _neg(w):
            return -float(np.sum(w * _s / np.maximum(caps, 1e-6)))
        _bnds = [(0.0, 1.0)] * len(_s)
        _cons = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            {"type": "ineq", "fun": lambda w: 7.0 - float(np.sum(w * wals))},
            {"type": "ineq", "fun": lambda w: float(np.sum(w * wals)) - 4.5},
        ]
        _x0 = np.array([1.0 / len(_s)] * len(_s))
        _r = minimize(_neg, _x0, method="SLSQP", bounds=_bnds, constraints=_cons,
                      options={"maxiter": 300, "ftol": 1e-7})
        _w = _r.x if _r.success else _x0
        return np.clip(_w, 0, 1) / max(np.clip(_w, 0, 1).sum(), 1e-9)

    for _s in _shifts:
        _sens_weights[_s] = _reoptimize(_s)
    _sens_weights[0] = optimal_w

    fig_sens = go.Figure()
    _palette = [NW["blue"], NW["dark_blue"], NW["teal"], NW["orange"], NW["red"], NW["purple"]]
    for _i, _t in enumerate(tranche_order):
        fig_sens.add_trace(go.Bar(
            name=_t,
            x=[f"+{s} bps" for s in _shifts],
            y=[_sens_weights[s][_i] * 100 for s in _shifts],
            marker_color=_palette[_i],
        ))
    fig_sens.update_layout(
        barmode="stack",
        title="Sensitivity — Optimal Allocation under Parallel Spread Shifts",
        yaxis_title="Allocation (%)", xaxis_title="Parallel shift",
        height=400,
    )
    return (fig_sens,)


@app.cell
def _(
    compare_df, effective_wal_band, fig_pareto, fig_pie, fig_sens, mo,
    objective_mode, optimal_cap, optimal_roc, optimal_tr, optimal_wal,
    roc_weight, wal_relaxed,
):
    _obj_label = objective_mode.value
    if _obj_label.startswith("Blend"):
        _obj_label = f"Blend @ {roc_weight.value}% ROC weight"
    _summary = mo.callout(
        mo.md(
            f"**Optimal portfolio** *(objective: {_obj_label})*: "
            f"ROC **{optimal_roc:.2f}** bps/1% cap · "
            f"Total Return **{optimal_tr:.1f}** bps · "
            f"WAL **{optimal_wal:.2f}** yr · "
            f"Capital **${optimal_cap:.1f}mm**."
        ),
        kind="info",
    )
    _items = [_summary]
    if wal_relaxed:
        _items.append(mo.callout(
            mo.md(
                f"⚠ **WAL target auto-relaxed** to "
                f"({effective_wal_band[0]:.2f}, {effective_wal_band[1]:.2f}) yrs "
                f"because the slider band didn't overlap the tranche WALs "
                f"(check the WAL profile in Section 1)."
            ),
            kind="warn",
        ))
    _items += [
        mo.hstack([mo.ui.plotly(fig_pie)], justify="start"),
        mo.md("**Comparison: Optimal vs Current vs Equal-Weight**"),
        mo.ui.table(compare_df, selection=None, page_size=10),
        mo.ui.plotly(fig_pareto),
        mo.ui.plotly(fig_sens),
    ]
    mo.vstack(_items)
    return


@app.cell
def _(mo):
    mo.md(
        "---\n"
        "## Section 4 — Cross-Region Comparison *(European overlay)*\n"
        "*Expand the panel below to compare EUR vs US tranche spreads and hedged ROC.*"
    )
    return


@app.cell
def _(cap_col, eur_defaults, hedged_pickup_bps, pd, us_defaults):
    cmp_df = pd.DataFrame({
        "Tranche": eur_defaults["Tranche"],
        "EUR Spread": eur_defaults["Spread"],
        "US Spread": us_defaults["Spread"],
        "EUR Hedged Spread": eur_defaults["Spread"] + hedged_pickup_bps,
        "EUR Capital %": eur_defaults[cap_col],
        "US Capital %": us_defaults[cap_col],
    })
    cmp_df["EUR ROC"] = (cmp_df["EUR Spread"] / cmp_df["EUR Capital %"]).round(1)
    cmp_df["US ROC"] = (cmp_df["US Spread"] / cmp_df["US Capital %"]).round(1)
    cmp_df["EUR Hedged ROC"] = (cmp_df["EUR Hedged Spread"] / cmp_df["EUR Capital %"]).round(1)
    cmp_df["Winner (Hedged)"] = cmp_df.apply(
        lambda r: "EUR Hedged" if r["EUR Hedged ROC"] > r["US ROC"] else "US", axis=1
    )
    return (cmp_df,)


@app.cell
def _(NW, cmp_df, go):
    fig_cmp = go.Figure()
    fig_cmp.add_trace(go.Bar(
        name="EUR (raw)", x=cmp_df["Tranche"], y=cmp_df["EUR Spread"],
        marker_color=NW["dark_blue"], text=cmp_df["EUR Spread"], textposition="outside",
    ))
    fig_cmp.add_trace(go.Bar(
        name="US (raw)", x=cmp_df["Tranche"], y=cmp_df["US Spread"],
        marker_color=NW["med_blue"], text=cmp_df["US Spread"], textposition="outside",
    ))
    fig_cmp.add_trace(go.Bar(
        name="EUR (hedged → USD)", x=cmp_df["Tranche"], y=cmp_df["EUR Hedged Spread"],
        marker_color=NW["orange"], text=cmp_df["EUR Hedged Spread"], textposition="outside",
    ))
    fig_cmp.update_layout(
        barmode="group", title="EUR vs US Spreads (hedged equivalent shown)",
        yaxis_title="Spread (bps)", xaxis_title="Tranche", height=440,
    )
    return (fig_cmp,)


@app.cell
def _(basis_swap, cmp_df, euribor, fig_cmp, hedged_pickup_bps, mo, rate_diff_bps, sofr):
    aaa_pickup = (cmp_df.loc[cmp_df["Tranche"] == "AAA", "EUR Hedged Spread"].iloc[0]
                  - cmp_df.loc[cmp_df["Tranche"] == "AAA", "US Spread"].iloc[0])
    basis_panel = mo.md(f"""
    **Cross-Currency Basis Math**

    | Input | Value |
    |---|---|
    | 3mo SOFR | {sofr.value:.2f}% |
    | 3mo Euribor | {euribor.value:.2f}% |
    | Rate differential | {rate_diff_bps:.0f} bps |
    | 2yr basis swap | {basis_swap.value:.1f} bps |
    | **Hedged pickup applied** | **{hedged_pickup_bps:+.1f} bps** |
    """)

    _summary = mo.callout(
        mo.md(
            f"At current rates, **EUR CLO AAAs offer approximately {aaa_pickup:+.0f} bps "
            f"hedged pickup over US equivalents.**"
        ),
        kind="success" if aaa_pickup > 0 else "warn",
    )
    _show_cols = ["Tranche", "EUR Spread", "US Spread", "EUR Hedged Spread",
                  "EUR ROC", "US ROC", "EUR Hedged ROC", "Winner (Hedged)"]
    mo.accordion({
        "▸ Show cross-region comparison (EUR vs US)": mo.vstack([
            mo.ui.plotly(fig_cmp),
            mo.ui.table(cmp_df[_show_cols], selection=None, page_size=10),
            basis_panel,
            _summary,
        ]),
    })
    return


@app.cell
def _(mo):
    mo.md("---\n## Section 5 — Scenario / Stress Analysis")
    return


@app.cell
def _(mo):
    scenario = mo.ui.dropdown(
        options=["Parallel Shift", "Curve Steepener", "Curve Flattener",
                "Mar 2026 Replay", "Custom"],
        value="Parallel Shift",
        label="Scenario",
    )
    shift_mag = mo.ui.slider(
        start=-200, stop=200, step=10, value=50,
        label="Parallel Shift (bps)", show_value=True,
    )
    custom_aaa = mo.ui.number(value=127, label="AAA (bps)")
    custom_aa = mo.ui.number(value=185, label="AA (bps)")
    custom_a = mo.ui.number(value=240, label="A (bps)")
    custom_bbb = mo.ui.number(value=350, label="BBB (bps)")
    custom_bb = mo.ui.number(value=650, label="BB (bps)")

    mo.vstack([
        mo.hstack([scenario, shift_mag], justify="start", gap=1.0),
        mo.md("*Custom override (used when 'Custom' scenario is selected)*"),
        mo.hstack([custom_aaa, custom_aa, custom_a, custom_bbb, custom_bb], justify="start", gap=1.0),
    ])
    return custom_a, custom_aa, custom_aaa, custom_bb, custom_bbb, scenario, shift_mag


@app.cell
def _(base_df, custom_a, custom_aa, custom_aaa, custom_bb, custom_bbb, np, scenario, shift_mag):
    base = base_df.copy()
    tranche_l = ["AAA", "AA", "A", "BBB", "BB", "Equity"]
    cur = base.set_index("Tranche").loc[tranche_l, "Spread"].values.astype(float)

    if scenario.value == "Parallel Shift":
        stressed = cur.copy()
        stressed[:5] = stressed[:5] + shift_mag.value  # don't shift equity
    elif scenario.value == "Curve Steepener":
        # AAA unchanged, BB widens 100, linear interp between
        steepen = np.array([0, 20, 40, 70, 100, 0], dtype=float)
        stressed = cur + steepen
    elif scenario.value == "Curve Flattener":
        # BB tightens 80, AAA widens 20
        flatten = np.array([20, 10, 0, -30, -80, 0], dtype=float)
        stressed = cur + flatten
    elif scenario.value == "Mar 2026 Replay":
        stressed = np.array([132, 205, 280, 420, 750, cur[5]], dtype=float)
    else:  # Custom
        stressed = np.array([
            custom_aaa.value, custom_aa.value, custom_a.value,
            custom_bbb.value, custom_bb.value, cur[5],
        ], dtype=float)

    delta = stressed - cur
    return cur, delta, stressed, tranche_l


@app.cell
def _(NW, base_df, cap_col, cur, go, np, pd, stressed, tranche_l):
    caps_v = base_df.set_index("Tranche").loc[tranche_l, cap_col].values.astype(float)
    wals_v = base_df.set_index("Tranche").loc[tranche_l, "WAL"].values.astype(float)

    base_roc = cur / np.maximum(caps_v, 1e-6)
    # "New-money" ROC = forward yield on capital if you buy at stressed spreads
    new_money_roc = stressed / np.maximum(caps_v, 1e-6)

    # "Realized 1y ROC" for an existing position = (annual spread income - MTM hit
    # over a 1y holding period assuming the move happens now) / capital
    # MTM hit (bps) ≈ ΔSpread × WAL (DV01 approximation)
    delta_bps = stressed - cur
    mtm_hit_bps = delta_bps * wals_v
    realized_1y_spread = cur - mtm_hit_bps  # one-year realized income
    realized_roc = realized_1y_spread / np.maximum(caps_v, 1e-6)

    fig_stress = go.Figure()
    fig_stress.add_trace(go.Bar(
        name="Base ROC", x=tranche_l, y=base_roc,
        marker_color=NW["blue"], text=np.round(base_roc, 1), textposition="outside",
    ))
    fig_stress.add_trace(go.Bar(
        name="Realized 1y ROC (existing position, MTM-adjusted)",
        x=tranche_l, y=realized_roc,
        marker_color=NW["red"], text=np.round(realized_roc, 1), textposition="outside",
    ))
    fig_stress.add_trace(go.Bar(
        name="New-money ROC (deploy at stressed spreads)",
        x=tranche_l, y=new_money_roc,
        marker_color=NW["teal"], text=np.round(new_money_roc, 1), textposition="outside",
    ))
    fig_stress.update_layout(
        barmode="group",
        title="ROC Before vs After Stress<br>"
              "<sub>Red = existing position after MTM hit (1y).  "
              "Teal = forward ROC on capital deployed at the new wider spreads.</sub>",
        yaxis_title="ROC (bps per 1% capital)", xaxis_title="Tranche", height=460,
    )

    stressed_roc = new_money_roc  # back-compat for downstream cells

    impact_df = pd.DataFrame({
        "Tranche": tranche_l,
        "Base Spread": cur.astype(int),
        "Stressed Spread": stressed.astype(int),
        "Δ Spread (bps)": delta_bps.astype(int),
        "MTM Hit (bps, 1y)": mtm_hit_bps.round(0).astype(int),
        "Capital %": caps_v,
        "Base ROC": np.round(base_roc, 1),
        "Realized 1y ROC": np.round(realized_roc, 1),
        "New-Money ROC": np.round(new_money_roc, 1),
    })
    return base_roc, fig_stress, impact_df, stressed_roc


@app.cell
def _(
    base_df,
    base_roc,
    caps,
    cur,
    fig_stress,
    impact_df,
    minimize,
    mo,
    np,
    optimal_w,
    pd,
    portfolio_size,
    stressed,
    stressed_roc,
    tranche_l,
    wals,
):
    def _opt_under(spreads_v):
        def _neg(w):
            return -float(np.sum(w * spreads_v / np.maximum(caps, 1e-6)))
        _bnds = [(0.0, 1.0)] * 6
        _cons = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            {"type": "ineq", "fun": lambda w: 7.0 - float(np.sum(w * wals))},
            {"type": "ineq", "fun": lambda w: float(np.sum(w * wals)) - 4.5},
        ]
        _x0 = np.array([1.0 / 6.0] * 6)
        _r = minimize(_neg, _x0, method="SLSQP", bounds=_bnds, constraints=_cons,
                      options={"maxiter": 300, "ftol": 1e-7})
        _w = _r.x if _r.success else _x0
        return np.clip(_w, 0, 1) / max(np.clip(_w, 0, 1).sum(), 1e-9)

    _w_stress = _opt_under(stressed)
    _w_base = _opt_under(cur)
    w_stress = _w_stress
    w_base = _w_base

    port_roc_base = float(np.sum(w_base * base_roc))
    port_roc_stress = float(np.sum(w_stress * stressed_roc))

    # Spread DV01 approximation: ΔSpread * WAL * 0.01% * notional
    # Apply to base optimal allocation
    dv01_pl = -float(np.sum(optimal_w * (stressed - cur) * wals * 0.0001)) * portfolio_size.value
    # Sign convention: spread widening → MTM loss → negative
    pl_pct = dv01_pl / portfolio_size.value * 100.0 if portfolio_size.value else 0.0

    cap_consumed_base = float(np.sum(w_base * np.array(base_df.set_index('Tranche').loc[tranche_l, 'Basel III Standardized'].values) / 100.0)) * portfolio_size.value
    cap_consumed_stress = float(np.sum(w_stress * np.array(base_df.set_index('Tranche').loc[tranche_l, 'Basel III Standardized'].values) / 100.0)) * portfolio_size.value

    shift_table = pd.DataFrame({
        "Tranche": tranche_l,
        "Base Optimal %": (w_base * 100).round(1),
        "Stressed Optimal %": (w_stress * 100).round(1),
        "Δ Weight (pp)": ((w_stress - w_base) * 100).round(1),
    })

    summary_panel = mo.callout(
        mo.md(
            f"**Portfolio impact (stress applied to current optimal weights):**\n\n"
            f"- Portfolio ROC: **{port_roc_base:.2f} → {port_roc_stress:.2f}**\n"
            f"- Estimated MTM P&L (DV01 approx.): **${dv01_pl:+,.1f}mm** ({pl_pct:+.2f}%)\n"
            f"- Capital consumed: **${cap_consumed_base:.1f}mm → ${cap_consumed_stress:.1f}mm**"
        ),
        kind="warn" if dv01_pl < 0 else "success",
    )
    mo.vstack([
        mo.ui.plotly(fig_stress),
        mo.md("**Tranche-level detail**"),
        mo.ui.table(impact_df, selection=None, page_size=10),
        mo.md("**Allocation shift under stress**"),
        mo.ui.table(shift_table, selection=None, page_size=10),
        summary_panel,
    ])
    return


@app.cell
def _(mo):
    mo.md(
        "---\n"
        "## Section 6 — Manager Quality Overlay *(European overlay)*\n"
        "*Manager metrics shown are European CLO managers. Expand below to see.*"
    )
    return


@app.cell
def _(pd):
    managers = pd.DataFrame({
        "name": [
            "Redding Ridge (Apollo)", "Blackstone (GSO)", "PGIM", "Tikehau", "Hayfin",
            "Permira", "Ares", "Barings", "Arini Capital", "Neuberger Berman",
        ],
        "warf": [2728, 2979, 2858, 2876, 2846, 2924, 2971, 2855, None, None],
        "was_bps": [337, 354, 390, 379, 342, 359, 370, 354, None, None],
        "ccc_pct": [1.6, 4.1, 4.7, 1.6, 3.3, 2.4, 2.8, 3.2, None, None],
        "jr_oc_pct": [5.78, 4.62, 3.48, 3.31, 3.65, 4.20, 3.68, 2.71, None, None],
        "style": [
            "Active/alpha", "Large-cap defensive", "Buy-and-hold", "EU specialist/ESG",
            "Senior/defensive", "EU specialist", "Diversified", "Conservative/insurance",
            "Fast-growing EU", "Defensive/HQ",
        ],
        "tier": [1, 1, 2, 2, 2, 2, 3, 3, 3, 4],
        "eu_aum_bn": [9.83, 8.14, 6.07, 5.58, 4.62, 4.05, 3.80, 3.28, 3.11, 1.49],
    })
    return (managers,)


@app.cell
def _(managers, np):
    def norm(x, lo, hi, invert=False):
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return None
        v = max(min((x - lo) / (hi - lo), 1.0), 0.0) * 100.0
        return 100.0 - v if invert else v

    rows = []
    for _, r in managers.iterrows():
        if any(r[c] is None or (isinstance(r[c], float) and np.isnan(r[c])) for c in ["jr_oc_pct", "ccc_pct", "warf"]):
            rows.append(None)
            continue
        joc = norm(r["jr_oc_pct"], 2.5, 6.0)
        ccc = norm(r["ccc_pct"], 0.0, 7.5, invert=True)
        warf_ = norm(r["warf"], 2600, 3100, invert=True)
        score = 0.4 * joc + 0.3 * ccc + 0.3 * warf_
        rows.append(round(score, 1))

    mgr = managers.copy()
    mgr["quality_score"] = rows
    return (mgr,)


@app.cell
def _(mgr, mo):
    cols = ["name", "tier", "eu_aum_bn", "warf", "was_bps", "ccc_pct", "jr_oc_pct", "style", "quality_score"]
    table = mo.ui.table(mgr[cols].rename(columns={
        "name": "Manager", "tier": "Tier", "eu_aum_bn": "EU AUM (€bn)",
        "warf": "WARF", "was_bps": "WAS (bps)", "ccc_pct": "CCC %",
        "jr_oc_pct": "Jr OC %", "style": "Style", "quality_score": "Quality Score",
    }), selection=None, page_size=15)
    return (table,)


@app.cell
def _(NW, go, mgr):
    plot_df = mgr.dropna(subset=["quality_score", "was_bps"]).copy()
    tier_colors = {1: NW["blue"], 2: NW["teal"], 3: NW["orange"], 4: NW["red"]}
    fig_mgr = go.Figure()
    for _t, _sub in plot_df.groupby("tier"):
        fig_mgr.add_trace(go.Scatter(
            x=_sub["quality_score"], y=_sub["was_bps"], mode="markers+text",
            marker=dict(size=_sub["eu_aum_bn"] * 4.0, color=tier_colors.get(int(_t), NW["dark_grey"]),
                        line=dict(width=1, color=NW["charcoal"])),
            name=f"Tier {int(_t)}",
            text=_sub["name"], textposition="top center", textfont=dict(size=10),
        ))
    fig_mgr.update_layout(
        title="Manager Quality vs Spread (bubble = EU AUM)",
        xaxis_title="Quality Score (0–100)", yaxis_title="WAS (bps)",
        height=480,
    )
    return (fig_mgr,)


@app.cell
def _(base_df, cap_col, go, mgr, np, px, tranche_order):
    # Manager-adjusted ROC heatmap: manager × tranche
    have = mgr.dropna(subset=["quality_score"]).copy()
    adj = ((have["quality_score"] - 50.0) / 500.0).values  # ±10% range
    spreads_b = base_df.set_index("Tranche").loc[tranche_order, "Spread"].values.astype(float)
    caps_b = base_df.set_index("Tranche").loc[tranche_order, cap_col].values.astype(float)
    base_roc_v = spreads_b / np.maximum(caps_b, 1e-6)
    matrix = np.outer(1.0 + adj, base_roc_v)

    fig_hm = go.Figure(data=go.Heatmap(
        z=matrix,
        x=tranche_order,
        y=have["name"].tolist(),
        colorscale="Blues",
        text=np.round(matrix, 1),
        texttemplate="%{text}",
        colorbar=dict(title="ROC"),
    ))
    fig_hm.update_layout(
        title="Manager-Adjusted ROC by Tranche",
        xaxis_title="Tranche", yaxis_title="Manager",
        height=440,
    )
    return (fig_hm,)


@app.cell
def _(fig_hm, fig_mgr, mo, table):
    mo.accordion({
        "▸ Show EU manager quality table, scatter, and adjusted-ROC heatmap": mo.vstack([
            table,
            mo.ui.plotly(fig_mgr),
            mo.ui.plotly(fig_hm),
        ]),
    })
    return


@app.cell
def _(mo):
    mo.md(
        "---\n"
        "## Section 7 — Cross-Region Correlation & Efficient Frontier *(European overlay)*\n"
        "*Shows the diversification case for adding EUR tranches to a US-only book.*"
    )
    return


@app.cell
def _(np):
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
    labels = ["US AAA", "US AA", "US A", "EUR AAA", "EUR AA", "EUR A"]
    return corr_matrix, cov_matrix, labels, returns, vols


@app.cell
def _(corr_matrix, go, labels):
    fig_corr = go.Figure(data=go.Heatmap(
        z=corr_matrix,
        x=labels, y=labels,
        text=corr_matrix,
        texttemplate="%{text:.2f}",
        colorscale="Blues",
        zmin=0.6, zmax=1.0,
        colorbar=dict(title="Corr"),
    ))
    fig_corr.update_layout(
        title="US ↔ EUR CLO Tranche Correlation (5yr monthly returns)",
        height=440,
    )
    return (fig_corr,)


@app.cell
def _(NW, cov_matrix, go, labels, minimize, np, returns):
    rng = np.random.default_rng(42)
    n_port = 5000
    n_asset = len(returns)

    weights = rng.dirichlet(np.ones(n_asset), size=n_port)
    weights = np.clip(weights, 0, 0.5)
    weights = weights / weights.sum(axis=1, keepdims=True)

    port_ret = weights @ returns
    port_vol = np.sqrt(np.einsum("ij,jk,ik->i", weights, cov_matrix, weights))
    sharpe = port_ret / np.where(port_vol > 0, port_vol, 1e-6)

    fig_ef = go.Figure()
    fig_ef.add_trace(go.Scatter(
        x=port_vol * 100, y=port_ret * 100, mode="markers",
        marker=dict(size=4, color=sharpe, colorscale="Blues",
                    colorbar=dict(title="Sharpe"), opacity=0.6),
        name="Random portfolios", hoverinfo="skip",
    ))

    _target_rets = np.linspace(returns.min() + 1e-4, returns.max() - 1e-4, 30)
    frontier_vols, frontier_rets = [], []
    for _tr in _target_rets:
        def _obj(w):
            return float(w @ cov_matrix @ w)
        _cons = [
            {"type": "eq", "fun": lambda w: w.sum() - 1.0},
            {"type": "eq", "fun": lambda w, tr=_tr: float(w @ returns) - tr},
        ]
        _bnds = [(0.0, 0.5)] * n_asset
        _x0 = np.array([1.0 / n_asset] * n_asset)
        _res = minimize(_obj, _x0, method="SLSQP", bounds=_bnds, constraints=_cons,
                        options={"maxiter": 300})
        if _res.success:
            frontier_rets.append(_tr * 100)
            frontier_vols.append(float(np.sqrt(_res.fun)) * 100)

    fig_ef.add_trace(go.Scatter(
        x=frontier_vols, y=frontier_rets, mode="lines",
        line=dict(color=NW["dark_blue"], width=3),
        name="Efficient frontier",
    ))

    # Current US-only allocation (proxy 70% US AAA / 25% US AA / 5% US A)
    cur_w = np.array([0.70, 0.25, 0.05, 0.0, 0.0, 0.0])
    cur_ret = float(cur_w @ returns) * 100
    cur_vol = float(np.sqrt(cur_w @ cov_matrix @ cur_w)) * 100

    # Proposed EUR-only allocation (70/25/5 on EUR AAA/AA/A)
    eur_w = np.array([0.0, 0.0, 0.0, 0.70, 0.25, 0.05])
    eur_ret = float(eur_w @ returns) * 100
    eur_vol = float(np.sqrt(eur_w @ cov_matrix @ eur_w)) * 100

    # Combined US + EUR (current $8.5bn US + $1.0bn EUR, weight by 8.5:1)
    w_us = 8.5 / 9.5
    w_eu = 1.0 / 9.5
    combo_w = w_us * cur_w + w_eu * eur_w
    combo_ret = float(combo_w @ returns) * 100
    combo_vol = float(np.sqrt(combo_w @ cov_matrix @ combo_w)) * 100

    fig_ef.add_trace(go.Scatter(
        x=[cur_vol], y=[cur_ret], mode="markers+text",
        marker=dict(size=14, color=NW["orange"], symbol="diamond",
                    line=dict(width=2, color=NW["charcoal"])),
        text=["Current US-only"], textposition="top right",
        name="Current US-only", showlegend=True,
    ))
    fig_ef.add_trace(go.Scatter(
        x=[eur_vol], y=[eur_ret], mode="markers+text",
        marker=dict(size=14, color=NW["red"], symbol="diamond",
                    line=dict(width=2, color=NW["charcoal"])),
        text=["Proposed EUR-only"], textposition="top right",
        name="Proposed EUR-only", showlegend=True,
    ))
    fig_ef.add_trace(go.Scatter(
        x=[combo_vol], y=[combo_ret], mode="markers+text",
        marker=dict(size=14, color=NW["teal"], symbol="diamond",
                    line=dict(width=2, color=NW["charcoal"])),
        text=["Combined US + EUR"], textposition="bottom right",
        name="Combined US + EUR", showlegend=True,
    ))
    fig_ef.update_layout(
        title="Efficient Frontier — US + EUR Tranches",
        xaxis_title="Volatility (% annualized)",
        yaxis_title="Return (% annualized)",
        height=520,
    )

    div_pct = (cur_vol - combo_vol) / cur_vol * 100.0 if cur_vol else 0.0
    return combo_ret, combo_vol, cur_ret, cur_vol, div_pct, eur_ret, eur_vol, fig_ef


@app.cell
def _(combo_vol, cur_vol, div_pct, fig_corr, fig_ef, mo):
    callout = mo.callout(
        mo.md(
            f"**Diversification benefit:** Combining $8.5bn US + $1.0bn EUR cuts portfolio volatility "
            f"from **{cur_vol:.2f}% → {combo_vol:.2f}%** (–{div_pct:.1f}%) at a similar expected return, "
            f"driven by cross-region correlations of 0.72–0.87 vs within-region 0.94–0.97."
        ),
        kind="success",
    )
    mo.accordion({
        "▸ Show cross-region correlation heatmap & efficient frontier": mo.vstack([
            mo.ui.plotly(fig_corr),
            mo.ui.plotly(fig_ef),
            callout,
        ]),
    })
    return


@app.cell
def _(mo):
    mo.md("---\n## Glossary")
    return


@app.cell
def _(mo):
    glossary = mo.accordion({
        "ROC": mo.md("**Return on Capital** = Spread / Capital Charge. Higher = more spread per unit of capital consumed."),
        "RWA": mo.md("**Risk-Weighted Assets** — determines how much capital a bank must hold against a position."),
        "WARF": mo.md("**Weighted Average Rating Factor** — composite credit quality score for a CLO portfolio (lower = better)."),
        "WAS": mo.md("**Weighted Average Spread** — average coupon on the CLO's underlying loan pool."),
        "WAL": mo.md("**Weighted Average Life** — effective duration of the tranche."),
        "OC test": mo.md("**Overcollateralization test** — par value coverage ratio; breach diverts cash to senior tranches."),
        "Jr OC cushion": mo.md("**Junior OC cushion** — excess coverage above minimum OC test level. Key risk metric (higher = safer)."),
        "CCC bucket": mo.md("% of underlying loans rated CCC+ or below — typically capped at 7.5%."),
        "Subordination": mo.md("Credit enhancement sitting below a tranche — thicker buffer = more protection."),
        "Cross-currency basis swap": mo.md("Derivative converting 3mo Euribor cash flows to 3mo SOFR, capturing the rate differential."),
        "Solvency II": mo.md("EU insurance capital framework. Jan 2027 reform slashes CLO AAA capital charges by 60–80%."),
        "CLO arb": mo.md("WAS minus weighted-average cost of liabilities — determines the equity holder's profit margin."),
    })
    glossary
    return


if __name__ == "__main__":
    app.run()
