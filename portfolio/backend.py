from flask import request, session, Blueprint, make_response
import json
from typing import Optional

import pandas as pd
import requests as http_requests

from portfolio.models.metrics import Metrics
from portfolio.models.alpaca_wrapper import Alpaca
from portfolio.utils.simulate import simulate
from portfolio.utils.portfolio_builder import build_real_portfolio
from portfolio.utils.sentiment_client import get_sentiment_by_asset


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


@bp_api.route("/api/sentiment", methods=["POST"])
def sentiment():
    """
    Return sentiment data for a list of asset symbols.

    Expected JSON body:
      {
        "assets":     ["AAPL", "MSFT", ...],   # required
        "start_date": "YYYY-MM-DD",             # optional
        "end_date":   "YYYY-MM-DD"              # optional
      }

    Response:
      {
        "AAPL": { asset, article_count, average_sentiment, label, articles[] },
        "MSFT": { ... },
        ...
      }

    Any asset for which the sentiment service returns an error is included
    with an "error" key so that a single failed ticker does not abort the
    entire request.
    """
    content = request.json or {}
    assets: list = content.get("assets", [])
    start_date: Optional[str] = content.get("start_date")
    end_date: Optional[str] = content.get("end_date")

    results = {}
    for asset in assets:
        try:
            results[asset] = get_sentiment_by_asset(asset, start_date, end_date)
        except http_requests.HTTPError as e:
            results[asset] = {"error": str(e), "status_code": e.response.status_code if e.response is not None else None}
        except Exception as e:
            results[asset] = {"error": str(e)}

    return results
