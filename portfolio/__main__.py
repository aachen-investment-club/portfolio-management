from flask import Flask
from flask_cors import CORS

from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

import routes
import backend

if __name__ == "__main__":
    app.run(debug=True)