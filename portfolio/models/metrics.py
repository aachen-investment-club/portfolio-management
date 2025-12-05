
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
    def get_value_at_risk(): 
        pass


    @staticmethod 
    def get_ROI(): 
        pass


    @staticmethod 
    def get_maximum_dropdown(): 
        pass