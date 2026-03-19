import unittest
import datetime

import pandas as pd
from datetime import date as dte

from portfolio.models.market import Market
from portfolio.exceptions import TickerException, TradingDayException

from dotenv import load_dotenv
load_dotenv()




class TestMarket(unittest.TestCase): 
  """
  Unit tests for Market model.

  To run:
      python -m unittest discover -s test 
  """

  def test_get_price_valid(self):
    valid_ticker = "AAPL"
    valid_date = datetime.date(2025, 11, 25)

    result = Market.get_price(valid_ticker, valid_date)
    
    self.assertIsInstance(result, float)

  # def test_get_price_invalid_ticker(self): 
     
  #   invalid_ticker = "AIC_Coin"
  #   valid_date = datetime.date(2025, 11, 25)

  #   with self.assertRaises(TickerException):
  #     Market.get_price(invalid_ticker, valid_date)
  
  # @patch("portfolio.models.market.Market.get_traded_assets", return_value=["AAPL"])
  # def test_get_price_invalid_trading_day(self):

  #   valid_ticker = "AAPL"
  #   invalid_trading_day_date = datetime.date(2025, 11, 23)
    
  #   with self.assertRaises(TradingDayException):
  #     Market.get_price(valid_ticker, invalid_trading_day_date)


  def test_get_us_treasury_bonds(self): 
    """checks if the nr of bond entries matches the monthly records since 2001. """
    bonds = Market.get_us_treasury_bonds()
    entries = len(bonds)
    today = dte.today()

    expected_entries = 12*(today.year-2001) + today.month
    self.assertTrue(expected_entries== entries or expected_entries== entries +1)


