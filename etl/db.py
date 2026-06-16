from sqlalchemy import create_engine

def get_engine():
    return create_engine(
        #"mysql+pymysql://root:root@localhost:8889/analytics_db"
        "mysql+pymysql://ft04user:Asdfg09876@127.0.0.1:3306/analytics_db"
    )