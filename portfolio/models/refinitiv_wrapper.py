import os
import threading

from typing import List

from datetime import datetime, timedelta

import pandas as pd

import lseg.data as ld


class Refinitiv:
    """Thin wrapper around lseg.data.

    The session is opened lazily on first use (class-level, shared), so the
    classmethods work without instantiating the class. Instantiating it /
    using it as a context manager is still supported and closes the shared
    session on exit.
    """

    _session = None
    _lock = threading.Lock()

    @classmethod
    def open(cls):
        """Open the shared LSEG session if it is not already open."""
        with cls._lock:
            if cls._session is not None:
                return cls._session

            session = ld.session.platform.Definition(
                app_key=os.environ["LSEG_APP_KEY"],
                grant=ld.session.platform.GrantPassword(
                    username=os.environ["LSEG_USER_ID"],
                    password=os.environ["LSEG_PASSWORD"],
                ),
                signon_control=True
            ).get_session()

            session.open()
            ld.session.set_default(session)
            cls._session = session
            return session

    @classmethod
    def close(cls):
        with cls._lock:
            if cls._session is not None:
                ld.close_session()
                cls._session = None

    def __init__(self):
        type(self).open()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @classmethod
    def get_bars_time_range(cls, tickers, start, end, interval="1D") -> dict:
        # input tickers must be with RIC
        cls.open()
        df = ld.get_history(universe=tickers,
                            fields=["OPEN_PRC", "HIGH_1", "LOW_1", "TRDPRC_1", "ACVOL_UNS", "VWAP", "NUM_MOVES"],
                            interval=interval, start=start, end=end)
        # all fields: ['TRDPRC_1', 'HIGH_1', 'LOW_1', 'ACVOL_UNS', 'OPEN_PRC', 'BID', 'ASK', 'TRNOVR_UNS', 'VWAP', 'BLKCOUNT', 'BLKVOLUM', 'NUM_MOVES', 'TRD_STATUS', 'SALTIM', 'NAVALUE', 'VWAP_VOL', 'ACVOL_DEC']

        if not isinstance(df.columns, pd.MultiIndex):
            df = pd.concat({tickers[0]: df}, axis=1)

        bars = {}
        for ric in tickers:
            if ric not in df.columns:
                continue

            # remove RIC to have same output structure as Alpaca
            ticker = ric.split(".", 1)[0]
            instrument_data = df[ric]
            bars[ticker] = []

            for date, row in instrument_data.iterrows():
                bars[ticker].append({
                    "date": pd.Timestamp(date).tz_localize("UTC").isoformat(),
                    "open": None if pd.isna(row["OPEN_PRC"]) else float(row["OPEN_PRC"]),
                    "high": None if pd.isna(row["HIGH_1"]) else float(row["HIGH_1"]),
                    "low": None if pd.isna(row["LOW_1"]) else float(row["LOW_1"]),
                    "close": None if pd.isna(row["TRDPRC_1"]) else float(row["TRDPRC_1"]),
                    "volume": None if pd.isna(row["ACVOL_UNS"]) else float(row["ACVOL_UNS"]),
                    "trade_count": None if pd.isna(row["NUM_MOVES"]) else float(row["NUM_MOVES"]),
                    "vwap": None if pd.isna(row["VWAP"]) else float(row["VWAP"]),
                })

        return bars or None

    @classmethod
    def get_historical_data(cls, tickers: List[str]) -> dict:
        start = datetime.now() - timedelta(days=30)
        end = datetime.now()

        bars = cls.get_bars_time_range(tickers, start, end)

        if not bars:
            return None

        res = {}
        for ticker, data_list in bars.items():
            temp_list = []
            for row in data_list:
                new_row = {
                    "date": row["date"],
                    "price close": row["close"]
                }
                temp_list.append(new_row)
            res[ticker] = temp_list
        return res

    @classmethod
    def get_historical_net_asset_value(cls, portfolio: pd.DataFrame) -> list:
        # input tickers must be with RIC
        tickers = list(portfolio["ticker"].unique())

        start = datetime.now() - timedelta(days=30)
        end = datetime.now()

        bars = cls.get_bars_time_range(tickers, start, end)

        ric_mapping = {ric.split(".", 1)[0]: ric for ric in tickers}
        flat_bars = []
        if bars:
            for base_ticker, rows in bars.items():
                original_ric = ric_mapping.get(base_ticker, base_ticker)
                for row in rows:
                    flat_bars.append({"ticker": original_ric, **row})

        if not flat_bars:
            return []

        bars_df = pd.DataFrame(flat_bars)

        df_merged = pd.merge(bars_df, portfolio, how="left", on="ticker")
        df_merged["price close"] = df_merged["close"] * df_merged["shares"]

        df_nav = df_merged.groupby("date", as_index=False)["price close"].sum()

        df_nav["date"] = df_nav["date"].apply(
            lambda x: x.isoformat() if hasattr(x, "isoformat") else str(x))

        return df_nav[["date", "price close"]].to_dict(orient="records")