import os

from typing import List

from datetime import datetime, timedelta

import pandas as pd

from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

class Alpaca:
    ALPACA_KEY_ID = os.getenv("APCA_API_KEY_ID")
    ALPACA_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")


    @classmethod 
    def get_bars_time_range(cls, tickers, start, end): 
        client = StockHistoricalDataClient(
            cls.ALPACA_KEY_ID,
            cls.ALPACA_SECRET_KEY
        )

        request_params= StockBarsRequest(
            symbol_or_symbols=tickers, 
            timeframe=TimeFrame.Day, 
            start= start, #: inclusive
            end = end# non inclusive; add one because of this
        )
        bars = client.get_stock_bars(request_params)

        if bars:  
            return bars
        return None









    @classmethod
    def get_historical_data(cls, tickers: List[str]) -> dict:
        client = StockHistoricalDataClient(
            cls.ALPACA_KEY_ID,
            cls.ALPACA_SECRET_KEY
        )

        params = StockBarsRequest(
            symbol_or_symbols=tickers,
            timeframe=TimeFrame.Day,
            start=datetime.now() - timedelta(days=30)
        )

        data = client.get_stock_bars(params)
        
        res = dict()
        for ticker in tickers:
            history = list(map(lambda x: {
                "date": x.timestamp.isoformat(),
                "price close": x.close
            }, data[ticker]))
            res[ticker] = history
        return res
    
    @classmethod
    def get_historical_net_asset_value(cls, portfolio: pd.DataFrame) -> dict:
        client = StockHistoricalDataClient(
            cls.ALPACA_KEY_ID,
            cls.ALPACA_SECRET_KEY
        )
        tickers = list(portfolio["ticker"].unique())
        params = StockBarsRequest(
            symbol_or_symbols=tickers,
            timeframe=TimeFrame.Day,
            start=datetime.now() - timedelta(days=30)
        )

        data = client.get_stock_bars(params)
        
        df = pd.DataFrame(columns=["date", "price close", "ticker"])
        for ticker in tickers:
            history = pd.DataFrame(list(map(lambda x: {
                "date": x.timestamp,
                "price close": x.close,
                "ticker": ticker
            }, data[ticker])))
            df = pd.concat([df, history])
        df_merged = pd.merge(df, portfolio, how="left", on="ticker")
        df_merged["price close"] = df_merged["price close"] * df_merged["shares"]
        df_merged = df_merged.groupby("date").sum().reset_index()
        df_merged["date"] = df_merged["date"].apply(lambda x: x.isoformat())
        
        return {
            "asset": df_merged[["date", "price close"]].to_dict(orient="records")
        }
            

