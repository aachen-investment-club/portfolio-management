import os
from dotenv import load_dotenv

# 1. Force the environment variables for local minute-level granularity
os.environ["DB_GRANULARITY"] = "minute"
os.environ["MINUTE_DATA_SOURCE"] = "local"

# Load any other configurations like API keys and DB URI from .env
load_dotenv()

from portfolio.models.market import Market
from portfolio.schemas.market import Base
from portfolio.utils.aws_config import engine

def initialize_minute_db(csv_path: str):
    """
    Initializes the local database with minute granularity from scratch.
    """
    print("Creating database tables if they do not exist...")
    Base.metadata.create_all(engine)

    # 2. Call the load ticker metadata function
    print(f"Loading ticker metadata from {csv_path}...")
    inserted_meta = Market.load_ticker_metadata(csv_path)
    print(f"Successfully loaded {inserted_meta} ticker metadata records.")

    # 3. Run the update market function 
    # (By default, this will fetch yfinance data using a 2-day rolling window for minute data, 
    # adjust the timedelta in market.py if you specifically need 3 days)
    print("Updating market data from yfinance...")
    Market.update_market()

    # 4. Run the update forex function
    print("Updating forex data from yfinance...")
    # Passing an optional chunk size if required by your forex function signature
    Market.update_forex()
    
    print("Local minute-level database initialized successfully!")

if __name__ == "__main__":
    # Specify the correct path to your ticker CSV file here
    METADATA_CSV_PATH = "./data/ticker_metadata.csv" 
    
    initialize_minute_db(METADATA_CSV_PATH)