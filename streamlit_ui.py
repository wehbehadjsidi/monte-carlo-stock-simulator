import streamlit as st
import requests
import base64
from io import BytesIO

st.set_page_config(
    page_title="Monte Carlo Stock Price Simulator",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("📈 Monte Carlo Stock Price Simulator")
st.write("Enter a stock ticker to simulate one-year price paths and visualize key risk metrics.")

ticker = st.text_input("Stock Ticker (e.g., AAPL, NEE, MSFT)", value="AAPL")

if st.button("Run Simulation"):
    with st.spinner("Running Monte Carlo simulation..."):
        try:
            response = requests.get(f"http://127.0.0.1:8000/montecarlo?ticker={ticker}")
            if response.status_code == 200:
                result = response.json()

                # ---- RESULTS SECTION ----
                st.subheader(f"Results for {result['ticker']}")
                col1, col2, col3 = st.columns(3)
                col1.metric("Current Price", f"${result['spot_price']}")
                col2.metric("Expected Annual Return", f"{result['mu_annual'] * 100:.2f}%")
                col3.metric("Volatility", f"{result['sigma_annual'] * 100:.2f}%")

                st.markdown(
                    "> **Insight:** The expected annual return is the average yearly growth implied by historical data, while volatility measures how widely prices may swing around that average. Higher volatility means greater uncertainty."
                )

                # ---- RISK METRICS SECTION ----
                st.markdown("---")
                st.subheader("Risk Metrics")
                col4, col5, col6, col7 = st.columns(4)
                col4.metric("VaR (95%)", f"{result['VaR95_return'] * 100:.2f}%")
                col5.metric("ES (95%)", f"{result['ES95_return'] * 100:.2f}%")
                col6.metric("Mean PnL", f"${result['mean_pnl']}")
                col7.metric("VaR95 PnL", f"${result['VaR95_pnl']}")

                st.markdown(
                    "> **Insight:** VaR (Value at Risk) shows the potential loss in the worst 5% of scenarios, while ES (Expected Shortfall) shows the *average* loss within those worst cases. Mean PnL reflects your expected gain or loss across all simulations."
                )

                # ---- VISUALIZATIONS ----
                st.markdown("---")
                st.subheader("Simulated Price Paths")
                img1 = base64.b64decode(result["paths_plot"])
                st.image(BytesIO(img1))
                st.markdown(
                    "> **Insight:** Each line shows one simulated path for the stock’s price over the next year, based on historical drift and volatility. These paths illustrate possible outcomes under the geometric brownian motion model."
                )

                st.subheader("Terminal Price Distribution")
                img2 = base64.b64decode(result["histogram_plot"])
                st.image(BytesIO(img2))
                st.markdown(
                    "> **Insight:** This histogram shows where the simulated prices ended after one year. The shape gives a sense of how likely different future prices are, centered around the expected return."
                )

            else:
                st.error(f"Error: {response.json().get('error', 'Unknown error')}")
        except Exception as e:
            st.error(f"An error occurred: {e}")
