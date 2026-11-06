import os

from typing import List

from datetime import datetime, timedelta

import pandas as pd

from lseg.data import rd


class Refinitiv:
    def __init__(self):
        rd.open_session()
        self._is_open = True

    def close(self):
        if self._is_open:
            rd.close_session()
            self._is_open = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        
    @classmethod
    def get_bars_time_range(cls, tickers, start, end):
        pass

    @classmethod
    def get_historical_data(cls, tickers: List[str]) -> dict:
        pass

    @classmethod
    def get_historical_net_asset_value(
            cls, portfolio: pd.DataFrame) -> pd.DataFrame:
        pass