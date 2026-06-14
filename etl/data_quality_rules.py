import pandas as pd
import re

def clean_results_header(file_path):
    """Clean historical result file where the actual headers are not in the first row. This function identifies the correct header row and sets it as the DataFrame's columns.  

    Args:
        file_path (str): The path to the Excel file.

    Returns:
        pd.DataFrame: The cleaned DataFrame with the correct headers.
    """
    preview = pd.read_excel(file_path, header=None, nrows=10)
    print("Preview of first 10 rows:")
    print(preview)
    header_row = 2

    results = pd.read_excel(file_path, header=header_row)
    export_clean_results(results, "data/raw/cleaned_standard_results.xlsx")

    return results

# export clean results_header in excle file 
def export_clean_results(results, file_path):
    """Export the cleaned results DataFrame to an Excel file.

    Args:
        results (pd.DataFrame): The cleaned results DataFrame.
        file_path (str): The path where the cleaned Excel file will be saved.
    """
    results.to_excel(file_path, index=False)

def filter_valid_student_records(results):
    """
    Remove non-student records from historical results exports.
    """
    results = results.copy()
    results["Person Id"] = pd.to_numeric(results["Person Id"], errors="coerce")
    results = results[results["Person Id"].notna()]
    results["Person Id"] = results["Person Id"].astype(int).astype(str) 
    return results

def remove_duplicates(df, dataset_name="dataset"):
    before = len(df)
    df = df.drop_duplicates()
    after = len(df)
    removed = before - after

    print(f"Removed {removed} duplicate rows from {dataset_name}.")
    print(f"DataFrame shape before removing duplicates: {before}, after: {after}")
    return df

def standardise_student_id(series):
    return (
        series.astype(str)
        .str.strip()
        .str.replace(".0", "", regex=False)
    )
def extract_student_id_from_username(series):
    return (
        series.astype(str)
        .str.strip()
        .str.split("@")
        .str[0]
    )



def standardise_column_names(df):
    df = df.copy()

    df.columns = [
        re.sub(r"_+", "_", re.sub(r"[^a-zA-Z0-9]+", "_", str(col).strip().lower())).strip("_")
        for col in df.columns
    ]

    return df

def check_required_columns(df, required_columns, dataset_name):
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        print(f"{dataset_name} missing columns: {missing_columns}")
        return False

    print(f"{dataset_name} required columns check passed.")
    return True

def handle_missing_values(logs, results):
    logs = logs.copy()
    results = results.copy()
    # because not needed for analytics
    if "ip_address" in logs.columns:
        logs = logs.drop(columns=["ip_address"])

    # missing delay means no delay
    delay_columns = [
        "assignment_1_delay_days",
        "assignment_2_delay_days"
    ]

    for col in delay_columns:
        if col in results.columns:
            results[col] = results[col].fillna(0)

    # Missing marks are preserved as NaN for later investigation/model handling

    # Critical IDs must exist
    if "username" in logs.columns:
        logs = logs[logs["username"].notna()]

    if "person_id" in results.columns:
        results = results[results["person_id"].notna()]

    return logs, results

def main():
    results = clean_results_header("data/raw/ICT001_S1_2025_RESULTS_ALL_MARKS_RELEASED_v1.0[6076970].xlsx")
    results = filter_valid_student_records(results)
    print(results.head())

if __name__ == "__main__":
    results = clean_results_header("data/raw/ICT001_S1_2025_RESULTS_ALL_MARKS_RELEASED_v1.0[6076970].xlsx")
    results = filter_valid_student_records(results)
    print(results.head())

