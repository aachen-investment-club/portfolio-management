import pandas as pd
from sqlalchemy import select
from portfolio.utils.aws_config import engine
from portfolio.schemas.market import MarketDB

def export_market_db_to_csv(output_filepath="market_data_export.csv", chunksize=10000):
    """
    Exports the contents of the MarketDB (day-level granularity) to a CSV file.
    Reads and writes in chunks to prevent memory overload.
    """
    print(f"Starting export of MarketDB to '{output_filepath}'...")
    
    stmt = select(MarketDB)
    
    first_chunk = True
    total_rows = 0
    
    with engine.connect() as conn:
        # pd.read_sql_query with a chunksize returns an iterator of DataFrames
        for chunk in pd.read_sql_query(stmt, conn, chunksize=chunksize):
            
            # For the first chunk, write the file ('w') and include headers
            # For all subsequent chunks, append ('a') and skip headers
            chunk.to_csv(
                output_filepath, 
                mode='w' if first_chunk else 'a', 
                index=False, 
                header=first_chunk
            )
            
            first_chunk = False
            total_rows += len(chunk)
            print(f"Exported {total_rows} rows so far...")
            
    print(f"Export completed successfully! Total rows exported: {total_rows}")

if __name__ == "__main__":
    # You can specify a different filename or path here if needed
    export_market_db_to_csv("market_day_granularity.csv")