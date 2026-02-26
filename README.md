# DCF Valuation Engine

> Automated Discounted Cash Flow valuation with live financial data integration

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28-red)](https://streamlit.io)

## Overview

An automated DCF engine that pulls real financial data and generates intrinsic valuations with WACC-based discounting, 2-stage growth modeling, and sensitivity analysis.

## Methodology

### Free Cash Flow to Firm (FCFF)
```
FCFF = EBIT × (1 - Tax Rate) + D&A - Capex
```

### WACC (Capital Asset Pricing Model)
```
Ke = Rf + β × ERP
WACC = Ke × (E/V) + Kd × (1-t) × (D/V)
Default: Rf=4.5%, ERP=5.5%
```

### 2-Stage DCF
- **Stage 1** (Years 1–5): High-growth phase (explicit projection)
- **Stage 2** (Years 6–10): Growth normalization
- **Terminal Value**: Gordon Growth Model `TV = FCFF × (1+g) / (WACC - g)`

### Sensitivity Analysis
Matrix of intrinsic values across WACC (8–14%) × Terminal Growth Rate (1–4%)

## Tech Stack

`Python 3.11` `Streamlit` `yfinance` `pandas` `numpy` `Plotly`

## How to Run

```bash
pip install -r requirements.txt

# Terminal output
python dcf_engine.py

# Streamlit dashboard
streamlit run app.py
```

## Author

**Wilfried LAWSON HELLU** | Finance Analyst  
📧 wilfriedlawpro@gmail.com | 🔗 [LinkedIn](https://linkedin.com/in/wilfried-lawsonhellu) | 🐙 [GitHub](https://github.com/Wxlly00)
