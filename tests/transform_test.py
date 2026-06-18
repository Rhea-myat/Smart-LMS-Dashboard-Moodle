import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from etl.extract import extract_data
from etl.data_quality_rules_v2 import (
    standardise_column_names,
    rename_result_columns,
    filter_valid_student_records,
    remove_duplicates,
    handle_missing_values,
    extract_student_id_from_username,
    standardise_student_id
)
from etl.transform import create_dim_assessment, create_dim_student, create_dim_time

RAW_DIR = BASE_DIR / "data" / "raw"
WAREHOUSE_DIR = BASE_DIR / "data" / "warehouse"
WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)

logs = extract_data(RAW_DIR / "ICT001 S1 2025 Logs RELEASED V1.0.xlsx")
results = extract_data(RAW_DIR / "cleaned_standard_results.xlsx")

logs = standardise_column_names(logs)
results = standardise_column_names(results)
results = rename_result_columns(results)

results = filter_valid_student_records(results)
logs, results = handle_missing_values(logs, results)

logs = remove_duplicates(logs, "logs")
results = remove_duplicates(results, "results")

logs["studentid_clean"] = extract_student_id_from_username(logs["username"])
results["studentid_clean"] = standardise_student_id(results["person_id"])

dim_student = create_dim_student(logs, results)

print(dim_student.head())
print(dim_student.shape)
print("Student key unique:", dim_student["student_key"].is_unique)
print("Student ID missing:", dim_student["student_id"].isnull().sum())

dim_student.to_csv(WAREHOUSE_DIR / "dim_student.csv", index=False)
print("Saved:", WAREHOUSE_DIR / "dim_student.csv")

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

dim_time = create_dim_time(logs)
dim_course, course_lookup = create_dim_course(logs)
dim_event = create_dim_event(logs)
dim_material = create_dim_material(logs)
dim_assessment = create_dim_assessment(results)
dim_grade = create_dim_grade(results)
fact_activity_log = create_fact_activity_log(logs, dim_student, dim_time, dim_course, dim_event, dim_material, course_lookup)
fact_result = create_fact_result(results, dim_student, dim_course, dim_assessment, dim_grade)

print("StudentKey missing:", fact_activity_log["student_key"].isnull().sum())
print("CourseKey missing:", fact_activity_log["course_key"].isnull().sum())
print("EventKey missing:", fact_activity_log["event_key"].isnull().sum())
print("MaterialKey missing:", fact_activity_log["material_key"].isnull().sum())
print("TimeKey missing:", fact_activity_log["time_key"].isnull().sum())

print("Original log rows:", len(logs))
print("Fact rows:", len(fact_activity_log))

dim_time.to_csv(WAREHOUSE_DIR / "dim_time.csv", index=False)
dim_course.to_csv(WAREHOUSE_DIR / "dim_course.csv", index=False)
dim_event.to_csv(WAREHOUSE_DIR / "dim_event.csv", index=False)
dim_material.to_csv(WAREHOUSE_DIR / "dim_material.csv", index=False)
dim_assessment.to_csv(WAREHOUSE_DIR / "dim_assessment.csv", index=False)    
dim_grade.to_csv(WAREHOUSE_DIR / "dim_grade.csv", index=False)
fact_activity_log.to_csv(WAREHOUSE_DIR / "fact_activity_log.csv", index=False)
fact_result.to_csv(WAREHOUSE_DIR / "fact_result.csv", index=False)
print("StudentKey missing:", fact_result["student_key"].isnull().sum())
print("AssessmentKey missing:", fact_result["assessment_key"].isnull().sum())
print("GradeKey missing:", fact_result["grade_key"].isnull().sum())

print(results["grade"].unique())
print(dim_grade["grade_code"].unique())