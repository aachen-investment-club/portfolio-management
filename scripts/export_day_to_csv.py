"""
this script can be used to generate csv files containing the data stored in the 
day level granularity db. 


run this script from the root dir using: 

python scripts/export_day_to_csv.py

"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

# Import engine and DB mappings from your existing module structure
from portfolio.utils.aws_config import engine
from portfolio.schemas.market import MarketDB,  ForexDayDB 

def export_table_to_csv(db_model, output_filename, chunk_size=5000):
    """
    Streams data from a database table using server-side cursor emulation/chunking
    and writes it directly to a CSV file safely.
    """
    
    # Define a clean mapping to rename the database columns to matches your requirements
    column_mapping = {
        "ticker": "Ticker",
        "date": "Date",
        "price_close": "Price Close",
        "open": "Open",
        "high": "High",
        "low": "Low",
        "volume": "Volume"
    }
    
    # Use standard select query
    stmt = select(db_model)
    
    first_chunk = True
    total_rows = 0
    
    with Session(engine) as session:
        # FIX: Use session.execute() with yield_per instead of session.stream()
        # This streams rows from the database driver in batches for synchronous sessions.
        result = session.execute(stmt.execution_options(yield_per=chunk_size))
        
        # .partitions() automatically chunks the streaming result iterator 
        for batch in result.partitions(chunk_size):
            
            # Convert raw database rows into a list of dictionaries
            records = []
            for row in batch:
                obj = row[0] # Unpack the ORM object from the row tuple
                record = {
                    "ticker": obj.ticker,
                    "date": obj.date,
                    "price_close": obj.price_close,
                    "open": getattr(obj, 'open', None),
                    "high": getattr(obj, 'high', None),
                    "low": getattr(obj, 'low', None),
                    "volume": getattr(obj, 'volume', None)
                }
                records.append(record)
                
            # Process dataframe for the chunk
            df_chunk = pd.DataFrame(records)
            
            # Format and normalize date column if present
            if "date" in df_chunk.columns and not df_chunk.empty:
                df_chunk["date"] = pd.to_datetime(df_chunk["date"]).dt.tz_localize(None)
                
            # Rename columns according to request (e.g., price_close -> Price Close)
            df_chunk = df_chunk.rename(columns=column_mapping)
            
            # Filter down to columns that exist in database table structure
            existing_columns = [col for col in column_mapping.values() if col in df_chunk.columns]
            df_chunk = df_chunk[existing_columns]
            
            # Append rows into CSV safely
            if first_chunk:
                df_chunk.to_csv(output_filename, mode='w', index=False)
                first_chunk = False
            else:
                df_chunk.to_csv(output_filename, mode='a', header=False, index=False)
                
            total_rows += len(df_chunk)
            print(f"  -> Written {total_rows} rows so far...")

    print(f"Finished! Total exported rows for {output_filename}: {total_rows}\n")


def main():
    # Export paths
    market_csv_path = f"./data/market_export.csv"
    forex_csv_path = f"./data/forex_export.csv"
    
    # Execute exports sequentially
    export_table_to_csv(MarketDB, market_csv_path, chunk_size=5000)
    export_table_to_csv(ForexDayDB, forex_csv_path, chunk_size=5000)


if __name__ == "__main__":
    main()