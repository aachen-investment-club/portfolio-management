import unittest
import datetime
import os

import pandas as pd
from datetime import date as dte

from portfolio.models.market import Market
from portfolio.exceptions import TickerException, TradingDayException, DateException

from dotenv import load_dotenv
load_dotenv()




class TestMarket(unittest.TestCase): 
  """
  Unit tests for Market model.

  Required:
      APCA_API_KEY_ID, APCA_API_SECRET_KEY required for tests to run correctly

  To run:
      python -m unittest discover -s test 
  """
  def setUp(self):
      # Load dummy data to prevent Docker from requiring the real database
      Market.load_ticker_metadata("test/data/mini_meta.csv")
      Market.load_from_csv("test/data/mini_sp500.csv")

  def tearDown(self):
      # Remove the temporary database to keep the container clean
    try:
      if os.path.exists("market.db"):
        os.remove("market.db")
    except PermissionError:
      # Prevent local tests from failing due to Windows file-locking
      # Docker (Linux) will delete it perfectly
      pass

  def test_get_price_valid(self):
    valid_ticker = "AAPL"
    valid_date = datetime.date(2025, 11, 25)

    result = Market.get_price(valid_ticker, valid_date)
    
    self.assertIsInstance(result, float)

  def test_get_price_invalid_ticker(self): 
     
    invalid_ticker = "AIC_Coin"
    valid_date = datetime.date(2025, 11, 25)

    with self.assertRaises(TickerException):
      Market.get_price(invalid_ticker, valid_date)
  

  def test_get_price_invalid_trading_day(self):

    valid_ticker = "AAPL"
    invalid_trading_day_date = datetime.date(2025, 11, 23)
    
    with self.assertRaises(TradingDayException):
      Market.get_price(valid_ticker, invalid_trading_day_date)
  
  def test_get_price_invalid_date(self):

    valid_ticker = "AAPL"
    invalid_date = datetime.date(1999, 11, 22)
    
    with self.assertRaises(DateException):
      Market.get_price(valid_ticker, invalid_date)

  def test_get_us_treasury_bonds(self): 
    """checks if the nr of bond entries matches the monthly records since 2001. """
    bonds = Market.get_us_treasury_bonds()
    entries = len(bonds)
    today = dte.today()

    expected_entries = 12*(today.year-2001) + today.month
    self.assertTrue(abs(expected_entries- entries)<= expected_entries+2)

