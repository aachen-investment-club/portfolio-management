from flask_caching import Cache
from authlib.integrations.flask_client import OAuth

cache = Cache()

oauth = OAuth()