import os 
from flask import request

import pandas as pd
import json

from models.metrics import Metrics
from models.market import Market
from models.alpaca import Alpaca

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