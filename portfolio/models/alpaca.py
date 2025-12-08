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