import os
import unittest
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from portfolio.models.refinitiv_wrapper import Refinitiv


@unittest.skipUnless(
    all(os.getenv(k) for k in ("LSEG_APP_KEY", "LSEG_USER_ID", "LSEG_PASSWORD")),
    "LSEG credentials not set",
)
class TestRefinitiv(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        Refinitiv.close()

    def test_bars(self):
        end = datetime.now()
        bars = Refinitiv.get_bars_time_range(
            ["AAPL.O"], end - timedelta(days=10), end)
        self.assertIn("AAPL", bars)
        self.assertGreater(len(bars["AAPL"]), 0)
        self.assertIsNotNone(bars["AAPL"][0]["close"])

    def test_nav(self):
        df = pd.DataFrame({"ticker": ["AAPL.O", "MSFT.O"], "shares": [10, 5]})
        nav = Refinitiv.get_historical_net_asset_value(df)
        self.assertGreater(len(nav), 0)
        self.assertIn("price close", nav[0])


if __name__ == "__main__":
    unittest.main()
