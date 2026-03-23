import unittest

import pandas as pd

from portfolio.models.metrics import Metrics
from portfolio.exceptions import EmptyPriceException, InsufficientDataException

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
    
