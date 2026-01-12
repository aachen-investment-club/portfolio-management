from flask import Flask
from flask_cors import CORS
from flask_caching import Cache
from flask_session import Session 

from dotenv import load_dotenv

load_dotenv()

config = {
    "CACHE_TYPE": "SimpleCache", # Use 'FileSystemCache' if you want it to survive server restarts
    "CACHE_DEFAULT_TIMEOUT": 300
}
app = Flask(__name__)
app.secret_key = "super-secret-key"  
app.config["SESSION_TYPE"] = "filesystem" 

Session(app) 

cache = Cache(app, config=config)
CORS(app)

import utils.aws_config
import routes
import backend

if __name__ == "__main__":
    app.run(debug=True)