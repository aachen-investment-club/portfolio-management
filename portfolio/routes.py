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
from models.metrics import Metrics

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



    positions= portfolio.get_position_weights()

    nav = portfolio.get_daily_nav() 
    
    #: has to be converted to a list of dicts for json 
    nav_ts = [
        {"date": d.strftime("%Y-%m-%d"), "nav": float(v)}
        for d, v in nav.items()
    ]

    bench_df = Market.get_us_treasury_bonds()


    
    bench_series = (
        bench_df
        ["price close"]
        .sort_index())


    port_returns = Metrics.get_daily_returns(nav)
    bench_returns = Metrics.get_daily_returns(bench_series)
    
    print(bench_returns.head() )

    portf_positions_df = portfolio.get_portfolio_positions_df() 

    portf_data = Market.get_historical_data(portf_positions_df["ticker"].to_list())
    port_weights = Metrics.get_portfolio_weights(portf_positions_df, portf_data)

    print(type(port_returns))

    metrics = {
        "total_return": f"{Metrics.get_ROI(nav):.2f}%",
        "cagr": f"{Metrics.get_CAGR(nav):.2f}%",
        "volatility": f"{Metrics.get_annual_volatility(port_returns):.2f}",
        "sharpe": f"{Metrics.get_sharpe_ratio(port_returns):.7f}",
        "max_drawdown": f"{Metrics.get_maximum_drawdown(nav):.7f}",
        "beta": f"{Metrics.get_beta(port_returns, bench_returns):.7f}",
        "alpha": f"{Metrics.get_alpha(port_returns, bench_returns):.7f}",
        "total_value": f"{float(nav.iloc[-1]):.7f}",
        #"value_at_risk": Metrics.get_value_at_risk(port_returns, port_weights)
    }



    return render_template(
        "index.html", 
        portfolios = portfolios, 
        selected_key = selected_key, 
        metrics=metrics,
        positions=positions, 
        nav_ts=nav_ts,         
        api_route=os.getenv("API_ROUTE"), 
    )




@app.route("/script/index.js")
def scriptIndex():

    return render_template("index.js",  api_route=os.getenv("API_ROUTE"))
