
from flask import Blueprint, render_template, request, jsonify
import os, datetime
import pandas as pd

from portfolio.models.portfolio import Portfolio
from portfolio.models.metrics import Metrics
from portfolio.models.market import Market
from portfolio.schemas.market import Base
from portfolio.utils.aws_config import engine
from portfolio.extensions import cache  

bp = Blueprint("bp", __name__)


Base.metadata.create_all(engine)


@bp.route("/health")
def health():
    return "healthy"


@bp.route("/load_market")
def load_market():
    Market.load_from_csv("./data/sp500_close_current.csv")

    return {"status": "success"}


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
    if Market.check_empty():
        Market.load_from_csv("./data/sp500_close_current.csv")

    initial_cash = request.args.get("cash", default=1000000, type=float)
    leverage_limit = request.args.get("leverage", default=100000, type=float)
    default_start = datetime.datetime(2000, 1, 3).date().strftime('%Y-%m-%d')

    start_date = request.args.get("start_date", default=default_start) or default_start
    #: this is important for edge cases
    start_date = pd.to_datetime(datetime.datetime.strptime(start_date, '%Y-%m-%d').date())


    default_end = Market.get_latest_date_in_db().strftime('%Y-%m-%d')


    end_date = request.args.get("end_date", default=default_end) or default_end 
    # this is important for edge cases

    end_date = pd.to_datetime(datetime.datetime.strptime(end_date, '%Y-%m-%d').date())


    portfolios = Portfolio.list_portfolios()

    selected_key = request.args.get("portfolio")


    if not portfolios : 
        selected_key = None
        selected_data = None

    else: 
        if selected_key not in portfolios: 
            selected_key= next(iter(portfolios))
        selected_data = portfolios[selected_key]

    portfolio, nav = get_cached_nav_data(selected_data, initial_cash, leverage_limit)
    bench_df = get_cached_bonds_data()




    positions = portfolio.get_position_weights()
    nav = nav[nav.index>=start_date]
    nav = nav[nav.index<= end_date]

    bench_df = bench_df[bench_df.index>=start_date]
    bench_df = bench_df[bench_df.index<=end_date]


    #: has to be converted to a list of dicts for json 
    nav_ts = [
        {"date": d.strftime("%Y-%m-%d"), "nav": float(v)}
        for d, v in nav.items()
    ]

    bench_series = (
        bench_df
        ["price close"]
        .sort_index())




    port_returns = Metrics.get_daily_returns(nav)
    bench_returns = Metrics.get_daily_returns(bench_series)


    portf_positions_df = portfolio.get_portfolio_positions_df() 

    portf_data = Market.get_historical_data(portf_positions_df["ticker"].to_list())
    # port_weights = Metrics.get_portfolio_weights(portf_positions_df, portf_data)

    metrics = {
        "total_return": f"{Metrics.get_ROI(nav):.7f}%",
        "cash": f"${portfolio.cash:.1f}",
        "cagr": f"{Metrics.get_CAGR(nav):.7f}%",
        "volatility": f"{Metrics.get_annual_volatility(port_returns):.7f}",
        "sharpe": f"{Metrics.get_sharpe_ratio(port_returns):.7f}",
        "max_drawdown": f"{Metrics.get_maximum_drawdown(nav):.7f}",
        "beta": f"{Metrics.get_beta(port_returns, bench_returns):.7f}",
        "alpha": f"{Metrics.get_alpha(port_returns, bench_returns):.7f}",
        "total_value": f"${float(nav.iloc[-1]):.1f}",
        # "value_at_risk": Metrics.get_value_at_risk(port_returns, port_weights)
    }

    return render_template(
        "index.html",
        portfolios=portfolios,
        selected_key=selected_key,
        metrics=metrics,
        positions=positions,
        nav_ts=nav_ts,
        initial_cash=f"{portfolio.initial_cash}",
        leverage_limit=f"{portfolio.leverage_limit}",
        api_route=os.getenv("API_ROUTE"),
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
