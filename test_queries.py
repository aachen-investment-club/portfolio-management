
from dotenv import load_dotenv

load_dotenv()


from sqlalchemy import func
from sqlalchemy.orm import Session
import os
# Import your engine and schemas based on the project structure in your snippets
from portfolio.utils.aws_config import engine
from portfolio.schemas.market import MarketDB, ForexDayDB, TickerMeta, MarketMinuteDB, ForexMinuteDB


DB_GRANULARITY = os.getenv("DB_GRANULARITY", "day").lower()
print(DB_GRANULARITY)
DB = MarketMinuteDB if DB_GRANULARITY == "minute" else MarketDB

FOREXDB= ForexMinuteDB if DB_GRANULARITY == "minute" else ForexDayDB




def run_database_tests():
    # Create a session using your AWS engine
    with Session(engine) as session:
        
        print("====== OLDEST RECORDS ======")
        # 1. Oldest record in the market
        oldest_market = session.query(func.min(DB.date)).scalar()
        print(f"Oldest Market Record : {oldest_market}")
        
        # 2. Oldest record in forex
        oldest_forex = session.query(func.min(FOREXDB.date)).scalar()
        print(f"Oldest Forex Record  : {oldest_forex}")


        print("\n====== NEWEST RECORDS ======")
        # 3. Newest record in the market
        newest_market = session.query(func.max(DB.date)).scalar()
        print(f"Newest Market Record : {newest_market}")
        
        # 4. Newest record in forex
        newest_forex = session.query(func.max(FOREXDB.date)).scalar()
        print(f"Newest Forex Record  : {newest_forex}")


        print("\n====== NUMBER OF TICKERS ======")
        # 5. Number of unique tickers in the market
        nr_market_tickers = session.query(func.count(func.distinct(DB.ticker))).scalar()
        print(f"Unique Tickers in Market: {nr_market_tickers}")
        
        # 6. Number of unique tickers in forex
        nr_forex_tickers = session.query(func.count(func.distinct(FOREXDB.ticker))).scalar()
        print(f"Unique Tickers in Forex : {nr_forex_tickers}")


        print("\n====== METADATA ======")
        # 7. Number of tickers in the metadata
        # (Assuming 'ticker' is the primary key column in TickerMeta)
        nr_meta_tickers = session.query(func.count(TickerMeta.ticker)).scalar()
        print(f"Tickers in Metadata     : {nr_meta_tickers}")

if __name__ == "__main__":
    run_database_tests()