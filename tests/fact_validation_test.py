


def validate_fact_activity_log(fact_activity, original_logs):
    print(
        "StudentKey missing:",
        fact_activity["student_key"].isnull().sum()
    )

    print(
        "CourseKey missing:",
        fact_activity["course_key"].isnull().sum()
    )

    print(
        "EventKey missing:",
        fact_activity["event_key"].isnull().sum()
    )

    print(
        "MaterialKey missing:",
        fact_activity["material_key"].isnull().sum()
    )

    print(
        "TimeKey missing:",
        fact_activity["time_key"].isnull().sum()
    )

    print(
        "Original log rows:",
        len(original_logs)
    )

    print(
        "Fact rows:",
        len(fact_activity)
    )

def validate_fact_result(fact_result, original_results):
    print(
        "StudentKey missing:",
        fact_result["student_key"].isnull().sum()
    )

    print(
        "AssessmentKey missing:",
        fact_result["assessment_key"].isnull().sum()
    )

    print(
        "GradeKey missing:",
        fact_result["grade_key"].isnull().sum()
    )

    print(
        "Original result rows:",
        len(original_results)
    )

    print(
        "Fact rows:",
        len(fact_result)
    )

