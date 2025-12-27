
import pandas as pd
import numpy as np
from scipy.stats import norm

from models.market import Market

tradingDays: int = 252

class Metrics: 
    @staticmethod
    def get_bonds_returns(start_date = None, end_date = None): 
        data = Market.get_us_treasury_bonds()
        data.index = pd.to_datetime(data.index)
        print(data.index.dtype)

        if start_date is not None:
            start_date = pd.Timestamp(start_date)
            data = data.loc[data.index >= start_date]

        if end_date is not None:
            end_date = pd.Timestamp(end_date)
            data = data.loc[data.index <= end_date]

        return Metrics.get_daily_returns(data['Rate'])

    @staticmethod
    def get_portfolio_weights(
            portfolio: pd.DataFrame, historical_data: pd.DataFrame):
        total = 0
        weights = []
        for i, data in portfolio.iterrows():
            ticker = data["ticker"]
            price_close = historical_data[ticker][-1]["price close"]
            value = price_close * data["shares"]
            total += value
            weights.append(value)
        weights = list(map(lambda x: x / total, weights))
        return np.array(weights)

    @staticmethod
    def get_basic_metrics(assets: pd.DataFrame) -> pd.DataFrame:
        prices = Market.get_latest_price(assets["ticker"].to_list())
        df_merged = pd.merge(assets, prices, how="left", on="ticker")
        df_merged["asset_value"] = df_merged["shares"] * df_merged["price close"]
        return df_merged

    @staticmethod
    def get_daily_returns(data: pd.Series)-> pd.Series:
        returns = data / data.shift(1)-1
        returns = returns.dropna()  #: the first entry is per definition undefined
        return returns

    @staticmethod
    def get_daily_log_returns(data: pd.Series)-> pd.Series:
        returns = np.log(data / data.shift(1))
        returns = returns.dropna()  #: the first entry is per definition undefined
        return returns

    @staticmethod
    def get_annual_volatility(returns: pd.Series, periods_per_year: int = 252) -> float: 
        annual_vol = returns.std() * np.sqrt(periods_per_year)
        return annual_vol

    @staticmethod
    def get_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> float:
        # normalize the annual risk free rate as per the number of trading days in a year

        norm_risk_free_rate = risk_free_rate / periods_per_year
        excess_returns = returns - norm_risk_free_rate
        excess_returns_mean = excess_returns.mean()
        excess_returns_std = excess_returns.std()
        if excess_returns_std == 0:  # check for division by zero error
            return float('nan')
        sharpe_ratio_annual = (excess_returns_mean / excess_returns_std) \
                * np.sqrt(1 / periods_per_year)
        return sharpe_ratio_annual


    @staticmethod
    def get_beta(
            portfolio_returns: pd.Series, benchmark_returns: pd.Series
            ) -> float:
        """
        Calculates the Beta of the portfolio relative to a benchmark.
        Beta = Cov(Rp, Rm) / Var(Rm)

        Args:
            portfolio_returns: Series of daily portfolio returns.
            benchmark_returns: Series of daily benchmark (e.g., SPY) returns.
        """
        # Align data by date to ensure we compare the same days
        # This handles cases where one series might have missing dates
        # Only dates where portfolio_returns and benchmark_returns have datapoints are kept
        df = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
        aligned_port_ret = df.iloc[:, 0]
        aligned_bench_ret = df.iloc[:, 1]

        # Calculate Beta using Covariance/Variance matrix
        # cov_matrix[0,1] is covariance, cov_matrix[1,1] is variance of benchmark
        cov_matrix = np.cov(aligned_port_ret, aligned_bench_ret)
        beta = cov_matrix[0, 1] / cov_matrix[1, 1]

        return beta

    @staticmethod
    def get_alpha(
            portfolio_returns: pd.Series, benchmark_returns: pd.Series,
            risk_free_rate: float = 0.0) -> float:
        """
        Calculates Jensen's Alpha (annualized).
        Alpha = Rp - [Rf + Beta * (Rm - Rf)]

        Args:
            portfolio_returns: Series of daily portfolio returns.
            benchmark_returns: Series of daily benchmark (e.g., SPY) returns.
            risk_free_rate: The annual risk-free rate (e.g., 0.04 for 4%). Defaults to 0.
        """
        # Align data
        df = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
        aligned_port_ret = df.iloc[:, 0]
        aligned_bench_ret = df.iloc[:, 1]

        # Calculate Beta
        beta = Metrics.get_beta(aligned_port_ret, aligned_bench_ret)

        # Simple Annualization of average daily return
        avg_port_ret = aligned_port_ret.mean() * tradingDays
        avg_bench_ret = aligned_bench_ret.mean() * tradingDays

        # Jensen's Alpha
        # Alpha = Portfolio Return - (Risk Free + Beta * (Benchmark Return - Risk Free))
        alpha = avg_port_ret - (risk_free_rate + beta * (avg_bench_ret - risk_free_rate))

        return alpha

    @staticmethod
    def get_value_at_risk(
            returns: pd.Series,
            portfolio_weights: np.ndarray,
            days_horizon: int = 10, n_simulations: int = 10000,
            CL: float = 0.95, portfolio_value: float = 100.0):

        mean_return = returns.mean()
        std_dev = returns.std()

        z_score = norm.ppf(1 - CL)
        VaR_var_cov = mean_return + z_score * std_dev
        return VaR_var_cov
        """ # time period for which future is simulated  : days_horizon
        mean_returns = returns.mean() 
        sigma_returns = returns.std()
        covmat_returns = returns.cov(returns).values()
        weights = np.array(portfolio_weights)

        L = np.linalg.cholesky(covmat_returns) # Cholesky decomposition creates correlated random variables based on the covmat

        stochastic_returns = np.zeros(n_simulations)

        for i in range(n_simulations):
            cumulative_returns = 0.0
            for _ in range(days_horizon):
                rand_vec = np.random.normal(size=(len(mean_returns), 1))
                corr_returns = mean_returns + L @ rand_vec
                daily_returns = float(weights.T @ corr_returns)  # convert to a scalar portfolio return for that day
                cumulative_returns = cumulative_returns + daily_returns
            stochastic_returns[i] = cumulative_returns

        confidence_interval = CL * 100
        stochastic_losses = - portfolio_value * stochastic_returns

        VaR = np.percentile (stochastic_losses, confidence_interval)

        return VaR"""

    # return on investment
    @staticmethod 
    def get_ROI(prices: pd.Series) -> float: 
        start_price = prices.iloc[0]
        end_price = prices.iloc[-1]

        roi = (end_price - start_price) / start_price * 100
        return roi

    def get_CAGR(prices: pd.Series) -> float:
        start_price = prices.iloc[0]
        end_price = prices.iloc[-1]

        days = (prices.index[-1] - prices.index[0]).days
        years = days / 252.0

        if years == 0:
            return float("nan")

        cagr = (end_price / start_price) ** (1 / years) - 1
        return cagr * 100
    '''
    The Maximum Drawdown (MDD) measures the largest percentage loss an asset
    would have experienced over a given period, calculated from the highest price
    to the subsequent lowest price.
    It is an important metric for assessing downside risk, indicating how much an
    investor could have lost in the worst-case scenario. A lower MDD value reflects lower loss risk.
    Unlike volatility, which accounts for both upward and downward movements, 
    MDD is an asymmetric risk measure that focuses exclusively on losses.
    '''
    @staticmethod
    def get_maximum_drawdown(prices: pd.Series) -> float:
        rolling_max = prices.cummax()
        drawdowns = prices / rolling_max - 1
        mdd = drawdowns.min() * 100
        return mdd
