import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from etl.extract import extract_data, load_to_staging
from etl.data_quality_rules_v2 import (
    standardise_column_names,
    filter_valid_student_records,
    remove_duplicates,
    handle_missing_values,
    check_required_columns,
    extract_student_id_from_username,
    standardise_student_id
)
from etl.reconcile_datasets import check_student_matching, generate_matching_log

RAW_DIR = BASE_DIR / "data" / "raw"
STAGING_DIR = BASE_DIR / "data" / "staging"
LOG_DIR = BASE_DIR / "logs"

logs = extract_data(RAW_DIR / "ICT001 S1 2025 Logs RELEASED V1.0.xlsx")
results = extract_data(RAW_DIR / "cleaned_standard_results.xlsx")

load_to_staging(logs, STAGING_DIR / "logs.csv")
load_to_staging(results, STAGING_DIR / "results.csv")

logs = standardise_column_names(logs)
results = standardise_column_names(results)


results = filter_valid_student_records(results)

logs, results = handle_missing_values(logs, results)

logs = remove_duplicates(logs, "logs")
results = remove_duplicates(results, "results")

logs["studentid_clean"] = extract_student_id_from_username(logs["username"])
results["studentid_clean"] = standardise_student_id(results["person_id"])

required_log_columns = ["time", "user_full_name", "username", "event_context", "component", "event_name", "description"]
required_result_columns = ["person_id", "surname", "mark", "grade"]

check_required_columns(logs, required_log_columns, "Moodle Logs")
check_required_columns(results, required_result_columns, "Student Results")

check_student_matching(logs, results)

matching_log = generate_matching_log(logs, results)
LOG_DIR.mkdir(exist_ok=True)
matching_log.to_csv(LOG_DIR / "student_reconciliation_log.csv", index=False)

print("ETL Phase 1 completed.")