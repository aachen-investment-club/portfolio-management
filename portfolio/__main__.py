from flask import Flask
from flask_cors import CORS
from flask_caching import Cache
from authlib.integrations.flask_client import OAuth
import os 
from dotenv import load_dotenv

load_dotenv()

config = {
    "CACHE_TYPE": "SimpleCache", # Use 'FileSystemCache' if you want it to survive server restarts
    "CACHE_DEFAULT_TIMEOUT": 300
}
app = Flask(__name__)
oauth = OAuth(app)

app.secret_key = os.environ.get("FLASK_SECRET_KEY")

oauth.register(
  name='oidc',
  authority='https://cognito-idp.eu-central-1.amazonaws.com/eu-central-1_unKiHP6hh',
  client_id=os.getenv("COGNITO_CLIENT_ID"),
  client_secret=os.getenv("AWS_COGNI_CLIENT_SECRET"),
  server_metadata_url='https://cognito-idp.eu-central-1.amazonaws.com/eu-central-1_unKiHP6hh/.well-known/openid-configuration',
  client_kwargs={'scope': 'openid email'}
)

cache = Cache(app, config=config)
CORS(app)

import utils.aws_config
import routes
import backend

if __name__ == "__main__":
    app.run(debug=True)