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

    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    missing = []
    if not user:
        missing.append("DB_USER")
    if password is None:
        missing.append("DB_PASSWORD")
    if not host:
        missing.append("DB_HOST")
    if not port:
        missing.append("DB_PORT")
    if not db_name:
        missing.append("DB_NAME")
    if missing:
        raise ValueError(f"Missing required analytics DB env vars: {', '.join(missing)}")

    return create_engine(
        f"mysql+pymysql://"
        f"{user}:"
        f"{password}@"
        f"{host}:"
        f"{port}/"
        f"{db_name}"
    )


def _first_env_value(*keys, default=None):
    for key in keys:
        value = os.getenv(key)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return default


def get_source_engine():
    source_db_name = _first_env_value(
        "MOODLE_DB_NAME",
        "SOURCE_DB_NAME",
        "Moodle_DB_Name",
    )
    source_host = _first_env_value("MOODLE_DB_HOST", "SOURCE_DB_HOST", "DB_HOST", default="127.0.0.1")
    source_port = _first_env_value("MOODLE_DB_PORT", "SOURCE_DB_PORT", "DB_PORT", default="3306")
    source_user = _first_env_value("MOODLE_DB_USER", "SOURCE_DB_USER", "DB_USER")
    source_password = _first_env_value("MOODLE_DB_PASSWORD", "SOURCE_DB_PASSWORD", "DB_PASSWORD", default="")

    missing = []
    if not source_user:
        missing.append("MOODLE_DB_USER or SOURCE_DB_USER")
    if not source_host:
        missing.append("MOODLE_DB_HOST or SOURCE_DB_HOST")
    if not source_port:
        missing.append("MOODLE_DB_PORT or SOURCE_DB_PORT")
    if not source_db_name:
        missing.append("MOODLE_DB_NAME or SOURCE_DB_NAME")
    if missing:
        raise ValueError(f"Missing required source DB env vars: {', '.join(missing)}")

    return create_engine(
        f"mysql+pymysql://{source_user}:{source_password}@{source_host}:{source_port}/{source_db_name}"
    )