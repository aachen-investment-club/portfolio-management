import pandas as pd
import numpy as np
import requests
import json 

from typing import List, Set, Dict
from datetime import datetime, timedelta 
from  datetime import date as dte
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


US_TREASURY_API = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"



class Market(): 
    """
    - quotes is a DataFrame with a multiindex of form Ticker (string), Date (datetime). 
    -  
    """
    universe: Set[str]= {}
    trading_days : Set[pd.Timestamp] = {}
    quotes: pd.DataFrame =None 
    latest_quote_date: pd.DataFrame = None



    @classmethod 
    def get_us_treasury_bonds(cls)-> pd.DataFrame: 
        """
        returns monthly 30 year treasury bonds 
        """


        endpoint = "v2/accounting/od/avg_interest_rates"
        today = str(dte.today())
        response = requests.get(
            url = US_TREASURY_API+ endpoint,
            params = {
                "format" : "json", 
                "filter" : f"record_date:lte:{today}", 
                "sort": "record_date", 
                "page[size]": 10000, 
                "page[number]": 1
            }
        )
        
        if response: 
            data:List[Dict] = json.loads(response.content) ["data"]

            df = pd.DataFrame(data)

            df = df[["record_date", "avg_interest_rate_amt", "security_desc"]]
            df= df[df["security_desc"]== "Treasury Bonds"] 
            
            df["record_date"] = pd.to_datetime(df["record_date"])
            df["avg_interest_rate_amt"] = pd.to_numeric(df["avg_interest_rate_amt"], errors = "coerce")

            df.dropna(inplace= True, axis = 0) 
            df = df.set_index(keys = "record_date")

            df.drop(columns= ["security_desc"], inplace=True)
            df = df.rename(columns = {"avg_interest_rate_amt":"rate"})
            df.index.name = "date"
            return df

        return None 








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
        today = pd.Timestamp(dte.today())
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
                bars:pd.DataFrame = bars.df[["close"]]
                bars.index = bars.index.set_levels(
                 [bars.index.levels[0], bars.index.levels[1].floor("D").tz_localize(None)]
                )
                bars.index.names = [TICKER, DATE]
                bars.columns =[PRICE]
                cls.quotes = pd.concat([cls.quotes, bars]).sort_index()
                cls.trading_days = cls.quotes.index.get_level_values(DATE).unique()
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
    def get_price(cls, ticker: str, date: datetime.date)->np.float64: 

        date = pd.Timestamp(date)
        if ticker not in cls.universe:
            #:TODO: make this error more expressive (indicate whether ticker or date error)
            raise KeyError 

        if date not in cls.trading_days: 
            raise KeyError 

        return cls.quotes.loc[(ticker, date), PRICE].iloc[0]

    @classmethod
    def get_latest_price(cls, ticker: str) -> np.float64: 
        today = dte.today()+timedelta(days=-1) #: today is not finished yet
        return cls.get_price(ticker, today)

    #: 


    @classmethod
    def init(cls): 
        cls.load_from_csv("./data/sp500_close.csv")
        cls.update_market() 

