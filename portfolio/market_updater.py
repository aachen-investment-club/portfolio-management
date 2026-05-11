from dotenv import load_dotenv


load_dotenv()

from portfolio.models.market import Market
from portfolio.schemas.market import Base
from portfolio.utils.aws_config import engine

if __name__ == "__main__":

    Base.metadata.create_all(engine)   # create ForexDB table if it does not exist
    Market.update_market()
    Market.update_forex()

