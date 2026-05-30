import pandas as pd
import numpy as np

from portfolio.exceptions import (
    EmptyPriceException,
    InvalidPriceException,
    InsufficientDataException,
)

class Features:

    @staticmethod
    def _validate(prices: pd.Series, required: int):
        if prices.empty:
            raise EmptyPriceException("")
        if len(prices) < required:
            raise InsufficientDataException(required=required, got=len(prices))
        if (prices <= 0).any():
            raise InvalidPriceException("prices must be positive")

    @staticmethod
    def get_moving_average(prices: pd.Series, window: int) -> pd.Series:
        Features._validate(prices, required=window)

        prices_list = prices.tolist()
        ma = [np.nan] * (window - 1)

        for i in range(window - 1, len(prices_list)):
            window_mean = sum(prices_list[i - window + 1 : i + 1]) / window
            ma.append(window_mean)

        result = pd.Series(ma, index=prices.index, name=f"MA_{window}")
        return result

    @staticmethod
    def get_exponential_moving_average(prices: pd.Series, span: int) -> pd.Series:
        Features._validate(prices, required=span)

        alpha = 2.0 / (span + 1)
        prices_list = prices.tolist()
        ema = [prices_list[0]]

        for i in range(1, len(prices_list)):
            new_ema = alpha * prices_list[i] + (1 - alpha) * ema[-1]
            ema.append(new_ema)

        result = pd.Series(ema, index=prices.index, name=f"EMA_{span}")
        return result

    @staticmethod
    def get_ma_convergence_divergence(
        prices: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> pd.DataFrame:
        Features._validate(prices, required=slow)

        ema_fast = Features.get_exponential_moving_average(prices, span=fast)
        ema_slow = Features.get_exponential_moving_average(prices, span=slow)

        macd_line = ema_fast - ema_slow

        # EMA of the MACD line for the signal
        alpha = 2.0 / (signal + 1)
        macd_list = macd_line.tolist()
        signal_list = [macd_list[0]]

        for i in range(1, len(macd_list)):
            new_signal = alpha * macd_list[i] + (1 - alpha) * signal_list[-1]
            signal_list.append(new_signal)

        signal_line = pd.Series(signal_list, index=prices.index, name="MACD_signal")
        histogram   = macd_line - signal_line

        return pd.DataFrame(
            {"MACD": macd_line, "MACD_signal": signal_line, "MACD_hist": histogram},
            index=prices.index,
        )

    @staticmethod
    def get_relative_strength_index(prices: pd.Series, window: int = 14) -> pd.Series:
        Features._validate(prices, required=window + 1)

        prices_list = prices.tolist()
        delta = [prices_list[i] - prices_list[i - 1] for i in range(1, len(prices_list))]

        gain = [max(d, 0) for d in delta]
        loss = [max(-d, 0) for d in delta]

        alpha = 1.0 / window  # Wilder's smoothing
        avg_gain = [gain[0]]
        avg_loss = [loss[0]]

        for i in range(1, len(gain)):
            avg_gain.append(alpha * gain[i] + (1 - alpha) * avg_gain[-1])
            avg_loss.append(alpha * loss[i] + (1 - alpha) * avg_loss[-1])

        rsi = []
        for g, l in zip(avg_gain, avg_loss):
            if l == 0:
                rsi.append(100.0)
            else:
                rs = g / l
                rsi.append(100.0 - (100.0 / (1.0 + rs)))

        padding = [np.nan] * (len(prices) - len(rsi))
        result = pd.Series(padding + rsi, index=prices.index, name=f"RSI_{window}")
        return result

