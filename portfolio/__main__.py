import sentry_sdk
import os
from dotenv import load_dotenv

load_dotenv()

#: its important to initialize here for more complete reports. 
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    send_default_pii=True,
)

from portfolio.models.market import Market, DB_GRANULARITY
from portfolio.utils.aws_config import engine #, minute_engine
from portfolio.schemas.market import Base #, MarketMinuteDB

#from portfolio.utils.aws_config import engine
Base.metadata.create_all(engine)
#MarketMinuteDB.__table__.create(minute_engine, checkfirst=True)

from flask import Flask
from flask_cors import CORS

from portfolio.extensions import cache, oauth
from portfolio.routes import bp
from portfolio.backend import bp_api


app = Flask(__name__)


CORS(app)

oauth.init_app(app)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")

# Cognito configuration via environment variables
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "eu-central-1_unKiHP6hh")
COGNITO_REGION = os.getenv("AWS_REGION", "eu-central-1")
MINUTE_DATA_SOURCE = os.getenv("MINUTE_DATA_SOURCE", "local")

oauth.register(
  name='oidc',
  authority=f'https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}',
  client_id=os.getenv("COGNITO_CLIENT_ID"),
  client_secret=os.getenv("AWS_COGNI_CLIENT_SECRET"),
  server_metadata_url=f'https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/openid-configuration',
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

    if Market.check_meta_empty():
        print("market metadata empty, proceeding with creation")
        Market.load_ticker_metadata("./data/ticker_metadata.csv", 300)
    else:
        print("Market metadata already exists, no need to load from csv")

    if Market.check_empty():
        if DB_GRANULARITY == "day":
            print("market empty, proceeding with creation (from CSV)")
            Market.load_from_csv("./data/sp500_close_extended.csv", chunks_dev)

        elif DB_GRANULARITY == "minute" and MINUTE_DATA_SOURCE=="local":
            #: only update on startup in the local case, never in the athena case. 
            print("market empty, proceeding with creation (from YF)")
            Market.update_market()
    
    if Market.check_forex_empty():
        print("forex empty, proceeding with creation (from YF)")
        if not (DB_GRANULARITY == "minute" and MINUTE_DATA_SOURCE=="athena"):
            #: this handles granularity automatically.
            #; never update on startup for the athena case. 
            Market.update_forex(chunks_dev)
        

    else:

        print("Market already exists, no need to load from csv")



    app.run(debug=True)
