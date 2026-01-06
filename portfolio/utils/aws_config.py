from sqlalchemy import create_engine
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

# engine = create_engine("sqlite:///app.db")
engine = create_engine("sqlite:///market.db", echo=False)
