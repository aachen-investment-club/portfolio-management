from flask import request, session, Blueprint, make_response
import json

import pandas as pd

from portfolio.models.metrics import Metrics
from portfolio.models.alpaca_wrapper import Alpaca
from portfolio.utils.simulate import simulate
from portfolio.utils.portfolio_builder import build_real_portfolio


bp_api = Blueprint("bp_api", __name__)


def get_real_portfolio():
    portfolio_key = request.args.get("portfolio")
    initial_cash = float(request.args.get("cash", 1000000))
    leverage = float(request.args.get("leverage", 100000))

    portfolio, _ = build_real_portfolio(portfolio_key, initial_cash, leverage)
    return portfolio

@bp_api.route("/api/simulate/purchase", methods=["POST"])
def simulate_purchase():
    trade = request.json

    simulation = json.loads(
        request.cookies.get("simulation") or "[]"
    )
    simulation.append(trade)

    resp = make_response("Success")
    resp.set_cookie("simulation", json.dumps(simulation))
    return resp


@bp_api.route("/api/simulate/reset", methods=["POST"])
def reset_simulation():
    resp = make_response({"status": "cleared"})
    resp.set_cookie("simulation", "[]")
    return resp

@bp_api.route("/api/portfolio", methods=["POST"])
def portfolio():
    content = request.json
    purchases = list(filter(
        lambda x: x["type"] == "PURCHASE", content["transactions"]))
    tickers = list(map(
        lambda x: x["security"]["ticker"].split(".")[0], purchases))

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
