from sqlalchemy import create_engine

def get_engine():
    return create_engine(
        "mysql+pymysql://root:root@localhost:8889/analytics_db"
    )