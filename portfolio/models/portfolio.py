from typing import List, Optional
from portfolio.models.market import Market

from datetime import date as dte
from datetime import datetime

import pandas as pd
import numpy as np
import json
import boto3
import yfinance as yf
import warnings

TR_TYPE = "type"
TR_CURRENCY = "currency"
TR_DATE = "date"
TR_VOLUME = "volume"
TR_TICKER = "ticker"
TR_TYPE = "type"


class Portfolio():
    def __init__(self, cash: float, leverage_limit: float) -> None:
        self.cash: float = cash
        self.leverage_limit: float = leverage_limit
        self.trades: Optional[pd.DataFrame] = None
        self.current_position = {}
        #: observation: we assume short selling in this implementation.
        self.initial_cash = cash

    def get_portfolio_positions_df(self):
        out = {
            "ticker": [],
            "shares": []
        }
        for symbol, value in self.current_position.items():
            out["ticker"].append(symbol)
            out["shares"].append(value)

        return pd.DataFrame(out)

    def get_position_weights(self):
        prices = self.get_prices_ts()

        if prices.empty:
            return []

        latest_prices = prices.iloc[-1]

        position_values = {}
        total_value = 0.0

        for symbol, shares in self.current_position.items():
            if symbol not in latest_prices:
                continue
            value = shares * latest_prices[symbol]
            position_values[symbol] = value
            total_value += value

        if total_value == 0:
            return []

        ttn, ntt = Market.get_ticker_short_name_map()
        metadata_map = Market.get_ticker_metadata_map()

        out = []
        for symbol, value in position_values.items():
            ticker_details = metadata_map.get(symbol, {"industry": "Unknown", "currency": "Unknown", "exchange": "Unknown"})
            
            item = {
                "symbol": symbol,
                "weight": value / total_value,
                "value": value,
                "shortname": ttn.get(symbol, symbol),
                "industry": ticker_details.get("industry"),
                "currency": ticker_details.get("currency"),
                "country": ticker_details.get("exchange")
            }
            
            if symbol in ttn:
                item["shortname"] = ttn[symbol]
            else:
                item["shortname"] = None
            out.append(item)

        return out

    def _signed_trades(self) -> pd.DataFrame:
        trades = self.trades.reset_index()

        trades["signed_qty"] = np.where(
            trades[TR_TYPE] == "PURCHASE",
            trades[TR_VOLUME],
            -trades[TR_VOLUME],
        )

        return trades[[TR_DATE, TR_TICKER, "signed_qty"]]

    def get_positions_ts(self) -> pd.DataFrame:
        trades = self._signed_trades()

        daily_flows = (
            trades
            .groupby([TR_DATE, TR_TICKER])["signed_qty"]
            .sum()
            .unstack(fill_value=0)
        )

        prices = self.get_prices_ts()

        daily_flows = (
            daily_flows
            .reindex(prices.index, fill_value=0)
            .sort_index()
        )

        return daily_flows.cumsum()

    def get_prices_ts(
        self,
        base_currency: str = "USD",
        convert_to_base: bool = True,
    ) -> pd.DataFrame:
        tickers = (
            self.trades
            .index
            .get_level_values(TR_TICKER)
            .unique()
            .tolist()
        )

        market = Market.get_historical_data(tickers)

        prices = (
            market
            .pivot_table(
                index="date",
                columns="ticker",
                values="price_close",
                aggfunc="last",
            )
            .sort_index()
        )

        prices.index = pd.to_datetime(prices.index).normalize()
        # Forward-fill prices
        prices = prices.ffill()

        if not convert_to_base:
            return prices

        ticker_currency_map = Market.get_ticker_currency_map(tickers)

        currencies = list({ticker_currency_map.get(t, base_currency) for t in prices.columns})

        fx_rates = Market.build_fx_rate_map(
            currencies=currencies,
            dates=prices.index,
            base_currency=base_currency,
        )

        usd_prices = prices.copy()
        for ticker in prices.columns:
            currency = ticker_currency_map.get(ticker, base_currency)
            conversion_series = fx_rates[currency]
            usd_prices[ticker] = prices[ticker] * conversion_series

        return usd_prices.ffill()

    def get_cash_ts(self, dates: pd.Index) -> pd.Series:
        trades = self.trades.reset_index()
        prices = self.get_prices_ts()   # already USD-normalized

        trades["date"] = pd.to_datetime(
            trades["date"]
        ).dt.normalize()

        px = prices.stack()
        trade_index = pd.MultiIndex.from_frame(
            trades[["date", TR_TICKER]]
        )
        trade_prices = px.reindex(trade_index).values

        trades["usd_trade_value"] = (
            trades[TR_VOLUME] * trade_prices
        )

        trades["signed_cash"] = np.where(
            trades[TR_TYPE] == "PURCHASE",
            -trades["usd_trade_value"],
            trades["usd_trade_value"],
        )

        daily_cash = (
            trades
            .groupby("date")["signed_cash"]
            .sum()
            .reindex(dates, fill_value=0)
            .cumsum()
        )

        return self.initial_cash + daily_cash

    def get_daily_nav(self) -> pd.Series:
        positions = self.get_positions_ts()
        prices = self.get_prices_ts()

        positions = positions.reindex(prices.index, method="ffill").fillna(0)

        """
        the core idea of this formula:

        nav_t = cash_t + sum_{assset}(position(asset, t)*price(asset, t) )
        """

        market_value = (positions * prices).sum(axis=1)
        cash = self.get_cash_ts(prices.index)

        nav = market_value + cash
        nav.name = "NAV"
        return nav

    def resample_trades_to_daily(self) -> None:
        """
        Compresses minute-level (or highly granular) tradelogs to a day-level frequency.
        Intraday trades for the same ticker are netted against each other, optimizing performance.
        """
        if self.trades is None or self.trades.empty:
            return

        trades = self.trades.reset_index()

        # Calculate signed quantity to properly net buys and sells
        trades["signed_qty"] = np.where(
            trades[TR_TYPE] == "PURCHASE",
            trades[TR_VOLUME],
            -trades[TR_VOLUME],
        )

        trades["normalized_date"] = pd.to_datetime(trades[TR_DATE]).dt.normalize()

        daily_trades = trades.groupby([TR_TICKER, "normalized_date", TR_CURRENCY], as_index=False)["signed_qty"].sum()
        daily_trades = daily_trades[daily_trades["signed_qty"] != 0].copy()

        daily_trades[TR_TYPE] = np.where(daily_trades["signed_qty"] > 0, "PURCHASE", "SALE")
        daily_trades[TR_VOLUME] = daily_trades["signed_qty"].abs()

        daily_trades = daily_trades.rename(columns={"normalized_date": TR_DATE})
        daily_trades = daily_trades.drop(columns=["signed_qty"])

        self.trades = daily_trades.set_index([TR_TICKER, TR_DATE]).sort_index()


    def import_from_dict(self, data):
        """
        imports a FULL trades log and:
        - saves the trades
        - updates the current position
        - updates current cash
        """

        rows = []

        for transaction in data["transactions"]:
            rows.append({
                TR_TICKER: transaction["security"]["ticker"],
                TR_CURRENCY: transaction["currency"],
                TR_TYPE: transaction["type"],
                TR_DATE: pd.Timestamp(transaction["date"]),
                TR_VOLUME: float(transaction["shares"]),
            })

        self.trades = pd.DataFrame(rows)
        self.trades = self.trades.set_index([TR_TICKER, TR_DATE]).sort_index()
        

        tickers = (
            self.trades
            .index
            .get_level_values(TR_TICKER)
            .unique()
            .tolist()
        )

        currency_map = Market.get_ticker_currency_map(tickers)

        missing_currency = [
            t for t in tickers
            if t not in currency_map
        ]

        if missing_currency:
            warnings.warn(
                f"Missing currency metadata for: {missing_currency}. Defaulting to USD.",
                UserWarning
            )

        # ✅ RECOMPUTE STATE FROM EXISTING METHODS
        prices = self.get_prices_ts()
        positions = self.get_positions_ts()

        # Prevent IndexError if price history is empty (eg initial local setup)
        if prices.empty:
                self.current_position = {}
                self.cash = self.initial_cash
                return

        positions = positions.reindex(prices.index, method="ffill").fillna(0)
        last_date = prices.index[-1]

        self.current_position = {
            ticker: float(qty)
            for ticker, qty in positions.loc[last_date].items()
            if qty != 0
        }

        self.cash = float(self.get_cash_ts(prices.index).loc[last_date])


    @staticmethod
    def import_from_csv(csv_rows): 
        """
        converts the csv into the intermediate dict format used during development.
        """

        def isin_to_security(isin, currency, data):
            if isin in data:# this is just a memoization approach.
                return data[isin]

            security = {"name": None, "ticker": None, "currency": currency}

            try:
                search = yf.Search(isin)
                if getattr(search, "quotes", None):
                    symbol = search.quotes[0].get("symbol")
                    security["ticker"] = symbol

                    if symbol:
                        t = yf.Ticker(symbol)
                        info = getattr(t, "info", {}) or {}
                        security["name"] = info.get("shortName") or info.get("longName")
            except Exception:
                pass

            data[isin] = security
            return security

        

        transactions = []

        portfolio = list(csv_rows[0].values())[0]
        currency_row = next(iter(csv_rows[1].values()))
        currency = "USD" if "USD" in currency_row else "EUR"

        security_cache = {}  

        for row in csv_rows[3:]:
            date, information = row.values()
            dt = datetime.strptime(date, "%d.%m.%Y %H:%M:%S")
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H:%M")
            tx = {}
            tx["type"] = "PURCHASE" if "Kauf" in information[0] else "SALE"
            security_isin = information[1]
            shares = information[2]

            tx["shares"] = float(shares.replace(",",""))
            tx["date"] = date_str
            tx["time"] = time_str
            tx["portfolio"] = portfolio
            tx["account"] = currency
            tx["currency"] = currency
            tx["security"] = isin_to_security(security_isin, currency, security_cache)

            transactions.append(tx)

        final = {"version": 1, "transactions": transactions}

        return final
                




    def import_from_json(self, path):
        """
        imports a FULL trades log and:
        - saves the trades
        - updates the current position
        - updates current cash
        """

        with open(path, mode="r", encoding="utf-8") as file:
            data = json.load(file)
            rows = []

            for transaction in data["transactions"]:
                rows.append({
                    TR_TICKER: transaction["security"]["ticker"],
                    TR_CURRENCY: transaction["currency"],
                    TR_TYPE: transaction["type"],
                    TR_DATE: pd.Timestamp(transaction["date"]),
                    TR_VOLUME: float(transaction["shares"])
                })

            #: TODO: consider the operation type; add options to reconstruct portfolio states

            self.trades = pd.DataFrame(rows)
            self.trades = self.trades \
                .set_index([TR_TICKER, TR_DATE]).sort_index()

            today = dte.today()
            self.current_position, self.cash = self.get_position(today)

    def get_owned_securities(self) -> List[str]:
        return list(self.current_position.keys())

    def get_buy_prices(self, ticker: str):
        asset_df = self.trades.loc[[ticker]].reset_index()
        asset_df["price"] = asset_df[TR_DATE].apply(
            lambda x: Market.get_price(ticker, x.date())
        )
        return asset_df

    def _latest_price(self, ticker: str) -> float:
        prices = self.get_prices_ts()
        return float(prices[ticker].iloc[-1])

    def get_gross_exposure(self) -> float:
        positions = self.get_positions_ts().iloc[-1]
        prices = self.get_prices_ts().iloc[-1]
        return float((positions.abs() * prices).sum())

    def get_net_asset_value(self) -> float:
        return self.cash + self.get_gross_exposure()

    def summary(self) -> dict:
        #: TODO: extend this with positions (?)
        return {
            "cash": self.cash,
            "gross_exposure": self.get_gross_exposure(),
            "net_asset_value": self.get_net_asset_value()
        }

    def check_leverage(self, new_cash, new_positions):
        gross = sum(abs(qty) * self._latest_price(p)
                    for p, qty in new_positions.items())
        net_value = new_cash + sum(qty * self._latest_price(p)
                                   for p, qty in new_positions.items())
        leverage = gross / max(net_value, 1e-8)
        return leverage <= self.leverage_limit

    def get_current_leverage(self):
        gross = sum(abs(qty) * self._latest_price(p)
                    for p, qty in self.current_position.items())
        net_value = self.cash + sum(qty * self._latest_price(p)
                                    for p, qty
                                    in self.current_position.items())
        leverage = gross / max(net_value, 1e-8)
        return leverage



    @staticmethod
    def list_portfolios():
        client = boto3.client("s3")
        bucket = "portfolio-management-developer"
        prefix = "portfolios/"
        objects = client.list_objects_v2(Bucket=bucket, Prefix=prefix)

        portfolios_names = [
                object["Key"] for object in objects["Contents"]
                if object["Key"] != prefix]

        portfolios = {}
        for file_name in portfolios_names:
            response = client.get_object(
                Bucket=bucket,
                Key=file_name
            )
            text = response["Body"].read().decode("utf-8")
            log = json.loads(text)
            portfolios[file_name] = log
        return portfolios



    @staticmethod
    def upload_portfolio(data, filename):

        s3_client = boto3.client("s3")
        bucket = "portfolio-management-developer"

        s3_client.put_object(
            Bucket=bucket,
            Key=f"portfolios/{filename}",
            Body=json.dumps(data, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )

            

    @staticmethod
    def remove_portfolio(file):
        portfolios = Portfolio.list_portfolios()
        print(file)
        print(portfolios.keys())
        if file in portfolios.keys():

            s3_client = boto3.client("s3")

            bucket = "portfolio-management-developer"
            s3_client.delete_object(
                Bucket=bucket,
                Key=file
            )
 
