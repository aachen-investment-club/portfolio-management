from sqlalchemy import create_engine
import os
"""
boto3.setup_default_session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

url = f"awsathena+rest://" + \
    f"{os.getenv("AWS_ACCESS_KEY_ID")}" + \
    f":{os.getenv("AWS_SECRET_ACCESS_KEY")}" + \
    f"@{os.getenv("AWS_REGION")}" + \
    f"/{os.getenv("AWS_ATHENA_DB")}" + \
    f"?s3_staging_dir={os.getenv("AWS_S3_STAGING_DIR")}"

"""

# Database path configurable via environment variable
# For local development: sqlite:///market.db (relative to working directory)
# For production (EC2 host): sqlite:////data/market.db (absolute path to host-mounted volume)
DB_PATH = os.getenv("DB_PATH", "sqlite:///market.db")
engine = create_engine(DB_PATH, echo=False)
