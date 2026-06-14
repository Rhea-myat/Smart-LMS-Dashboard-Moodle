import datetime
from tests.etl_test import LOG_DIR


def write_log(message): 
    with open(LOG_DIR / "etl_test_log.txt", "a") as f: 
        f.write(f"{datetime.datetime.now()}: {message}\n")