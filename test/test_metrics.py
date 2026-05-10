import unittest

import math
import pandas as pd
import numpy as np

from dotenv import load_dotenv
load_dotenv()

from portfolio.models.metrics import Metrics
from portfolio.exceptions import EmptyPriceException, InsufficientDataException ,InvalidPriceException

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

    def test_cagr_negative_price(self):
        dates=pd.to_datetime(['2025-01-01','2025-03-01','2025-09-01'])
        prices=pd.Series([0,150,200],index=dates)
        with self.assertRaises(InvalidPriceException):
            Metrics.get_CAGR(prices)

    def test_cagr_same_day(self):
        dates=pd.to_datetime(['2025-01-01','2025-01-01'])
        prices=pd.Series([150,200],index=dates)
        result = Metrics.get_CAGR(prices)
        assert math.isnan(result)
        
    def test_cagr(self):
        dates=pd.to_datetime(['2025-01-01','2025-03-01','2025-09-01'])
        prices=pd.Series([100,150,200],index=dates)
        result = Metrics.get_CAGR(prices)
        assert math.isclose(result, 105.20, abs_tol=1e-2)

    def test_cagr_loss(self):
        dates=pd.to_datetime(['2025-01-01','2025-03-01','2025-09-01'])
        prices=pd.Series([200,150,100],index=dates)
        result = Metrics.get_CAGR(prices)
        assert math.isclose(result, -51.27, abs_tol=1e-2)

    def test_volatility_empty_series(self):
        invalid_prices = pd.Series([ ], dtype=float)
        with self.assertRaises(EmptyPriceException):
            Metrics.get_annual_volatility(invalid_prices)

    def test_volatility_same_series(self):
        returns=pd.Series([100.00,100.00,100.00])
        assert Metrics.get_annual_volatility(returns)==0.0

    def test_volatality(self):
        periods_per_year=252
        returns=pd.Series([100.00,125.00,150.00])
        result = Metrics.get_annual_volatility(returns)
        assert math.isclose(result, 396.86, abs_tol=1e-2)

    def test_maximum_markdown_empty_prices(self):
        prices = pd.Series([], dtype=float)
        with self.assertRaises(EmptyPriceException):
            Metrics.get_maximum_drawdown(prices)

    def test_maximum_markdown_only_peaks(self):
        dates=pd.to_datetime(['2025-01-01','2025-03-01','2025-09-01'])
        prices=pd.Series([200,250,300],index=dates)
        assert Metrics.get_maximum_drawdown(prices)==0.0

    def test_maximum_markdown(self):
        dates=pd.to_datetime(['2025-01-01','2025-03-01','2025-09-01','2025-12-01'])
        prices=pd.Series([200,250,100,300],index=dates)
        assert Metrics.get_maximum_drawdown(prices)==-60.00