from portfolio.models.portfolio import Portfolio
from portfolio.models.market import Market

def build_real_portfolio(portfolio_key, initial_cash, leverage_limit):
    portfolios = Portfolio.list_portfolios()

    if not portfolios:
        return None, None

    if portfolio_key not in portfolios:
        portfolio_key = next(iter(portfolios))

    selected_data = portfolios[portfolio_key]

    portfolio = Portfolio(initial_cash, leverage_limit)
    portfolio.import_from_dict(selected_data)

    nav = portfolio.get_daily_nav()
    return portfolio, nav