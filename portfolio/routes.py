from __main__ import app

import os

import pandas as pd
from models.alpaca_wrapper import Alpaca
from models.portfolio import Portfolio

from flask import Flask
from flask import render_template

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
