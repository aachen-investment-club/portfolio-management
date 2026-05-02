import pandas as pd
from portfolio.models.portfolio import Portfolio
from portfolio.models.metrics import Metrics
from portfolio.models.market import Market

def simulate(base_data, trades, initial_cash, leverage):
    data = dict(base_data)
    for t in trades:
        prices = Market.get_historical_data([t["ticker"]])

        date_col = "date" if "date" in prices.columns else prices.columns[0]
        prices[date_col] = pd.to_datetime(prices[date_col])
        buy_date = pd.to_datetime(t["date"])

        prices = prices[prices[date_col] <= buy_date]

        price_col = None
        for c in prices.columns:
            if "close" in c.lower() or "price" in c.lower():
                price_col = c
                break

        price = float(prices.iloc[-1][price_col])
        shares = float(t["cash"]) / price

        data["transactions"].append({
            "type": "PURCHASE",
            "account": "USD",
            "portfolio": "Simulation",
            "date": t["date"],
            "time": "00:00",
            "currency": "USD",
            "shares": shares,
            "security": {
                "ticker": t["ticker"],
                "currency": "USD"
            }
        })




    p = Portfolio(initial_cash, leverage)
    p.import_from_dict(data)

    nav = p.get_daily_nav()

    bench_df = Market.get_us_treasury_bonds()
    bench_df = bench_df[bench_df.index >= nav.index.min()]
    bench_df = bench_df[bench_df.index <= nav.index.max()]
    bench_series = bench_df["price close"].sort_index()

    port_returns = Metrics.get_daily_returns(nav)
    bench_returns = Metrics.get_daily_returns(bench_series)

    metrics = {
        "total_return": f"{Metrics.get_ROI(nav):.7f}%",
        "cash": f"${p.cash:.1f}",
        "cagr": f"{Metrics.get_CAGR(nav):.7f}%",
        "volatility": f"{Metrics.get_annual_volatility(port_returns):.7f}",
        "sharpe": f"{Metrics.get_sharpe_ratio(port_returns):.7f}",
        "max_drawdown": f"{Metrics.get_maximum_drawdown(nav):.7f}",
        "beta": f"{Metrics.get_beta(port_returns, bench_returns):.7f}",
        "alpha": f"{Metrics.get_alpha(port_returns, bench_returns):.7f}",
        "total_value": f"${float(nav.iloc[-1]):.1f}",
        "value_at_risk": f"${Metrics.get_value_at_risk(port_returns, days_horizon=10, CL=0.95, portfolio_value=float(nav.iloc[-1])):.2f}",
    }

    return nav, metrics
