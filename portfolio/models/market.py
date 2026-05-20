from typing import List, Iterable,Dict , Tuple
from typing import List, Iterable, Union
from datetime import datetime, timedelta
import awswrangler as wr

from click import clear
import pandas as pd
import numpy as np
import requests
import json
import os
import yfinance as yf
import warnings

from sqlalchemy import (
    select,
    and_,
    func
)
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from portfolio.utils.aws_config import engine
from portfolio.schemas.market import MarketDB, MarketMinuteDB, TickerMeta, ForexDayDB, ForexMinuteDB
from alpaca.trading import GetCalendarRequest
from alpaca.trading.client import TradingClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.historical import StockHistoricalDataClient

from portfolio.exceptions import (
    TickerException,
    TradingDayException,
    DateException )


DATE = "date"
TICKER = "ticker"
PRICE = "price_close"
BASE_CURRENCY = "USD"
FX_SUFFIX = "=X"

VALID_YF_INTERVALS = {"1m", "1d"}

MINUTE_GRANULARITY = "1m"
DAY_GRANULARITY= "1d"
SEVEN_DAYS = timedelta(days=7)


DB_GRANULARITY = os.getenv("DB_GRANULARITY", "day").lower()
DB = MarketMinuteDB if DB_GRANULARITY == "minute" else MarketDB

FOREXDB= ForexMinuteDB if DB_GRANULARITY == "minute" else ForexDayDB
GRANULARITY = MINUTE_GRANULARITY if DB_GRANULARITY == "minute" else DAY_GRANULARITY

MINUTE_DATA_SOURCE =  os.getenv("MINUTE_DATA_SOURCE", "day").lower()
MINUTE_DATA_SOURCE_LOCAL = "local"
MINUTE_DATA_SOURCE_ATHENA = "athena"



threads_env = os.getenv("YF_THREADS", "0")

try:
    threads_count = int(threads_env)
    yf_threads = False if threads_count <= 0 else threads_count
except ValueError:
    yf_threads = False

print(f"using {yf_threads if yf_threads else "no"} threads for yfinance")


class Market:
    """
    - quotes is a DataFrame with a multiindex of form Ticker (string), Date (datetime).
    """
    US_TREASURY_API = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"




    @classmethod
    def load_ticker_metadata(cls, path, batch_size: int = 5_000): 

        total_inserted = 0


        with Session(engine) as session:
            with pd.read_csv(path, chunksize=batch_size) as reader:
                #: similar as for vanilla "with open" statement, read_csv can also be unsafe.
                for chunk in reader:
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
        market_empty = False
        stmt_market = select(DB.ticker).limit(1)
        with Session(engine) as session:
            market_empty = session.scalar(stmt_market) is None
        return market_empty
    
    @classmethod
    def check_forex_empty(cls):
        forex_empty = False
        stmt_forex = select(FOREXDB.ticker).limit(1)
        with Session(engine) as session:
            forex_empty = session.scalar(stmt_forex) is None
        return forex_empty 
    



        
    @classmethod
    def get_all_tickers(cls):
        stmt = select(DB.ticker).distinct()
        with Session(engine) as session:
            result = session.scalars(stmt).all()
            return result

    @classmethod
    def load_from_csv(cls, path: str, batch_size: int = 5_000) -> int:
        
        total_inserted = 0


        with Session(engine) as session:

            with pd.read_csv(path, chunksize=batch_size) as reader: 
                for chunk in reader:
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
                        insert(DB)
                        .values(records)
                        .on_conflict_do_nothing(index_elements=["ticker", "date"])
                    )


                    result = session.execute(stmt)
                    total_inserted += result.rowcount or 0

                    session.commit()

        return total_inserted 

    @classmethod
    def get_price(cls, ticker: str, date: Union[datetime.date, datetime])->np.float64: 

        if ticker not in cls.get_traded_assets():
            raise TickerException(f"Ticker {ticker} is not traded in the market.")

        day_only = date.date() if isinstance(date, datetime) else date 

        if not cls.is_trading_day(date): 
            raise TradingDayException(f"{date} is not a trading day (might be weekend or public holiday).")

        if date not in cls.get_trading_days(): 
            raise DateException(f"{date} is not available in the market database.") 

        if GRANULARITY == MINUTE_GRANULARITY:
            if not isinstance(date, datetime): 
                raise ValueError("For minute level granularity, target_date must be a datetime.datetime object with minute level information.")
        else: 
            query_dt = datetime.combine(day_only, datetime.min.time())

        stmt = (
            select(DB.price_close).where(
                DB.ticker == ticker, 
                DB.date == query_dt 
            )
        )

        with Session(engine) as session:
            result = session.scalar(stmt)

        if result is None:
            raise LookupError(f"No price for {ticker} on {date}")

        return float(result)

    @classmethod
    def get_trading_days(cls) -> List:
        stmt = select(DB.date).distinct().order_by(DB.date)

        with Session(engine) as session:
            return [d.date() for d in session.scalars(stmt)]

    @classmethod
    def get_traded_assets_meta(cls) -> List[str]:
        """
        fetches traded assets in the METADATA DB
        """
        stmt = select(TickerMeta.ticker).distinct().order_by(TickerMeta.ticker)

        with Session(engine) as session:
            return list(session.scalars(stmt))






    @classmethod
    def get_traded_assets(cls) -> List[str]:
        """
        fetches traded assets in the DB 
        """
        stmt = select(DB.ticker).distinct().order_by(DB.ticker)

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
    def get_ticker_metadata_map(cls) -> Dict[str, Dict[str, str]]:
        """
        Returns a dictionary mapping each ticker to its metadata properties.

        """
        stmt = select(TickerMeta.ticker, TickerMeta.industry, TickerMeta.currency, TickerMeta.exchange).distinct()
        
        with Session(engine) as session:
            rows = session.execute(stmt).all()
        
        metadata_map = {}
        for ticker, industry, currency, exchange in rows:
            if not ticker:
                continue
            metadata_map[ticker] = {
                "industry": industry or "Unknown",
                "currency": currency or "Unknown",
                "exchange": exchange or "Unknown"  
            }
            
        return metadata_map


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
            latest_db_date = session.query(func.max(DB.date)).scalar()
            return latest_db_date.date() if latest_db_date else None

    @classmethod
    def get_latest_forex_date_in_db(cls):
        with Session(engine) as session:
            result = session.query(func.max(FOREXDB.date)).scalar()
            return result.date() if result else None  

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



        #tickers = list(cls.get_traded_assets())
        tickers = list(cls.get_traded_assets_meta())


        if GRANULARITY == MINUTE_GRANULARITY:
            # 1. ALWAYS fetch a rolling 7-day window for minute data
            start_dt = pd.to_datetime(today - timedelta(days=7))
            end_dt_excl = pd.to_datetime(today + timedelta(days=1)) # Include up to right now
        else:
            # 2. Daily data continues to rely on the latest DB date
            latest_db_date = cls.get_latest_date_in_db()
            
            if latest_db_date is None:
                start_dt = pd.to_datetime(today - timedelta(days=365)) # fallback
            else:
                start_dt = pd.to_datetime(latest_db_date + timedelta(days=1))
                
            end_dt_excl = pd.to_datetime(target_end_date) + pd.Timedelta(days=1)
            
            # Safety check for daily data
            if start_dt >= end_dt_excl:
                print("Daily database is already up to date for this period.")
                return
        
        

        yfinance_data_output = yf.download(
            tickers=tickers,
            start=start_dt,
            end=end_dt_excl,
            interval=GRANULARITY,
            group_by="ticker",
            progress=False,
            threads = yf_threads
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
        df_bars["date"] = pd.to_datetime(df_bars["date"]).dt.tz_localize(None)

        df_bars = df_bars[
            (df_bars["date"] >= start_dt) &
            (df_bars["date"] <  pd.to_datetime(end_dt_excl))
        ]


        if GRANULARITY == MINUTE_GRANULARITY and MINUTE_DATA_SOURCE == "athena":
            print("DEBUG: started athena update (minute level)")

            s3_bucket = os.getenv("ATHENA_BUCKET_BASE")
            glue_db = os.getenv("GLUE_DB")
            table_name = os.getenv("ATHENA_MINUTE_TABLE")
            
            # Create partition column
            df_bars['month'] = df_bars['date'].dt.strftime('%Y-%m')
            affected_months = df_bars['month'].unique()

            
            for month in affected_months:
                new_month_data = df_bars[df_bars['month'] == month]
                
                # 1. Fetch existing data for this month
                try:
                    existing_data = pd.read_sql(
                        f"SELECT * FROM {table_name} WHERE month = '{month}'", 
                        con=engine
                    )
                except Exception:
                    existing_data = pd.DataFrame()

                if not existing_data.empty:
                    combined_df = pd.concat([existing_data, new_month_data])
                else:
                    combined_df = new_month_data

                combined_df = combined_df.drop_duplicates(subset=["ticker", "date"], keep="last")
                print("inside the if: ")
                print(combined_df)
                
                # 3. Overwrite the S3 partition (Maintains 3 buckets)
                wr.s3.to_parquet(
                    df=combined_df,
                    path=f"{s3_bucket}/market_minute/",
                    dataset=True,
                    database=glue_db,
                    table=table_name,
                    partition_cols=['month'],
                    bucketing_info=(["ticker"], 3),
                    mode='overwrite_partitions',
                    index=False
                )
            print("Athena market update complete.")
            return 


        records = df_bars.to_dict(orient="records")
        inserted = 0

        with Session(engine) as session:
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                stmt = (
                    insert(DB)
                    .values(batch)
                    .on_conflict_do_nothing(index_elements=["ticker", "date"])
                )
                result = session.execute(stmt)
                inserted += result.rowcount or 0
            session.commit()

        print("done updating market")


    FOREX_PAIRS = [
        "EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X",
        "AUDUSD=X", "EURJPY=X", "USDCNH=X"
            ] # added the popular forex pairs

    @classmethod
    def update_forex(cls,  batch_size: int = 300):
        print("started Forex update")

        #trading_client = TradingClient(
            #api_key=os.getenv("APCA_API_KEY_ID"),
            #secret_key=os.getenv("APCA_API_SECRET_KEY")
        #)

        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        #calendar_req = GetCalendarRequest(start=today - timedelta(days=10), end=yesterday)
        #calendar = trading_client.get_calendar(calendar_req)
        #if not calendar:
            #print("no calendar data returned; aborting update")
            #return

        #target_end_date = calendar[-1].date  

        latest_db_date = cls.get_latest_forex_date_in_db()
        
        
        if latest_db_date and latest_db_date >= yesterday:
            print("forex already up to date")
            return

        
        if GRANULARITY == MINUTE_GRANULARITY:
            start_dt = pd.to_datetime(today - timedelta(days=7))
            end_dt_excl = pd.to_datetime(today + timedelta(days=1)) 
        else:
            latest_db_date = cls.get_latest_forex_date_in_db()
            
            if latest_db_date and latest_db_date >= yesterday:
                print("Forex daily data already up to date")
                return
                
            if cls.check_forex_empty(): 
                # (Note: I changed DB.date to FOREXDB.date here for correctness)
                stmt = select(func.min(FOREXDB.date))
                with Session(engine) as session:
                    earliest_db_date = session.scalar(stmt)
                
                if earliest_db_date:
                    start_dt = pd.to_datetime(earliest_db_date)
                else:
                    start_dt = pd.to_datetime(yesterday - timedelta(days=365))
            else: 
                start_dt = pd.to_datetime(latest_db_date + timedelta(days=1))
            
            end_dt_excl = pd.to_datetime(yesterday) + pd.Timedelta(days=1)
            
            if start_dt >= end_dt_excl:
                return

        yfinance_data_output = yf.download(
            tickers=cls.FOREX_PAIRS,
            start=start_dt,
            end=end_dt_excl,
            interval=GRANULARITY,
            group_by="ticker",
            progress=False,
            threads = yf_threads
        )

        if yfinance_data_output is None or yfinance_data_output.empty:
            print("yfinance did not return any forex data")
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
                for t in cls.FOREX_PAIRS:
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
                    rows.append(pd.DataFrame({"ticker": cls.FOREX_PAIRS[0], "date": s.index, "price_close": s.values}))

        if not rows:
            print("no forex rows to insert")
            return

        df_bars = pd.concat(rows, ignore_index=True)
        df_bars["date"] = pd.to_datetime(df_bars["date"]).dt.tz_localize(None)
        df_bars = df_bars[
            (df_bars["date"] >= start_dt) &
            (df_bars["date"] <end_dt_excl)
        ]
        if GRANULARITY == MINUTE_GRANULARITY and MINUTE_DATA_SOURCE == "athena":
            s3_bucket = os.getenv("ATHENA_BUCKET_BASE")
            glue_db = os.getenv("GLUE_DB")
            table_name = os.getenv("ATHENA_MINUTE_TABLE_FOREX")
            
            df_bars['month'] = df_bars['date'].dt.strftime('%Y-%m')
            affected_months = df_bars['month'].unique()

            print(f"Syncing Forex to Athena. Affected months: {affected_months}")
            
            for month in affected_months:
                new_month_data = df_bars[df_bars['month'] == month]
                
                try:
                    existing_data = pd.read_sql(
                        f"SELECT * FROM {table_name} WHERE month = '{month}'", 
                        con=engine
                    )
                except Exception:
                    existing_data = pd.DataFrame()

                if not existing_data.empty:
                    combined_df = pd.concat([existing_data, new_month_data])
                else:
                    combined_df = new_month_data
                    
                combined_df = combined_df.drop_duplicates(subset=["ticker", "date"], keep="last")
                
                wr.s3.to_parquet(
                    df=combined_df,
                    path=f"{s3_bucket}/forex_minute/",
                    dataset=True,
                    database=glue_db,
                    table=table_name,
                    partition_cols=['month'],
                    bucketing_info=(["ticker"], 5), # 5 buckets for Forex
                    mode='overwrite_partitions',
                    index=False
                )
            print("Athena forex update complete.")
            return

        records = df_bars.to_dict(orient="records")
        inserted = 0
        with Session(engine) as session:
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                stmt = (
                    insert(FOREXDB)
                    .values(batch)
                    .on_conflict_do_nothing(index_elements=["ticker", "date"])
                )
                result = session.execute(stmt)
                inserted += result.rowcount or 0
            session.commit()

        print(f"forex update done: {inserted} new rows inserted")





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
            latest_db_date_raw = session.query(func.max(DB.date)).scalar()
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
                .dt.tz_localize(None)

            #: OBSERVATION: remember that sqlalchemy has a limitation for the
            # number of sim. write operations (per query) --> batching is necessary
            records = df_bars.to_dict(orient="records")
            inserted = 0

            with Session(engine) as session:
                for i in range(0, len(records), 300):
                    batch = records[i:i + 300]
                    stmt = (
                        insert(DB)
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

        conditions = [DB.ticker.in_(tickers)]

        if start:
            conditions.append(DB.date >= start)
        if end:
            conditions.append(DB.date <= end)

        if start and end and MINUTE_DATA_SOURCE == "athena":
            start_month = start.replace(day=1) # Ensure we capture the start month
            months = pd.date_range(start_month, end, freq='MS').strftime('%Y-%m').tolist()
            
            if not months: 
                months = [start.strftime('%Y-%m')]
                
            conditions.append(DB.month.in_(months))



        stmt = (
            select(DB)
            .where(and_(*conditions))
            .order_by(DB.date)
        )

        return pd.read_sql(stmt, engine)

    @classmethod
    def get_latest_prices(cls, tickers: Iterable[str]) -> pd.DataFrame:
        if not tickers:
            raise ValueError("tickers must not be empty")

        subq = (
            select(
                DB.ticker,
                func.max(DB.date).label("max_date")
            )
            .where(DB.ticker.in_(tickers))
            .group_by(DB.ticker)
            .subquery()
        )

        stmt = (
            select(DB)
            .join(
                subq,
                and_(
                    DB.ticker == subq.c.ticker,
                    DB.date == subq.c.max_date
                )
            )
        )

        return pd.read_sql(stmt, engine)
    
    
    @classmethod
    def get_ticker_currency_map(cls, tickers: Iterable[str]) -> dict:
        """
        Returns:
            {
                "AAPL": "USD",
                "SAP.DE": "EUR"
            }
        """
        if not tickers:
            return {}

        stmt = (
            select(
                TickerMeta.ticker,
                TickerMeta.currency
            )
            .where(TickerMeta.ticker.in_(tickers))
        )

        with Session(engine) as session:
            rows = session.execute(stmt).all()

        out = {}
        for ticker, currency in rows:
            if currency is None:
                out[ticker] = BASE_CURRENCY
            else:
                out[ticker] = currency.upper()

        return out

    @classmethod
    def get_forex_history(
        cls,
        forex_tickers: Iterable[str],
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame:
        if not forex_tickers:
            return pd.DataFrame(columns=["ticker", "date", "price_close"])

        conditions = [FOREXDB.ticker.in_(forex_tickers)]

        if start:
            conditions.append(FOREXDB.date >= start)
        if end:
            conditions.append(FOREXDB.date <= end)
        
        if start and end and MINUTE_DATA_SOURCE == "athena":
            # this is impotant wrt. how we do partitioning in athena
            start_month = start.replace(day=1)
            months = pd.date_range(start_month, end, freq='MS').strftime('%Y-%m').tolist()
            
            if not months: 
                months = [start.strftime('%Y-%m')]
                
            conditions.append(FOREXDB.month.in_(months))

        stmt = (
            select(FOREXDB)
            .where(and_(*conditions))
            .order_by(FOREXDB.date)
        )

        return pd.read_sql(stmt, engine)

    @classmethod
    def build_fx_rate_map(
        cls,
        currencies: Iterable[str],
        dates: pd.Index,
        base_currency: str = BASE_CURRENCY,
    ) -> pd.DataFrame:
        """
        Returns a DataFrame indexed by date.
        Columns are currency codes.
        Values are FX conversion factors INTO USD.

        Example:
            EUR -> 1.08
            JPY -> 0.0067

        meaning:
            usd_price = local_price * fx_factor
        """

        currencies = sorted(set([c.upper() for c in currencies]))

        fx_df = pd.DataFrame(index=dates)

        for currency in currencies:
            if currency == base_currency:
                fx_df[currency] = 1.0
                continue

            direct_pair = f"{currency}{base_currency}{FX_SUFFIX}"   # e.g. EURUSD=X
            inverse_pair = f"{base_currency}{currency}{FX_SUFFIX}"  # e.g. USDJPY=X

            fx_history = cls.get_forex_history([direct_pair, inverse_pair])

            if fx_history.empty:
                warnings.warn(
                    f"No FX history found for {currency}, defaulting conversion to 1.0 (USD assumed)",
                    UserWarning
                )
                fx_df[currency] = 1.0
                continue

            fx_pivot = (
                fx_history
                .pivot_table(
                    index="date",
                    columns="ticker",
                    values="price_close",
                    aggfunc="last",
                )
                .sort_index()
            )

            fx_pivot.index = pd.to_datetime(fx_pivot.index).normalize()
            fx_pivot = fx_pivot.reindex(dates).ffill()

            if direct_pair in fx_pivot.columns:
                fx_df[currency] = fx_pivot[direct_pair]
            elif inverse_pair in fx_pivot.columns:
                fx_df[currency] = 1.0 / fx_pivot[inverse_pair]
            else:
                warnings.warn(
                    f"Could not construct FX series for {currency}, defaulting to 1.0",
                    UserWarning
                )
                fx_df[currency] = 1.0

        return fx_df.ffill()
    
    

    @classmethod
    def get_market_data_from_yf(cls, tickers, start_date, end_date):
        print(f"Getting data from yfinance from {start_date} until {end_date} with granularity {GRANULARITY} ...")

        available_tickers = cls.get_traded_assets()

        if isinstance(tickers, str):
            tickers = [tickers]

        tickers = list(set(available_tickers) & set(tickers))
        if not tickers:
            raise ValueError("Given tickers are not supported.")

        if GRANULARITY not in VALID_YF_INTERVALS:
            raise ValueError(f"Given interval is not supported. Valid options: {VALID_YF_INTERVALS}")

        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d")

        if GRANULARITY == MINUTE_GRANULARITY and (end_date - start_date) >= SEVEN_DAYS:
            raise ValueError("yfinance does not give minute granularity for durations of 7 days or more.")

        try:
            yfinance_data_output = yf.download(
                tickers=tickers,
                start=start_date,
                end=end_date,
                interval=GRANULARITY,
                group_by="ticker",
                progress=False,
                threads = yf_threads
            )
        except Exception as e:
            raise RuntimeError(f"Failed to download data from yfinance: {e}") from e

        if yfinance_data_output is None or yfinance_data_output.empty:
            raise ValueError("yfinance did not return any data.")

        rows = []

        if isinstance(yfinance_data_output.columns, pd.MultiIndex):
            if "Close" in yfinance_data_output.columns.get_level_values(0):
                close = yfinance_data_output["Close"]
                for t in close.columns:
                    s = close[t].dropna()
                    if not s.empty:
                        rows.append(pd.DataFrame({
                            TICKER: t,
                            DATE: s.index,
                            PRICE: s.values,
                        }))
            else:
                for t in tickers:
                    try:
                        s = yfinance_data_output[t]["Close"].dropna()
                    except Exception:
                        continue

                    if not s.empty:
                        rows.append(pd.DataFrame({
                            TICKER: t,
                            DATE: s.index,
                            PRICE: s.values,
                        }))
        else:
            if "Close" in yfinance_data_output.columns:
                s = yfinance_data_output["Close"].dropna()
                if not s.empty:
                    rows.append(pd.DataFrame({
                        TICKER: tickers[0],
                        DATE: s.index,
                        PRICE: s.values,
                    }))

        if not rows:
            raise ValueError("No close prices were returned for the requested tickers.")

        df_bars = pd.concat(rows, ignore_index=True)

        df_bars[DATE] = pd.to_datetime(df_bars[DATE])

        if getattr(df_bars[DATE].dt, "tz", None) is not None:
            df_bars[DATE] = df_bars[DATE].dt.tz_localize(None)

        print(df_bars.head())
        return df_bars
