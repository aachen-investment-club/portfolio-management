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
from pandas.core.groupby.generic import DataFrameGroupBy

import time


import boto3
import awswrangler as wr
from dotenv import load_dotenv
load_dotenv()

boto3.setup_default_session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

API_KEY = os.getenv("APCA_API_KEY_ID") 
SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")

DATE = "date"
TICKER = "ticker"
PRICE = "price close"

stock_client = StockHistoricalDataClient(API_KEY,  SECRET_KEY)
trading_client = TradingClient(API_KEY,  SECRET_KEY)

US_TREASURY_API = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"


class Market(): 
    """
    - quotes is a DataFrame with a multiindex of form Ticker (string), Date (datetime). 
    """
    ATHENA_DB =  "portfolio-management-db"
    ATHENA_TABLE = "portfolio_management_developer"
    ATHENA_OUTPUT_LOCATION = "s3://athena-outputs-developer/athena/"
    
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
            df = df.rename(columns = {"avg_interest_rate_amt":"Rate"})
            df.index.name = "Date"
            return df

        return None 

    @classmethod
    def update_market(cls): 
        expected_latest_quote = pd.Timestamp(Market.get_latest_quotation_date())

        if cls.latest_quote_date != expected_latest_quote and cls.is_trading_day(expected_latest_quote): 
            print("updating market...")

            stocks = list(cls.universe)
            request_params= StockBarsRequest(
                symbol_or_symbols=stocks, 
                timeframe=TimeFrame.Day, 
                start= cls.latest_quote_date+timedelta(1), #: inclusive
                end =expected_latest_quote+timedelta(1)# non inclusive; add one because of this
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


                cls.write_csv()
                print("done updating market")
        else: 
            print("market up to date")
            return 
            
    @staticmethod
    def is_trading_day(date:datetime)->bool: 
        request = GetCalendarRequest(start = date, end =date)
        response = trading_client.get_calendar(request)
        if response: 
            return True
        return False

    @staticmethod
    def get_latest_trading_day(): 
        today = dte.today()
        while not Market.is_trading_day(today): 
            today = today+ timedelta(days = -1)
        return today

    @classmethod
    def get_latest_quotation_date(cls): 
        return cls.latest_quote_date

    @classmethod
    def get_price(cls, ticker: str, date: datetime.date)->np.float64: 

        date = pd.Timestamp(date)
        if ticker not in cls.universe:
            #:TODO: make this error more expressive (indicate whether ticker or date error)
            raise Exception("the selected ticker is not traded in the market")

        if not cls.is_trading_day(date): #: this may also raise a more descriptive exception
            raise Exception("the selected date is not a trading date")

        if date not in cls.trading_days: 
            raise Exception("the selected date is unavailable in the market") 

        return cls.quotes.loc[(ticker, date), PRICE].iloc[0]
    
    @classmethod
    def get_historical_data(cls, tickers: List[str]) -> DataFrameGroupBy:
        if len(tickers) == 0:
            raise Exception("arg `ticker` must be at least of size 1")
        
        tickers_dict = dict()
        for i, ticker in enumerate(tickers):
            tickers_dict[f'p{i}'] = ticker
        
        query = f"""
            SELECT *
            FROM "{cls.ATHENA_DB}"."{cls.ATHENA_TABLE}"
            WHERE Date >= 2025-12-01 AND
                ({" OR ".join(map(lambda x: f'ticker = :{x}', tickers_dict.keys()))})
            ORDER BY Date

        """ 
        df = wr.athena.read_sql_query(
            sql=query,
            params=tickers_dict,
            database=cls.ATHENA_DB
        )
        return df.groupby("ticker")
    
    @classmethod
    def get_latest_price(cls, tickers: List[str]) ->  pd.DataFrame:
        if len(tickers) == 0:
            raise Exception("arg `ticker` must be at least of size 1")
        
        df = pd.DataFrame(columns=["ticker", "date", "price close"])
        df = df.astype(dtype={
            "ticker": "string",
            "date": "datetime64[ms]",
            "price close": "double"
        })
        for ticker in tickers:
            query = f"""
                SELECT *
                FROM "{cls.ATHENA_DB}"."{cls.ATHENA_TABLE}"
                WHERE ticker = :ticker
                ORDER BY Date DESC
                LIMIT 1
            """
            price_close = wr.athena.read_sql_query(
                sql=query,
                params={"ticker": ticker},
                database=cls.ATHENA_DB
            )  
            df = pd.concat([df, price_close])
        return df