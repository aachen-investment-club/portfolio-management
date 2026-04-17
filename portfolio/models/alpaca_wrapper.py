from http import client
import os
from typing import List
from datetime import datetime, timedelta
import pandas as pd

from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from dotenv import load_dotenv
load_dotenv()

DAILY_GRANULARITY = 'daily'
MINUTE_GRANULARITY = 'minute'


class Alpaca:
    _ALPACA_KEY_ID = os.getenv("APCA_API_KEY_ID")
    _ALPACA_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")
    _client = StockHistoricalDataClient(_ALPACA_KEY_ID, _ALPACA_SECRET_KEY)

    @classmethod
    def _get_client(cls):
        if cls._client is None:
            cls._client = StockHistoricalDataClient(cls._ALPACA_KEY_ID, cls._ALPACA_SECRET_KEY)
        return cls._client

    @classmethod
    def _build_request(cls, tickers, timeframe, start, end):
        return StockBarsRequest(
            symbol_or_symbols=tickers,
            timeframe=timeframe,
            start=start,
            end=end
        )
    
    @classmethod
    def _get_timeframe(cls, granularity=DAILY_GRANULARITY):
     if granularity == DAILY_GRANULARITY:
         return TimeFrame.Day
     if granularity == MINUTE_GRANULARITY:
         return TimeFrame.Minute
     
     raise ValueError(f"Unsupported granularity: {granularity}")
    
    @classmethod
    def _get_raw_historical_data(cls, tickers: List[str], granularity=DAILY_GRANULARITY) -> dict:
        client = cls._get_client()
        timeframe = cls._get_timeframe(granularity)
        request = cls._build_request(tickers=tickers, timeframe=timeframe, start=datetime.now() - timedelta(days=5), end=None)
        historical_data = client.get_stock_bars(request)
        if historical_data:
            return historical_data
        raise ValueError(f"There is no historical data.")
    
    
    @classmethod
    def _get_raw_historical_data_by_time_range(cls, tickers, start, end, granularity=DAILY_GRANULARITY):
        client = cls._get_client()
        timeframe = cls._get_timeframe(granularity)
        request = cls._build_request(tickers=tickers, timeframe=timeframe, start=start, end=end)
        historical_data = client.get_stock_bars(request)

        if historical_data:
            return historical_data
        raise ValueError(f"There is no historical data for this time range")

    @classmethod
    def get_historical_data(cls, tickers: List[str], granularity=DAILY_GRANULARITY) -> dict:
        historical_data = cls._get_raw_historical_data(tickers=tickers, granularity=granularity)

        res = dict()
        for ticker in tickers:
            history = list(map(lambda x: {
                "date": x.timestamp.isoformat(),
                "price close": x.close
            }, historical_data[ticker]))
            res[ticker] = history
        return res

    @classmethod
    def get_net_asset_value(
            cls, portfolio: pd.DataFrame, granularity=DAILY_GRANULARITY) -> pd.DataFrame:
        tickers = list(portfolio["ticker"].unique())
        data = cls._get_raw_historical_data(tickers=tickers, granularity=granularity)

        df = pd.DataFrame(columns=["date", "price close", "ticker"])
        for ticker in tickers:
            history = pd.DataFrame(list(map(lambda x: {
                "date": x.timestamp,
                "price close": x.close,
                "ticker": ticker
            }, data[ticker])))
            df = pd.concat([df, history])
        df_merged = pd.merge(df, portfolio, how="left", on="ticker")
        df_merged["price close"] = df_merged["price close"] * \
            df_merged["shares"]
        df_merged = df_merged.groupby("date").sum().reset_index()
        df_merged["date"] = df_merged["date"].apply(lambda x: x.isoformat())

        return df_merged

alpaca = Alpaca()
data = alpaca.get_historical_data(['AAPL'], DAILY_GRANULARITY)
print(len(data['AAPL']))