"""
You can use this script to populate your local minute level 
database by pulling from athena. 


run using: 

python scripts/pull_from_athena.py

"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from dotenv import load_dotenv
import boto3
import pandas as pd
import awswrangler as wr
from sqlalchemy import create_engine, text, inspect


from portfolio.schemas.market import Base


load_dotenv()

boto3.setup_default_session(
    region_name=os.getenv("AWS_REGION", "eu-central-1"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

GLUE_DATABASE = os.getenv("GLUE_DB", "financial_db")
ATHENA_BUCKET_NAME = os.getenv("ATHENA_BUCKET_BASE")
S3_STAGING_DIR = f"{ATHENA_BUCKET_NAME}/athena-query-results/"

LOCAL_DB_URI = "sqlite:///market_minute.db"
local_engine = create_engine(LOCAL_DB_URI)

# Initialize the local database schema (Creates the .db file and empty tables with Primary Keys)
print("Initializing local database schema...")
Base.metadata.create_all(local_engine)

def sync_athena_to_local(athena_table: str, local_table: str, chunk_size: int = 500):
    """
    Downloads data from Athena in chunks and appends it to a local SQLite database.
    """
    print(f"\n--- Syncing AWS Table '{athena_table}' to Local Table '{local_table}' ---")
    
    # Safely check if the table exists before attempting to clear it
    inspector = inspect(local_engine)
    if local_table in inspector.get_table_names():
        with local_engine.begin() as conn:
            conn.execute(text(f"DELETE FROM {local_table}"))
            print(f"Cleared existing data in local '{local_table}' table.")
    else:
        print(f"Table '{local_table}' is empty/new. Proceeding to insert data.")
        
    sql_query = f"SELECT * FROM {athena_table}"
    
    print(f"Executing Athena query and downloading in chunks of {chunk_size}...")
    
    # Using chunksize returns a Python Generator that yields DataFrames
    print(GLUE_DATABASE)
    print(S3_STAGING_DIR)
    chunked_dfs = wr.athena.read_sql_query(
        sql=sql_query,
        database=GLUE_DATABASE,
        s3_output=S3_STAGING_DIR,
        chunksize=chunk_size
    )
    
    total_rows = 0
    for i, chunk in enumerate(chunked_dfs):
        if chunk.empty:
            continue
            
        if 'date' in chunk.columns:
            chunk['date'] = pd.to_datetime(chunk['date']).dt.tz_localize(None)
            
        chunk.to_sql(
            name=local_table,
            con=local_engine,
            if_exists='append',
            index=False,
            method='multi'  
        )
        
        total_rows += len(chunk)
        print(f"  -> Chunk {i+1} inserted. Total rows restored: {total_rows:,}")
        
    print(f"Finished restoring '{local_table}'. Total rows: {total_rows:,}")


if __name__ == "__main__":
    
    # 1. Restore Metadata
    sync_athena_to_local(
        athena_table="ticker_metadata", 
        local_table="ticker_metadata"
    )
    
    # 2. Restore Stock Market Data
    sync_athena_to_local(
        athena_table="portfolio_management_developer_minute", 
        local_table="portfolio_management_developer_minute",
        chunk_size=1000
    )
    
    # 3. Restore Forex Data
    sync_athena_to_local(
        athena_table="forex_data_minute", 
        local_table="forex_data_minute",
        chunk_size=1000
    )
    
    print("done")