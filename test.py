from alpaca.trading.client import TradingClient
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("APCA_API_KEY_ID")
SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")

client = TradingClient(API_KEY, SECRET_KEY, paper=True)


account = client.get_account()
print("Account status:", account.status)
print("Cash available:", account.cash)
