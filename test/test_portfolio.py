import unittest
from unittest.mock import patch

import pandas as pd
import numpy as np

from portfolio.models.portfolio import Portfolio


TR_TYPE = "type"
TR_CURRENCY = "currency"
TR_DATE = "date"
TR_VOLUME = "volume"
TR_TICKER = "ticker"

class TestPortfolio(unittest.TestCase):
    """
        Unit tests for Portfolio model.

        Required:
            APCA_API_KEY_ID, APCA_API_SECRET_KEY required for tests to run correctly

        To run:
            python -m unittest discover -s test 
    """

    def setUp(self):
        self.initial_cash = 10000
        self.portfolio = Portfolio(cash=self.initial_cash, leverage_limit=2.0)

        mock_trades = pd.DataFrame({
            TR_TICKER: ["AAPL", "GOOG", "AAPL", "GOOG"],
            TR_CURRENCY: ["USD", "USD", "USD", "USD"],
            TR_TYPE: ["PURCHASE", "SALE", "PURCHASE", "SALE"],
            TR_DATE: pd.to_datetime(["2023-01-01", "2023-01-01", "2023-01-02", "2023-01-02"]),
            TR_VOLUME: [6, 5, 3, 10],
        })
        self.portfolio.trades = mock_trades.set_index([TR_TICKER, TR_DATE]).sort_index()

        # Creates a mock Market
        self.patcher = patch('portfolio.models.market.Market.get_historical_data')
        self.mock_market = self.patcher.start()
        self.mock_market.return_value = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01", "2023-01-01", "2023-01-02", "2023-01-02"]),
            "price_close": [100, 200, 110, 190], 
            "ticker": ["AAPL", "GOOG", "AAPL", "GOOG"]
        })

    # Stops the mock Market
    def tearDown(self):
        self.patcher.stop()

    def test_get_prices_ts(self):
        expected_values = np.array([[100, 200], [110, 190]])

        actual_values = np.array(self.portfolio.get_prices_ts())
        
        np.testing.assert_allclose(
            actual_values, expected_values
        )
        
    def test_signed_trades(self):
        expected_values = np.array([6, 3, -5, -10])

        actual_values = np.array(self.portfolio._signed_trades()["signed_qty"].values)

        np.testing.assert_allclose(
            actual_values, expected_values
        )

    def test_get_positions_ts(self):
        expected_values = np.array([[6, -5], [9, -15]])

        actual_values = np.array(self.portfolio.get_positions_ts())

        np.testing.assert_allclose(
            actual_values, expected_values
        )

    def test_get_cash_ts(self):
        expected_values = np.array([10400, 11970])

        dates = pd.date_range(start="2023-01-01", end="2023-01-02", freq="D")
        actual_values = np.array(self.portfolio.get_cash_ts(dates))

        np.testing.assert_allclose(
            actual_values, expected_values
        )

    def test_get_daily_nav(self):
        expected_values = [10000, 10110]

        actual_values = np.array(self.portfolio.get_daily_nav())

        np.testing.assert_allclose(
            actual_values, expected_values
        )