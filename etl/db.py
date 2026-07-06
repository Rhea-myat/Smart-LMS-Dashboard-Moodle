from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv()

"""
def get_engine():
    return create_engine(
        #"mysql+pymysql://root:root@localhost:8889/analytics_db"
        "mysql+pymysql://ft04user:Asdfg09876@127.0.0.1:3306/analytics_db"
    )
"""


def get_engine(db_name=None):
    if db_name is None:
        db_name = os.getenv("DB_NAME")

    return create_engine(
        f"mysql+pymysql://"
        f"{os.getenv('DB_USER')}:"
        f"{os.getenv('DB_PASSWORD')}@"
        f"{os.getenv('DB_HOST')}:"
        f"{os.getenv('DB_PORT')}/"
        f"{db_name}"
    )