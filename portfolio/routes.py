from __main__ import app

import os

import pandas as pd
from models.alpaca_wrapper import Alpaca
from models.portfolio import Portfolio

from flask import Flask
from flask import render_template
from flask import request
from models.market import Market

from schemas.market import Base
from utils.aws_config import engine

Base.metadata.create_all(engine)




@app.route("/health")
def health():
    return "healthy"

@app.route("/")
def index():


    perform = False 
    if perform: 
        Market.load_from_csv("./data/sp500_close_current.csv")

    portfolios = Portfolio.list_portfolios()

    selected_key = request.args.get("portfolio")


    if not portfolios : 
        selected_key = None
        selected_data = None

    else: 
        if selected_key not in portfolios: 
            selected_key= next(iter(portfolios))
        selected_data = portfolios[selected_key]


    portfolio = Portfolio(100000, 100000)

    portfolio.import_from_dict(selected_data)



    portfolio_metrics = {
        "total_return": "12.4%",
        "cagr": "8.1%",
        "volatility": "14.3%",
        "sharpe": 1.25,
        "beta": 0.92
    }
    positions= portfolio.get_position_weights()

    nav = portfolio.get_daily_nav() 
    
    #: has to be converted to a list of dicts for json 
    nav_ts = [
        {"date": d.strftime("%Y-%m-%d"), "nav": float(v)}
        for d, v in nav.items()
    ]

    return render_template(
        "index.html", 
        portfolios = portfolios, 
        selected_key = selected_key, 
        metrics=portfolio_metrics,
        positions=positions, 
        nav_ts=nav_ts,         
        api_route=os.getenv("API_ROUTE"), 
    )




@app.route("/script/index.js")
def scriptIndex():

    return render_template("index.js",  api_route=os.getenv("API_ROUTE"))
