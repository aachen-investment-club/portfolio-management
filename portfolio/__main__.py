import sentry_sdk
import os
from dotenv import load_dotenv

load_dotenv()

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    send_default_pii=True,
)

from portfolio.models.market import Market
from portfolio.utils.aws_config import engine
from portfolio.schemas.market import Base

#from portfolio.utils.aws_config import engine
Base.metadata.create_all(engine)

from flask import Flask
from flask_cors import CORS

from portfolio.extensions import cache, oauth
from portfolio.routes import bp
from portfolio.backend import bp_api



load_dotenv()

app = Flask(__name__)


CORS(app)

oauth.init_app(app)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
oauth.register(
  name='oidc',
  authority='https://cognito-idp.eu-central-1.amazonaws.com/eu-central-1_unKiHP6hh',
  client_id=os.getenv("COGNITO_CLIENT_ID"),
  client_secret=os.getenv("AWS_COGNI_CLIENT_SECRET"),
  server_metadata_url='https://cognito-idp.eu-central-1.amazonaws.com/eu-central-1_unKiHP6hh/.well-known/openid-configuration',
  client_kwargs={'scope': 'openid email'}
)



cache.init_app(app, config={
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
})

app.register_blueprint(bp)
app.register_blueprint(bp_api)

if __name__ == "__main__":
    chunks_prod = 5000
    chunks_dev = 10000

    if Market.check_empty():
        print("market empty, proceeding with creation")
        Market.load_from_csv("./data/sp500_close_extended.csv", chunks_dev)
        #Market.load_from_csv("./data/sp500_close_current.csv", chunks_dev)

    else:
        print("Market already exists, no need to load from csv")


    if Market.check_meta_empty():
        print("market metadata empty, proceeding with creation")
        Market.load_ticker_metadata("./data/ticker_metadata.csv", 300)
    else:
        print("Market metadata already exists, no need to load from csv")


    app.run(debug=True)
