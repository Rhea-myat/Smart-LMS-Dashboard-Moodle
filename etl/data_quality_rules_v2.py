import pandas as pd
import re

def remove_duplicates(df, dataset_name="dataset"):
    before = len(df)
    df = df.drop_duplicates()
    after = len(df)
    removed = before - after

    print(f"Removed {removed} duplicate rows from {dataset_name}.")
    print(f"DataFrame shape before removing duplicates: {before}, after: {after}")
    return df

def standardise_column_names(df):
    df = df.copy()

    df.columns = [
        re.sub(r"_+", "_", re.sub(r"[^a-zA-Z0-9]+", "_", str(col).strip().lower())).strip("_")
        for col in df.columns
    ]

    return df

def rename_result_columns(results):
    """
    Rename ambiguous result columns to meaningful names.
    """

    return results.rename(columns={
        "delay_days": "assignment_1_delay_days",
        "delay_days_1": "assignment_2_delay_days"
    })

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

def filter_valid_student_records(results):
    results = results.copy()

    id_col = "person_id" if "person_id" in results.columns else "Person Id"

    results[id_col] = pd.to_numeric(results[id_col], errors="coerce")
    results = results[results[id_col].notna()]
    results[id_col] = results[id_col].astype(int).astype(str)

    return results

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


def handle_missing_enrolment_values(enrolments):
    enrolments = enrolments.copy()

    enrolments = enrolments[
        enrolments["student_id"].notna() &
        enrolments["course_id"].notna()
    ]

    if "enrolment_status" in enrolments.columns:
        enrolments["enrolment_status"] = enrolments["enrolment_status"].fillna("unknown")

    return enrolments



