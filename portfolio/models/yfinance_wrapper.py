import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import List

class YFinanceProvider:
    
    @classmethod
    def get_bars_time_range(cls, tickers: List[str], start: datetime, end: datetime):
        """Fetches historical data for a specific range."""
        # yfinance download returns a multi-index DataFrame for multiple tickers
        data = yf.download(tickers, start=start, end=end, interval="1d", group_by='column')
        return data if not data.empty else None

    @classmethod
    def get_historical_data(cls, tickers: List[str]) -> dict:
        """Fetches last 30 days of closing prices in a dictionary format."""
        start_date = datetime.now() - timedelta(days=30)
        # Fetching 'Close' prices specifically
        data = yf.download(tickers, start=start_date, interval="1d")['Close']
        
        # If only one ticker, yfinance returns a Series; convert to DataFrame for consistency
        if isinstance(data, pd.Series):
            data = data.to_frame(name=tickers[0])
            
        res = dict()
        for ticker in tickers:
            # Handle potential missing data with dropna()
            ticker_data = data[ticker].dropna()
            res[ticker] = [
                {"date": date.isoformat(), "price close": price}
                for date, price in ticker_data.items()
            ]
        return res

    @classmethod
    def get_historical_net_asset_value(cls, portfolio: pd.DataFrame) -> dict:
        """Calculates total portfolio value over the last 30 days."""
        tickers = portfolio["ticker"].unique().tolist()
        start_date = datetime.now() - timedelta(days=30)
        
        # Download historical closing prices
        data = yf.download(tickers, start=start_date, interval="1d")['Close']
        
        # Handle single ticker edge case
        if len(tickers) == 1:
            data = data.to_frame(name=tickers[0])

        # Convert wide format to long format (melt) to match the portfolio structure
        df_prices = data.reset_index().melt(id_vars='Date', var_name='ticker', value_name='price close')
        df_prices.rename(columns={'Date': 'date'}, inplace=True)

        # Merge with portfolio to get share counts
        df_merged = pd.merge(df_prices, portfolio, on="ticker", how="left")
        
        # Calculate value: shares * price
        df_merged["total_value"] = df_merged["price close"] * df_merged["shares"]
        
        # Aggregate by date
        nav_history = df_merged.groupby("date")["total_value"].sum().reset_index()
        nav_history["date"] = nav_history["date"].apply(lambda x: x.isoformat())

        return {
            "asset": nav_history.rename(columns={"total_value": "price close"}).to_dict(orient="records")
        }