from flask import request, session

import pandas as pd

from models.metrics import Metrics
from models.alpaca_wrapper import Alpaca
from utils.simulation import add_trade, clear_simulation, get_simulation
from utils.simulate import simulate
from utils.portfolio_builder import build_real_portfolio


from __main__ import app


@app.route("/api/portfolio", methods=["POST"])
def portfolio():
    content = request.json
    purchases = list(filter(lambda x: x["type"] == "PURCHASE", content["transactions"]))
    tickers = list(map(lambda x: x["security"]["ticker"].split(".")[0], purchases))

    df = pd.DataFrame({
        "ticker": tickers,
        "shares": list(map(lambda x: x["shares"], purchases))
    })

    # Transform to JSON
    portfolio_data = Metrics.get_basic_metrics(df)
    historical_data = Alpaca.get_historical_net_asset_value(df)
    return {
        "portfolio": portfolio_data.to_dict(orient="records"),
        "historical": historical_data
    }

def get_real_portfolio():
    portfolio_key = request.args.get("portfolio")
    initial_cash = float(request.args.get("cash", 1000000))
    leverage = float(request.args.get("leverage", 100000))

    portfolio, _ = build_real_portfolio(portfolio_key, initial_cash, leverage)
    return portfolio

@app.route("/api/simulate/purchase", methods=["POST"])
def simulate_purchase():
    trade = request.json
    add_trade(trade)

    base = session.get("base_portfolio")
    if base is None:
        return {"error": "No base portfolio"}, 400

    initial_cash = float(request.args.get("cash", 1000000))
    leverage = float(request.args.get("leverage", 100000))

    nav, metrics = simulate(base, get_simulation(), initial_cash, leverage)

    nav_ts = [
        {"date": d.strftime("%Y-%m-%d"), "nav": float(v)}
        for d, v in nav.items()
    ]

    return {"nav": nav_ts, "metrics": metrics}


@app.route("/api/simulate/reset", methods=["POST"])
def reset_simulation():
    clear_simulation()
    return {"status": "cleared"}