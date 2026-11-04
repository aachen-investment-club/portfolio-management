import os

from typing import List

from datetime import datetime, timedelta

import pandas as pd

from lseg.data import rd


class Refinitiv:
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