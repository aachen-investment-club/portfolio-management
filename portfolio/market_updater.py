from dotenv import load_dotenv


load_dotenv()

from portfolio.models.market import Market

if __name__ == "__main__":

    Market.update_market()

