# streamlit_ui.py
import streamlit as st
import requests
import base64
from io import BytesIO

# ---------- config ----------
st.set_page_config(
    page_title="Monte Carlo Stock Price Simulator",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# prefer a secret if you set one in Streamlit
API_URL = st.secrets.get(
    "API_URL",
    "https://monte-carlo-stock-simulator.onrender.com"  # <— your Render backend
)

# ---------- header ----------
st.title("📈 Monte Carlo Stock Price Simulator")
st.write("enter a stock ticker to simulate one year price paths and visualize risk metrics")

ticker = st.text_input("stock ticker (example AAPL NEE MSFT)", value="AAPL")

run = st.button("run simulation")

# small helper to show base64 pngs returned by the api
def show_b64_png(b64_png: str, caption: str = ""):
    try:
        img_bytes = base64.b64decode(b64_png)
        st.image(BytesIO(img_bytes), caption=caption, use_container_width=True)
    except Exception as e:
        st.error(f"could not render image. {e}")

# ---------- main action ----------
if run:
    if not ticker.strip():
        st.warning("please enter a ticker")
        st.stop()

    with st.spinner("running Monte Carlo simulation…"):
        try:
            resp = requests.get(f"{API_URL}/montecarlo", params={"ticker": ticker.strip()})
        except Exception as e:
            st.error(f"could not reach the backend. check API_URL and internet. {e}")
            st.info(f"API_URL in use: {API_URL}")
            st.stop()

    if resp.status_code != 200:
        try:
            msg = resp.json()
        except Exception:
            msg = resp.text
        st.error(f"backend error {resp.status_code}. {msg}")
        st.stop()

    result = resp.json()

    st.subheader(f"results for {result.get('ticker', ticker).upper()}")

    # top summary row
    col1, col2, col3 = st.columns(3)
    spot = result.get("spot_price")
    mu = result.get("mu_annual")
    sigma = result.get("sigma_annual")

    with col1:
        if spot is not None:
            st.metric("current price", f"${spot:,.2f}")
            st.caption("last adjusted close from price history")
    with col2:
        if mu is not None:
            st.metric("expected annual return", f"{mu*100:.2f}%")
            st.caption("average drift used in the simulation based on recent history")
    with col3:
        if sigma is not None:
            st.metric("volatility", f"{sigma*100:.2f}%")
            st.caption("how wide paths tend to spread. higher means more risk")

    st.markdown("---")

    # risk metrics
    st.subheader("risk metrics")

    r_VaR = result.get("VaR95_return")
    r_ES = result.get("ES95_return")
    pnl_mean = result.get("mean_pnl")
    pnl_std = result.get("std_pnl")
    pnl_VaR = result.get("VaR95_pnl")
    pnl_ES = result.get("ES95_pnl")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if r_VaR is not None:
            st.metric("VaR 95% (return)", f"{r_VaR*100:.2f}%")
            st.caption("bad but not worst case over one year")
    with c2:
        if r_ES is not None:
            st.metric("ES 95% (return)", f"{r_ES*100:.2f}%")
            st.caption("average of the worst five percent returns")
    with c3:
        if pnl_mean is not None:
            st.metric("mean PnL", f"${pnl_mean:,.2f}")
            st.caption("average profit or loss for the position in dollars")
    with c4:
        if pnl_VaR is not None:
            st.metric("VaR 95% PnL", f"${pnl_VaR:,.0f}")
            st.caption("dollar loss level that only gets breached five percent of the time")

    # second row for extra color
    d1, d2 = st.columns(2)
    with d1:
        if pnl_std is not None:
            st.metric("std PnL", f"${pnl_std:,.2f}")
            st.caption("spread of outcomes in dollars around the average")
    with d2:
        if pnl_ES is not None:
            st.metric("ES 95% PnL", f"${pnl_ES:,.0f}")
            st.caption("average loss inside the worst five percent. deeper cut than VaR")

    # a short plain language explainer
    st.info(
        "what you are seeing: we estimated average return and volatility from recent daily data "
        "then simulated many one year paths using geometric brownian motion. VaR is a downside guardrail "
        "ES shows how rough it gets inside that tail. charts below show the spread of final prices and sample paths"
    )

    st.markdown("---")

    # charts
    st.subheader("simulated price paths and distribution")

    paths_plot = result.get("paths_plot")
    hist_plot = result.get("histogram_plot")

    if paths_plot:
        show_b64_png(paths_plot, caption=f"{result.get('ticker', ticker).upper()} Monte Carlo simulated paths")
    if hist_plot:
        show_b64_png(hist_plot, caption="distribution of terminal prices after one year")

    # debug section if needed
    with st.expander("details"):
        st.json({k: v for k, v in result.items() if k not in ["paths_plot", "histogram_plot"]})

# footer
st.caption(f"backend api: {API_URL}")
