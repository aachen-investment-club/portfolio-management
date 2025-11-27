import unittest

from dotenv import load_dotenv

load_dotenv()#: it is important to call this before the market!!

from portfolio.models.market import Market, DateException, TickerException, TradingDayException
from portfolio.models.portfolio import Portfolio
import os
import pandas as pd
import datetime
from datetime import date as dte





class TestMarket(unittest.TestCase): 
  """
  python -m unittest discover -s tes 
  """

  def setUp(self):
    """this runs before each test!"""
    Market.init("./data/sp500_close_current.csv")



  def test_init(self):
    """Test whether the update function updates upto the last trading day"""
    if not os.path.isfile("./data/test_quotes.csv"): 
        Market.init("./data/sp500_close_current.csv")
        date = datetime.date(2022,4,10)
        subquotes = Market.quotes[Market.quotes.index.get_level_values("Date")<=pd.Timestamp(date)]
        subquotes.to_csv("./data/test_quotes.csv")

    Market.init("./data/test_quotes.csv")
    quotes = Market.quotes
    max_date = quotes.index.get_level_values("Date").max()
    truth_date = pd.Timestamp(Market.get_latest_trading_day())
    self.assertEqual(max_date, truth_date)

    Market.is_trading_day(max_date)


  def test_get_price(self): 
     
    wrong_trading_day = datetime.date(2025, 11, 23) #: sunday
    date= datetime.date(2025, 11, 25) 



    wrong_ticker  = "AIC_COIN"
    ticker = "AAPL"


    with self.assertRaises(TickerException): 
      Market.get_price(wrong_ticker, date)

    with self.assertRaises(TradingDayException): 
      Market.get_price(ticker, wrong_trading_day)

  def test_get_us_treasury_bonds(self): 
    """checks if the nr of bond entries matches the monthly records since 2001. """
    bonds = Market.get_us_treasury_bonds()
    entries = len(bonds)
    today = dte.today()

    expected_entries = 12*(today.year-2001) + today.month
    self.assertTrue(expected_entries== entries or expected_entries== entries +1)


