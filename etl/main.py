from etl.extract import BASE_DIR, extract_data
from etl.transform import (
    create_dim_student,
    create_dim_time,
    create_dim_course,
    create_dim_event,
    create_dim_material,
    create_dim_assessment,
    create_dim_grade,
    create_fact_activity_log,
    create_fact_result
)
from etl.db import get_engine
from etl.load import load_to_mysql_initial
from etl.data_quality_rules_v2 import (
    standardise_column_names,
    rename_result_columns,
    extract_student_id_from_username,
    filter_valid_student_records,
    handle_missing_values,  
    check_required_columns,
    remove_duplicates
)
from etl.logging_utils import write_log
from etl.reconcile_datasets import check_student_matching, generate_matching_log


def main():
    logs_path = BASE_DIR / "data" / "raw" / "ICT001 S1 2025 Logs RELEASED V1.0.xlsx"
    results_path = BASE_DIR / "data" / "raw" / "cleaned_standard_results.xlsx"

    logs = extract_data(logs_path)
    results = extract_data(results_path)

    logs = standardise_column_names(logs)
    results = standardise_column_names(results)

    results = rename_result_columns(results)

    logs["studentid_clean"] = extract_student_id_from_username(logs["username"])
    results = filter_valid_student_records(results)
    results["studentid_clean"] = results["person_id"].astype(str).str.strip()

    logs, results = handle_missing_values(logs, results)

    logs = remove_duplicates(logs, "logs")
    results = remove_duplicates(results, "results")

    check_student_matching(logs, results)
    matching_log = generate_matching_log(logs, results)

    dim_student = create_dim_student(logs, results)
    dim_time = create_dim_time(logs)
    dim_course = create_dim_course(logs)
    dim_event = create_dim_event(logs)
    dim_material = create_dim_material(logs)
    dim_assessment = create_dim_assessment(results)
    dim_grade = create_dim_grade(results)

    fact_activity_log = create_fact_activity_log(
        logs,
        dim_student,
        dim_time,
        dim_course,
        dim_event,
        dim_material
    )

    fact_result = create_fact_result(
        results,
        dim_student,
        dim_course,
        dim_assessment,
        dim_grade
    )

    engine = get_engine()

    load_to_mysql_initial(dim_student, "dim_student", engine)
    load_to_mysql_initial(dim_time, "dim_time", engine)
    load_to_mysql_initial(dim_course, "dim_course", engine)
    load_to_mysql_initial(dim_event, "dim_event", engine)
    load_to_mysql_initial(dim_material, "dim_material", engine)
    load_to_mysql_initial(dim_assessment, "dim_assessment", engine)
    load_to_mysql_initial(dim_grade, "dim_grade", engine)
    load_to_mysql_initial(fact_activity_log, "fact_activity_log", engine)
    load_to_mysql_initial(fact_result, "fact_result", engine)


if __name__ == "__main__":
    main()