class PortfolioBaseException(Exception):
    """Base exception for all portfolio errors. Catch this to handle any portfolio error."""
    pass

class EmptyPriceException(PortfolioBaseException):
    """Raised when a price Series is empty or has no usable data."""
    flash_message = "EmptyPriceException"
    def __init__(self, ticker: str):
        self.ticker = ticker
        msg = f"Price data is empty for ticker '{ticker}'." if ticker else "Price data is empty."
        super().__init__(msg)


class TickerException(PortfolioBaseException):
    """Raised when a ticker is not recognised or not tradeable."""
    flash_message = "TickerException"
    def __init__(self, ticker: str):
        self.ticker = ticker
        super().__init__(f"Ticker '{ticker}' is not found in the traded market.")


class DateException(PortfolioBaseException):
    """Raised when a date range is invalid or out of bounds."""
    flash_message = "No data available for the selected date range."
    def __init__(self, message: str):
        super().__init__(message)


class TradingDayException(PortfolioBaseException):
    """Raised when an operation is attempted on a non-trading day."""
    flash_message = "TradingDayException"
    def __init__(self, date=None):
        msg = f"'{date}' is not a valid trading day." if date else "Invalid trading day."
        super().__init__(msg)

class InsufficientDataException(PortfolioBaseException):
    """Raised when there is not enough data to perform a calculation (e.g. < 2 points)."""
    flash_message = "InsufficientDataException"
    def __init__(self, required: int, got: int):
        super().__init__(f"Need at least {required} data points, got {got}.")


class InvalidPriceException(PortfolioBaseException):
    """Raised when a price value is mathematically invalid (e.g. zero or negative start price)."""
    flash_message = "InvalidPriceException"
    def __init__(self, reason: str):
        super().__init__(f"Invalid price value: {reason}")

class StartDateAfterEndDateException(PortfolioBaseException):
    """Raised when end date is sooner than start date (e.g. start date is 2000.10.1 and end date is 1999.10.1)"""

    flash_message = "Start date must be before end date. Showing default date range."
    def __init__(self, start_date, end_date):
        super().__init__(f"Invalid date range : start date is {start_date} and end date is {end_date}")

class InvalidDateFormat(PortfolioBaseException):
    """Raised when the date format is invalid."""
    
    flash_message = "Date format is invalid. Please enter a valid date."
    def __init__(self, date):
        super().__init__(f"Invalid date format: {date}")