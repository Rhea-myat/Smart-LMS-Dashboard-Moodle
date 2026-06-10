import pandas as pd 
from datetime import datetime 
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "data/raw"
LOG_DIR = BASE_DIR / "logs"  
LOG_DIR.mkdir(exist_ok=True)



def write_log(message): 
    with open(LOG_DIR/ "etl_test_log.txt", "a") as f: 
        f.write(f"{datetime.now()}: {message}\n")


def load_data(): 
    logs = pd.read_excel(RAW_DIR / "ICT001 S1 2025 Logs RELEASED V1.0.xlsx")
    results = pd.read_excel(RAW_DIR / "ICT001_S1_2025_RESULTS_ALL_MARKS_RELEASED_v1.0[6076970].xlsx")

    write_log(f"Moodle logs loaded: {len(logs)} rows")
    write_log(f"Results data loaded: {len(results)} rows")

    return logs, results


if __name__ == "__main__":
    write_log("Starting ETL test.")
    try: 
        df = pd.read_excel(RAW_DIR / "ICT001 S1 2025 Logs RELEASED V1.0.xlsx")
        write_log("Successfully read test data.")
    except Exception as e: 
        write_log(f"Error reading test data: {e}")
        raise e





   
