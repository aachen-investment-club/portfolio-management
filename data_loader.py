import streamlit
from alpaca.data import  StockHistoricalDataClient , StockBarsRequest, TimeFrame, TimeFrameUnit
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

API_KEY = os.getenv("APCA_API_KEY_ID") 
SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")



stock_client = StockHistoricalDataClient(API_KEY,  SECRET_KEY)


request_params= StockBarsRequest(
       symbol_or_symbols=["NVDA"], 
        timeframe=TimeFrame.Day, 
        start= datetime(2025, 10, 1), 
        end = datetime(2025, 10, 31)
    )





bars = stock_client.get_stock_bars(request_params)

print(bars["NVDA"][0])



