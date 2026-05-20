
import os
from dotenv import load_dotenv


load_dotenv()
import pandas as pd
import awswrangler as wr
import boto3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

LOCAL_DB_URI = "sqlite:///market_minute.db" 
local_engine = create_engine(LOCAL_DB_URI)

# 2. AWS Configuration Variables

S3_BUCKET_BASE= os.getenv("ATHENA_BUCKET_BASE")
GLUE_DATABASE= os.getenv("GLUE_DB")



AWS_REGION = os.getenv("AWS_REGION", "eu-central-1:") 
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

boto3.setup_default_session(
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

def push_market_data():
    print("Extracting Market Minute data...")
    query = "SELECT * FROM portfolio_management_developer_minute"
    df = pd.read_sql(query, con=local_engine)
    
    if df.empty:
        print("No market data found to push.")
        return

    table_name = os.getenv("ATHENA_MINUTE_TABLE")
    # Create partition column
    df['month'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m')
    
    print(f"Pushing {len(df)} market records to S3 (3 Buckets)...")
    wr.s3.to_parquet(
        df=df,
        path=f"{S3_BUCKET_BASE}/market_minute/",
        dataset=True,
        database=GLUE_DATABASE,
        table=table_name,
        partition_cols=['month'],
        bucketing_info=(["ticker"], 3),  # 3 Buckets
        mode='overwrite_partitions',
        index=False
    )
    print("Market data push complete.\n")

def push_forex_data():
    print("Extracting Forex Minute data...")
    query = "SELECT * FROM forex_data_minute"
    df = pd.read_sql(query, con=local_engine)
    
    if df.empty:
        print("No forex data found to push.")
        return

    table_name = os.getenv("ATHENA_MINUTE_TABLE_FOREX")
    # Create partition column
    df['month'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m')
    
    print(f"Pushing {len(df)} forex records to S3 (5 Buckets)...")
    wr.s3.to_parquet(
        df=df,
        path=f"{S3_BUCKET_BASE}/forex_minute/",
        dataset=True,
        database=GLUE_DATABASE,
        table=table_name,
        partition_cols=['month'],
        bucketing_info=(["ticker"], 5),  # 5 Buckets
        mode='overwrite_partitions',
        index=False
    )
    print("Forex data push complete.\n")

def push_metadata():
    print("Extracting Ticker Metadata...")
    query = "SELECT * FROM ticker_metadata"
    df = pd.read_sql(query, con=local_engine)
    
    if df.empty:
        print("No metadata found to push.")
        return

    print(f"Pushing {len(df)} metadata records to S3...")
    wr.s3.to_parquet(
        df=df,
        path=f"{S3_BUCKET_BASE}/ticker_metadata/",
        dataset=True,
        database=GLUE_DATABASE,
        table="ticker_metadata",
        mode='overwrite', # Metadata usually overwrites entirely rather than partitioning
        index=False
    )
    print("Metadata push complete.\n")

if __name__ == "__main__":
    print("Starting ETL Pipeline to AWS Data Lake...\n" + "-"*40)
    
    push_market_data()
    push_forex_data()
    push_metadata()
    
    print("-" * 40 + "\nPipeline execution finished successfully.")
