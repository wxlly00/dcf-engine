# DCF Valuation Engine

> Automated Discounted Cash Flow valuation with live market data, Hamada beta adjustment, and sensitivity analysis.

## Description

A production-ready DCF engine that pulls live financials via **yfinance** (with synthetic fallback) and computes intrinsic value per share through a 2-stage DCF model. Features include Hamada-adjusted WACC, NWC-aware FCFF calculation, and an interactive Streamlit dashboard with WACC × terminal growth sensitivity heatmap.

## Tech Stack

| Layer | Library |
|-------|---------|
| Data  | `yfinance` |
| Numerics | `numpy`, `pandas` |
| Optimisation | `scipy` |
| Visualisation | `plotly`, `streamlit` |

## Installation

```bash
git clone https://github.com/Wxlly00/dcf-engine.git
cd dcf-engine
pip install -r requirements.txt
```

## Usage

### CLI
```bash
python dcf_engine.py          # Runs AAPL demo
```

### Streamlit App
```bash
streamlit run app.py
```

Enter any ticker (e.g. `MSFT`, `TSLA`), adjust growth assumptions, and get an instant valuation with sensitivity table.

## Features

- **Live financials** via yfinance (revenue, EBIT, CapEx, D&A, net debt, beta) — synthetic fallback if unavailable
- **Hamada beta adjustment** — unlever observed beta, re-lever at target capital structure before computing WACC
- **NWC change in FCFF** — estimated at 2% of revenue growth for each historical period
- **2-stage DCF** — explicit 10-year projection + Gordon Growth terminal value
- **WACC via CAPM** — `Ke = Rf + β_levered × ERP`
- **Sensitivity heatmap** — WACC (8–14%) × Terminal Growth Rate (1–4.5%)
- **Upside/downside** vs current market price

## Model Details

### FCFF
```
FCFF = EBIT × (1 − Tax) + D&A − CapEx − ΔNWC
ΔNWC ≈ 2% × ΔRevenue
```

### Hamada-Adjusted WACC
```
β_unlevered  = β_levered / (1 + (1−t) × D/E)
β_relevered  = β_unlevered × (1 + (1−t) × D/E_target)
Ke           = Rf + β_relevered × ERP
WACC         = Ke × (E/V) + Kd × (1−t) × (D/V)
```

## Author

**Wilfried LAWSON HELLU** — Finance Analyst  
[github.com/Wxlly00](https://github.com/Wxlly00)
