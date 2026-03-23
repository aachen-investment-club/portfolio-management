from functools import wraps

import os
import datetime
import pandas as pd

from flask import (request, session, redirect, 
                   url_for, Blueprint, render_template, 
                   request, jsonify, make_response, flash)

import urllib

from portfolio.models.portfolio import Portfolio
from portfolio.models.metrics import Metrics
from portfolio.models.market import Market
from portfolio.exceptions import PortfolioBaseException
#from portfolio.utils.aws_config import engine
import io
import csv
import json
from portfolio.extensions import cache, oauth
from portfolio.utils.simulate import simulate
from dotenv import load_dotenv

load_dotenv()

COGNITO_DOMAIN_PREFIX = os.getenv("COGNITO_DOMAIN_PREFIX")  
COGNITO_REGION = os.getenv("AWS_REGION")   
COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")



bp = Blueprint("bp", __name__)


def check_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:

            print("unauthenticated")
            return redirect(url_for('login', _external=True))
        print("authenticated")
        return f(*args, **kwargs)
    return decorated_function



@bp.route('/login')
def login():
    redirect_uri = url_for('bp.authorize', _external=True)

    return oauth.oidc.authorize_redirect(redirect_uri)


@bp.route('/authorize')
def authorize():
    token = oauth.oidc.authorize_access_token()
    user = token['userinfo']
    session['user'] = user
    return redirect(url_for('bp.index'))


@bp.route('/logout')
def logout():
    session.pop('user', None)

    logout_uri = url_for("bp.index", _external=True)
    params = {
        "client_id": COGNITO_CLIENT_ID,
        "logout_uri": logout_uri,  
    }
    qs = urllib.parse.urlencode(params)

    cognito_logout = f"https://{COGNITO_DOMAIN_PREFIX}.auth.{COGNITO_REGION}.amazoncognito.com/logout?{qs}"


    return redirect(cognito_logout) 

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

    leverage = float(request.args.get("leverage", 100000))
    simulation = json.loads(
        request.cookies.get("simulation") or "[]"
    )

    sim_nav = None
    sim_metrics = None
    sim_nav_ts = None

    if len(simulation) > 0:
        sim_nav, sim_metrics = simulate(
            selected_data, simulation, initial_cash, leverage)
        
        sim_nav_ts = [
            {"date": d.strftime("%Y-%m-%d"), "nav": float(v)}
            for d, v in sim_nav.items()
        ]

    preview = request.cookies.get("preview")
    preview_data = None
    if preview:
        market_data = Market.get_historical_data([preview])
        preview_data = {
            "name": preview,
            "x": market_data["date"].apply(lambda x: x.strftime("%Y-%m-%d")).tolist(),
            "y": market_data["price_close"].tolist(), 
            "yaxis": "y2", 
            "line": {
                "dash": "solid",
                "width": 2,
                "color": "#FF7F50"
            }
        }



    tickers = Market.get_all_tickers()

    try:
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
    except PortfolioBaseException as e:
        print(f"Metrics calculation failed: {e}")
        flash("No data available for the selected date range.", "warning")
        return redirect(url_for('bp.index'))


    if 'user' in session:
        user = session['user']
        print(f"logged in as {user['email']}")
    else:
        user = None
        print(f"not logged in yet")

    ttn, ntt = Market.get_ticker_short_name_map()
    ttn = {key:val for key, val in ttn.items() if val is not None}

    resp = make_response(render_template(
        "index.html",
        user = user, 
        portfolios=portfolios,
        selected_key=selected_key,
        metrics=metrics,
        positions=positions,
        simulation=simulation,
        nav_ts=all_charts,
        initial_cash=f"{selected_portfolio.initial_cash}",
        leverage_limit=f"{selected_portfolio.leverage_limit}",
        api_route=os.getenv("API_ROUTE"),
        shown=shown,
        tickers=tickers,
        sim_nav=sim_nav_ts,
        sim_metrics=sim_metrics,
        preview_data=preview_data, 
        ticker_to_name = ttn, 
        name_to_timer = ntt
    ))
    resp.set_cookie("base_portfolio", json.dumps(selected_data))
    return resp





@bp.route('/upload_portfolio', methods=['POST'])
@check_auth
def upload_portfolio():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file:
        file.stream.seek(0)
        with io.TextIOWrapper(file.stream, encoding="utf-32-le", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            rows = list(reader)
            data = Portfolio.import_from_csv(rows)
            Portfolio.upload_portfolio(data, file.filename.replace("csv", "json"))

    return jsonify({"status": "success"})



@bp.route('/remove_portfolio', methods=['POST'])
@check_auth
def remove_portfolio():

    selected_portfolio = request.form.get("portfolio")
    if not selected_portfolio: 
        return jsonify({"error": "No selected portfolio"}), 400

    Portfolio.remove_portfolio(selected_portfolio)
    return jsonify({"status": "success"})








@bp.route("/script/index.js")
def scriptIndex():
    return render_template("index.js",  api_route=os.getenv("API_ROUTE"))
