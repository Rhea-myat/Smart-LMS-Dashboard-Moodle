import pandas as pd

def check_student_matching(logs, results):
    log_ids = set(logs["studentid_clean"].dropna())
    result_ids = set(results["studentid_clean"].dropna())

    matched = log_ids.intersection(result_ids)
    log_only = log_ids - result_ids
    result_only = result_ids - log_ids

    print("\nStudent Matching Result")
    print(f"Matched students: {len(matched)}")
    print(f"Students in logs only: {len(log_only)}")
    print(f"Students in results only: {len(result_only)}")

    return matched, log_only, result_only

def generate_matching_log(logs, results):
    log_ids = set(logs["studentid_clean"].dropna())
    result_ids = set(results["studentid_clean"].dropna())

    rows = []
    for sid in log_ids.union(result_ids):
        rows.append({
            "student_id": sid,
            "in_logs": sid in log_ids,
            "in_results": sid in result_ids,
            "matching_status":
                "matched" if sid in log_ids and sid in result_ids
                else "log_only" if sid in log_ids
                else "result_only"
        })

    return pd.DataFrame(rows)

def check_moodle_student_matching(students, enrolments, logs, grades):
    student_ids = set(students["student_id"].dropna())
    enrolment_ids = set(enrolments["student_id"].dropna())
    log_ids = set(logs["userid"].dropna())

    if grades.empty:
        grade_ids = set()
    else:
        grade_ids = set(grades["userid"].dropna())

    print("\nMoodle Student Matching Result")
    print(f"Students extracted: {len(student_ids)}")
    print(f"Students enrolled: {len(enrolment_ids)}")
    print(f"Students with logs: {len(log_ids.intersection(student_ids))}")
    print(f"Students with grades: {len(grade_ids.intersection(student_ids))}")

    return {
        "students_without_enrolment": student_ids - enrolment_ids,
        "enrolled_students_without_logs": enrolment_ids - log_ids,
        "enrolled_students_without_grades": enrolment_ids - grade_ids
    }
