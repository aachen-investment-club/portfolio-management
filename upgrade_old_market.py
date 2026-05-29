import sqlalchemy
from sqlalchemy import text
from portfolio.utils.aws_config import engine

def upgrade_database_schema():
    """
    Upgrades the existing market database tables to include the new 
    day-level granularity columns (open, high, low, volume).
    """
    
    # The tables that need the new columns based on your schema
    tables_to_upgrade = [
        "portfolio_management_developer",  # MarketDB
        "forex_data"                       # ForexDayDB
    ]
    
    # The new columns and their SQL data types
    new_columns = [
        "open FLOAT",
        "high FLOAT",
        "low FLOAT",
        "volume FLOAT"
    ]

    print("Starting database schema upgrade...")

    with engine.connect() as conn:
        for table in tables_to_upgrade:
            print(f"\nProcessing table: '{table}'")
            
            for column_def in new_columns:
                column_name = column_def.split()[0]
                alter_query = text(f"ALTER TABLE {table} ADD COLUMN {column_def};")
                
                try:
                    conn.execute(alter_query)
                    print(f"  [SUCCESS] Added column '{column_name}'")
                except sqlalchemy.exc.OperationalError:
                    # If the column already exists, SQLAlchemy throws an OperationalError.
                    # We catch it so the script doesn't crash and just skips to the next one.
                    print(f"  [SKIPPED] Column '{column_name}' likely already exists.")
        
        # Commit the transaction to save changes to the database
        conn.commit()
        
    print("\nDatabase schema upgrade complete! Your database is now backward compatible.")

if __name__ == "__main__":
    upgrade_database_schema()