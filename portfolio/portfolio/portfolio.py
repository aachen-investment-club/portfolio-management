

from ..market.market import Market

from datetime import datetime, timedelta, date


class Portfolio(): 
    pass


Market.init()



date = date.today()+timedelta(days = -5)
print(Market.get_price("NVDA", date))