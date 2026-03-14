"""
DCF Valuation Engine
Author: Wilfried LAWSON HELLU | Finance Analyst
GitHub: github.com/Wxlly00

Automated Discounted Cash Flow valuation:
- Live financials via yfinance (fallback: synthetic data)
- 2-stage DCF (explicit + terminal value)
- WACC via CAPM
- Sensitivity analysis: WACC vs terminal growth rate
"""

import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


def get_stock_data(ticker: str) -> dict:
    """Pull financial data for a ticker; fallback to synthetic if unavailable."""
    if YFINANCE_AVAILABLE:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            current_price = info.get("currentPrice") or info.get("regularMarketPrice") or 100

            # Get income statement
            income = stock.financials
            cashflow = stock.cashflow
            balance = stock.balance_sheet

            if income.empty or cashflow.empty:
                raise ValueError("Empty financials")

            revenues = income.loc["Total Revenue"].dropna().iloc[:4].values if "Total Revenue" in income.index else [5e9, 4.5e9, 4e9, 3.6e9]
            ebit_vals = income.loc["EBIT"].dropna().iloc[:4].values if "EBIT" in income.index else [0.15 * r for r in revenues]

            capex_vals = abs(cashflow.loc["Capital Expenditure"].dropna().iloc[:4].values) if "Capital Expenditure" in cashflow.index else [0.05 * r for r in revenues]
            da_vals = cashflow.loc["Depreciation And Amortization"].dropna().iloc[:4].values if "Depreciation And Amortization" in cashflow.index else [0.04 * r for r in revenues]

            # Net debt
            total_debt = info.get("totalDebt", 0) or 0
            cash = info.get("totalCash", 0) or 0
            net_debt = total_debt - cash
            shares = info.get("sharesOutstanding", 1e9) or 1e9
            beta = info.get("beta", 1.2) or 1.2
            name = info.get("longName", ticker)

            return {
                "ticker": ticker,
                "name": name,
                "current_price": float(current_price),
                "revenues": [float(r) for r in revenues],
                "ebit_vals": [float(e) for e in ebit_vals],
                "capex_vals": [float(c) for c in capex_vals],
                "da_vals": [float(d) for d in da_vals],
                "net_debt": float(net_debt),
                "shares": float(shares),
                "beta": float(beta),
                "tax_rate": 0.25,
                "data_source": "live",
            }
        except Exception as e:
            pass

    # Synthetic fallback (Apple-like financials)
    return {
        "ticker": ticker,
        "name": f"{ticker} Inc. (synthetic)",
        "current_price": 185.0,
        "revenues": [3.83e11, 3.74e11, 3.65e11, 3.55e11],
        "ebit_vals": [1.14e11, 1.09e11, 1.07e11, 1.00e11],
        "capex_vals": [1.07e10, 1.08e10, 1.09e10, 1.08e10],
        "da_vals": [1.13e10, 1.11e10, 1.09e10, 1.07e10],
        "net_debt": -5.0e10,  # net cash position
        "shares": 1.55e10,
        "beta": 1.25,
        "tax_rate": 0.25,
        "data_source": "synthetic",
    }


def calculate_fcff(data: dict) -> list:
    """
    Calculate historical Free Cash Flow to Firm:
    FCFF = EBIT × (1 - Tax Rate) + D&A - Capex - ΔNWC

    NWC change is estimated as 2% of revenue growth (simplified assumption).
    A positive revenue growth implies increased NWC investment (cash outflow).
    """
    fcff_list = []
    tax = data["tax_rate"]
    revenues = data["revenues"]
    years = min(len(revenues), len(data["ebit_vals"]),
                len(data["capex_vals"]), len(data["da_vals"]))

    for i in range(years):
        nopat = data["ebit_vals"][i] * (1 - tax)
        # Estimate NWC change: 2% of revenue growth vs prior year
        if i < years - 1:
            rev_growth = revenues[i] - revenues[i + 1]  # data is most-recent-first
        else:
            rev_growth = revenues[i] * 0.05  # assume ~5% growth for oldest year
        delta_nwc = 0.02 * abs(rev_growth) * (1 if rev_growth > 0 else -1)
        fcff = nopat + data["da_vals"][i] - data["capex_vals"][i] - delta_nwc
        fcff_list.append(fcff)

    return fcff_list


def hamada_unlever(beta_levered: float, debt_ratio: float, tax_rate: float) -> float:
    """
    Hamada equation: unlever beta to remove financial risk.
    β_unlevered = β_levered / (1 + (1 - t) × D/E)
    """
    d_e = debt_ratio / (1 - debt_ratio)
    return beta_levered / (1 + (1 - tax_rate) * d_e)


def hamada_relever(beta_unlevered: float, debt_ratio: float, tax_rate: float) -> float:
    """
    Hamada equation: re-lever beta for a target capital structure.
    β_levered = β_unlevered × (1 + (1 - t) × D/E)
    """
    d_e = debt_ratio / (1 - debt_ratio)
    return beta_unlevered * (1 + (1 - tax_rate) * d_e)


def estimate_wacc(beta: float, risk_free: float = 0.045, equity_premium: float = 0.055,
                  debt_rate: float = 0.05, debt_ratio: float = 0.25, tax_rate: float = 0.25,
                  target_debt_ratio: float = None) -> float:
    """
    WACC = Ke × (E/V) + Kd × (1-t) × (D/V)
    Ke = risk_free + β_relevered × equity_premium (CAPM)

    Hamada adjustment:
    1. Unlever the observed beta (remove current financial risk)
    2. Re-lever with target capital structure (default: same as debt_ratio)

    Args:
        beta: Observed (levered) beta from market data
        risk_free: Risk-free rate (default: 4.5%)
        equity_premium: Equity risk premium (default: 5.5%)
        debt_rate: Pre-tax cost of debt
        debt_ratio: Current D/(D+E) ratio used to unlever beta
        tax_rate: Corporate tax rate
        target_debt_ratio: Target D/(D+E) for re-levering (defaults to debt_ratio)
    """
    target = target_debt_ratio if target_debt_ratio is not None else debt_ratio
    # Step 1: Unlever observed beta
    beta_u = hamada_unlever(beta, debt_ratio, tax_rate)
    # Step 2: Re-lever at target structure
    beta_l = hamada_relever(beta_u, target, tax_rate)
    ke = risk_free + beta_l * equity_premium
    equity_ratio = 1 - target
    wacc = ke * equity_ratio + debt_rate * (1 - tax_rate) * target
    return wacc


def project_fcff(base_fcff: float, stage1_growth: float, stage2_growth: float,
                 terminal_growth: float, years_stage1: int = 5, years_stage2: int = 5) -> list:
    """2-stage FCFF projection."""
    projections = []
    current = base_fcff

    for _ in range(years_stage1):
        current *= (1 + stage1_growth)
        projections.append(current)

    for _ in range(years_stage2):
        current *= (1 + stage2_growth)
        projections.append(current)

    return projections


def terminal_value(fcff_terminal: float, wacc: float, terminal_growth: float) -> float:
    """Gordon Growth Model terminal value."""
    if wacc <= terminal_growth:
        raise ValueError("WACC must be greater than terminal growth rate")
    return fcff_terminal * (1 + terminal_growth) / (wacc - terminal_growth)


def dcf_valuation(fcff_projections: list, tv: float, wacc: float,
                  net_debt: float, shares: float) -> tuple:
    """
    Discount all cash flows + terminal value.
    Returns (intrinsic_value_per_share, pv_fcff, pv_tv, enterprise_value)
    """
    pv_fcff = sum(cf / (1 + wacc) ** (t + 1) for t, cf in enumerate(fcff_projections))
    pv_tv = tv / (1 + wacc) ** len(fcff_projections)
    enterprise_value = pv_fcff + pv_tv
    equity_value = enterprise_value - net_debt
    intrinsic = equity_value / shares
    return intrinsic, pv_fcff, pv_tv, enterprise_value


def sensitivity_table(data: dict, base_wacc: float, base_tgr: float,
                       stage1_g: float = 0.08, stage2_g: float = 0.05) -> pd.DataFrame:
    """WACC (rows) × Terminal Growth Rate (cols) sensitivity matrix."""
    wacc_range = np.arange(0.08, 0.15, 0.01)
    tgr_range = np.arange(0.01, 0.05, 0.005)

    fcff_list = calculate_fcff(data)
    base_fcff = abs(np.mean(fcff_list)) if fcff_list else 1e9

    table = {}
    for tgr in tgr_range:
        col = {}
        for w in wacc_range:
            try:
                projections = project_fcff(base_fcff, stage1_g, stage2_g, tgr)
                tv = terminal_value(projections[-1], w, tgr)
                iv, _, _, _ = dcf_valuation(projections, tv, w, data["net_debt"], data["shares"])
                col[f"{w*100:.1f}%"] = round(iv, 1)
            except Exception:
                col[f"{w*100:.1f}%"] = np.nan
        table[f"TGR {tgr*100:.1f}%"] = col

    df = pd.DataFrame(table)
    df.index.name = "WACC \\ TGR"
    return df


def run_valuation(ticker: str, stage1_growth: float = 0.08, stage2_growth: float = 0.05,
                  terminal_growth: float = 0.025, wacc_override: float = None) -> dict:
    """Full DCF valuation pipeline."""
    data = get_stock_data(ticker)
    fcff_list = calculate_fcff(data)

    if not fcff_list or max(abs(f) for f in fcff_list) == 0:
        return {"error": "Insufficient financial data"}

    # Use average FCFF as base
    base_fcff = abs(np.mean(fcff_list))

    wacc = wacc_override if wacc_override else estimate_wacc(data["beta"])
    projections = project_fcff(base_fcff, stage1_growth, stage2_growth, terminal_growth)
    tv = terminal_value(projections[-1], wacc, terminal_growth)
    iv, pv_fcff, pv_tv, ev = dcf_valuation(projections, tv, wacc, data["net_debt"], data["shares"])

    upside = (iv / data["current_price"] - 1) * 100 if data["current_price"] > 0 else 0

    return {
        "ticker": ticker,
        "name": data["name"],
        "current_price": data["current_price"],
        "intrinsic_value": round(iv, 2),
        "upside_pct": round(upside, 1),
        "enterprise_value": ev,
        "pv_fcff": pv_fcff,
        "pv_tv": pv_tv,
        "tv_pct": round(pv_tv / (pv_fcff + pv_tv) * 100, 1) if (pv_fcff + pv_tv) > 0 else 0,
        "wacc": round(wacc * 100, 2),
        "projections": projections,
        "data_source": data["data_source"],
        "data": data,
    }


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  DCF VALUATION ENGINE")
    print("  Author: Wilfried LAWSON HELLU | github.com/Wxlly00")
    print("="*60)

    result = run_valuation("AAPL", stage1_growth=0.08, stage2_growth=0.05, terminal_growth=0.025)

    if "error" not in result:
        print(f"\n  Company: {result['name']}")
        print(f"  Current Price: ${result['current_price']:.2f}")
        print(f"  Intrinsic Value: ${result['intrinsic_value']:.2f}")
        print(f"  Upside/Downside: {result['upside_pct']:+.1f}%")
        print(f"  WACC: {result['wacc']:.1f}%")
        print(f"  Terminal Value % of EV: {result['tv_pct']:.0f}%")
        print(f"  Data source: {result['data_source']}")
    else:
        print(f"  Error: {result['error']}")
