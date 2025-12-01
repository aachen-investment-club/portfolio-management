"""
This file is intended to be used for local development of the market and portfolio classes
"""

from dotenv import load_dotenv

load_dotenv()#: it is important to call this before the market!!



from market import Market, TICKER, PRICE
from portfolio import Portfolio
from metrics import Metrics
import os
import pandas as pd
import datetime
from datetime import date as dte




def generate_sublog (): 
    Market.init("./data/sp500_close_current.csv")
    pf = Portfolio(10000, 100)
    pf.import_from_json("./data/trades.json")
    date = datetime.date(2022,4,10)
    subquotes = Market.quotes[Market.quotes.index.get_level_values("Date")<=pd.Timestamp(date)]
    print("max:")
    print(subquotes.index.get_level_values("Date").max())
    subquotes.to_csv("./data/test_quotes.csv")

def test_import(): 
    Market.init("./data/test_quotes.csv")
    print("max date:")
    print(Market.quotes.index.get_level_values("Date").max())


def test1(): 
    Market.init("./data/sp500_close_current.csv")

    pf = Portfolio(100, 100)
    pf.import_from_json("./data/trades.json")

    print(pf.current_position)


    pf.buy("UPS", 10, "USD")
    print(pf.current_position)
    pf.buy("UPS", 15, "USD")

    print(pf.current_position)
    pf.sell("UPS", 2, "USD")
    print(pf.current_position)

    pf.sell("NVDA", 100000, "USD")
    print(pf.current_position)
    print(pf.get_current_leverage())

    print(Market.quotes.index.get_level_values(TICKER))
    #print(Metrics.get_daily_log_returns())




def test2():
    Market.init("./data/sp500_close_current.csv")
    data = Market.quotes.loc["NVDA"][PRICE]

    print(Metrics.get_daily_returns(data))
    print(Metrics.get_daily_log_returns(data))

test2()

#generate_sublog()
#test_import()
