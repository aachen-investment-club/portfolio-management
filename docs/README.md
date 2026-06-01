# Portfolio Management


Portable, lightweight dashboard with custom metrics to visualize
the portfolios managed by the portfolio management group. 

## Installation

1. Setup the `.env` file based on the `.env.example` template (you will be provided with these credentials).

2. Make sure to create a free Alpaca paper trading account to fill in the 
missing Alpaca keys. 

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
