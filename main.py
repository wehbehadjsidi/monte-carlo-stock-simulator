from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime, timedelta

app = FastAPI(title="Monte Carlo Stock Simulator")

# allow your Streamlit app to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # you can restrict later to your streamlit domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- utils ----------
def simulate_gbm(S0, mu, sigma, T, steps, n_sims, seed=123):
    rng = np.random.default_rng(seed)
    dt = T / steps
    Z = rng.standard_normal(size=(n_sims, steps))
    increments = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * Z
    log_paths = np.cumsum(increments, axis=1)
    S_paths = S0 * np.exp(log_paths)
    return np.hstack([np.full((n_sims, 1), S0), S_paths])

def plot_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")

# ---------- core ----------
def run_monte_carlo(
    ticker: str,
    years_history=5,
    horizon_years=1.0,
    steps=252,
    n_sims=10000,
    position_shares=200
):
    ticker = ticker.upper().strip()

    # download price history with one retry
    data = None
    for attempt in range(2):
        try:
            data = yf.download(
                ticker,
                start=datetime.today() - timedelta(days=int(years_history * 365)),
                end=datetime.today(),
                progress=False,
                auto_adjust=True
            )
            if data is not None and len(data) > 0:
                break
        except Exception as e:
            if attempt == 1:
                raise ValueError(f"error downloading data for {ticker}: {e}")

    if data is None or len(data) == 0:
        raise ValueError(f"no price data found for {ticker}. check if it is valid or delisted.")

    price_col = "Adj Close" if "Adj Close" in data.columns else "Close"
    if price_col not in data.columns:
        raise ValueError(f"neither 'Adj Close' nor 'Close' found for {ticker}.")

    close = data[price_col].dropna()
    if close.empty:
        raise ValueError(f"no valid prices found for {ticker}.")

    # estimate parameters
    S0 = float(close.iloc[-1])
    daily_returns = close.pct_change().dropna()
    mu_daily = float(daily_returns.mean())
    sigma_daily = float(daily_returns.std())

    mu_annual = (1 + mu_daily) ** 252 - 1.0
    sigma_annual = sigma_daily * np.sqrt(252)

    # simulate paths
    S_paths = simulate_gbm(S0, mu_annual, sigma_annual, horizon_years, steps, n_sims)
    terminal_prices = S_paths[:, -1]
    terminal_returns = terminal_prices / S0 - 1.0

    # risk metrics
    VaR95_ret = np.percentile(terminal_returns, 5)
    ES95_ret = terminal_returns[terminal_returns <= VaR95_ret].mean()

    pnl = (terminal_prices - S0) * position_shares
    VaR95_pnl = np.percentile(pnl, 5)
    ES95_pnl = pnl[pnl <= VaR95_pnl].mean()

    # plots
    fig1, ax1 = plt.subplots()
    ax1.hist(terminal_prices, bins=60)
    ax1.set_title(f"{ticker} Monte Carlo: Terminal Price Distribution (1 year)")
    ax1.set_xlabel("terminal price")
    ax1.set_ylabel("frequency")
    hist_b64 = plot_to_base64(fig1)
    plt.close(fig1)

    fig2, ax2 = plt.subplots()
    for i in range(min(50, n_sims)):
        ax2.plot(S_paths[i, :], linewidth=0.8)
    ax2.set_title(f"{ticker} Monte Carlo: First 50 simulated paths")
    ax2.set_xlabel("trading days")
    ax2.set_ylabel("price")
    paths_b64 = plot_to_base64(fig2)
    plt.close(fig2)

    return {
        "ticker": ticker,
        "spot_price": round(S0, 2),
        "mu_annual": round(mu_annual, 4),
        "sigma_annual": round(sigma_annual, 4),
        "mean_return": round(terminal_returns.mean(), 4),
        "std_return": round(terminal_returns.std(), 4),
        "VaR95_return": round(VaR95_ret, 4),
        "ES95_return": round(ES95_ret, 4),
        "mean_pnl": round(pnl.mean(), 2),
        "std_pnl": round(pnl.std(), 2),
        "VaR95_pnl": round(VaR95_pnl, 2),
        "ES95_pnl": round(ES95_pnl, 2),
        "histogram_plot": hist_b64,
        "paths_plot": paths_b64
    }

# ---------- endpoint ----------
@app.get("/montecarlo")
async def montecarlo_endpoint(ticker: str = Query(..., description="stock ticker like AAPL")):
    try:
        result = run_monte_carlo(ticker)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
