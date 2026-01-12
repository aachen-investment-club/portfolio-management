

from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

from portfolio.extensions import cache
from portfolio.routes import bp

load_dotenv()

app = Flask(__name__)
CORS(app)


cache.init_app(app, config={
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
})
app.register_blueprint(bp)

from portfolio.models.market import Market

if __name__ == "__main__":


    if Market.check_empty():
        print("market empty, proceeding with creation")
        Market.load_from_csv("./data/sp500_close_current.csv", 5000)
    else: 
        print("Market already exists, no need to load from csv.")

    app.run(debug=True)
