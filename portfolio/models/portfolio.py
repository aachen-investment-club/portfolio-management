from typing import List, Dict, Tuple

from portfolio.models.market import Market

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
TR_TYPE= "type"

class Portfolio(): 
    def __init__(self, cash:float, leverage_limit:float)-> None:
        self.cash: float = cash
        self.leverage_limit: float = leverage_limit
        self.trades:pd.DataFrame = None
        self.current_position ={} #: observation: we assume short selling in this implementation.



    def import_from_json(self, path): 
        """
        imports a FULL trades log and: 
        - saves the trades 
        - updates the current position
        - updates current cash
        """

        with open(path, mode="r", encoding="utf-8") as file:
            data = json.load(file)
            rows = []

            for transaction in data["transactions"]: 
                rows.append({
                    TR_TICKER:transaction["security"]["ticker"], 
                    TR_CURRENCY:transaction["currency"], 
                    TR_TYPE:transaction["type"],
                    TR_DATE:pd.Timestamp(transaction["date"]), 
                    TR_VOLUME:float(transaction["shares"]) 
                })

            #: TODO: consider the operation type; add options to reconstruct portfolio states.  


            self.trades= pd.DataFrame(rows)
            self.trades=self.trades.set_index([TR_TICKER, TR_DATE]).sort_index()
            
            today = dte.today()
            self.current_position, self.cash = self.get_position(dte.today())



    def get_owned_securities(self) -> List[str]: 
        return list(self.current_position.keys())


    def get_buy_prices(self, ticker: str): 
        asset_df = self.trades.loc[[ticker]]
        asset_df= asset_df.reset_index()
        asset_df["price"] = asset_df[TR_DATE].apply(
            lambda x: Market.get_price(ticker, x)
        )

        return asset_df




    def get_gross_exposure(self)-> float: 
        total = 0.0
        assets= self.get_owned_securities()


        for product, vol in self.current_position.items():
            price = Market.get_latest_price(product)
            total += abs(vol)*price
        return total


    def get_net_asset_value(self) -> float: 
        return self.cash+ self.get_gross_exposure()

   


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

    def get_position(self, date:datetime)-> Tuple[Dict, float]: 

        sublog = self.trades[self.trades.index.get_level_values(TR_DATE)<= pd.Timestamp(date)]
        position = {}

        traded_assets =  self.trades.index.get_level_values(TR_TICKER).unique()
        total_cash = self.cash
        for asset in traded_assets: 
            operations = sublog[sublog.index.get_level_values(TR_TICKER)== asset]
            operations = operations.reset_index()
            
            #print(operations)
            #print(operations.columns)
            operations["close_price"] = operations.apply(
                lambda x: Market.get_price(x[TR_TICKER], x[TR_DATE] ), 
                axis = 1
            )

            purchases = operations[operations[TR_TYPE]== "PURCHASE"]
            purchases_cash = (purchases[TR_VOLUME]*purchases["close_price"]).sum()

            sales = operations[operations[TR_TYPE]== "SALE"]
            sales_cash = (sales[TR_VOLUME]*sales["close_price"]).sum()


            total_cash = total_cash + sales_cash- purchases_cash
            #: OBSERVATION: WE ASSUME SHORT SELLING
            position[asset] = sum(purchases[TR_VOLUME])-sum(sales[TR_VOLUME])

        return position, total_cash


    def buy(self, product:str, quantity: int , currency: str): 
        date = dte.today()
        price = Market.get_latest_price(product)

        cost = price* quantity
        new_cash = self.cash-cost 
        new_row = pd.DataFrame (
            {
                TR_VOLUME: [quantity], 
                TR_CURRENCY:[currency] , 
                TR_TYPE: ["PURCHASE"] 
            }, 
            index = pd.MultiIndex.from_tuples([(product, pd.Timestamp(date))], names = [TR_TICKER, TR_DATE])
        )

        self.current_position[product]+= quantity


        #: TODO: add leverage check?


        self.cash = new_cash
        self.trades= pd.concat([self.trades, new_row]).sort_index()

        return True



