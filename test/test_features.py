import unittest
import math
import pandas as pd
import numpy as np

from dotenv import load_dotenv
load_dotenv()

from portfolio.models.features import Features
from portfolio.exceptions import EmptyPriceException, InsufficientDataException, InvalidPriceException


def make_prices(values, freq='D'):
    index = pd.date_range('2025-01-01', periods=len(values), freq=freq)
    return pd.Series(values, index=index, dtype=float)


class TestFeatures(unittest.TestCase):

    def test_ma_empty_prices(self):
        with self.assertRaises(EmptyPriceException):
            Features.get_moving_average(make_prices([]), window=3)

    def test_ma_insufficient_data(self):
        with self.assertRaises(InsufficientDataException):
            Features.get_moving_average(make_prices([100, 200]), window=3)

    def test_ma_invalid_price(self):
        with self.assertRaises(InvalidPriceException):
            Features.get_moving_average(make_prices([-100, 200, 300]), window=3)

    def test_ma_zero_price(self):
        with self.assertRaises(InvalidPriceException):
            Features.get_moving_average(make_prices([0, 200, 300]), window=3)

    def test_ma_output_length(self):
        prices = make_prices([100, 110, 105, 120, 115])
        result = Features.get_moving_average(prices, window=3)
        assert len(result) == len(prices)

    def test_ma_leading_nans(self):
        prices = make_prices([100, 110, 105, 120, 115])
        result = Features.get_moving_average(prices, window=3)
        assert math.isnan(result.iloc[0])
        assert math.isnan(result.iloc[1])

    def test_ma_first_valid_value(self):
        prices = make_prices([100, 110, 105, 120, 115])
        result = Features.get_moving_average(prices, window=3)
        assert math.isclose(result.iloc[2], (100 + 110 + 105) / 3, rel_tol=1e-9)

    def test_ma_correctness(self):
        prices = make_prices([100, 110, 105, 120, 115])
        result = Features.get_moving_average(prices, window=3)
        assert math.isclose(result.iloc[2], 105.0,   rel_tol=1e-9)
        assert math.isclose(result.iloc[3], 111.666, abs_tol=1e-3)
        assert math.isclose(result.iloc[4], 113.333, abs_tol=1e-3)

    def test_ma_window_equals_length(self):
        prices = make_prices([100, 200, 300])
        result = Features.get_moving_average(prices, window=3)
        assert math.isclose(result.iloc[2], 200.0, rel_tol=1e-9)

    def test_ma_constant_prices(self):
        prices = make_prices([100, 100, 100, 100, 100])
        result = Features.get_moving_average(prices, window=3)
        assert all(math.isclose(v, 100.0, rel_tol=1e-9) for v in result.dropna())

    def test_ma_series_name(self):
        prices = make_prices([100, 110, 105, 120, 115])
        result = Features.get_moving_average(prices, window=3)
        assert result.name == "MA_3"

    def test_ma_index_preserved(self):
        prices = make_prices([100, 110, 105, 120, 115])
        result = Features.get_moving_average(prices, window=3)
        assert list(result.index) == list(prices.index)

    def test_ema_empty_prices(self):
        with self.assertRaises(EmptyPriceException):
            Features.get_exponential_moving_average(make_prices([]), span=3)

    def test_ema_insufficient_data(self):
        with self.assertRaises(InsufficientDataException):
            Features.get_exponential_moving_average(make_prices([100, 200]), span=3)

    def test_ema_invalid_price(self):
        with self.assertRaises(InvalidPriceException):
            Features.get_exponential_moving_average(make_prices([-100, 200, 300]), span=3)

    def test_ema_zero_price(self):
        with self.assertRaises(InvalidPriceException):
            Features.get_exponential_moving_average(make_prices([0, 200, 300]), span=3)

    def test_ema_output_length(self):
        prices = make_prices([100, 110, 105, 120, 115])
        result = Features.get_exponential_moving_average(prices, span=3)
        assert len(result) == len(prices)

    def test_ema_first_value_equals_first_price(self):
        prices = make_prices([100, 110, 105, 120, 115])
        result = Features.get_exponential_moving_average(prices, span=3)
        assert math.isclose(result.iloc[0], 100.0, rel_tol=1e-9)

    def test_ema_correctness(self):
        # alpha = 2 / (3+1) = 0.5
        prices = make_prices([100, 110, 105])
        result = Features.get_exponential_moving_average(prices, span=3)
        expected_day2 = 0.5 * 110 + 0.5 * 100   
        expected_day3 = 0.5 * 105 + 0.5 * 105.0  
        assert math.isclose(result.iloc[1], expected_day2, rel_tol=1e-9)
        assert math.isclose(result.iloc[2], expected_day3, rel_tol=1e-9)

    def test_ema_reacts_faster_than_ma(self):
        # after a big price jump EMA should be closer to new price than MA
        prices = make_prices([100] * 30 + [200] * 3)        
        ma  = Features.get_moving_average(prices, window=10)
        ema = Features.get_exponential_moving_average(prices, span=10)
        assert abs(ema.iloc[-1] - 200) < abs(ma.iloc[-1] - 200)

    def test_ema_constant_prices(self):
        prices = make_prices([100, 100, 100, 100, 100])
        result = Features.get_exponential_moving_average(prices, span=3)
        assert all(math.isclose(v, 100.0, rel_tol=1e-9) for v in result)

    def test_ema_series_name(self):
        prices = make_prices([100, 110, 105, 120, 115])
        result = Features.get_exponential_moving_average(prices, span=3)
        assert result.name == "EMA_3"

    def test_ema_index_preserved(self):
        prices = make_prices([100, 110, 105, 120, 115])
        result = Features.get_exponential_moving_average(prices, span=3)
        assert list(result.index) == list(prices.index)

    # ─── MACD ─────────────────────────────────────────────────────────────────

    def test_macd_empty_prices(self):
        with self.assertRaises(EmptyPriceException):
            Features.get_ma_convergence_divergence(make_prices([]))

    def test_macd_insufficient_data(self):
        with self.assertRaises(InsufficientDataException):
            Features.get_ma_convergence_divergence(make_prices([100, 110]), slow=26)

    def test_macd_invalid_price(self):
        prices = make_prices([-100] + [200] * 26)
        with self.assertRaises(InvalidPriceException):
            Features.get_ma_convergence_divergence(prices)

    def test_macd_output_columns(self):
        prices = make_prices([100] * 30)
        result = Features.get_ma_convergence_divergence(prices)
        assert set(result.columns) == {"MACD", "MACD_signal", "MACD_hist"}

    def test_macd_output_length(self):
        prices = make_prices([100] * 30)
        result = Features.get_ma_convergence_divergence(prices)
        assert len(result) == len(prices)

    def test_macd_histogram_is_macd_minus_signal(self):
        prices = make_prices([100 + i for i in range(30)])
        result = Features.get_ma_convergence_divergence(prices)
        expected_hist = result["MACD"] - result["MACD_signal"]
        assert all(math.isclose(a, b, rel_tol=1e-9)
                   for a, b in zip(result["MACD_hist"], expected_hist))

    def test_macd_constant_prices_all_zero(self):
        prices = make_prices([100] * 30)
        result = Features.get_ma_convergence_divergence(prices)
        assert all(math.isclose(v, 0.0, abs_tol=1e-9) for v in result["MACD"])
        assert all(math.isclose(v, 0.0, abs_tol=1e-9) for v in result["MACD_hist"])

    def test_macd_index_preserved(self):
        prices = make_prices([100] * 30)
        result = Features.get_ma_convergence_divergence(prices)
        assert list(result.index) == list(prices.index)

    def test_macd_fast_above_slow_gives_positive_macd(self):
        # steadily rising prices → fast EMA > slow EMA → MACD > 0
        prices = make_prices([100 + i * 2 for i in range(30)])
        result = Features.get_ma_convergence_divergence(prices)
        assert result["MACD"].iloc[-1] > 0

    def test_macd_fast_below_slow_gives_negative_macd(self):
        # steadily falling prices → fast EMA < slow EMA → MACD < 0
        prices = make_prices([300 - i * 2 for i in range(30)])
        result = Features.get_ma_convergence_divergence(prices)
        assert result["MACD"].iloc[-1] < 0

    # ─── RSI ──────────────────────────────────────────────────────────────────

    def test_rsi_empty_prices(self):
        with self.assertRaises(EmptyPriceException):
            Features.get_relative_strength_index(make_prices([]))

    def test_rsi_insufficient_data(self):
        with self.assertRaises(InsufficientDataException):
            Features.get_relative_strength_index(make_prices([100] * 5), window=14)

    def test_rsi_invalid_price(self):
        prices = make_prices([-100] + [200] * 15)
        with self.assertRaises(InvalidPriceException):
            Features.get_relative_strength_index(prices)

    def test_rsi_output_length(self):
        prices = make_prices([100 + i for i in range(20)])
        result = Features.get_relative_strength_index(prices, window=3)
        assert len(result) == len(prices)

    def test_rsi_leading_nans(self):
        prices = make_prices([100 + i for i in range(10)])
        result = Features.get_relative_strength_index(prices, window=3)
        assert math.isnan(result.iloc[0])

    def test_rsi_range_between_0_and_100(self):
        prices = make_prices([100 + i for i in range(20)])
        result = Features.get_relative_strength_index(prices, window=3)
        valid = result.dropna()
        assert all(0.0 <= v <= 100.0 for v in valid)

    def test_rsi_pure_uptrend_gives_100(self):
        # all gains, no losses → avg_loss = 0 → RSI = 100
        prices = make_prices([100, 110, 120, 130, 140, 150])
        result = Features.get_relative_strength_index(prices, window=3)
        assert all(math.isclose(v, 100.0, rel_tol=1e-9) for v in result.dropna())

    def test_rsi_pure_downtrend_gives_zero(self):
        # all losses, no gains → avg_gain = 0 → RSI → 0
        prices = make_prices([150, 140, 130, 120, 110, 100])
        result = Features.get_relative_strength_index(prices, window=3)
        assert all(v < 1.0 for v in result.dropna())

    def test_rsi_series_name(self):
        prices = make_prices([100 + i for i in range(20)])
        result = Features.get_relative_strength_index(prices, window=14)
        assert result.name == "RSI_14"

    def test_rsi_index_preserved(self):
        prices = make_prices([100 + i for i in range(20)])
        result = Features.get_relative_strength_index(prices, window=3)
        assert list(result.index) == list(prices.index)

    def test_rsi_correctness(self):
        # manual calculation with window=3, alpha=1/3
        prices = make_prices([100, 102, 101, 105, 103])
        result = Features.get_relative_strength_index(prices, window=3)

        delta = [2, -1, 4, -2]
        gain  = [2,  0, 4,  0]
        loss  = [0,  1, 0,  2]

        alpha = 1 / 3
        avg_g = [gain[0]]
        avg_l = [loss[0]]
        for i in range(1, len(gain)):
            avg_g.append(alpha * gain[i] + (1 - alpha) * avg_g[-1])
            avg_l.append(alpha * loss[i] + (1 - alpha) * avg_l[-1])

        expected_rsi = []
        for g, l in zip(avg_g, avg_l):
            if l == 0:
                expected_rsi.append(100.0)
            else:
                expected_rsi.append(100.0 - 100.0 / (1.0 + g / l))

        valid = result.dropna().tolist()
        for actual, expected in zip(valid, expected_rsi):
            assert math.isclose(actual, expected, rel_tol=1e-9)


