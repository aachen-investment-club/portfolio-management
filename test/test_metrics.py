import unittest
from unittest.mock import patch

import pandas as pd

from portfolio.models.metrics import Metrics
from portfolio.exceptions import EmptyPriceException, InsufficientDataException, InvalidPriceException

def make_prices(values, freq='D'):
    index = pd.date_range('2023-01-01', periods=len(values), freq=freq)
    return pd.Series(values, index=index)

def make_returns(values,freq='D'):
    index = pd.date_range("2023-01-01", periods=len(values), freq=freq)
    return pd.Series(values, index=index)


class TestMetrics(unittest.TestCase):
    """
        Unit tests for Metrics model.

        Required:
            APCA_API_KEY_ID, APCA_API_SECRET_KEY required for tests to run correctly

        To run:
            python -m unittest discover -s test 
    """

    def test_roi_empty_price(self):
        invalid_prices = pd.Series([], dtype=float)
        with self.assertRaises(EmptyPriceException):
            Metrics.get_ROI(invalid_prices)
    
    def test_roi_insufficient_prices(self):
        insufficient_prices = make_prices([100])
        with self.assertRaises(InsufficientDataException):
            Metrics.get_ROI(insufficient_prices)
    
    def test_roi(self):
        prices = pd.Series([100.0, 50.0, 200.0])
        assert Metrics.get_ROI(prices) == 100.0

    def test_cagr_empty_price(self):
        invalid_prices = pd.Series([], dtype=float)
        with self.assertRaises(EmptyPriceException):
            Metrics.get_CAGR(invalid_prices)

    def test_cagr_insufficient_prices(self):
        insufficient_prices = make_prices([100])
        with self.assertRaises(InsufficientDataException):
            Metrics.get_CAGR(insufficient_prices)

    def test_annual_volatility_empty_returns(self):
        empty_returns = make_returns([])
        with self.assertRaises(EmptyPriceException):
            Metrics.get_annual_volatility(empty_returns)

    def test_annual_volatility(self):
        returns = make_returns([100, 0, -100])
        assert Metrics.get_annual_volatility(returns, 144) == returns.std() * 12

    def test_get_ROI_empty_prices(self):
        empty_prices = make_prices([])
        with self.assertRaises(EmptyPriceException):
            Metrics.get_ROI(empty_prices)

    def test_get_ROI_insufficient_prices(self):
        insufficient_prices = make_prices([100])
        with self.assertRaises(InsufficientDataException):
            Metrics.get_ROI(insufficient_prices)
    
    def test_get_ROI_invalid_price(self):
        prices = make_prices([-1, 10])
        with self.assertRaises(InvalidPriceException):
            Metrics.get_ROI(prices)

    def test_get_ROI(self):
        prices = make_prices([10, 20])
        assert Metrics.get_ROI(prices) == (20 - 10) / 10 * 100

    def test_get_basic_metrics_value(self):
        assets = pd.DataFrame({"shares": [5, 10], "ticker": ["AAPL", "GOOG"]})
        mock_prices = pd.DataFrame({"price close": [100, 200], "ticker": ["AAPL", "GOOG"]})

        with patch('portfolio.models.market.Market.get_latest_prices', return_value=mock_prices):
            result = Metrics.get_basic_metrics(assets)

            assert result.loc[result["ticker"] == "AAPL", "asset_value"].iloc[0] == 500
            assert result.loc[result["ticker"] == "GOOG", "asset_value"].iloc[0] == 2000