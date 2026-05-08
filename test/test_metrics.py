import unittest
from unittest.mock import patch
import math
from scipy.stats import norm
import pandas as pd
import numpy as np
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

    def test_sharpe_zero_std(self):
        assert math.isnan(Metrics.get_sharpe_ratio(make_returns([1,1,1])))

    def test_sharpe_empty(self):
        with self.assertRaises(EmptyPriceException):
            Metrics.get_sharpe_ratio(pd.Series())
    
    def test_sharpe_correctness(self):
      returns = make_returns([0.01, 0.02, 0.03])                                                                                                        
      expected = (0.02 / 0.01) * np.sqrt(1 / 252)
      assert math.isclose(Metrics.get_sharpe_ratio(returns), expected, rel_tol=1e-9)
    
    def test_beta_too_short(self):
        portfolio_returns = pd.Series([0.1])
        benchmark_returns = pd.Series([0.1])
        with self.assertRaises(InsufficientDataException):
            Metrics.get_beta(portfolio_returns,benchmark_returns)
    
    def test_beta_identical(self):
        portfolio_returns = pd.Series([0.1, 0.2, 0.0, 5, 0.3])
        benchmark_returns = pd.Series([0.1, 0.2, 0.0, 5, 0.3])
        assert Metrics.get_beta(portfolio_returns,benchmark_returns) == 1
    
    def test_beta_misaligned(self):
        portfolio_returns = make_returns([0.1, 0.2, 0.0, 5.0, 0.3])
        benchmark_returns = make_returns([0.9, 0.4, 0.7, 0.1, -0.3])
        benchmark_returns.index = pd.date_range("2023-01-03", periods=5)
        overlap_p = np.array([0.0, 5.0, 0.3])
        overlap_b = np.array([0.9, 0.4, 0.7])
        cov = np.cov(overlap_p, overlap_b)
        expected = cov[0, 1] / cov[1, 1]
        assert math.isclose(Metrics.get_beta(portfolio_returns, benchmark_returns), expected, rel_tol=1e-9)

    def test_beta_correctness(self):
        portfolio_returns = np.array([0.1, 0.2, 0.0, 5, 0.3])
        benchmark_returns = np.array([0.3, 0.7, 0.1, -0.3, 0.001])
        cov = np.cov(portfolio_returns, benchmark_returns)
        expected = cov[0, 1] / cov[1, 1]
        assert math.isclose(Metrics.get_beta(pd.Series(portfolio_returns), pd.Series(benchmark_returns)), expected, rel_tol=1e-9)

    def test_alpha_too_short(self):
        with self.assertRaises(InsufficientDataException):
            Metrics.get_alpha(pd.Series([0.1]), pd.Series([0.1]))

    def test_alpha_identical(self):
        returns = pd.Series([0.1, 0.2, 0.0, 0.5, 0.3])
        assert math.isclose(Metrics.get_alpha(returns, returns), 0.0, abs_tol=1e-9)

    def test_alpha_correctness(self):
        portfolio_returns = pd.Series([0.1, 0.2, 0.0, 0.5, 0.3])
        benchmark_returns = pd.Series([0.3, 0.7, 0.1, -0.3, 0.001])
        beta = Metrics.get_beta(portfolio_returns, benchmark_returns)
        expected = portfolio_returns.mean() * 252 - (beta * benchmark_returns.mean() * 252)
        assert math.isclose(Metrics.get_alpha(portfolio_returns, benchmark_returns), expected, rel_tol=1e-9)

    def test_alpha_risk_free_rate(self):
        portfolio_returns = pd.Series([0.1, 0.2, 0.0, 0.5, 0.3])
        benchmark_returns = pd.Series([0.3, 0.7, 0.1, -0.3, 0.001])
        rf = 0.04
        beta = Metrics.get_beta(portfolio_returns, benchmark_returns)
        expected = portfolio_returns.mean() * 252 - (rf + beta * (benchmark_returns.mean() * 252 - rf))
        assert math.isclose(Metrics.get_alpha(portfolio_returns, benchmark_returns, risk_free_rate=rf), expected, rel_tol=1e-9)

    def test_var_empty(self):
        with self.assertRaises(EmptyPriceException):
            Metrics.get_value_at_risk(pd.Series([], dtype=float))

    def test_var_correctness(self):
        portfolio_returns = pd.Series([0.01, -0.02, 0.03, -0.01, 0.02])
        mu = portfolio_returns.mean()
        sigma = portfolio_returns.std(ddof=1)
        mu_h = mu * 10
        sigma_h = sigma * np.sqrt(10)
        expected = max(-(mu_h + norm.ppf(0.05) * sigma_h) * 100.0, 0.0)
        assert math.isclose(Metrics.get_value_at_risk(portfolio_returns), expected, rel_tol=1e-9)

    def test_var_portfolio_value_scales(self):
        portfolio_returns = pd.Series([0.01, -0.02, 0.03, -0.01, 0.02])
        var_100 = Metrics.get_value_at_risk(portfolio_returns, portfolio_value=100.0)
        var_200 = Metrics.get_value_at_risk(portfolio_returns, portfolio_value=200.0)
        assert math.isclose(var_200, var_100 * 2, rel_tol=1e-9)

    def test_var_dataframe_input(self):
        
        asset_returns = pd.DataFrame({"A": [0.01, -0.02, 0.03], "B": [-0.01, 0.02, -0.03]})
        weights = np.array([0.5, 0.5])
        portfolio_returns = asset_returns.dot(weights)
        mu_h = portfolio_returns.mean() * 10
        sigma_h = portfolio_returns.std(ddof=1) * np.sqrt(10)
        expected = max(-(mu_h + norm.ppf(0.05) * sigma_h) * 100.0, 0.0)
        assert math.isclose(Metrics.get_value_at_risk(asset_returns, portfolio_weights=weights), expected, rel_tol=1e-9)

    def test_var_missing_weights_raises(self):
        asset_returns = pd.DataFrame({"A": [0.01, -0.02], "B": [-0.01, 0.02]})
        with self.assertRaises(ValueError):
            Metrics.get_value_at_risk(asset_returns)


