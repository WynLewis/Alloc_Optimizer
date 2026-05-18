# CLO Allocation Optimizer

Interactive marimo notebook for optimizing CLO tranche allocation by Return on Capital (ROC), incorporating current spreads, historical curve steepness, manager quality, cross-region correlation and stress scenarios.

## Run

```bash
pip install -r requirements.txt
# Edit mode (tweak inputs and code):
marimo edit clo_allocation_optimizer.py
# App mode (clean read-only UI):
marimo run clo_allocation_optimizer.py
```

## Sections

1. **Deal-Level ROC Analysis** — Per-tranche raw / loss-adjusted / hedged ROC under selectable capital framework (Basel III Std/IRB, Solvency II current/post-reform, custom).
2. **Curve Steepness Dashboard** — Current spread curve vs historical range, AAA→BB differential time series, percentile signals.
3. **Allocation Optimizer** — SLSQP maximization of weighted ROC subject to per-tranche bounds, WAL band, and capital budget; sensitivity under parallel shifts.
4. **Cross-Region Comparison** — EUR vs US spreads, basis-swap math, hedged ROC winner per tranche.
5. **Scenario / Stress Analysis** — Parallel shifts, steepener/flattener, Mar 2026 replay, custom; DV01-style P&L on the optimal allocation.
6. **Manager Quality Overlay** — Composite quality score from Jr OC / CCC / WARF, manager-adjusted ROC heatmap.
7. **Portfolio Correlation & Efficient Frontier** — 5y correlation heatmap, random-portfolio cloud, SLSQP efficient frontier, current / proposed / combined points.

All inputs are reactive: changing a spread, slider, or dropdown in any section cascades through downstream calculations and charts automatically.

Branding follows the Nationwide palette (Vibrant Blue `#0047BB`, Dark Blue `#141B4D`, Teal, Orange) via a plotly template registered at notebook start.
