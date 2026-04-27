# Portfolio Management


Portable, lightweight dashboard with custom metrics to visualize
the portfolios managed by the portfolio management group. 

## Installation

1. Setup the `.env` file based on the `.env.example` template.
2. [optional] Create a virtual python environment using
Assuming bash: 
```sh
python3.12 -m venv env && source env/bin/activate
```

3. Run installation of dependencies
```sh
pip install -r requirements.txt
```

4. To run the application, simply run

```sh
python -m portfolio
```


5. To manually update the market run  

```sh
python market_updater.py
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
