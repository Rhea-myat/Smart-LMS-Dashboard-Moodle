import datetime
from pathlib import Path
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)


def write_log(message): 
    with open(LOG_DIR / "etl_test_log.txt", "a") as f: 
        f.write(f"{datetime.datetime.now()}: {message}\n")