import streamlit as st
import requests
from alpaca.trading.client import TradingClient
from alpaca.trading import Asset
from dotenv import load_dotenv
import os
import pandas as pd

load_dotenv()

API_KEY = os.getenv("APCA_API_KEY_ID")
SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")

client = TradingClient(API_KEY, SECRET_KEY, paper=True)

assets = client.get_all_assets()

attributes= list(assets[0].__dict__.keys())


"""
assets_df =  pd.DataFrame({
     'ticker': [x.symbol for x in assets],
     'status': [x.status for x in assets]
})
"""


selected_attributes = st.multiselect(label = "select attributes", options = attributes, default= ["symbol", "status"])

filtered_objects = []
for asset in assets: 
    d= {}
    asset_dict= asset.__dict__
    for selected_attribute in selected_attributes:
        d[selected_attribute]= asset_dict[selected_attribute]
    filtered_objects.append(d)

assets_df = pd.DataFrame(filtered_objects)

st.title("Asset overview: ")


st.dataframe(assets_df)



st.title("Asset selector: ")
symbols= [asset.symbol for asset in assets]

selected_symbol = st.selectbox(label = "select asset", options = symbols)

asset = client.get_asset(selected_symbol)


asset_dict = asset.__dict__
st.write(pd.DataFrame(asset_dict))
st.write(asset.attributes)