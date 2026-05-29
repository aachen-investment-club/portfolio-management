"""
this file is used to migrate the local metadata table into athena. 

only used for admin context. IGNORE THIS SCRIPT. 


"""




import os
import pandas as pd
import awswrangler as wr
from dotenv import load_dotenv

# Force local read
os.environ["DB_GRANULARITY"] = "minute"
os.environ["MINUTE_DATA_SOURCE"] = "local"
load_dotenv()

from portfolio.utils.aws_config import engine
from portfolio.schemas.market import TickerMeta

def migrate_tickers():
    ATHENA_BUCKET_BASE = os.getenv("ATHENA_BUCKET_BASE")
    GLUE_DB = os.getenv("GLUE_DB", "portfolio-management-db")
    TABLE_NAME = TickerMeta.__tablename__

    print(f"Reading local ticker metadata from '{TABLE_NAME}'...")
    ticker_df = pd.read_sql_table(TABLE_NAME, con=engine)

    if not ticker_df.empty:
        print(f"Deleting corrupted Glue table metadata for '{TABLE_NAME}'...")
        wr.catalog.delete_table_if_exists(database=GLUE_DB, table=TABLE_NAME)

        print(f"Pushing {len(ticker_df)} ticker records to S3 and Athena...")
        wr.s3.to_parquet(
            df=ticker_df,
            path=f"{ATHENA_BUCKET_BASE}/{TABLE_NAME}/",
            dataset=True,
            database=GLUE_DB,
            table=TABLE_NAME,
            mode="overwrite",
            index=False
        )
        print("Ticker metadata successfully migrated!")
    else:
        print("No ticker metadata found locally.")

if __name__ == "__main__":
    migrate_tickers()