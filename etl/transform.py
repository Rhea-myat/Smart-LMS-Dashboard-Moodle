import pandas as pd

# 1. Student dimension
def create_dim_student(logs, results, enrolments=None):
    """
    Create Dim_Student dimension table.

    Priority of data sources:
    1. Enrolment data (future authoritative source)
    2. Moodle activity logs
    3. Historical results
    """

    if enrolments is not None:
        students = enrolments[
            ["studentid_clean", "full_name", "email"]
        ].drop_duplicates()

    else:
        # Extract from logs
        log_students = logs[
            ["studentid_clean", "user_full_name", "username"]
        ].drop_duplicates()

        log_students = log_students.rename(columns={
            "user_full_name": "full_name",
            "username": "email"
        })

        # Results only provide IDs
        result_students = results[
            ["studentid_clean"]
        ].drop_duplicates()

        result_students["full_name"] = None
        result_students["email"] = None

        # Combine sources
        students = pd.concat(
            [log_students, result_students],
            ignore_index=True
        )

        # Prefer richer records from logs
        students = students.drop_duplicates(
            subset=["studentid_clean"],
            keep="first"
        )

    students = students.rename(columns={
        "studentid_clean": "student_id"
    })

    students = students.reset_index(drop=True)

    students.insert(
        0,
        "student_key",
        range(1, len(students) + 1)
    )

    return students

# 2. time dimension
def create_dim_time(logs):
    dim_time = logs[["time"]].drop_duplicates().copy()

    dim_time["datetime"] = pd.to_datetime(
        dim_time["time"],
        format="%d/%m/%y, %H:%M:%S",
        errors="coerce"
    )

    dim_time = dim_time[dim_time["datetime"].notna()]

    dim_time["date"] = dim_time["datetime"].dt.date
    dim_time["hour"] = dim_time["datetime"].dt.hour
    dim_time["day"] = dim_time["datetime"].dt.day_name()
    dim_time["week"] = dim_time["datetime"].dt.isocalendar().week
    dim_time["month"] = dim_time["datetime"].dt.month
    dim_time["year"] = dim_time["datetime"].dt.year

    dim_time.insert(0, "time_key", range(1, len(dim_time) + 1))

    return dim_time

# 3. course dimension
def create_dim_course(logs):
    dim_course = logs[["event_context"]].drop_duplicates().copy()

    dim_course["course_name"] = dim_course["event_context"].str.extract(
        r"Unit:\s*(.*)"
    )

    dim_course.insert(0, "course_key", range(1, len(dim_course) + 1))

    return dim_course

# 4. event dimension
def create_dim_event(logs):
    dim_event = logs[["event_name"]].drop_duplicates().copy()

    dim_event.insert(0, "event_key", range(1, len(dim_event) + 1))

    return dim_event

# 5. material dimension
def create_dim_material(logs):
    dim_material = (
        logs[["event_context", "component"]]
        .drop_duplicates()
        .copy()
    )

    def classify_material(row):
        context = str(row["event_context"]).lower()
        component = str(row["component"]).lower()

        if "assignment" in context or "assign" in component:
            return "Assignment"

        elif "quiz" in context or "quiz" in component:
            return "Quiz"

        elif "forum" in context or "forum" in component:
            return "Forum"

        elif "file" in component and (
            "lecture" in context or
            "lab" in context or
            "notes" in context or
            "slides" in context or
            "solution" in context or
            "pdf" in context
        ):
            return "Lecture Material"

        elif "recorded" in context or "video" in context:
            return "Recorded Session"

        elif "unit:" in context:
            return "Course Page"

        else:
            return "Other"

    dim_material["material_type"] = dim_material.apply(
        classify_material,
        axis=1
    )

    dim_material = dim_material.rename(
        columns={
            "event_context": "context"
        }
    )

    dim_material.insert(
        0,
        "material_key",
        range(1, len(dim_material) + 1)
    )

    return dim_material

# 6. Assessment dimension
def create_dim_assessment(results):
    assessment_columns = [
        "ass_ex_1", "ass_ex_2", "ass_ex_3", "ass_ex_4", "ass_ex_5",
        "ass_ex_6", "ass_ex_7", "ass_ex_8", "ass_ex_9", "ass_ex_10",
        "weekly_lab_quizzes_100",
        "assignment_1_100",
        "ass_1_with_penalty_100",
        "ass_2_100",
        "ass_2_with_penalty_100",
        "exam_100",
        "total_100",
        "rounded_total_100"
    ]

    dim_assessment = pd.DataFrame({
        "assessment_name": assessment_columns
    })

    dim_assessment.insert(0, "assessment_key", range(1, len(dim_assessment) + 1))

    return dim_assessment

# 7. Grade Dimesnion - reference:  https://askmurdoch.custhelp.com/app/answers/detail/a_id/714

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
# 1. activity log fact table
def create_fact_activity_log(logs, dim_student, dim_time, dim_course, dim_event, dim_material):
    fact = logs.copy()

    fact = fact.merge(dim_student, left_on="studentid_clean", right_on="student_id", how="left")
    fact = fact.merge(dim_time[["time_key", "time"]], on="time", how="left")
    fact = fact.merge(dim_course[["course_key", "event_context"]], on="event_context", how="left")
    fact = fact.merge(dim_event[["event_key", "event_name"]], on="event_name", how="left")
    fact = fact.merge(
        dim_material[["material_key", "context", "component"]],
        left_on=["event_context", "component"],
        right_on=["context", "component"],
        how="left"
    )

    fact = fact[[
        "student_key",
        "course_key",
        "time_key",
        "event_key",
        "material_key",
        "description"
    ]]

    fact.insert(0, "activity_fact_id", range(1, len(fact) + 1))
    fact["event_count"] = 1

    return fact

# 2. assessment fact table 
def create_fact_result(results, dim_student, dim_course, dim_assessment, dim_grade):
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
    fact["final_mark"] = fact["mark"]

    fact = fact[
        [
            "student_key",
            "course_key",
            "assessment_key",
            "grade_key",
            "assessment_score",
            "final_mark"
        ]
    ]

    fact.insert(0, "result_fact_id", range(1, len(fact) + 1))

    return fact
