"""
DCF Valuation Engine — Streamlit Dashboard
Author: Wilfried LAWSON HELLU | github.com/Wxlly00
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

from dcf_engine import run_valuation, sensitivity_table, get_stock_data

st.set_page_config(
    page_title="DCF Valuation Engine | Wilfried LAWSON HELLU",
    page_icon="🔢",
    layout="wide",
)

with st.sidebar:
    st.title("🔢 DCF Engine")
    ticker = st.text_input("Ticker Symbol", "AAPL").upper().strip()
    st.markdown("### Growth Assumptions")
    stage1 = st.slider("Stage 1 Growth (Yrs 1–5)", 0.0, 30.0, 8.0, 0.5) / 100
    stage2 = st.slider("Stage 2 Growth (Yrs 6–10)", 0.0, 20.0, 5.0, 0.5) / 100
    tgr = st.slider("Terminal Growth Rate", 0.5, 4.0, 2.5, 0.25) / 100
    override_wacc = st.checkbox("Override WACC")
    if override_wacc:
        wacc_val = st.slider("WACC (%)", 5.0, 18.0, 10.0, 0.25) / 100
    else:
        wacc_val = None
    run = st.button("🚀 Run Valuation", type="primary", use_container_width=True)
    st.markdown("---")
    st.caption("By [Wilfried LAWSON HELLU](https://linkedin.com/in/wilfried-lawsonhellu)")

st.title("🔢 DCF Valuation Engine")
st.markdown("*Automated intrinsic value estimation via 2-stage Discounted Cash Flow*")

if not run:
    st.info("Enter a ticker and click **Run Valuation** to start")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **Methodology:**
        - FCFF = EBIT × (1–Tax) + D&A – Capex
        - WACC via CAPM (auto-estimated from Beta)
        - 2-Stage DCF: explicit 10-year projection + terminal value
        - Sensitivity: WACC × Terminal Growth Rate matrix
        """)
    st.stop()

with st.spinner(f"Fetching data and running DCF for {ticker}..."):
    result = run_valuation(ticker, stage1, stage2, tgr, wacc_val)

if "error" in result:
    st.error(f"Valuation error: {result['error']}")
    st.stop()

# ─── Header metrics ───────────────────────────────────────────────────────
st.markdown(f"### {result['name']} ({ticker})")
data_badge = "🟢 Live Data" if result["data_source"] == "live" else "🟡 Synthetic Data"
st.caption(f"{data_badge} | WACC: {result['wacc']:.1f}% | Terminal Value: {result['tv_pct']:.0f}% of EV")

upside = result["upside_pct"]
if upside > 10:
    verdict = "🟢 Undervalued"
    color = "#4CAF50"
elif upside < -10:
    verdict = "🔴 Overvalued"
    color = "#EF4444"
else:
    verdict = "🟡 Fairly Valued"
    color = "#FFC107"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Intrinsic Value", f"${result['intrinsic_value']:.2f}")
c2.metric("Current Price", f"${result['current_price']:.2f}")
c3.metric("Upside / Downside", f"{upside:+.1f}%")
c4.markdown(f"<br><span style='font-size:1.3rem; font-weight:bold; color:{color}'>{verdict}</span>",
            unsafe_allow_html=True)

st.markdown("---")

# ─── Charts ───────────────────────────────────────────────────────────────
col_a, col_b = st.columns([1.2, 1])

with col_a:
    st.subheader("📊 FCF Projections + Terminal Value")
    projections = result["projections"]
    years = [f"Y{i+1}" for i in range(len(projections))]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=years, y=[p/1e9 for p in projections],
        name="Projected FCFF", marker_color="#C9A84C",
    ))
    
    # Show TV contribution conceptually
    tv_bar_height = result["pv_tv"] / result["enterprise_value"] * max(projections) / 1e9
    fig.add_trace(go.Bar(
        x=["TV"], y=[result["pv_tv"]/1e9],
        name="Terminal Value (PV)", marker_color="#4A6FA5",
    ))
    
    fig.update_layout(
        paper_bgcolor="#050D1A", plot_bgcolor="#0A1628",
        font_color="#94A3B8",
        xaxis=dict(gridcolor="#1E2D45"),
        yaxis=dict(title="FCFF (€B)", gridcolor="#1E2D45"),
        title="10-Year FCFF Projection + Terminal Value",
        title_font_color="white",
        legend=dict(bgcolor="#0A1628", font=dict(color="white")),
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("🎯 Value Composition")
    pv_fcff_pct = result["pv_fcff"] / (result["pv_fcff"] + result["pv_tv"]) * 100
    pv_tv_pct = result["tv_pct"]
    
    fig2 = go.Figure(go.Pie(
        labels=["Explicit Period FCFF", "Terminal Value"],
        values=[pv_fcff_pct, pv_tv_pct],
        hole=0.5,
        marker=dict(colors=["#C9A84C", "#4A6FA5"]),
        textinfo="label+percent",
        textfont=dict(color="white"),
    ))
    fig2.update_layout(
        paper_bgcolor="#050D1A",
        font_color="white",
        title="Enterprise Value Decomposition",
        title_font_color="white",
        height=380,
        annotations=[dict(text=f"EV<br>${result['enterprise_value']/1e9:.1f}B",
                           x=0.5, y=0.5, font_size=14, showarrow=False,
                           font_color="white")],
    )
    st.plotly_chart(fig2, use_container_width=True)

# ─── Sensitivity Table ─────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📋 Sensitivity Analysis: WACC × Terminal Growth Rate")
st.caption("Intrinsic value per share ($) — Green = upside vs current price | Red = downside")

with st.spinner("Computing sensitivity matrix..."):
    data_obj = result["data"]
    sens_df = sensitivity_table(data_obj, result["wacc"]/100, tgr, stage1, stage2)

current_price = result["current_price"]

def color_sensitivity(val):
    try:
        v = float(val)
        if v > current_price * 1.1:
            return "background-color: rgba(76,175,80,0.25); color: #4CAF50"
        elif v > current_price * 0.9:
            return "background-color: rgba(255,193,7,0.15); color: #FFC107"
        else:
            return "background-color: rgba(239,68,68,0.2); color: #EF4444"
    except Exception:
        return ""

styled_sens = sens_df.style.applymap(color_sensitivity)
st.dataframe(styled_sens, use_container_width=True)
st.caption(f"Current Price: ${current_price:.2f} | Green = >10% upside | Yellow = ±10% | Red = >10% downside")

st.caption("Built by **Wilfried LAWSON HELLU** | Finance Analyst | github.com/Wxlly00")
