import os
import pandas as pd
import awswrangler as wr
from dotenv import load_dotenv

# 1. Force the local environment to read from the local DB for extraction
os.environ["DB_GRANULARITY"] = "minute"
os.environ["MINUTE_DATA_SOURCE"] = "local"

# Load environment variables (Make sure your AWS credentials are also loaded/configured)
load_dotenv()

from portfolio.utils.aws_config import engine
from portfolio.schemas.market import MarketMinuteDB, ForexMinuteDB

def migrate_local_to_athena():
    """
    Reads minute-level data from the local database and pushes it to AWS S3/Athena.
    """
    # Fetch Athena config from environment variables
    ATHENA_BUCKET_BASE = os.getenv("ATHENA_BUCKET_BASE", "s3://aic-developer-portfolio-management-minute-granularity")
    GLUE_DB = os.getenv("GLUE_DB", "portfolio-management-db")
    ATHENA_MINUTE_TABLE = os.getenv("ATHENA_MINUTE_TABLE", "market_data_minute")
    ATHENA_MINUTE_TABLE_FOREX = os.getenv("ATHENA_MINUTE_TABLE_FOREX", "forex_data_minute")

    print(f"Using AWS Glue DB: {GLUE_DB}")
    print("--------------------------------------------------")

    # ==========================================
    # 1. Migrate Market Data
    # ==========================================
    print("Reading local minute market data...")
    market_df = pd.read_sql_table(MarketMinuteDB.__tablename__, con=engine)
    
    if not market_df.empty:
        print(f"Deleting old Glue table metadata for '{ATHENA_MINUTE_TABLE}' if it exists...")
        wr.catalog.delete_table_if_exists(database=GLUE_DB, table=ATHENA_MINUTE_TABLE)

        print(f"Writing {len(market_df)} market records to S3 and Athena table '{ATHENA_MINUTE_TABLE}'...")
        
        # Write to S3 and register in Glue Catalog
        wr.s3.to_parquet(
            df=market_df,
            path=f"{ATHENA_BUCKET_BASE}/{ATHENA_MINUTE_TABLE}/",
            dataset=True,                  
            database=GLUE_DB,
            table=ATHENA_MINUTE_TABLE,
            mode="overwrite", # Completely replaces the old S3 data with the new local DB data
            partition_cols=['month'], # <--- ADDED: Explicitly set partition key
            schema_evolution=True,    # <--- ADDED: Allows the new open/high/low/vol columns
            index=False                    
        )
        print("Market data successfully migrated!")
    else:
        print("No market data found in the local database to migrate.")

    print("--------------------------------------------------")

    # ==========================================
    # 2. Migrate Forex Data
    # ==========================================
    print("Reading local minute forex data...")
    forex_df = pd.read_sql_table(ForexMinuteDB.__tablename__, con=engine)
    
    if not forex_df.empty:
        print(f"Deleting old Glue table metadata for '{ATHENA_MINUTE_TABLE_FOREX}' if it exists...")
        wr.catalog.delete_table_if_exists(database=GLUE_DB, table=ATHENA_MINUTE_TABLE_FOREX)

        print(f"Writing {len(forex_df)} forex records to S3 and Athena table '{ATHENA_MINUTE_TABLE_FOREX}'...")
        
        # Write to S3 and register in Glue Catalog
        wr.s3.to_parquet(
            df=forex_df,
            path=f"{ATHENA_BUCKET_BASE}/{ATHENA_MINUTE_TABLE_FOREX}/",
            dataset=True,                  
            database=GLUE_DB,
            table=ATHENA_MINUTE_TABLE_FOREX,
            mode="overwrite",         # Completely replaces the old S3 data 
            partition_cols=['month'], # <--- ADDED: Explicitly set partition key
            schema_evolution=True,    # <--- ADDED: Allows the new open/high/low/vol columns
            index=False                    
        )
        print("Forex data successfully migrated!")
    else:
        print("No forex data found in the local database to migrate.")

if __name__ == "__main__":
    # Ensure that AWS Glue database exists before attempting to write to it
    try:
        glue_databases = wr.catalog.databases()
        db_name = os.getenv("GLUE_DB", "portfolio-management-db")
        
        if db_name not in glue_databases['Database'].values:
            print(f"Glue Database '{db_name}' not found. Creating it now...")
            wr.catalog.create_database(db_name)
    except Exception as e:
        print(f"Warning: Could not verify/create Glue Database. Ensure AWS credentials are correct. Error: {e}")

    migrate_local_to_athena()