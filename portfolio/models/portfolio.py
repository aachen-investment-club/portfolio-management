from typing import List, Dict, Tuple

#from portfolio.models.market import Market
from market import Market

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

   


    
    def summary(self)-> dict: 
        
        #: TODO: extend this with positions (?)
        return {
            "cash": self.cash, 
            "gross_exposure": self.get_gross_exposure(), 
            "net_asset_value": self.get_net_asset_value()
        }

    

    def get_position(self, date:datetime)-> Tuple[Dict, float]: 
        #: observation: we assume that past states comply with leverage, thus we dont check this

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



    def check_leverage(self, new_cash, new_positions): 
        gross = sum(abs(qty) * Market.get_latest_price(p) for p, qty in new_positions.items())
        net_value = new_cash + sum(qty * Market.get_latest_price(p) for p, qty in new_positions.items())
        leverage = gross / max(net_value, 1e-8)
        return leverage <= self.leverage_limit

    def get_current_leverage(self): 
        gross = sum(abs(qty) * Market.get_latest_price(p) for p, qty in self.current_position.items())
        net_value = self.cash+ sum(qty * Market.get_latest_price(p) for p, qty in self.current_position.items())
        leverage = gross / max(net_value, 1e-8)
        return leverage 



    def sell(self, product: str, quantity: int, currency: str)-> bool: 
        date = Market.get_latest_quotation_date()
        price = Market.get_latest_price(product)
        new_cash = price *quantity  + self.cash
        new_position = self.current_position.copy()
        new_position[product]  = new_position[product] - quantity

        if not self.check_leverage(new_cash, new_position):
            print("trade rejected - leverage limit surpassed")
            return False
    
        new_row = pd.DataFrame (
            {
                TR_VOLUME: [quantity], 
                TR_CURRENCY:[currency] , 
                TR_TYPE: ["SALE"] 
            }, 
            index = pd.MultiIndex.from_tuples([(product, pd.Timestamp(date))], names = [TR_TICKER, TR_DATE])
        )

        self.current_position = new_position

        self.cash = new_cash
        self.trades= pd.concat([self.trades, new_row]).sort_index()

        return True


        #: maybe this function for the objective of the program does not make sense




    def buy(self, product:str, quantity: int , currency: str): 
        date = Market.get_latest_quotation_date()
        price = Market.get_latest_price(product)

        cost = price* quantity
        new_cash = self.cash-cost 


        new_position = self.current_position.copy()

        new_position[product]+= quantity

        if not self.check_leverage(new_cash, new_position): 
            print("trade rejected - leverage limit surpassed")
            return False

        new_row = pd.DataFrame (
            {
                TR_VOLUME: [quantity], 
                TR_CURRENCY:[currency] , 
                TR_TYPE: ["PURCHASE"] 
            }, 
            index = pd.MultiIndex.from_tuples([(product, pd.Timestamp(date))], names = [TR_TICKER, TR_DATE])
        )

        self.current_position = new_position

        self.cash = new_cash
        self.trades= pd.concat([self.trades, new_row]).sort_index()

        return True



