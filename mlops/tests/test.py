import sys
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

sys.path.append(str(BASE_DIR))
from etl.data_quality_rules import check_required_columns, clean_results_header, filter_valid_student_records, handle_missing_values, remove_duplicates, standardise_column_names
from tests.etl_test import check_duplicates, check_student_matching, checks_missing_values, load_data, standardise_student_id, write_log

def generate_matching_log(logs, results):
    log_ids = set(logs["studentid_clean"])
    result_ids = set(results["studentid_clean"])

    all_ids = log_ids.union(result_ids)

    reconciliation = []

    for sid in all_ids:
        reconciliation.append({
            "student_id": sid,
            "in_logs": sid in log_ids,
            "in_results": sid in result_ids,
            "matching_status":
                "matched" if sid in log_ids and sid in result_ids
                else "log_only" if sid in log_ids
                else "result_only"
        })

    return pd.DataFrame(reconciliation)

if __name__ == "__main__":
    write_log("Starting ETL tests.")
    logs, results = load_data() 

    print("Before:", results.shape)
    results = filter_valid_student_records(results)
    print("After:", results.shape)


    checks_missing_values(logs, "logs")
    checks_missing_values(results, "results")
    print(results[results["Person Id"].isnull()])

    check_duplicates(logs, "logs")
    check_duplicates(results, "results")

    standardised_ids = standardise_student_id(results["Person Id"])
    print(standardised_ids.head())

    check_student_matching(logs, results)

    remove_duplicates(results, "results")
    remove_duplicates(logs, "logs")

    logs = standardise_column_names(logs)
    results = standardise_column_names(results)

    results = results.rename(columns={
        "delay_days": "assignment_1_delay_days",
        "delay_days_1": "assignment_2_delay_days"
    })

    required_log_columns = [
        "time",
        "user_full_name",
        "username",
        "event_context",
        "component",
        "event_name",
        "description"
    ]

    required_result_columns = [
        "person_id",
        "surname",
        "mark",
        "grade",
        "ass_ex_1",
        "ass_ex_2",
        "ass_ex_3",
        "ass_ex_4",
        "ass_ex_5",
        "ass_ex_6",
        "ass_ex_7",
        "ass_ex_8",
        "ass_ex_9",
        "ass_ex_10",
        "weekly_lab_quizzes_100",
        "assignment_1_100",
        "assignment_1_delay_days",
        "ass_1_with_penalty_100",
        "ass_2_100",
        "assignment_2_delay_days",
        "ass_2_with_penalty_100",
        "exam_100",
        "total_100",
        "rounded_total_100",
        "cal_g"
    ]

    print(results.columns.tolist())

        

  

    check_required_columns(logs, required_log_columns, "Moodle Logs")
    check_required_columns(results, required_result_columns, "Student Results")

    matching_log = generate_matching_log(logs, results)
    matching_log.to_csv(
    "logs/student_reconciliation_log.csv",
    index=False
)
    logs, results = handle_missing_values(logs, results)
    print("new logs shape:", logs.shape)
    print("new results shape:", results.shape)
    print("results preview:")
    print(results.head())
    print("logs preview:")
    print(logs.head())