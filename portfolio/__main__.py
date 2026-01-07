

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


if __name__ == "__main__":

    app.run(debug=True)
