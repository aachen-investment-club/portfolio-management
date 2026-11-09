# Portfolio Management


Portable, lightweight dashboard with custom metrics to visualize
the portfolios managed by the portfolio management group. 

## Installation

1. Setup the `.env` file based on the `.env.example` template (you will be provided with these credentials).

2. Fill in the data credentials in `.env`:
   - `LSEG_APP_KEY`, `LSEG_USER_ID`, `LSEG_PASSWORD` (Refinitiv): prices and
     portfolio value.
   - `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY` (Alpaca): only the trading
     calendar / market updates.

3. [optional] Create a virtual python environment using
Assuming bash: 
```sh
python3.12 -m venv venv && source venv/bin/activate
```

4. Run installation of dependencies
```sh
pip install -r requirements.txt
```

5. Download the necessary setup data from the following URL, and 
place them in the `./data` folder. (From the root dir of the repo)
- [google drive](https://drive.google.com/drive/folders/1BEqdjOI4otPHc3-4iggC3r244uuY0_z4?usp=sharing)


6. To run the application, simply run

```sh
python -m portfolio
```


## Alpaca

Prices no longer come from Alpaca, but it is still used for two things that
Refinitiv does not replace yet, which is why the `APCA_*` keys are still needed:

- the **trading calendar** (`Market.update_market` and `Market.is_trading_day`
  in `portfolio/models/market.py`)
- the legacy `Market.update_market_old` updater

`alpaca-py` is imported only inside those functions, so the app starts without
it, but those functions fail if it is missing or the keys are not set.

### Switching the price source

Prices for `/api/portfolio` are fetched in `portfolio/backend.py`. Both
`Refinitiv` and `Alpaca` (`portfolio/models/alpaca_wrapper.py`) provide
`get_historical_net_asset_value`, so to switch:

1. Change the import at the top of the file:
```python
from portfolio.models.refinitiv_wrapper import Refinitiv   # Refinitiv
from portfolio.models.alpaca_wrapper import Alpaca         # Alpaca
```
2. Change the call in `portfolio()`. Note the different ticker format:
```python
# Refinitiv: full RICs (AAPL.O)
historical_data = Refinitiv.get_historical_net_asset_value(df_ric)
# Alpaca: bare symbols (AAPL)
historical_data = Alpaca.get_historical_net_asset_value(df_bare)
```
3. Make sure the matching keys are set in `.env` (`LSEG_*` or `APCA_*`).

## Refinitiv

Prices and portfolio value come from Refinitiv. Use RICs (e.g. `AAPL.O`).
Check your credentials with:

```sh
python -m unittest test.test_refinitiv
```


## Market data in minute level granularity
We also support access to minute level data to allow for model training. 
For this, you will be provided with additional env variables. (ask an admin). 

Run the `athena_to_localdb.py` file to sync with the database called `market_minute.db` which will contain the minute level data. From the repo root: 
```sh
python athena_to_localdb.py
```

Important: to interact with this database, you can use the defined functions in  `portfolio/models/market.py`. However, you must make sure to set
```sh
DB_GRANULARITY=minute
MINUTE_DATA_SOURCE=local
```
in your `.env` file. Observation: this might break your local frontend! To
switch back to day level granularity, use: 
```sh
DB_GRANULARITY=day
MINUTE_DATA_SOURCE=local
```




## Market data & credentials
To get access to the market data & other credentials, please contact the admins. 

Only for AIC Developer members. 


## Automatic API documentation

1. Go to folder `docs/`
2. Run Sphinx

```
sphinx-build -b html . _build
```

3. Open `docs/_build/index.html`
