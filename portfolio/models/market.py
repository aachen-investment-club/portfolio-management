from typing import List, Iterable
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import requests
import json
import os
import yfinance as yf

from sqlalchemy import (
    select,
    and_,
    func
)
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from portfolio.utils.aws_config import engine
from portfolio.schemas.market import MarketDB, TickerMeta
from alpaca.trading import GetCalendarRequest
from alpaca.trading.client import TradingClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.historical import StockHistoricalDataClient

from portfolio.exceptions import TickerException, TradingDayException, DateException


DATE = "date"
TICKER = "ticker"
PRICE = "price_close"


class Market:
    """
    - quotes is a DataFrame with a multiindex of form Ticker (string), Date (datetime).
    """
    US_TREASURY_API = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"




    @classmethod
    def load_ticker_metadata(cls, path, batch_size: int = 5_000): 

        total_inserted = 0


        with Session(engine) as session:
            for chunk in pd.read_csv(path, chunksize=batch_size):
                """
                due to production memory constraints it is important to 
                read the csv file in chunks!
                """

                print(total_inserted)
                chunk = chunk.rename(columns={
                    "exchange": "exchange",
                    "shortname":"shortname",
                    "longname":"longname",
                    "symbol":"ticker",
                    "sector":"sector",
                    "industry":"industry",
                    "origin":"origin", 
                    "type":"type",
                    "currency":"currency"
                })
                chunk = chunk.drop_duplicates(subset=["ticker"], keep="last")

                records = chunk.to_dict(orient="records")
                if not records:
                    continue

                stmt = (
                    insert(TickerMeta)
                    .values(records)
                    .on_conflict_do_nothing(index_elements=["ticker"])
                )

                result = session.execute(stmt)
                total_inserted += result.rowcount or 0

                session.commit()

        return total_inserted 



    @classmethod
    def check_meta_empty(cls):
        stmt = select(TickerMeta.ticker).limit(1)
        with Session(engine) as session:
            #: in contrast to scalars, scalar selects the first ie equivalent
            # to .execute().first()
            result = session.scalar(stmt)
            return result is None



    @classmethod
    def check_empty(cls):
        stmt = select(MarketDB.ticker).limit(1)
        with Session(engine) as session:
            #: in contrast to scalars, scalar selects the first ie equivalent
            # to .execute().first()
            result = session.scalar(stmt)
            return result is None
        
    @classmethod
    def get_all_tickers(cls):
        stmt = select(MarketDB.ticker).distinct()
        with Session(engine) as session:
            result = session.scalars(stmt).all()
            return result

    @classmethod
    def load_from_csv(cls, path: str, batch_size: int = 5_000) -> int:
        
        total_inserted = 0


        with Session(engine) as session:
            for chunk in pd.read_csv(path, chunksize=batch_size):
                """
                due to production memory constraints it is important to 
                read the csv file in chunks!
                """

                print(total_inserted)
                chunk = chunk.rename(columns={
                    "Ticker": "ticker",
                    "Date": "date",
                    "Price Close": "price_close",
                })

                chunk["date"] = pd.to_datetime(chunk["date"]).dt.floor("D")

                chunk = chunk.drop_duplicates(subset=["ticker", "date"], keep="last")

                records = chunk.to_dict(orient="records")
                if not records:
                    continue

                stmt = (
                    insert(MarketDB)
                    .values(records)
                    .on_conflict_do_nothing(index_elements=["ticker", "date"])
                )

                result = session.execute(stmt)
                total_inserted += result.rowcount or 0

                session.commit()

        return total_inserted 

    @classmethod
    def get_price(cls, ticker: str, date: datetime.date)->np.float64: 
        if ticker not in cls.get_traded_assets():
            raise TickerException(f"Ticker {ticker} is not traded in the market.")

        if not cls.is_trading_day(date): 
            raise TradingDayException(f"{date} is not a trading day (might be weekend or public holiday).")

        if date not in cls.get_trading_days(): 
            raise DateException(f"{date} is not available in the market database.") 

        stmt = (
            select(MarketDB.price_close).where(
                MarketDB.ticker == ticker, 
                MarketDB.date == datetime.combine(date, datetime.min.time())
            )
        )

        with Session(engine) as session:
            result = session.scalar(stmt)

        if result is None:
            raise LookupError(f"No price for {ticker} on {date}")

        return float(result)

    @classmethod
    def get_trading_days(cls) -> List:
        stmt = select(MarketDB.date).distinct().order_by(MarketDB.date)

        with Session(engine) as session:
            return [d.date() for d in session.scalars(stmt)]

    @classmethod
    def get_traded_assets(cls) -> List[str]:
        stmt = select(MarketDB.ticker).distinct().order_by(MarketDB.ticker)

        with Session(engine) as session:
            return list(session.scalars(stmt))


    @classmethod
    def get_traded_etfs(cls) -> List[str]:
        stmt = select(TickerMeta.ticker).where(TickerMeta.type=="ETF").distinct()
        with Session(engine) as session:
            return list(session.scalars(stmt))


    @classmethod
    def get_ticker_short_name_map(cls) -> List[str]:
        stmt = select(TickerMeta.ticker, TickerMeta.shortname).distinct()
        with Session(engine) as session:
            rows = session.execute(stmt).all()
        
        ticker_to_name = {ticker:name for ticker, name in rows}
        name_to_ticker = {name:ticker for ticker, name in rows}

        return ticker_to_name, name_to_ticker



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
            data = json.loads(response.content)["data"]

            df = pd.DataFrame(data)

            df = df[["record_date", "avg_interest_rate_amt", "security_desc"]]
            df = df[df["security_desc"]== "Treasury Bonds"]

            df["record_date"] = pd.to_datetime(df["record_date"])
            df["avg_interest_rate_amt"] = pd.to_numeric(
                df["avg_interest_rate_amt"],
                errors="coerce")

            df.dropna(inplace= True, axis = 0) 
            df = df.set_index(keys = "record_date")

            df.drop(columns=["security_desc"], inplace=True)
            df = df.rename(columns={"avg_interest_rate_amt": "price close"})
            df.index.name = "date"
            return df
        else:
            raise Exception("Error: US Treasury API sent no response")

    @classmethod
    def get_latest_date_in_db(cls): 
        with Session(engine) as session:
            latest_db_date = session.query(func.max(MarketDB.date)).scalar().date()
            return latest_db_date



    

    @classmethod
    def update_market(cls,  batch_size: int = 300):
        print("started market update")

        trading_client = TradingClient(
            api_key=os.getenv("APCA_API_KEY_ID"),
            secret_key=os.getenv("APCA_API_SECRET_KEY")
        )

        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        calendar_req = GetCalendarRequest(start=today - timedelta(days=10), end=yesterday)
        calendar = trading_client.get_calendar(calendar_req)
        if not calendar:
            print("no calendar data returned; aborting update")
            return

        target_end_date = calendar[-1].date  

        latest_db_date = cls.get_latest_date_in_db()


        tickers = list(cls.get_traded_assets())

        start_dt = pd.to_datetime(latest_db_date + timedelta(days=1))
        end_dt_excl = pd.to_datetime(target_end_date) + pd.Timedelta(days=1)

        yfinance_data_output = yf.download(
            tickers=tickers,
            start=start_dt,
            end=end_dt_excl,
            interval="1d",
            group_by="ticker",
            progress=False,
        )

        if yfinance_data_output is None or yfinance_data_output.empty:
            print("yfinance did not return anything")
            return

        rows = []

        if isinstance(yfinance_data_output.columns, pd.MultiIndex):
            if "Close" in yfinance_data_output.columns.get_level_values(0):
                close = yfinance_data_output["Close"]
                for t in close.columns:
                    s = close[t].dropna()
                    if not s.empty:
                        rows.append(pd.DataFrame({"ticker": t, "date": s.index, "price_close": s.values}))
            else:
                for t in tickers:
                    try:
                        s = yfinance_data_output[t]["Close"].dropna()
                    except Exception:
                        continue
                    if not s.empty:
                        rows.append(pd.DataFrame({"ticker": t, "date": s.index, "price_close": s.values}))
        else:
            if "Close" in yfinance_data_output.columns:
                s = yfinance_data_output["Close"].dropna()
                if not s.empty:
                    rows.append(pd.DataFrame({"ticker": tickers[0], "date": s.index, "price_close": s.values}))


        df_bars = pd.concat(rows, ignore_index=True)
        df_bars["date"] = pd.to_datetime(df_bars["date"]).dt.tz_localize(None).dt.floor("D")

        df_bars = df_bars[
            (df_bars["date"] >= start_dt) &
            (df_bars["date"] <= pd.to_datetime(target_end_date))
        ]


        records = df_bars.to_dict(orient="records")
        inserted = 0
        with Session(engine) as session:
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                stmt = (
                    insert(MarketDB)
                    .values(batch)
                    .on_conflict_do_nothing(index_elements=["ticker", "date"])
                )
                result = session.execute(stmt)
                inserted += result.rowcount or 0
            session.commit()

        print("done updating market")








    @classmethod
    def update_market_old(cls):
        print("started updating market")
        trading_client = TradingClient(
            api_key=os.getenv("APCA_API_KEY_ID"),
            secret_key=os.getenv("APCA_API_SECRET_KEY")
        )
        data_client = StockHistoricalDataClient(
            api_key=os.getenv("APCA_API_KEY_ID"),
            secret_key=os.getenv("APCA_API_SECRET_KEY")
        )

        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        # we can use the calendar api to be sure
        calendar_req = GetCalendarRequest(start=today - timedelta(days=5), end=yesterday)
        calendar = trading_client.get_calendar(calendar_req)
        target_end_date = calendar[-1].date
        with Session(engine) as session:
            latest_db_date_raw = session.query(func.max(MarketDB.date)).scalar()
            latest_db_date = latest_db_date_raw.date() \
                if latest_db_date_raw else None

        if latest_db_date and latest_db_date >= target_end_date:
            #: if so, then dw dont need the update
            print("no update necessary")
            return

        start_fetch = (latest_db_date + timedelta(days=1)) if latest_db_date else (target_end_date - timedelta(days=365))

        tickers = cls.get_traded_assets()
        request_params = StockBarsRequest(
            symbol_or_symbols=tickers,
            timeframe=TimeFrame.Day,
            start=datetime.combine(start_fetch, datetime.min.time()),
            end=datetime.combine(target_end_date, datetime.max.time()),
            # feed='IEX' # Safest for free tier
        )

        bars = data_client.get_stock_bars(request_params)

        if bars.data:
            df_bars = bars.df.reset_index()
            df_bars = df_bars[['symbol', 'timestamp', 'close']].rename(
                columns={
                    "symbol": "ticker",
                    "timestamp": "date",
                    "close": "price_close"
                }
            )
            df_bars['date'] = df_bars['date'] \
                .dt.tz_localize(None).dt.floor('D')

            #: OBSERVATION: remember that sqlalchemy has a limitation for the
            # number of sim. write operations (per query) --> batching is necessary
            records = df_bars.to_dict(orient="records")
            inserted = 0

            with Session(engine) as session:
                for i in range(0, len(records), 300):
                    batch = records[i:i + 300]
                    stmt = (
                        insert(MarketDB)
                        .values(batch)
                        .on_conflict_do_nothing(
                            index_elements=["ticker", "date"]
                            )
                    )
                    result = session.execute(stmt)
                    inserted += result.rowcount or 0
                session.commit()
        print("market updated")

        

    @staticmethod
    def is_trading_day(date) -> bool:
        client = TradingClient(
            api_key=os.getenv("APCA_API_KEY_ID"),
            secret_key=os.getenv("APCA_API_SECRET_KEY"),
            paper=True,

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

        conditions = [MarketDB.ticker.in_(tickers)]

        if start:
            conditions.append(MarketDB.date >= start)
        if end:
            conditions.append(MarketDB.date <= end)

        stmt = (
            select(MarketDB)
            .where(and_(*conditions))
            .order_by(MarketDB.date)
        )

        return pd.read_sql(stmt, engine)

    @classmethod
    def get_latest_prices(cls, tickers: Iterable[str]) -> pd.DataFrame:
        if not tickers:
            raise ValueError("tickers must not be empty")

        subq = (
            select(
                MarketDB.ticker,
                func.max(MarketDB.date).label("max_date")
            )
            .where(MarketDB.ticker.in_(tickers))
            .group_by(MarketDB.ticker)
            .subquery()
        )

        stmt = (
            select(MarketDB)
            .join(
                subq,
                and_(
                    MarketDB.ticker == subq.c.ticker,
                    MarketDB.date == subq.c.max_date
                )
            )
        )

        return pd.read_sql(stmt, engine)
