from flask import Blueprint, render_template, request, jsonify
import os
import datetime
import pandas as pd

from models.portfolio import Portfolio
from models.metrics import Metrics
from models.market import Market
from schemas.market import Base
from utils.aws_config import engine
from extensions import cache
from flask import render_template
from flask import request, jsonify
from flask import session

bp = Blueprint("bp", __name__)


Base.metadata.create_all(engine)


@bp.route("/health")
def health():
    return "healthy"


@bp.route("/update_market")
def update_market():
    Market.update_market()
    return {"status": "success"}


@cache.memoize(timeout=600)
def get_cached_nav_data(
        selected_data,
        initial_cash,
        leverage_limit):
    portfolio = Portfolio(initial_cash, leverage_limit)
    portfolio.import_from_dict(selected_data)
    nav = portfolio.get_daily_nav()

    return portfolio, nav


@cache.memoize(timeout=600)
def get_cached_bonds_data():
    return Market.get_us_treasury_bonds()


@bp.route("/")
def index():
    initial_cash = request.args.get("cash", default=1000000, type=float)
    leverage_limit = request.args.get("leverage", default=100000, type=float)

    default_start = datetime.datetime(2000, 1, 3).date().strftime('%Y-%m-%d')
    start_date = request.args.get("start_date", default=default_start)
    start_date = pd.to_datetime(
            datetime.datetime.strptime(start_date, '%Y-%m-%d').date())

    default_end = Market.get_latest_date_in_db().strftime('%Y-%m-%d')
    end_date = request.args.get("end_date", default=default_end) or default_end
    end_date = pd.to_datetime(
            datetime.datetime.strptime(end_date, '%Y-%m-%d').date())

    portfolios = Portfolio.list_portfolios()
    selected_key = request.args.get("portfolio")
    shown = request.args.getlist("shown")

    if not portfolios:
        selected_key = None
        selected_data = None
    else:
        if selected_key not in portfolios:
            selected_key = next(iter(portfolios))
        selected_data = portfolios[selected_key]
    bench_df = get_cached_bonds_data()

    selected_portfolio = None
    nav = None
    all_charts = []
    shown_portfolios = [
        (k, v)
        for k, v in portfolios.items()
        if k == selected_key or k in shown
    ]
    for key, portfolio in shown_portfolios:
        p, data =  get_cached_nav_data(
            portfolio, initial_cash, leverage_limit
        )
        data = data[data.index >= start_date]
        data = data[data.index <= end_date]

        if key == selected_key:
            selected_portfolio = p
            nav = data
        
        json_data = {
            "x": list(map(lambda x: x.strftime("%Y-%m-%d"), data.index)),
            "y": list(data),
            "name": key.split("/")[-1]
        }
        all_charts.append(json_data)


    positions = selected_portfolio.get_position_weights()
    nav = nav[nav.index >= start_date]
    nav = nav[nav.index <= end_date]

    bench_df = bench_df[bench_df.index >= start_date]
    bench_df = bench_df[bench_df.index <= end_date]

    bench_series = (bench_df["price close"].sort_index())

    port_returns = Metrics.get_daily_returns(nav)
    bench_returns = Metrics.get_daily_returns(bench_series)

    # portf_positions_df = selecportfolio.get_portfolio_positions_df() 
    # portf_data = Market.get_historical_data(portf_positions_df["ticker"].to_list())
    # port_weights = Metrics.get_portfolio_weights(portf_positions_df, portf_data)

    metrics = {
        "total_return": f"{Metrics.get_ROI(nav):.7f}%",
        "cash": f"${selected_portfolio.cash:.1f}",
        "cagr": f"{Metrics.get_CAGR(nav):.7f}%",
        "volatility": f"{Metrics.get_annual_volatility(port_returns):.7f}",
        "sharpe": f"{Metrics.get_sharpe_ratio(port_returns):.7f}",
        "max_drawdown": f"{Metrics.get_maximum_drawdown(nav):.7f}",
        "beta": f"{Metrics.get_beta(port_returns, bench_returns):.7f}",
        "alpha": f"{Metrics.get_alpha(port_returns, bench_returns):.7f}",
        "total_value": f"${float(nav.iloc[-1]):.1f}",
        # "value_at_risk": Metrics.get_value_at_risk(port_returns, port_weights)
    }
    session["base_portfolio"] = selected_data
    return render_template(
        "index.html",
        portfolios=portfolios,
        selected_key=selected_key,
        metrics=metrics,
        positions=positions,
        nav_ts=all_charts,
        initial_cash=f"{selected_portfolio.initial_cash}",
        leverage_limit=f"{selected_portfolio.leverage_limit}",
        api_route=os.getenv("API_ROUTE"),
        shown=shown
    )


@bp.route('/upload-portfolio', methods=['POST'])
def upload_portfolio():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file:
        Portfolio.upload_portfolio(file)

    return jsonify({"status": "success"})


@bp.route("/script/index.js")
def scriptIndex():
    return render_template("index.js",  api_route=os.getenv("API_ROUTE"))
