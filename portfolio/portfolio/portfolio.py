from typing import List

from ..market.market import Market

from datetime import datetime, timedelta
from datetime import date as dte

import pandas as pd
import json
import os



TR_TYPE = "type"
TR_CURRENCY = "currency"
TR_DATE = "date"
TR_VOLUME = "volume"
TR_TICKER = "ticker"

class Portfolio(): 
    def __init__(self, cash:float, leverage_limit:float)-> None:
        self.cash: float = cash
        self.leverage_limit: float = leverage_limit
        self.portfolio:pd.DataFrame = None


    def import_from_json(self, path): 

        with open(path, mode="r", encoding="utf-8") as file:
            data = json.load(file)
            rows = []

            for transaction in data["transactions"]: 
                rows.append({
                    TR_TICKER:transaction["security"]["ticker"], 
                    TR_CURRENCY:transaction["currency"], 
                    TR_DATE:pd.Timestamp(transaction["date"]), 
                    TR_VOLUME:float(transaction["shares"]) 
                })

            #: TODO: consider the operation type; add options to reconstruct portfolio states.  


            self.portfolio= pd.DataFrame(rows)
            self.portfolio=self.portfolio.set_index([TR_TICKER, TR_DATE]).sort_index()



    def get_owned_securities(self) -> List[str]: 
        return list(set(self.portfolio.index.get_level_values(TR_TICKER)))


    def get_buy_prices(self, ticker: str): 
        asset_df = self.portfolio.loc[[ticker]]
        asset_df= asset_df.reset_index()
        asset_df["price"] = asset_df[TR_DATE].apply(
            lambda x: Market.get_price(ticker, x)
        )

        return asset_df




    def get_gross_exposure(self)-> float: 
        total = 0.0
        assets= self.get_owned_securities()
        asset_df = self.portfolio.reset_index()
        asset_df["latest_price"] = asset_df.apply(
            lambda x: Market.get_latest_price(x[TR_TICKER]), 
            axis =1
            )
        asset_df["prod"]  = asset_df["latest_price"]*asset_df[TR_VOLUME]
        return asset_df.groupby(TR_TICKER)["prod"].sum().sum()


    def get_net_asset_value(self) -> float: 
        return self.cash+ self.get_gross_exposure()

    def get_gross_exposure_ticker(self, ticker:str)-> float: 
        """
        computes the product: volume_asset * latest_price_asset 
        """
        total = 0.0
        assets= self.get_owned_securities()
        asset_df = self.portfolio.reset_index()
        asset_df = asset_df[asset_df[TR_TICKER]==ticker]
        print(asset_df)
        asset_df["latest_price"] = asset_df.apply(
            lambda x: Market.get_latest_price(x[TR_TICKER]), 
            axis =1
            )
        asset_df["prod"]  = asset_df["latest_price"]*asset_df[TR_VOLUME]
        return asset_df.groupby(TR_TICKER)["prod"].sum().sum()


    def buy(self, product:str, quantity: int , currency: str): 
        date = dte.today()
        price = Market.get_latest_price(product)

        cost = price* quantity
        new_cash = self.cash-cost 
        new_row = pd.DataFrame (
            {
                TR_VOLUME: [quantity], 
                TR_CURRENCY:[currency] 
            }, 
            index = pd.MultiIndex.from_tuples([(product, pd.Timestamp(date))], names = [TR_TICKER, TR_DATE])
        )
        #: TODO: add leverage check?


        self.cash = new_cash
        self.portfolio= pd.concat([self.portfolio, new_row]).sort_index()

        return True


    def sell(self, product: str, quantity: int)-> bool: 
        date = dte.today()
        price = Market.get_latest_price(product)
        delta_cash = price*quantity
        new_cash = price *quantity 


        #:TODO: figure out how sell works when having stocks bought at different points in time. 
        #: maybe this function for the objective of the program does not make sense


    def summary(self)-> dict: 
        
        #: TODO: extend this with positions (?)
        return {
            "cash": self.cash, 
            "gross_exposure": self.get_gross_exposure(), 
            "net_asset_value": self.get_net_asset_value()
        }


Market.init()
date = dte.today()+timedelta(days = -2)

pf = Portfolio(10000, 100)
pf.import_from_json("./data/trades.json")


print(Market.get_us_treasury_bonds())


#print(pf.get_gross_exposure())
#pf.buy("NVDA", 10000000, "USD")
#print(pf.get_gross_exposure())
