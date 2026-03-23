class PortfolioBaseException(Exception):
    """Base exception for all portfolio errors. Catch this to handle any portfolio error."""
    pass

class EmptyPriceException(PortfolioBaseException):
    """Raised when a price Series is empty or has no usable data."""
    def __init__(self, ticker: str):
        self.ticker = ticker
        msg = f"Price data is empty for ticker '{ticker}'." if ticker else "Price data is empty."
        super().__init__(msg)


class TickerException(PortfolioBaseException):
    """Raised when a ticker is not recognised or not tradeable."""
    def __init__(self, ticker: str):
        self.ticker = ticker
        super().__init__(f"Ticker '{ticker}' is not found in the traded market.")


class DateException(PortfolioBaseException):
    """Raised when a date range is invalid or out of bounds."""
    def __init__(self, message: str):
        super().__init__(message)


class TradingDayException(PortfolioBaseException):
    """Raised when an operation is attempted on a non-trading day."""
    def __init__(self, date=None):
        msg = f"'{date}' is not a valid trading day." if date else "Invalid trading day."
        super().__init__(msg)

class InsufficientDataException(PortfolioBaseException):
    """Raised when there is not enough data to perform a calculation (e.g. < 2 points)."""
    def __init__(self, required: int, got: int):
        super().__init__(f"Need at least {required} data points, got {got}.")


class InvalidPriceException(PortfolioBaseException):
    """Raised when a price value is mathematically invalid (e.g. zero or negative start price)."""
    def __init__(self, reason: str):
        super().__init__(f"Invalid price value: {reason}")