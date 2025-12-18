from utils.aws_config import engine
from schemas.market import Market as MarketSchema

from typing import List, Dict
from datetime import datetime, timedelta, date
from alpaca.trading import GetCalendarRequest
import json
import requests

import pandas as pd
import numpy as np

from sqlalchemy import select, and_


class Market():
    """
    - quotes is a DataFrame with a multiindex of form Ticker (string), Date (datetime).
    """
    US_TREASURY_API = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"

    @classmethod
    def get_traded_assets(cls):
        stmt = select(MarketSchema.ticker).distinct()

        df = pd.read_sql(stmt, engine)
        return df

    @classmethod
    def get_trading_days(cls):
        stmt = select(MarketSchema.date).distinct()
        df = pd.read_sql(stmt, engine)
        return df

    @classmethod
    def get_us_treasury_bonds(cls) -> pd.DataFrame:
        """
        # returns monthly 30 year treasury bonds
        """

        endpoint = "v2/accounting/od/avg_interest_rates"
        today = str(datetime.today())
        response = requests.get(
            url=cls.US_TREASURY_API+endpoint,
            params={
                "format": "json",
                "filter": f"record_date:lte:{today}",
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
        else:
            raise Exception("Error: US Treasury API sent no response")

    # @classmethod
    # def update_market(cls): 
    #     expected_latest_quote = pd.Timestamp(Market.get_latest_quotation_date())
    #
    #     if cls.latest_quote_date != expected_latest_quote and cls.is_trading_day(expected_latest_quote): 
    #         print("updating market...")
    #
    #         stocks = list(cls.universe)
    #
    #         bars =Alpaca.get_bars_time_range(stocks, cls.latest_quote_date+timedelta(1), expected_latest_quote+timedelta(1)) 
    #
    #         if bars:  
    #
    #             bars:pd.DataFrame = bars.df[["close"]]
    #             bars.index = bars.index.set_levels(
    #              [bars.index.levels[0], bars.index.levels[1].floor("D").tz_localize(None)]
    #             )
    #             bars.index.names = [TICKER, DATE]
    #             bars.columns =[PRICE]
    #             cls.quotes = pd.concat([cls.quotes, bars]).sort_index()
    #             cls.trading_days = cls.quotes.index.get_level_values(DATE).unique()
    #
    #
    #             cls.write_csv()
    #             print("done updating market")
    #     else: 
    #         print("market up to date")
    #         return 

    @staticmethod
    def is_trading_day(date: datetime) -> bool:
        request = GetCalendarRequest(start=date, end=date)
        response = trading_client.get_calendar(request)
        if response:
            return True
        return False

    @staticmethod
    def get_latest_trading_day():
        today = datetime.today()
        while not Market.is_trading_day(today):
            today = today+timedelta(days=-1)
        return today

    @classmethod
    def get_historical_data(cls, tickers: List[str]) -> pd.DataFrame:
        if len(tickers) == 0:
            raise Exception("arg `ticker` must be at least of size 1")

        stmt = select(MarketSchema) \
            .where(and_(MarketSchema.date > datetime.now() - timedelta(days = 30),
                        MarketSchema.ticker.in_(tickers))) \
            .order_by(MarketSchema.date)
        df = pd.read_sql(stmt, engine)
        return df

    @classmethod
    def get_latest_price(cls, tickers: List[str]) -> pd.DataFrame:
        if len(tickers) == 0:
            raise Exception("arg `ticker` must be at least of size 1")

        stmt = select(MarketSchema) \
            .where(and_(MarketSchema.date > datetime.now() - timedelta(days = 30),
                        MarketSchema.ticker.in_(tickers))) \
            .order_by(MarketSchema.date)
        df = pd.read_sql(stmt, engine)
        return df

