import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

# Load your local .env file which should contain your AWS credentials,
# DB_ATHENA_PATH, and optionally DB_MINUTE_PATH
load_dotenv()

from portfolio.schemas.market import MarketMinuteDB


def sync_athena_to_local_batched():
    
    athena_conn_str = os.getenv("DB_ATHENA_PATH")
    local_db_path = os.getenv("DB_MINUTE_PATH", "sqlite:///market_minute.db")
    
    if not athena_conn_str:
        print("DB_ATHENA_PATH is not set in your environment variables.")
        return
        
    athena_engine = create_engine(athena_conn_str, echo=False)
    local_engine = create_engine(local_db_path, echo=False)
    
    # Ensure the table exists in the local database
    MarketMinuteDB.metadata.create_all(local_engine)

    try:
        stmt = select(
            MarketMinuteDB.ticker,
            MarketMinuteDB.date,
            MarketMinuteDB.price_close,
            MarketMinuteDB.month
        )
        
        CHUNK_SIZE =5000 
        total_inserted = 0
        
        print(f"Fetching and writing data in batches of {CHUNK_SIZE}... (This might take a while)")
        
        with Session(local_engine) as session:
            
            for chunk_idx, df_chunk in enumerate(pd.read_sql(stmt, athena_engine, chunksize=CHUNK_SIZE)):
                
                if df_chunk.empty:
                    continue
                    
                
                df_chunk["date"] = pd.to_datetime(df_chunk["date"])
                
                records = df_chunk.to_dict(orient="records")
                
                insert_stmt = (
                    insert(MarketMinuteDB)
                    .values(records)
                    .on_conflict_do_nothing(index_elements=["ticker", "date"])
                )
                
                result = session.execute(insert_stmt)
                total_inserted += result.rowcount or 0
                
                session.commit()
                print((chunk_idx + 1)*CHUNK_SIZE)
                
        print(f"Sync complete! Total new rows inserted: {total_inserted}")
            
    except Exception as e:
        print(f"Error during batched sync: {e}")




if __name__ == "__main__":
    #sync_athena_to_local()
    sync_athena_to_local_batched()