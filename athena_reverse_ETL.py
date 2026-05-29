import os
import pandas as pd
import awswrangler as wr
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import delete

# 1. Force the environment variables for local DB writing
os.environ["DB_GRANULARITY"] = "minute"
os.environ["MINUTE_DATA_SOURCE"] = "local"

load_dotenv()

from portfolio.utils.aws_config import engine
from portfolio.schemas.market import Base, MarketMinuteDB, ForexMinuteDB, TickerMeta

def reverse_etl():
    """
    Scans tables from AWS Athena and writes them back into the local minute-level database.
    """
    # Load AWS configuration variables
    GLUE_DB = os.getenv("GLUE_DB", "portfolio-management-db")
    ATHENA_MINUTE_TABLE = os.getenv("ATHENA_MINUTE_TABLE", "portfolio_management_developer_minute")
    ATHENA_MINUTE_TABLE_FOREX = os.getenv("ATHENA_MINUTE_TABLE_FOREX", "forex_data_minute")
    TICKER_TABLE = TickerMeta.__tablename__
    
    # Athena requires an S3 location to store query execution results
    ATHENA_S3_OUTPUT = os.getenv("ATHENA_BUCKET_BASE") + "/athena-query-results/"

    print(f"Connecting to AWS Athena (Database: {GLUE_DB})...")
    print("--------------------------------------------------")

    # ==========================================
    # 1. Fetch Data From Athena
    # ==========================================
    
    print(f"Fetching market data from Athena...")
    market_df = wr.athena.read_sql_query(
        sql=f'SELECT * FROM "{ATHENA_MINUTE_TABLE}"', 
        database=GLUE_DB, 
        s3_output=ATHENA_S3_OUTPUT
    )
    
    print(f"Fetching forex data from Athena...")
    forex_df = wr.athena.read_sql_query(
        sql=f'SELECT * FROM "{ATHENA_MINUTE_TABLE_FOREX}"', 
        database=GLUE_DB, 
        s3_output=ATHENA_S3_OUTPUT
    )

    print(f"Fetching ticker metadata from Athena...")
    ticker_df = wr.athena.read_sql_query(
        sql=f'SELECT * FROM "{TICKER_TABLE}"', 
        database=GLUE_DB, 
        s3_output=ATHENA_S3_OUTPUT
    )

    print("\nData fetched successfully. Proceeding to update the local database...")
    print("--------------------------------------------------")

    # ==========================================
    # 2. Clear Local Tables (Preserving Schema)
    # ==========================================
    
    with Session(engine) as session:
        print("Clearing existing local market, forex, and ticker records...")
        session.execute(delete(MarketMinuteDB))
        session.execute(delete(ForexMinuteDB))
        session.execute(delete(TickerMeta))
        session.commit()

    # ==========================================
    # 3. Append Fresh Data to Local Database
    # ==========================================
    
    if not market_df.empty:
        print(f"Writing {len(market_df)} records to the local Market table...")
        market_df.to_sql(MarketMinuteDB.__tablename__, con=engine, if_exists='append', index=False)
        
    if not forex_df.empty:
        print(f"Writing {len(forex_df)} records to the local Forex table...")
        forex_df.to_sql(ForexMinuteDB.__tablename__, con=engine, if_exists='append', index=False)

    if not ticker_df.empty:
        print(f"Writing {len(ticker_df)} records to the local Ticker Meta table...")
        ticker_df.to_sql(TickerMeta.__tablename__, con=engine, if_exists='append', index=False)

    print("\nReverse ETL complete! Local database is completely synced with Athena.")

if __name__ == "__main__":
    # Ensure tables exist locally before we attempt to clear and append to them
    print("Verifying local database schemas...")
    Base.metadata.create_all(engine)
    
    reverse_etl()