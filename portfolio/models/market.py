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
import boto3

import time

import awswrangler as wr


API_KEY = os.getenv("APCA_API_KEY_ID") 
SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")




DATE = "date"
TICKER = "ticker"
PRICE = "price close"

stock_client = StockHistoricalDataClient(API_KEY,  SECRET_KEY)
trading_client = TradingClient(API_KEY,  SECRET_KEY)



athena = boto3.client("athena")
#session = boto3.Session()
#print(session.client("sts").get_caller_identity())

US_TREASURY_API = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"


ATHENA_DB =  "portfolio-management-db"
ATHENA_TABLE = "portfolio_management_developer"
ATHENA_OUTPUT_LOCATION = "s3://athena-outputs-developer/athena/"


class Market(): 
    """
    - quotes is a DataFrame with a multiindex of form Ticker (string), Date (datetime). 
    -  
    """
    universe: Set[str]= {}
    trading_days : Set[pd.Timestamp] = {}
    quotes: pd.DataFrame =None 
    latest_quote_date =None
    csv_path:str = None

    @classmethod 
    def test_athena2(cls): 
        query = f"""
            SELECT *
            FROM "{ATHENA_DB}"."{ATHENA_TABLE}"
            WHERE ticker IN ('NVDA', 'INTC')
            LIMIT 100
            """
        df = wr.athena.read_sql_query(sql=query, database=ATHENA_DB)

        return df



    @classmethod 
    def test_athena(cls): 
        query = f"""
            SELECT *
            FROM "{ATHENA_DB}"."{ATHENA_TABLE}"
            WHERE ticker IN ('NVDA', 'INTC')
            LIMIT 100
            """
        wr.athena.read_sql_query(sql="QUERY", database="db")
        response = athena.start_query_execution(
            QueryString=query,
            QueryExecutionContext={"Database": ATHENA_DB},
            ResultConfiguration={"OutputLocation":  ATHENA_OUTPUT_LOCATION}
        )
        query_execution_id = response["QueryExecutionId"]

        while True:
            status = athena.get_query_execution(QueryExecutionId=query_execution_id)
            state = status["QueryExecution"]["Status"]["State"]

            if state in ["SUCCEEDED", "FAILED", "CANCELLED"]:
                break

            time.sleep(1)

        if state == "SUCCEEDED":
            results = athena.get_query_results(QueryExecutionId=query_execution_id)
            rows = results["ResultSet"]["Rows"]
            
            columns = [col["VarCharValue"] for col in rows[0]["Data"]]

            data = []
            for row in rows[1:]:
                data.append([col["VarCharValue"] for col in row["Data"]])

            df = pd.DataFrame(data, columns=columns) 

            df[DATE]= pd.to_datetime(df[DATE])
            df= df.set_index([TICKER, DATE])
                    
            return df
        else:
            print("Query failed:", state)






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
            raise TickerException("the selected ticker is not traded in the market")

        if not cls.is_trading_day(date): #: this may also raise a more descriptive exception
            raise TradingDayException("the selected date is not a trading date")

        if date not in cls.trading_days: 
            raise DateException("the selected date is unavailable in the market") 

        return cls.quotes.loc[(ticker, date), PRICE].iloc[0]

    @classmethod
    def get_latest_price(cls, ticker: str) -> np.float64: 
        
        today = cls.get_latest_quotation_date()  #: today is not finished yet
        return cls.get_price(ticker, today)



    @classmethod
    def init(cls, csv_path:str): 
        cls.csv_path = csv_path
        cls.load_from_csv(cls.csv_path,False)
        cls.update_market() 

    @classmethod 
    def update_csv(cls): 
        pass


    @classmethod
    def write_csv(cls): 
        cls.quotes.to_csv(cls.csv_path)



    @classmethod
    def load_from_csv(
            cls, 
            path, 
            original_mathis = False #: this is temporary
        )->None: 

        if original_mathis: 
            data = pd.read_csv(path)
            data[DATE]= pd.to_datetime(data[DATE])
            data[TICKER]= data[TICKER].str.split(".").str[0] #: use this to convert yahoo finance/ refinitiv format to standard ticker naming.
            df_new = data.set_index([TICKER, DATE])[[PRICE]]


            cls.latest_quote_date = data[DATE].max()
            cls.quotes = df_new
            cls.trading_days = set(data[DATE])
            cls.universe = set(data[TICKER].unique())
        else: 
            data = pd.read_csv(path)
            data[DATE]= pd.to_datetime(data[DATE])
            df_new = data.set_index([TICKER, DATE])[[PRICE]]
            

            cls.latest_quote_date = data[DATE].max()
            cls.quotes = df_new
            cls.trading_days = set(data[DATE])
            cls.universe = set(data[TICKER].unique())





class DateException(Exception): 
    pass



class TradingDayException(Exception): 
    pass

class TickerException(Exception): 
    pass