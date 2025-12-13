
import pandas as pd
import numpy as np

from market import Market, PRICE, DATE, TICKER

tradingDays: int = 252

class Metrics: 
    @staticmethod
    def get_basic_metrics(assets: pd.DataFrame) -> pd.DataFrame:
        prices = Market.get_latest_price(assets["ticker"].to_list())
        df_merged = pd.merge(assets, prices, how="left", on="ticker")
        df_merged["asset_value"] = df_merged["shares"] * df_merged["price close"]
        return df_merged

    @staticmethod
    def get_daily_returns(data: pd.Series)-> pd.Series:
        returns = data/ data.shift(1)-1
        returns = returns.dropna() #: the first entry is per definition undefined
        return  returns

    @staticmethod
    def get_daily_log_returns(data: pd.Series)-> pd.Series:
        returns =np.log(data/ data.shift(1))
        returns = returns.dropna() #: the first entry is per definition undefined
        return  returns

    @staticmethod 
    def get_historical_value_at_risk(
        ticker: str,
        date_lower_bound : pd.Timestamp, 
        risk_thresh:float = 0.5
    ): 
        data = Market.get_ticker_lower_bound_quotes(ticker, date_lower_bound)
        daily_returns = Metrics.get_daily_returns(data).to_numpy()
        mu = daily_returns.mean()#: this estimates a normal distribution
        std= daily_returns.std()#: this estimates a normal distribution


        pass




    @staticmethod 
    def get_implied_value_at_risk(): 
        pass

    @staticmethod 
    def get_annual_volatility(): 
        pass

    @staticmethod 
    def get_sharpe_ratio(): 
        pass


    @staticmethod
    def get_beta(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> float:
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
    def get_alpha(portfolio_returns: pd.Series, benchmark_returns: pd.Series, risk_free_rate: float = 0.0) -> float:
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
    def get_value_at_risk(): 
        pass

    #return on investment 
    @staticmethod 
    def get_ROI(prices: pd.Series) -> float: 
        start_price = prices.iloc[0]
        end_price = prices.iloc[-1]

        roi = (end_price - start_price) / start_price *100
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
