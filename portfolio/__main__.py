from flask import Flask
from flask_cors import CORS
from flask_caching import Cache

from dotenv import load_dotenv

load_dotenv()

config = {
    "CACHE_TYPE": "SimpleCache", # Use 'FileSystemCache' if you want it to survive server restarts
    "CACHE_DEFAULT_TIMEOUT": 300
}
app = Flask(__name__)
cache = Cache(app, config=config)
CORS(app)


from portfolio.utils import aws_config
from portfolio import routes, backend


if __name__ == "__main__":
    app.run(debug=True)