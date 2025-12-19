from typing import List, Iterable
from datetime import datetime, date, timedelta

import pandas as pd
import numpy as np
import requests
import json
import os

from sqlalchemy import (
    select,
    and_,
    func
)
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session, Mapped, mapped_column
from sqlalchemy import String, DateTime, Float

from utils.aws_config import engine
from schemas.market import Base
from alpaca.trading import GetCalendarRequest
from alpaca.trading.client import TradingClient



DATE = "date"
TICKER = "ticker"
PRICE = "price_close"


class Market(Base):
    """
    - quotes is a DataFrame with a multiindex of form Ticker (string), Date (datetime).
    """
    US_TREASURY_API = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"
    __tablename__ = "portfolio_management_developer"

    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    date: Mapped[datetime] = mapped_column(DateTime(), primary_key=True)
    price_close: Mapped[float] = mapped_column(Float(), nullable=False)




    @classmethod
    def load_from_csv(cls, path: str, batch_size: int = 300) -> int:
        df = pd.read_csv(path)

        df = df.rename(
            columns={
                "Ticker": "ticker",
                "Date": "date",
                "Price Close": "price_close",
            }
        )
        required = {"ticker", "date", "price_close"}
        if not required.issubset(df.columns):
            raise ValueError(f"CSV must contain columns {required}")

        df["date"] = pd.to_datetime(df["date"])


        df = df.drop_duplicates(subset=["ticker", "date"], keep="last")

        records = df.to_dict(orient="records")
        inserted = 0

        with Session(engine) as session:
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]

                stmt = (
                    insert(cls)
                    .values(batch)
                    .on_conflict_do_nothing(
                        index_elements=["ticker", "date"]
                    )
                )

                result = session.execute(stmt)
                inserted += result.rowcount or 0

            session.commit()
            total_rows = session.scalar(
            select(func.count()).select_from(cls)
            )

        print(total_rows)
        return inserted

    @classmethod
    def get_price(cls, ticker: str, date: datetime.date)->np.float64: 
        
        print(date)
        if ticker not in cls.get_traded_assets():
            #:TODO: make this error more expressive (indicate whether ticker or date error)
            raise Exception("the selected ticker is not traded in the market")

        if not cls.is_trading_day(date): #: this may also raise a more descriptive exception
            raise Exception("the selected date is not a trading date")

        if date not in cls.get_trading_days(): 
            raise Exception("the selected date is unavailable in the market") 

        stmt = (
            select(cls.price_close).where(
                cls.ticker == ticker, 
                cls.datre == datetime.combine(date, datetime.min.time())
            )
        )

        with Session(engine) as session:
            result = session.scalar(stmt)

        if result is None:
            raise LookupError(f"No price for {ticker} on {date}")

        return float(result)
       

    @classmethod
    def get_trading_days(cls) -> List:
        stmt = select(cls.date).distinct().order_by(cls.date)

        with Session(engine) as session:
            return [d.date() for d in session.scalars(stmt)]


    @classmethod
    def get_traded_assets(cls) -> List[str]:
        stmt = select(cls.ticker).distinct().order_by(cls.ticker)

        with Session(engine) as session:
            return list(session.scalars(stmt))


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
    def is_trading_day(date) -> bool:
        client = TradingClient(
            api_key=os.getenv("APCA_API_KEY_ID"),
            secret_key=os.getenv("APCA_API_SECRET_KEY"),
            paper=True,  # or False if live

        )
        request = GetCalendarRequest(start=date, end=date)
        return bool(client.get_calendar(request))  
    

    @staticmethod
    def get_latest_trading_day():
        today = datetime.today()
        while not Market.is_trading_day(today):
            today = today+timedelta(days=-1)
        return today


    
    @classmethod
    def get_historical_data(
        cls,
        tickers: Iterable[str],
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame:
        if not tickers:
            raise ValueError("tickers must not be empty")

        conditions = [cls.ticker.in_(tickers)]

        if start:
            conditions.append(cls.date >= start)
        if end:
            conditions.append(cls.date <= end)

        stmt = (
            select(cls)
            .where(and_(*conditions))
            .order_by(cls.date)
        )

        return pd.read_sql(stmt, engine)

    @classmethod
    def get_latest_prices(cls, tickers: Iterable[str]) -> pd.DataFrame:
        if not tickers:
            raise ValueError("tickers must not be empty")

        subq = (
            select(
                cls.ticker,
                func.max(cls.date).label("max_date")
            )
            .where(cls.ticker.in_(tickers))
            .group_by(cls.ticker)
            .subquery()
        )

        stmt = (
            select(cls)
            .join(
                subq,
                and_(
                    cls.ticker == subq.c.ticker,
                    cls.date == subq.c.max_date
                )
            )
        )

        return pd.read_sql(stmt, engine)

