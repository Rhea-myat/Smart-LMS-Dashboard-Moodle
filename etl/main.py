import pandas as pd

from etl.extract import BASE_DIR, extract_data
from etl.transform import (
    create_dim_student,
    create_dim_time,
    create_dim_academic_period,
    lookup_academic_period_key,
    parse_academic_period_from_label,
    create_dim_course_from_historical_logs,
    create_dim_event,
    create_dim_material,
    create_dim_assessment,
    create_dim_grade,
    create_fact_activity_log_from_historical,
    create_fact_result,
    create_fact_enrolment
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
from etl.data_quality_rules import validate_academic_period_integrity
from etl.logging_utils import write_log
from etl.reconcile_datasets import check_student_matching, generate_matching_log



def main():
    logs_path = BASE_DIR / "data" / "raw" / "ICT001 S1 2025 Logs RELEASED V1.0.xlsx"
    results_path = BASE_DIR / "data" / "raw" / "cleaned_standard_results.xlsx"
    source_label = logs_path.stem

    warehouse_path = BASE_DIR / "data" / "warehouse"
    warehouse_path.mkdir(parents=True, exist_ok=True)

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

    # Historical ETL: the source dataset determines the academic period.
    source_semester, source_academic_year = parse_academic_period_from_label(
        source_label
    )

    dim_student = create_dim_student(logs, results)
    dim_time = create_dim_time(logs)
    dim_academic_period = create_dim_academic_period(
        source_semester,
        source_academic_year
    )

    historical_academic_period_key = lookup_academic_period_key(
        dim_academic_period,
        source_semester,
        source_academic_year
    )

    # Daily production ETL path:
    # 1) ask Moodle for current semester / teaching period / academic year
    # 2) if Moodle is unavailable, fall back to the date-based lookup below
    # production_academic_period_key = resolve_academic_period_key(
    #     dim_academic_period,
    #     current_semester,
    #     current_academic_year
    # )
    # production_academic_period_key = resolve_academic_period_from_date(
    #     dim_academic_period,
    #     pd.Timestamp.today().date()
    # )

    dim_course, course_lookup = create_dim_course_from_historical_logs(logs)
    dim_event = create_dim_event(logs)
    dim_material = create_dim_material(logs)
    dim_assessment = create_dim_assessment(results)
    dim_grade = create_dim_grade(results)

    fact_activity_log = create_fact_activity_log_from_historical(
        logs,
        dim_student,
        dim_time,
        historical_academic_period_key,
        dim_course,
        dim_event,
        dim_material,
        course_lookup
    )

    fact_result = create_fact_result(
        results,
        dim_student,
        dim_course,
        dim_assessment,
        dim_grade,
        historical_academic_period_key
    )

    fact_enrolment = create_fact_enrolment(
        logs,
        results,
        dim_student,
        dim_course,
        dim_time,
        historical_academic_period_key
    )

    validate_academic_period_integrity(
        dim_academic_period,
        fact_activity_log,
        fact_result,
        fact_enrolment
    )

    dim_student.to_csv(warehouse_path / "dim_student.csv", index=False)
    dim_time.to_csv(warehouse_path / "dim_time.csv", index=False)
    dim_academic_period.to_csv(warehouse_path / "dim_academic_period.csv", index=False)
    dim_course.to_csv(warehouse_path / "dim_course.csv", index=False)
    dim_event.to_csv(warehouse_path / "dim_event.csv", index=False)
    dim_material.to_csv(warehouse_path / "dim_material.csv", index=False)
    dim_assessment.to_csv(warehouse_path / "dim_assessment.csv", index=False)
    dim_grade.to_csv(warehouse_path / "dim_grade.csv", index=False)
    fact_activity_log.to_csv(warehouse_path / "fact_activity_log.csv", index=False)
    fact_result.to_csv(warehouse_path / "fact_result.csv", index=False)
    fact_enrolment.to_csv(warehouse_path / "fact_enrolment.csv", index=False)

    engine = get_engine()

    load_to_mysql_initial(dim_student, "dim_student", engine)
    load_to_mysql_initial(dim_time, "dim_time", engine)
    load_to_mysql_initial(dim_academic_period, "dim_academic_period", engine)
    load_to_mysql_initial(dim_course, "dim_course", engine)
    load_to_mysql_initial(dim_event, "dim_event", engine)
    load_to_mysql_initial(dim_material, "dim_material", engine)
    load_to_mysql_initial(dim_assessment, "dim_assessment", engine)
    load_to_mysql_initial(dim_grade, "dim_grade", engine)
    load_to_mysql_initial(fact_activity_log, "fact_activity_log", engine)
    load_to_mysql_initial(fact_result, "fact_result", engine)
    load_to_mysql_initial(fact_enrolment, "fact_enrolment", engine)


if __name__ == "__main__":
    main()