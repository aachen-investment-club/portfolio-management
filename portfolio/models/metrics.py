
import pandas as pd
import numpy as np

from market import Market, PRICE


class Metrics: 




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
    def get_annual_volatility(returns: pd.Series, periods_per_year: int = 252) -> float: 
        annual_vol = returns.std() * np.sqrt(periods_per_year)
        return annual_vol


    @staticmethod 
    def get_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> float:
        norm_risk_free_rate = risk_free_rate / periods_per_year # normalize the annual risk free rate as per the number of trading days in a year
        excess_returns = returns - norm_risk_free_rate 
        excess_returns_mean = excess_returns.mean()
        excess_returns_std = excess_returns.std()
        
        if excess_returns_std == 0: # check for division by zero error
            return float('nan')
        
        sharpe_ratio_annual = (excess_returns_mean / excess_returns_std) * np.sqrt(1 / periods_per_year)
        
        return sharpe_ratio_annual


    @staticmethod 
    def get_alpha(): 
        pass



    @staticmethod 
    def get_beta(): 
        pass


        @staticmethod 
    def get_value_at_risk(returns: pd.Series, portfolio_weights: np.ndarray, days_horizon: int = 7, n_simulations: int = 10000, CL: float = 0.95, portfolio_value: float = 1000.0):
        # returns : multi asset returns not for single asset
        
        # time period for which future is simulated  : days_horizon
        mean_returns = returns.mean().values.reshape(-1, 1)
        covmat_returns = returns.cov().values
        weights = np.array(portfolio_weights)
        weights = weights.reshape(-1, 1)

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
        
        return VaR


    @staticmethod 
    def get_ROI(): 
        pass


    @staticmethod 
    def get_maximum_dropdown(): 
        pass
