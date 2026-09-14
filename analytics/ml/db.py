import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()


def get_ml_engine():
    host = os.getenv("ML_DB_HOST", os.getenv("DB_HOST", "127.0.0.1"))
    port = os.getenv("ML_DB_PORT", os.getenv("DB_PORT", "3306"))
    name = os.getenv("ML_DB_NAME", "ml_db")
    user = os.getenv("ML_DB_USER", os.getenv("DB_USER"))
    password = os.getenv("ML_DB_PASSWORD", os.getenv("DB_PASSWORD", ""))

    password = quote_plus(password)

    return create_engine(
        f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"
    )