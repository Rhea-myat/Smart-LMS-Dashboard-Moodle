import pandas as pd
import re


def filter_logs_to_students(logs, student_ids):
    """Keep only log rows related to student users."""
    filtered_logs = logs.copy()

    if "userid" in filtered_logs.columns:
        filtered_logs["userid"] = pd.to_numeric(filtered_logs["userid"], errors="coerce")
    if "relateduserid" in filtered_logs.columns:
        filtered_logs["relateduserid"] = pd.to_numeric(filtered_logs["relateduserid"], errors="coerce")

    mask_user = filtered_logs["userid"].isin(student_ids) if "userid" in filtered_logs.columns else pd.Series(False, index=filtered_logs.index)
    mask_related = filtered_logs["relateduserid"].isin(student_ids) if "relateduserid" in filtered_logs.columns else pd.Series(False, index=filtered_logs.index)

    return filtered_logs[mask_user | mask_related].copy()

# 1. Student dimension
def create_dim_time_from_moodle_logs(logs):
    dim_time = logs[["timecreated"]].drop_duplicates().copy()

    dim_time["datetime"] = pd.to_datetime(
        dim_time["timecreated"],
        unit="s",
        errors="coerce"
    )

    dim_time = dim_time[dim_time["datetime"].notna()]

    dim_time["time"] = dim_time["datetime"].dt.strftime("%d/%m/%y, %H:%M:%S")
    dim_time["date"] = dim_time["datetime"].dt.date
    dim_time["hour"] = dim_time["datetime"].dt.hour
    dim_time["day"] = dim_time["datetime"].dt.day_name()
    dim_time["week"] = dim_time["datetime"].dt.isocalendar().week.astype(int)
    dim_time["month"] = dim_time["datetime"].dt.month
    dim_time["year"] = dim_time["datetime"].dt.year

    dim_time.insert(0, "time_key", range(1, len(dim_time) + 1))

    return dim_time[
        ["time_key", "time", "datetime", "date", "hour", "day", "week", "month", "year", "timecreated"]
    ]

# 2. time dimension
def create_dim_event_from_moodle_logs(logs):
    dim_event = logs[
        ["eventname", "component", "action", "target", "crud"]
    ].drop_duplicates().copy()

    dim_event = dim_event.rename(columns={
        "eventname": "event_name"
    })

    dim_event.insert(0, "event_key", range(1, len(dim_event) + 1))

    return dim_event

# lookup helper function 
def lookup_academic_period_key(
    dim_academic_period,
    semester,
    academic_year
):
    if isinstance(academic_year, str):
        year_parts = re.findall(r"\d{4}", academic_year)
        if year_parts:
            academic_year = int(year_parts[-1])

    match = dim_academic_period[
        (dim_academic_period["semester"] == semester)
        &
        (dim_academic_period["academic_year"] == academic_year)
    ]

    if match.empty:
        raise ValueError(
            f"Academic period not found: {semester} {academic_year}"
        )

    return int(match.iloc[0]["academic_period_key"])

# 3A . Academic period dimension for ETL - ask Moodle for current semester and academic year in production ETL path
def create_dim_academic_period(
        semester,
        academic_year
    ):
    if isinstance(academic_year, str):
        year_parts = re.findall(r"\d{4}", academic_year)
        if year_parts:
            academic_year = int(year_parts[-1])

    return pd.DataFrame({
        "academic_period_key": [1],
        "semester": [semester],
        "academic_year": [academic_year]
    })

#3B.  parse semester and academic year from source label (Historical ETL path)
def parse_academic_period_from_label(source_label):
    """
    Historical ETL path: derive semester and academic year from the dataset label.

    Example: 'ICT302 S1 2025' -> semester='S1', academic_year=2025
    """
    match = re.search(
        r"(S1|S2).*?(\d{4})",
        str(source_label).upper())
    if not match:
        raise ValueError(
            f"Could not parse semester and academic year from source label: {source_label}"
        )

    return match.group(1), int(match.group(2))

# 4A. Historical course dimension
def create_dim_course_from_historical_logs(logs):
    course_lookup = logs[
        logs["event_context"].astype(str).str.startswith("Unit:", na=False)
    ][["event_context"]].drop_duplicates().copy()

    course_lookup["course_name"] = (
        course_lookup["event_context"]
        .str.replace("Unit:", "", regex=False)
        .str.strip()
    )

    course_lookup["course_code"] = (
        course_lookup["course_name"]
        .str.extract(r"([A-Z]{3}\d{3})", expand=False)
    )

    course_lookup["course_id"] = (
        "HIST_" + course_lookup["course_code"].fillna("UNKNOWN")
    )

    course_lookup.insert(0, "course_key", range(1, len(course_lookup) + 1))

    dim_course = course_lookup[
        ["course_key", "course_id", "course_name", "course_code"]
    ].copy()

    return dim_course, course_lookup[["course_key", "course_id", "event_context"]]

# 4B. Future Moodle course dimension
def create_dim_course_from_moodle_courses(courses):
    dim_course = courses[
        ["id", "fullname", "shortname"]
    ].drop_duplicates().copy()

    dim_course = dim_course.rename(columns={
        "id": "course_id",
        "fullname": "course_name",
        "shortname": "course_code"
    })

    dim_course.insert(0, "course_key", range(1, len(dim_course) + 1))

    dim_course = dim_course[
        ["course_key", "course_id", "course_name", "course_code"]
    ]

    return dim_course

# 5. event dimension
def create_dim_event(logs):
    dim_event = logs[["event_name"]].drop_duplicates().copy()

    dim_event.insert(0, "event_key", range(1, len(dim_event) + 1))

    return dim_event

# 6. material dimension
def create_dim_material_from_moodle_logs(logs):
    dim_material = logs[
        ["component", "target", "objecttable"]
    ].drop_duplicates().copy()

    def classify_material(row):
        component = str(row["component"]).lower()
        target = str(row["target"]).lower()
        objecttable = str(row["objecttable"]).lower()

        if "assign" in component or "assign" in objecttable:
            return "Assignment"
        elif "quiz" in component or "quiz" in objecttable:
            return "Quiz"
        elif "forum" in component or "forum" in objecttable:
            return "Forum"
        elif "resource" in component or "file" in target:
            return "Lecture Material"
        elif "course" in component:
            return "Course Page"
        else:
            return "Other"

    dim_material["material_type"] = dim_material.apply(classify_material, axis=1)
    dim_material["context"] = dim_material["target"]

    dim_material.insert(0, "material_key", range(1, len(dim_material) + 1))

    return dim_material

# 7. Assessment dimension
def create_dim_assessment_from_moodle_grades(grades):
    if grades.empty:
        return pd.DataFrame(columns=[
            "assessment_key", "assessment_id", "assessment_name", "assessment_type"
        ])

    if {"itemid", "itemname", "itemtype"}.issubset(grades.columns):
        dim_assessment = grades[
            ["itemid", "itemname", "itemtype"]
        ].drop_duplicates().copy()

        dim_assessment = dim_assessment.rename(columns={
            "itemid": "assessment_id",
            "itemname": "assessment_name",
            "itemtype": "assessment_type"
        })

        # Ensure every Moodle assessment has a stable, non-empty display label.
        dim_assessment["assessment_name"] = dim_assessment["assessment_name"].fillna("").astype(str).str.strip()
        missing_name_mask = dim_assessment["assessment_name"] == ""
        if missing_name_mask.any():
            dim_assessment.loc[missing_name_mask, "assessment_name"] = (
                "Assessment " + dim_assessment.loc[missing_name_mask, "assessment_id"].astype(str)
            )
    else:
        dim_assessment = grades[["itemname"]].drop_duplicates().copy()
        dim_assessment = dim_assessment.rename(columns={
            "itemname": "assessment_name"
        })
        dim_assessment.insert(0, "assessment_id", range(1, len(dim_assessment) + 1))
        dim_assessment["assessment_type"] = "moodle_grade_item"

    dim_assessment.insert(0, "assessment_key", range(1, len(dim_assessment) + 1))

    return dim_assessment


def normalize_moodle_assessment_scores(fact):
    fact = fact.copy()
    fact["assessment_score"] = pd.to_numeric(fact.get("finalgrade"), errors="coerce")

    # Moodle module grades can use arbitrary scales (for example quiz out of 10).
    # Convert to percentage before downstream pass/fail feature logic (>= 50).
    if "grademax" in fact.columns:
        grademax = pd.to_numeric(fact["grademax"], errors="coerce")
        valid_scale_mask = fact["assessment_score"].notna() & grademax.notna() & (grademax > 0)
        fact.loc[valid_scale_mask, "assessment_score"] = (
            fact.loc[valid_scale_mask, "assessment_score"]
            / grademax.loc[valid_scale_mask]
            * 100.0
        )

    if "due_timestamp" not in fact.columns:
        return fact

    due_ts = pd.to_numeric(fact["due_timestamp"], errors="coerce")
    now_ts = pd.Timestamp.utcnow().timestamp()
    overdue_mask = due_ts.notna() & (due_ts > 0) & (due_ts <= now_ts)

    itemtype = fact.get("itemtype", "").fillna("").astype(str).str.lower()
    itemmodule = fact.get("itemmodule", "").fillna("").astype(str).str.lower()
    has_finished_attempt = pd.to_numeric(fact.get("has_finished_attempt", 0), errors="coerce").fillna(0).astype(int)
    has_submission = pd.to_numeric(fact.get("has_submission", 0), errors="coerce").fillna(0).astype(int)

    no_submission_mask = (
        ((itemmodule == "quiz") & (has_finished_attempt <= 0)) |
        ((itemmodule == "assign") & (has_submission <= 0))
    )

    awaiting_to_zero_mask = (
        fact["assessment_score"].isna()
        & (itemtype == "mod")
        & overdue_mask
        & no_submission_mask
    )

    fact.loc[awaiting_to_zero_mask, "assessment_score"] = 0.0
    return fact

# 8. Grade Dimension - reference:  https://askmurdoch.custhelp.com/app/answers/detail/a_id/714

def create_dim_grade(results):
    grades = [
        {"grade_code": "HD", "grade_name": "High Distinction", "pass_status": "Pass"},
        {"grade_code": "D", "grade_name": "Distinction", "pass_status": "Pass"},
        {"grade_code": "C", "grade_name": "Credit", "pass_status": "Pass"},
        {"grade_code": "P", "grade_name": "Pass", "pass_status": "Pass"},
        {"grade_code": "N", "grade_name": "Fail", "pass_status": "Fail"},
        {"grade_code": "DNS", "grade_name": "Did Not Submit", "pass_status": "Fail"},
        {"grade_code": "SA", "grade_name": "Supplementary Assessment", "pass_status": "Pending"},
        {"grade_code": "SX", "grade_name": "Supplementary Examination", "pass_status": "Pending"},
        {"grade_code": "DX", "grade_name": "Deferred Assessment - Examination", "pass_status": "Pending"},
        {"grade_code": "GP", "grade_name": "Grade Pending", "pass_status": "Pending"},
        {"grade_code": "UP", "grade_name": "Pass", "pass_status": "Pass"},
        {"grade_code": "UF", "grade_name": "No Mark", "pass_status": "Other"},
        {"grade_code": "RPL", "grade_name": "Recognition for Prior Learning", "pass_status": "Other"},
        {"grade_code": "AW", "grade_name": "Approved Withdrawal", "pass_status": "Other"},
        {"grade_code": "UW", "grade_name": "University Withdrawal", "pass_status": "Other"},
        {"grade_code": "AS", "grade_name": "Academic Safety Net", "pass_status": "Other"},
        {"grade_code": "FCR", "grade_name": "Forward Credit", "pass_status": "Other"},
        {"grade_code": "G", "grade_name": "Good Standing", "pass_status": "Other"},
        {"grade_code": "NA", "grade_name": "Not Available", "pass_status": "Other"},
        {"grade_code": "NS", "grade_name": "Not Submitted", "pass_status": "Fail"},
        {"grade_code": "Q", "grade_name": "Deferred Assessment", "pass_status": "Pending"},
        {"grade_code": "S","grade_name": "Supplementary Examination","pass_status": "Pending"},
    ]

    dim_grade = pd.DataFrame(grades)
    dim_grade.insert(0, "grade_key", range(1, len(dim_grade) + 1))

    return dim_grade

# fact tables
# 1A. historical activity log fact table
def create_fact_activity_log_from_historical(
    logs,
    dim_student,
    dim_time,
    academic_period_key,
    dim_course,
    dim_event,
    dim_material,
    course_lookup
):
    fact = logs.copy()

    fact = fact.merge(
        dim_student,
        left_on="studentid_clean",
        right_on="student_id",
        how="left"
    )

    fact = fact.merge(
        dim_time[["time_key", "time"]],
        on="time",
        how="left"
    )

    fact["academic_period_key"] = academic_period_key

    fact = fact.merge(
        course_lookup[["course_key", "event_context"]],
        on="event_context",
        how="left"
    )

    # Current historical dataset has one course.
    # Unmatched activity contexts are assigned to the only available course.
    if len(dim_course) == 1:
        fact["course_key"] = fact["course_key"].fillna(
            dim_course["course_key"].iloc[0]
        )

    fact["course_key"] = fact["course_key"].astype("Int64")

    fact = fact.merge(
        dim_event[["event_key", "event_name"]],
        on="event_name",
        how="left"
    )

    fact = fact.merge(
        dim_material[["material_key", "context", "component"]],
        left_on=["event_context", "component"],
        right_on=["context", "component"],
        how="left"
    )

    fact = fact[
        [
            "student_key",
            "course_key",
            "time_key",
            "academic_period_key",
            "event_key",
            "material_key",
            "description"
        ]
    ]

    fact.insert(0, "activity_fact_id", range(1, len(fact) + 1))
    fact["event_count"] = 1
    fact["source_system"] = "Historical"

    return fact

# 1B. future Moodle activity log fact table - to be implemented when Moodle data is available
def create_fact_activity_log_from_moodle(
    logs,
    dim_student,
    dim_time,
    academic_period_key,
    dim_course,
    dim_event,
    dim_material
):
    fact = logs.copy()
    original_count = len(fact)

    for col in ["userid", "relateduserid", "courseid", "timecreated"]:
        if col in fact.columns:
            fact[col] = pd.to_numeric(fact[col], errors="coerce")

    dim_student_join = dim_student[["student_key", "student_id"]].copy()
    dim_student_join["student_id"] = pd.to_numeric(dim_student_join["student_id"], errors="coerce")

    dim_course_join = dim_course[["course_key", "course_id"]].copy()
    dim_course_join["course_id"] = pd.to_numeric(dim_course_join["course_id"], errors="coerce")

    dim_time_join = dim_time[["time_key", "timecreated"]].copy()
    dim_time_join["timecreated"] = pd.to_numeric(dim_time_join["timecreated"], errors="coerce")

    student_from_user = dim_student_join.rename(columns={
        "student_key": "student_key_from_user",
        "student_id": "student_id_from_user"
    })
    fact = fact.merge(
        student_from_user,
        left_on="userid",
        right_on="student_id_from_user",
        how="left"
    )

    if "relateduserid" in fact.columns:
        student_from_related = dim_student_join.rename(columns={
            "student_key": "student_key_from_related",
            "student_id": "student_id_from_related"
        })
        fact = fact.merge(
            student_from_related,
            left_on="relateduserid",
            right_on="student_id_from_related",
            how="left"
        )
        fact["student_key"] = fact["student_key_from_user"].combine_first(fact["student_key_from_related"])
    else:
        fact["student_key"] = fact["student_key_from_user"]

    fact = fact.merge(
        dim_course_join,
        left_on="courseid",
        right_on="course_id",
        how="left"
    )

    fact = fact.merge(
        dim_time_join,
        on="timecreated",
        how="left"
    )

    fact["academic_period_key"] = academic_period_key

    fact = fact.merge(
        dim_event[["event_key", "event_name"]],
        left_on="eventname",
        right_on="event_name",
        how="left"
    )

    fact = fact.merge(
        dim_material[["material_key", "component", "target"]],
        on=["component", "target"],
        how="left"
    )

    # Student-only analytics: require student and core event context keys.
    fact = fact.dropna(subset=["student_key", "course_key", "time_key", "event_key"])

    fact["description"] = (
        fact["action"].fillna("").astype(str).str.strip()
        + " "
        + fact["target"].fillna("").astype(str).str.strip()
    ).str.strip()

    id_col = "id" if "id" in fact.columns else None
    selected_cols = [
        "student_key",
        "course_key",
        "time_key",
        "academic_period_key",
        "event_key",
        "material_key",
        "description"
    ]
    if id_col:
        selected_cols = [id_col] + selected_cols

    fact = fact[selected_cols]

    if id_col:
        fact = fact.rename(columns={"id": "activity_fact_id"})
        fact["activity_fact_id"] = pd.to_numeric(fact["activity_fact_id"], errors="coerce").astype("Int64")
    else:
        fact.insert(0, "activity_fact_id", range(1, len(fact) + 1))
    fact["event_count"] = 1
    fact["source_system"] = "Moodle"
    fact.attrs["dropped_unresolved_fk"] = int(original_count - len(fact))

    return fact

# 2. assessment fact table 
def create_fact_result(
    results,
    dim_student,
    dim_course,
    dim_assessment,
    dim_grade,
    academic_period_key
):
    # Moodle grades are already in long format (one row per user/item).
    if results.empty:
        empty_fact = pd.DataFrame(columns=[
            "result_fact_id",
            "student_key",
            "course_key",
            "academic_period_key",
            "assessment_key",
            "grade_key",
            "assessment_score",
            "final_mark",
            "source_system"
        ])
        empty_fact.attrs["dropped_unresolved_fk"] = 0
        return empty_fact

    is_moodle_long_format = {"userid", "courseid", "itemname", "finalgrade"}.issubset(results.columns)

    if is_moodle_long_format:
        fact = results.copy()
        original_count = len(fact)
        fact = normalize_moodle_assessment_scores(fact)

        fact = fact.merge(
            dim_student[["student_key", "student_id"]],
            left_on="userid",
            right_on="student_id",
            how="left"
        )

        fact = fact.merge(
            dim_course[["course_key", "course_id"]],
            left_on="courseid",
            right_on="course_id",
            how="left"
        )

        if "itemid" in fact.columns and "assessment_id" in dim_assessment.columns:
            fact = fact.merge(
                dim_assessment[["assessment_key", "assessment_id"]],
                left_on="itemid",
                right_on="assessment_id",
                how="left"
            )
        else:
            fact = fact.merge(
                dim_assessment[["assessment_key", "assessment_name"]],
                left_on="itemname",
                right_on="assessment_name",
                how="left"
            )

        na_grade_rows = dim_grade.loc[dim_grade["grade_code"] == "NA", "grade_key"]
        fallback_grade_key = int(na_grade_rows.iloc[0]) if not na_grade_rows.empty else pd.NA
        fact["grade_key"] = fallback_grade_key
        fact["academic_period_key"] = academic_period_key
        fact["final_mark"] = fact["assessment_score"]

        fact = fact.dropna(subset=["student_key", "course_key", "assessment_key"])

        id_col = "grade_id" if "grade_id" in fact.columns else None
        selected_cols = [
            "student_key",
            "course_key",
            "academic_period_key",
            "assessment_key",
            "grade_key",
            "assessment_score",
            "final_mark"
        ]
        if id_col:
            selected_cols = [id_col] + selected_cols

        fact = fact[selected_cols]

        if id_col:
            fact = fact.rename(columns={"grade_id": "result_fact_id"})
            fact["result_fact_id"] = pd.to_numeric(fact["result_fact_id"], errors="coerce").astype("Int64")
        else:
            fact.insert(0, "result_fact_id", range(1, len(fact) + 1))
        fact["source_system"] = "Moodle"
        fact.attrs["dropped_unresolved_fk"] = int(original_count - len(fact))
        return fact

    # Fallback path for historical wide-format results.
    assessment_cols = dim_assessment["assessment_name"].tolist()

    fact = results.melt(
        id_vars=["studentid_clean", "grade", "mark"],
        value_vars=assessment_cols,
        var_name="assessment_name",
        value_name="assessment_score"
    )

    fact = fact.merge(
        dim_student[["student_key", "student_id"]],
        left_on="studentid_clean",
        right_on="student_id",
        how="left"
    )

    fact = fact.merge(
        dim_assessment,
        on="assessment_name",
        how="left"
    )

    fact = fact.merge(
        dim_grade[["grade_key", "grade_code"]],
        left_on="grade",
        right_on="grade_code",
        how="left"
    )

    fact["course_key"] = dim_course["course_key"].iloc[0]
    fact["academic_period_key"] = academic_period_key
    fact["final_mark"] = fact["mark"]

    fact = fact[
        [
            "student_key",
            "course_key",
            "academic_period_key",
            "assessment_key",
            "grade_key",
            "assessment_score",
            "final_mark"
        ]
    ]

    fact.insert(0, "result_fact_id", range(1, len(fact) + 1))
    fact["source_system"] = "Historical"

    return fact

# 3. enrolment fact table
def create_fact_enrolment_from_moodle(
    enrolments,
    dim_student,
    dim_course,
    dim_time,
    academic_period_key
):
    fact = enrolments.copy()
    original_count = len(fact)

    fact = fact.merge(
        dim_student[["student_key", "student_id"]],
        on="student_id",
        how="left"
    )

    fact = fact.merge(
        dim_course[["course_key", "course_id"]],
        on="course_id",
        how="left"
    )

    fact["academic_period_key"] = academic_period_key
    fact["time_key"] = 1 if not dim_time.empty else pd.NA
    fact["enrolment_status"] = fact.get("status", "active")
    fact["enrolment_source"] = "Moodle"

    fact = fact.dropna(subset=["student_key", "course_key"])

    if "user_enrolment_id" in fact.columns:
        fact = fact.rename(columns={"user_enrolment_id": "enrolment_fact_id"})
        fact["enrolment_fact_id"] = pd.to_numeric(fact["enrolment_fact_id"], errors="coerce").astype("Int64")
    else:
        fact.insert(0, "enrolment_fact_id", range(1, len(fact) + 1))

    fact = fact[
        [
            "enrolment_fact_id",
            "student_key",
            "course_key",
            "academic_period_key",
            "time_key",
            "enrolment_status",
            "enrolment_source"
        ]
    ]
    fact.attrs["dropped_unresolved_fk"] = int(original_count - len(fact))
    return fact

def transform_moodle_data(courses, students, enrolments, logs, grades, semester, academic_year):
    # Create dimensions
    dim_student = students.rename(columns={
        "id": "student_id",
        "email": "email"
    }).copy()
    dim_student["full_name"] = (
        dim_student["firstname"].fillna("").astype(str).str.strip()
        + " "
        + dim_student["lastname"].fillna("").astype(str).str.strip()
    ).str.strip()
    dim_student = dim_student[["student_id", "full_name", "email"]]
    dim_student["student_id"] = pd.to_numeric(dim_student["student_id"], errors="coerce")
    dim_student = dim_student.dropna(subset=["student_id"])
    dim_student["student_id"] = dim_student["student_id"].astype(int)
    dim_student = dim_student.drop_duplicates(subset=["student_id"], keep="last")
    dim_student.insert(0, "student_key", range(1, len(dim_student) + 1))

    # Student-only scope: keep only student enrolments and student-related logs.
    if "role" in enrolments.columns:
        enrolments = enrolments[enrolments["role"].astype(str).str.lower() == "student"].copy()

    student_ids = set(dim_student["student_id"].tolist())
    logs = filter_logs_to_students(logs, student_ids)

    dim_time = create_dim_time_from_moodle_logs(logs)
    dim_academic_period = create_dim_academic_period(semester, academic_year)
    dim_course = create_dim_course_from_moodle_courses(courses)
    dim_event = create_dim_event_from_moodle_logs(logs)
    dim_material = create_dim_material_from_moodle_logs(logs)
    dim_assessment = create_dim_assessment_from_moodle_grades(grades)
    dim_grade = create_dim_grade(grades)

    # Lookup academic period key
    academic_period_key = lookup_academic_period_key(
        dim_academic_period,
        semester,
        academic_year
    )

    # Create fact tables
    fact_activity_log = create_fact_activity_log_from_moodle(
        logs,
        dim_student,
        dim_time,
        academic_period_key,
        dim_course,
        dim_event,
        dim_material
    )

    fact_result = create_fact_result(
        grades,
        dim_student,
        dim_course,
        dim_assessment,
        dim_grade,
        academic_period_key
    )

    fact_enrolment = create_fact_enrolment_from_moodle(
        enrolments,
        dim_student,
        dim_course,
        dim_time,
        academic_period_key
    )

    return {
        "dim_student": dim_student[["student_key", "student_id", "full_name", "email"]],
        "dim_time": dim_time[["time_key", "time", "datetime", "date", "hour", "day", "week", "month", "year"]],
        "dim_academic_period": dim_academic_period,
        "dim_course": dim_course,
        "dim_event": dim_event[["event_key", "event_name"]],
        "dim_material": dim_material[["material_key", "context", "component", "material_type"]],
        "dim_assessment": dim_assessment[["assessment_key", "assessment_name"]],
        "dim_grade": dim_grade,
        "fact_activity_log": fact_activity_log,
        "fact_result": fact_result,
        "fact_enrolment": fact_enrolment
    }


def main():
    # This main function is for testing purposes only.
    # In production, the ETL process will call the functions as needed.
    pass

if __name__ == "__main__":
    main()