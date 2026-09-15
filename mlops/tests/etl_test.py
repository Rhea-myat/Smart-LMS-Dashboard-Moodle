import pandas as pd 
from datetime import datetime 
from pathlib import Path

from etl.data_quality_rules import extract_student_id_from_username, filter_valid_student_records

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "data/raw"
LOG_DIR = BASE_DIR / "logs"  
LOG_DIR.mkdir(exist_ok=True)



def write_log(message): 
    with open(LOG_DIR/ "etl_test_log.txt", "a") as f: 
        f.write(f"{datetime.now()}: {message}\n")


def load_data(): 
    logs = pd.read_excel(RAW_DIR / "ICT001 S1 2025 Logs RELEASED V1.0.xlsx")
    results = pd.read_excel(RAW_DIR / "cleaned_standard_results.xlsx")

    write_log(f"Moodle logs loaded: {len(logs)} rows")
    write_log(f"Results data loaded: {len(results)} rows")

    return logs, results


def checks_missing_values(df, df_name): 
    # ignore ip_address column for missing value check
    if "ip_address" in df.columns:
        df = df.drop(columns=["ip_address"])
        write_log(f"Ignored 'ip_address' column for missing value check in {df_name}.")
    missing = df.isnull().sum()
    if missing.sum() == 0: 
        write_log(f"No missing values in {df_name}.")
        write_log(f"Missing value check for {df_name} passed.")
    else:
        write_log(f"Missing values in {df_name}: {missing.sum()} total")
        write_log(f"Missing values by column in {df_name}:\n{missing}")
    return missing


def check_duplicates(df, name):
    duplicate_count = df.duplicated().sum()
    print(f"\nDuplicate rows in {name}: {duplicate_count}")
    duplicates = df[df.duplicated(keep=False)]
    print(f"Duplicate rows in {name}:\n{duplicates}")
    write_log(f"Duplicate check completed for {name}: {duplicate_count} duplicates")


def standardise_student_id(series):
    return (
        series.astype(str)
        .str.strip()
        .str.replace(".0", "", regex=False)
    )

def check_student_matching(logs, results):
    logs["StudentID_Clean"] = extract_student_id_from_username(logs["Username"])
    results["StudentID_Clean"] = standardise_student_id(results["Person Id"])

    log_ids = set(logs["StudentID_Clean"].dropna())
    result_ids = set(results["StudentID_Clean"].dropna())

    matched = log_ids.intersection(result_ids)
    log_only = log_ids - result_ids
    result_only = result_ids - log_ids

    print("\nStudent Matching Result")
    print(f"Matched students: {len(matched)}")
    print(f"Students in logs only: {len(log_only)}")
    print(f"Students in results only: {len(result_only)}")
    write_log(f"Matched students: {len(matched)}")
    write_log(f"Log-only students: {len(log_only)}")
    write_log(f"Result-only students: {len(result_only)}")


"""
def main():
    write_log("Starting ETL tests.")
    logs, results = load_data() 

    print("Before:", results.shape)
    results = filter_valid_student_records(results)
    print("After:", results.shape)

    checks_missing_values(logs, "logs")
    checks_missing_values(results, "results")

    check_duplicates(logs, "logs")
    check_duplicates(results, "results")

    standardised_ids = standardise_student_id(results["Person Id"])
    print(standardised_ids.head())

    check_student_matching(logs, results)

"""

#if __name__ == "__main__":    main()
    


   
