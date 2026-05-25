import os
import unittest
from datetime import datetime
from unittest.mock import patch

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import portfolio.models.market as market_module
import portfolio.utils.aws_config as aws_config
from portfolio.models.market import Market, FOREXDB
from portfolio.schemas.market import Base
from dotenv import load_dotenv
load_dotenv()


class TestForex(unittest.TestCase):
  """
  Unit tests for Forex model behavior.

  To run:
      python -m unittest discover -s test
  """

  def setUp(self):
      self.engine = create_engine(
          "sqlite://",
          connect_args={"check_same_thread": False},
          poolclass=StaticPool,
      )
      self.engine_patcher_market = patch.object(market_module, "engine", self.engine)
      self.engine_patcher_config = patch.object(aws_config, "engine", self.engine)
      self.engine_patcher_market.start()
      self.engine_patcher_config.start()
      Base.metadata.create_all(self.engine)

  def tearDown(self):
      Base.metadata.drop_all(self.engine)
      self.engine_patcher_market.stop()
      self.engine_patcher_config.stop()
      self.engine.dispose()

  def _insert_forex_rows(self, rows):
      with Session(self.engine) as session:
          session.add_all([FOREXDB(**row) for row in rows])
          session.commit()

  def test_check_forex_empty_true(self):
      self.assertTrue(Market.check_forex_empty())

  def test_check_forex_empty_false(self):
      self._insert_forex_rows([
          {
              "ticker": "EURUSD=X",
              "date": datetime(2025, 1, 1),
              "price_close": 1.1,
          }
      ])

      self.assertFalse(Market.check_forex_empty())

  def test_get_latest_forex_date_in_db(self):
      self._insert_forex_rows([
          {
              "ticker": "EURUSD=X",
              "date": datetime(2025, 1, 1, 9, 30),
              "price_close": 1.1,
          },
          {
              "ticker": "GBPUSD=X",
              "date": datetime(2025, 1, 2, 10, 0),
              "price_close": 1.3,
          },
      ])

      result = Market.get_latest_forex_date_in_db()

      self.assertEqual(result, datetime(2025, 1, 2).date())

  def test_get_forex_history_empty_input(self):
      result = Market.get_forex_history([])

      self.assertTrue(result.empty)
      self.assertListEqual(list(result.columns), ["ticker", "date", "price_close"])

  def test_get_forex_history_returns_expected_rows(self):
      self._insert_forex_rows([
          {
              "ticker": "EURUSD=X",
              "date": datetime(2025, 1, 1),
              "price_close": 1.1,
          },
          {
              "ticker": "EURUSD=X",
              "date": datetime(2025, 1, 2),
              "price_close": 1.2,
          },
          {
              "ticker": "GBPUSD=X",
              "date": datetime(2025, 1, 2),
              "price_close": 1.3,
          },
      ])

      result = Market.get_forex_history(
          ["EURUSD=X"],
          start=datetime(2025, 1, 1),
          end=datetime(2025, 1, 2),
      )

      self.assertEqual(list(result["ticker"]), ["EURUSD=X", "EURUSD=X"])
      self.assertEqual(len(result), 2)

  def test_get_forex_history_filters_dates(self):
      self._insert_forex_rows([
          {
              "ticker": "EURUSD=X",
              "date": datetime(2025, 1, 1),
              "price_close": 1.1,
          },
          {
              "ticker": "EURUSD=X",
              "date": datetime(2025, 1, 3),
              "price_close": 1.2,
          },
      ])

      result = Market.get_forex_history(
          ["EURUSD=X"],
          start=datetime(2025, 1, 2),
          end=datetime(2025, 1, 2),
      )

      self.assertTrue(result.empty)

  def test_build_fx_rate_map_uses_direct_pair(self):
      fx_history = pd.DataFrame(
          {
              "ticker": ["EURUSD=X", "EURUSD=X"],
              "date": pd.to_datetime(["2025-01-01", "2025-01-02"]),
              "price_close": [1.1, 1.2],
          }
      )
      dates = pd.to_datetime(["2025-01-01", "2025-01-02"])

      with patch.object(Market, "get_forex_history", return_value=fx_history):
          result = Market.build_fx_rate_map(["EUR", "USD"], dates)

      self.assertListEqual(list(result.columns), ["EUR", "USD"])
      self.assertEqual(result["USD"].tolist(), [1.0, 1.0])
      self.assertEqual(result["EUR"].tolist(), [1.1, 1.2])

  def test_build_fx_rate_map_uses_inverse_pair(self):
      fx_history = pd.DataFrame(
          {
              "ticker": ["USDJPY=X", "USDJPY=X"],
              "date": pd.to_datetime(["2025-01-01", "2025-01-02"]),
              "price_close": [150.0, 200.0],
          }
      )
      dates = pd.to_datetime(["2025-01-01", "2025-01-02"])

      with patch.object(Market, "get_forex_history", return_value=fx_history):
          result = Market.build_fx_rate_map(["JPY"], dates)

      self.assertAlmostEqual(result["JPY"].iloc[0], 1.0 / 150.0, places=8)
      self.assertAlmostEqual(result["JPY"].iloc[1], 1.0 / 200.0, places=8)

  def test_build_fx_rate_map_ffill_missing_dates(self):
      fx_history = pd.DataFrame(
          {
              "ticker": ["EURUSD=X"],
              "date": pd.to_datetime(["2025-01-01"]),
              "price_close": [1.25],
          }
      )
      dates = pd.to_datetime(["2025-01-01", "2025-01-02"])

      with patch.object(Market, "get_forex_history", return_value=fx_history):
          result = Market.build_fx_rate_map(["EUR"], dates)

      self.assertEqual(result["EUR"].tolist(), [1.25, 1.25])

  def test_build_fx_rate_map_defaults_to_usd_when_missing_history(self):
      dates = pd.to_datetime(["2025-01-01", "2025-01-02"])
      empty_history = pd.DataFrame(columns=["ticker", "date", "price_close"])

      with patch.object(Market, "get_forex_history", return_value=empty_history):
          with self.assertWarns(UserWarning):
              result = Market.build_fx_rate_map(["JPY"], dates)

      self.assertTrue((result["JPY"] == 1.0).all())
