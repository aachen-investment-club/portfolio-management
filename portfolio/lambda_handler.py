from dotenv import load_dotenv


load_dotenv()

from portfolio.models.market import Market
from portfolio.schemas.market import Base
from portfolio.utils.aws_config import engine




def handler(event, context):
    print("Initializing database tables...")
    Base.metadata.create_all(engine)
    
    print("Starting market data update...")
    Market.update_market()
    
    print("Starting forex data update...")
    Market.update_forex()
    
    return {
        "statusCode": 200,
        "body": "Market and Forex update executed successfully."
    }

