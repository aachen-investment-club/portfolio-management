
import pandas as pd
import numpy as np

from market import Market, PRICE, DATE, TICKER


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
    def get_ROI(current_value, cost): 
        return (current_value- cost)/ cost


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
    def get_alpha(): 
        pass



    @staticmethod 
    def get_beta(): 
        pass



    @staticmethod 
    def get_maximum_dropdown(): 
        pass