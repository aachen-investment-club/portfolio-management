import requests as req
import os 
import json
import random 

from flask import request
from __main__ import app

@app.route("/api/portfolio", methods=["POST"])
def portfolio():
    content = request.json
    
    ticker_data = dict()
    for ticker in set(map(lambda x: x["security"]["ticker"], content["transactions"])):
        ticker = ticker.split(".")[0]
        # url = f"https://api.massive.com/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}" + \
        #     f"?apiKey={os.getenv("MASSIVE_API_KEY")}"
        # response = req.get(url)
        # response.raise_for_status()
        ticker_data[ticker] = round(random.random() * 200.0, 2)
    ticker_data

    purchase_transactions = filter(lambda x: x["type"] =="PURCHASE", content["transactions"])
    portfolio_data = []
    for purchase in purchase_transactions:
        ticker = purchase["security"]["ticker"].split(".")[0]
        portfolio_data.append({
            "stock": purchase["security"]["name"],
            "current": ticker_data[ticker],
            "shares": purchase["shares"],
            "asset_value": purchase["shares"] * ticker_data[ticker]
        })
    return portfolio_data