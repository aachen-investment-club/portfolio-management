import os 
from flask import request

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.historical import StockHistoricalDataClient

from datetime import datetime, timedelta

from __main__ import app

@app.route("/api/portfolio", methods=["POST"])
def portfolio():
    content = request.json
    
    # Init Alpaca Client
    client = StockHistoricalDataClient(
        os.getenv("APCA_API_KEY_ID"),
        os.getenv("APCA_API_SECRET_KEY")
    )
    tickers = set(map(lambda x: x["security"]["ticker"].split(".")[0], content["transactions"]))
    
    # Fetch from API
    req = StockBarsRequest(
        symbol_or_symbols=list(tickers),
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=10),
    )
    ticker_data = client.get_stock_bars(req)
    
    # Transform to JSON
    purchase_transactions = filter(lambda x: x["type"] =="PURCHASE", content["transactions"])
    portfolio_data = []
    for purchase in purchase_transactions:
        ticker = purchase["security"]["ticker"].split(".")[0]
        portfolio_data.append({
            "stock": purchase["security"]["name"],
            "current": ticker_data.data[ticker][-1].open,
            "shares": purchase["shares"],
            "asset_value": purchase["shares"] * ticker_data.data[ticker][-1].open
        })
    return portfolio_data