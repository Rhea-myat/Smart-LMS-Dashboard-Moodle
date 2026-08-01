import pandas as pd
from pathlib import Path
from etl.db import get_engine, get_source_engine

BASE_DIR = Path(__file__).resolve().parent.parent
STAGING_DIR = BASE_DIR / "data" / "staging"

STAGING_DIR.mkdir(parents=True, exist_ok=True)

def extract_data(file_path):
    """
    Extract data from a source file into a DataFrame.
    Args:
        file_path (str or Path): Path to the source file.
    Returns:
        pd.DataFrame: Extracted data.
    """
    file_path = str(file_path)

    if file_path.endswith(".csv"):
        return pd.read_csv(file_path)

    elif file_path.endswith((".xlsx", ".xls")):
        return pd.read_excel(file_path)

    else:
        raise ValueError(f"Unsupported file type: {file_path}")
    

def load_to_staging(df, file_path):
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(file_path, index=False)
    print(f"Saved to staging: {file_path}")

# extract from mdl_course 
def extract_moodle_courses(engine=None):
    if engine is None:
        engine = get_source_engine()

    sql = """
    SELECT
        id,
        fullname,
        shortname,
        idnumber,
        category,
        visible
    FROM mdl_course
    WHERE id > 1
    """

    return pd.read_sql(sql, engine)

# extract student from mdl_user
def extract_moodle_students(engine=None):
    if engine is None:
        engine = get_source_engine()

    sql = """
    SELECT DISTINCT
        u.id,
        u.username,
        u.firstname,
        u.lastname,
        u.email,
        u.suspended,
        u.deleted
    FROM mdl_user u
        JOIN mdl_role_assignments ra
            ON ra.userid = u.id
        JOIN mdl_role r
            ON r.id = ra.roleid
    WHERE
        r.shortname='student'
        AND u.deleted=0
    """

    return pd.read_sql(sql, engine)

# extract teacher (UC) from mdl_user
def extract_moodle_teachers(engine=None):
    if engine is None:
        engine = get_source_engine()

    sql = """
    SELECT DISTINCT
        u.id,
        u.firstname,
        u.lastname,
        u.email
    FROM mdl_user u
        JOIN mdl_role_assignments ra
            ON ra.userid=u.id
        JOIN mdl_role r
            ON r.id=ra.roleid
    WHERE r.shortname IN ('teacher', 'editingteacher')
    """

    return pd.read_sql(sql, engine)

# extract enrolments from mdl_user, mdl_role_assignments, mdl_context, mdl_course, mdl_role
def extract_moodle_enrolments(engine=None):
    if engine is None:
        engine = get_source_engine()

    sql = """
    SELECT DISTINCT
        ue.id         AS user_enrolment_id,
        ue.userid     AS student_id,
        e.courseid    AS course_id,
        c.fullname,
        ue.status,
        r.shortname   AS role
    FROM mdl_user_enrolments ue
        JOIN mdl_enrol e
            ON e.id = ue.enrolid
        JOIN mdl_course c
            ON c.id = e.courseid
        JOIN mdl_role_assignments ra
            ON ra.userid = ue.userid
        JOIN mdl_context ctx
            ON ctx.id = ra.contextid
        JOIN mdl_role r
            ON r.id = ra.roleid
    WHERE
        ctx.contextlevel = 50
        AND ctx.instanceid = c.id
        AND r.shortname = 'student'
    """

    return pd.read_sql(sql, engine)

# extract activity logs from mdl_logstore_standard_log
def extract_moodle_logs(engine=None):
    if engine is None:
        engine = get_source_engine()

    sql = """
    SELECT *
    FROM mdl_logstore_standard_log
    """

    return pd.read_sql(sql, engine)

# extract results from mdl_grade_grades, mdl_grade_items, mdl_user, mdl_course
def extract_moodle_grades(engine=None):
    if engine is None:
        engine = get_source_engine()

    sql = """
    SELECT
        gg.id AS grade_id,
        gg.userid,
        gi.courseid,
        gi.id AS itemid,
        gi.itemname,
        gi.itemtype,
        gi.itemmodule,
        gi.grademax,
        CASE
            WHEN gi.itemmodule = 'quiz' THEN q.timeclose
            WHEN gi.itemmodule = 'assign' THEN a.duedate
            ELSE NULL
        END AS due_timestamp,
        COALESCE(qa.has_finished_attempt, 0) AS has_finished_attempt,
        COALESCE(asub.has_submission, 0) AS has_submission,
        gg.finalgrade,
        gg.timemodified
    FROM mdl_grade_grades gg
        JOIN mdl_grade_items gi
            ON gg.itemid=gi.id
        LEFT JOIN mdl_quiz q
            ON gi.itemmodule = 'quiz'
            AND q.id = gi.iteminstance
        LEFT JOIN mdl_assign a
            ON gi.itemmodule = 'assign'
            AND a.id = gi.iteminstance
        LEFT JOIN (
            SELECT
                quiz,
                userid,
                MAX(CASE WHEN preview = 0 AND state = 'finished' THEN 1 ELSE 0 END) AS has_finished_attempt
            FROM mdl_quiz_attempts
            GROUP BY quiz, userid
        ) qa
            ON gi.itemmodule = 'quiz'
            AND qa.quiz = gi.iteminstance
            AND qa.userid = gg.userid
        LEFT JOIN (
            SELECT
                assignment,
                userid,
                MAX(CASE WHEN status = 'submitted' THEN 1 ELSE 0 END) AS has_submission
            FROM mdl_assign_submission
            GROUP BY assignment, userid
        ) asub
            ON gi.itemmodule = 'assign'
            AND asub.assignment = gi.iteminstance
            AND asub.userid = gg.userid
    WHERE gi.itemtype = 'mod'
      AND gi.itemmodule IN ('quiz', 'assign')
    """

    return pd.read_sql(sql, engine)


def main():
    """
    historical extraction for logs and results from the provided Excel files, 
    and save them to staging as CSVs.
    logs = BASE_DIR / "data" / "raw" / "ICT001 S1 2025 Logs RELEASED V1.0.xlsx"
    results = BASE_DIR / "data" / "raw" / "cleaned_standard_results.xlsx"
    staging_path_logs = STAGING_DIR / "logs.csv"
    staging_path_results = STAGING_DIR / "results.csv"

    df_logs = extract_data(logs)
    load_to_staging(df_logs, staging_path_logs)
    print(f"Extracted logs data shape: {df_logs.shape}")

    df_results = extract_data(results)
    load_to_staging(df_results, staging_path_results)
    print(f"Extracted results data shape: {df_results.shape}")"""

    #moodle extraction
    df_courses = extract_moodle_courses()
    load_to_staging(df_courses, STAGING_DIR / "courses.csv")

    df_students = extract_moodle_students()
    load_to_staging(df_students, STAGING_DIR / "students.csv")

    df_teachers = extract_moodle_teachers()
    load_to_staging(df_teachers, STAGING_DIR / "teachers.csv")

    df_enrolments = extract_moodle_enrolments()
    load_to_staging(df_enrolments, STAGING_DIR / "enrolments.csv")

    df_logs = extract_moodle_logs()
    load_to_staging(df_logs, STAGING_DIR / "activity_logs.csv")

    df_grades = extract_moodle_grades()
    load_to_staging(df_grades, STAGING_DIR / "grades.csv")
    



if __name__ == "__main__":
    main()