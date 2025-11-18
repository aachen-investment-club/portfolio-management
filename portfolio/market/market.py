import pandas as pd
import numpy as np

from typing import List, Set
from datetime import datetime, timedelta, date
import os

from alpaca.data import  StockHistoricalDataClient , StockBarsRequest, TimeFrame, TimeFrameUnit
from alpaca.trading.client import TradingClient, GetCalendarRequest




from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("APCA_API_KEY_ID") 
SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")



DATE = "Date"
TICKER = "Ticker"
PRICE = "Price Close"

stock_client = StockHistoricalDataClient(API_KEY,  SECRET_KEY)
trading_client = TradingClient(API_KEY,  SECRET_KEY)






class Market(): 
    """
    - quotes is a DataFrame with a multiindex of form Ticker (string), Date (datetime). 
    -  
    """
    universe: Set[str]= {}
    trading_days : Set[datetime] = {}
    quotes: pd.DataFrame =None 
    latest_quote_date: pd.DataFrame = None


    @classmethod
    def load_from_csv(cls, path, from_yahoo= True)->None: 
        data = pd.read_csv(path)
        data[DATE]= pd.to_datetime(data[DATE])
        if from_yahoo: 
            data[TICKER]= data[TICKER].str.split(".").str[0] #: use this to convert yahoo finance/ refinitiv format to standard ticker naming.
        df_new = data.set_index([TICKER, DATE])[[PRICE]]


        cls.latest_quote_date = data[DATE].max()
        cls.quotes = df_new
        cls.trading_days = set(data[DATE])
        cls.universe = set(data[TICKER].unique())


    @classmethod
    def update_market(cls): 
        today = pd.Timestamp(date.today())
        if cls.latest_quote_date != today and cls.is_trading_day(today): 

            stocks = list(cls.universe)
            request_params= StockBarsRequest(
                symbol_or_symbols=stocks, 
                timeframe=TimeFrame.Day, 
                start= cls.latest_quote_date+timedelta(1), #: inclusive
                end =today  # non inclusive
            )
            bars = stock_client.get_stock_bars(request_params)
        
            if bars:  
                bars = bars.df[["close"]]
                print(bars.head())
        else: 
            return 
            



    @staticmethod
    def is_trading_day(date:datetime)->bool: 
        request = GetCalendarRequest(start = date, end =date)
        response = trading_client.get_calendar(request)
        if response: 
            return True
        return False



    @classmethod
    def get_price(cls, ticker: str, date: datetime)->np.float64: 
        if ticker not in cls.universe:
            raise KeyError 

        if date not in cls.trading_days: 
            raise KeyError 

        return cls.quotes.loc[(ticker, date), PRICE].iloc[0]

 

Market.load_from_csv("./data/sp500_close.csv")
Market.update_market()
