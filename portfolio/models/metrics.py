
import pandas as pd
import numpy as np

from models.market import Market


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