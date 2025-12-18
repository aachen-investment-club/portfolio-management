from __main__ import app

import os

from models.alpaca import Alpaca

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

    return render_template("index.js", spdr=spdr, api_route=os.getenv("API_ROUTE"))