from datetime import datetime
from portfolio.exceptions import StartDateAfterEndDateException, DateException, InvalidDateFormat

def validate_date(start_date: str, end_date: str):
    now = datetime.now()

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
        raise InvalidDateFormat(start_date)

    try:
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise InvalidDateFormat(end_date)
    
    if start > end:
        raise StartDateAfterEndDateException(start_date=start_date, end_date=end_date)
    
    if start > now:
        raise DateException(f"Start date is invalid {start_date}")
    
    if end > now:
        raise DateException(f"End date is invalid {end_date}")