from __main__ import app

import os

import pandas as pd
from models.alpaca_wrapper import Alpaca
from models.portfolio import Portfolio
from models.metrics import Metrics
from models.market import Market

from flask import Flask
from flask import render_template
from flask import jsonify

@app.route("/health")
def health():
    return "healthy"

@app.route("/")
def index():
    return render_template("index.html", api_route=os.getenv("API_ROUTE"))

@app.route("/script/index.js")
def scriptIndex():
    spdr = Alpaca.get_historical_data(["SPY"])

    portfolio = pd.DataFrame(data={
        "ticker": ["NVDA", "UPS"],
        "shares": [120000, 44]
        })
    historical_data = Alpaca.get_historical_net_asset_value(portfolio)

    return render_template("index.js",
                           spdr=spdr,
                           historical_data=historical_data,
                           api_route=os.getenv("API_ROUTE"))


@app.route("/api/portfolio/metrics")
def portfolio_metrics():
    spdr = Alpaca.get_historical_data(["SPY"])
    portfolio = pd.DataFrame({
        "ticker": ["NVDA", "UPS"],
        "shares": [120000, 44]
    })
    historical_data = Alpaca.get_historical_net_asset_value(portfolio)

    port_df = pd.DataFrame(historical_data)
    bench_df = pd.DataFrame(spdr["SPY"])

    port_df["date"] = pd.to_datetime(port_df["date"])
    bench_df["date"] = pd.to_datetime(bench_df["date"])

    port_series = (
        port_df
        .set_index("date")["price close"]
        .sort_index()
    )

    bench_series = (
        bench_df
        .set_index("date")["price close"]
        .sort_index()
    )

    port_returns = Metrics.get_daily_returns(port_series)
    bench_returns = Metrics.get_daily_returns(bench_series)

    metrics = {
        "total_return": Metrics.get_ROI(port_series),
        "cagr": Metrics.get_CAGR(port_series),
        "volatility": Metrics.get_annual_volatility(port_returns),
        "sharpe": Metrics.get_sharpe_ratio(port_returns),
        "max_drawdown": Metrics.get_maximum_drawdown(port_series),
        "beta": Metrics.get_beta(port_returns, bench_returns),
        "alpha": Metrics.get_alpha(port_returns, bench_returns),
        "total_value": float(port_series.iloc[-1])
    }

    return jsonify(metrics)

@app.route("/api/portfolio/positions")
def portfolio_positions():
    portfolio = pd.DataFrame({
        "ticker": ["NVDA", "UPS"],
        "shares": [120000, 44]
    })

    raw_prices = Alpaca.get_historical_data(portfolio["ticker"].tolist())

    rows = []
    for ticker, data in raw_prices.items():
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])

        latest = df.sort_values("date").iloc[-1]

        rows.append({
            "ticker": ticker,
            "price": float(latest["price close"])
        })

    prices = pd.DataFrame(rows)

    df = portfolio.merge(prices, on="ticker", how="left")
    df["value"] = df["shares"] * df["price"]

    return jsonify(
        df[["ticker", "shares", "price", "value"]]
        .to_dict(orient="records")
    )
