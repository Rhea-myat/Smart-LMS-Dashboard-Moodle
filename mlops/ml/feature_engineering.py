import pandas as pd


# create behaviour features based on activity logs, materials accessed and time spent

"""
def create_behaviour_features(
        fact_activity_log,
        dim_material,
        dim_time
        ):
    activity = fact_activity_log.copy()

    activity = activity.merge(
        dim_material[["material_key", "material_type"]],
        on="material_key",
        how="left"
    )
    activity = activity.merge(
        dim_time[["time_key", "date", "hour", "day"]],
        on="time_key",
        how="left"
    )

    activity["material_type"] = activity["material_type"].fillna("Unknown")
    activity["is_after_hours"] = ((activity["hour"] < 8) | (activity["hour"] >= 18)).astype(int)
    activity["is_weekend"] = activity["day"].isin(["Saturday", "Sunday"]).astype(int)

    grouped = activity.groupby(["student_key", "course_key"], as_index=False)
    behaviour = grouped.agg(
        total_events=("event_count", "sum"),
        active_days=("date", "nunique"),
        unique_materials=("material_key", "nunique"),
        after_hours_events=("is_after_hours", "sum"),
        weekend_events=("is_weekend", "sum")
    )

    material_pref = (
        activity.groupby(["student_key", "course_key", "material_type"])
        .size()
        .reset_index(name="material_events")
        .sort_values(["student_key", "course_key", "material_events"], ascending=[True, True, False])
        .drop_duplicates(["student_key", "course_key"])
        [["student_key", "course_key", "material_type"]]
        .rename(columns={"material_type": "top_material_type"})
    )

    behaviour = behaviour.merge(material_pref, on=["student_key", "course_key"], how="left")
    behaviour["avg_events_per_active_day"] = (
        behaviour["total_events"] / behaviour["active_days"].replace(0, pd.NA)
    )
    behaviour["avg_events_per_active_day"] = behaviour["avg_events_per_active_day"].fillna(0)

    return behaviour
"""
def create_behaviour_features(
        fact_activity_log,
        dim_material,
        dim_time
        ):
    activity = fact_activity_log.copy()

    activity = activity.merge(
        dim_material[["material_key", "material_type"]],
        on="material_key",
        how="left"
    )

    activity = activity.merge(
        dim_time[["time_key", "date", "hour", "day"]],
        on="time_key",
        how="left"
    )

    activity["material_type"] = activity["material_type"].fillna("Unknown")

    activity["is_after_hours"] = (
        (activity["hour"] < 8) |
        (activity["hour"] >= 18)
    ).astype(int)

    activity["is_weekend"] = (
        activity["day"].isin(["Saturday", "Sunday"])
    ).astype(int)

    grouped = activity.groupby(
        ["student_key", "course_key"],
        as_index=False
    )

    behaviour = grouped.agg(
        total_events=("event_count", "sum"),
        active_days=("date", "nunique"),
        unique_materials=("material_key", "nunique"),
        after_hours_events=("is_after_hours", "sum"),
        weekend_events=("is_weekend", "sum")
    )

    material_pref = (
        activity.groupby(
            ["student_key", "course_key", "material_type"]
        )
        .size()
        .reset_index(name="material_events")
        .sort_values(
            ["student_key", "course_key", "material_events"],
            ascending=[True, True, False]
        )
        .drop_duplicates(
            ["student_key", "course_key"]
        )
        [["student_key", "course_key", "material_type"]]
        .rename(
            columns={
                "material_type": "top_material_type"
            }
        )
    )

    behaviour = behaviour.merge(
        material_pref,
        on=["student_key", "course_key"],
        how="left"
    )

    # Material view counts
    material_counts = (
        activity.groupby(
            ["student_key", "course_key", "material_type"]
        )["event_count"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )

    material_counts.columns.name = None

    material_counts = material_counts.rename(
        columns={
            "Lecture Material": "lecture_material_views",
            "Assignment": "assignment_views",
            "Course Page": "course_page_views",
            "Forum": "forum_views",
            "Quiz": "quiz_views"
        }
    )

    expected_cols = [
        "lecture_material_views",
        "assignment_views",
        "course_page_views",
        "forum_views",
        "quiz_views"
    ]

    for col in expected_cols:
        if col not in material_counts.columns:
            material_counts[col] = 0

    behaviour = behaviour.merge(
        material_counts[
            ["student_key", "course_key"] + expected_cols
        ],
        on=["student_key", "course_key"],
        how="left"
    )

    behaviour["avg_events_per_active_day"] = (
        behaviour["total_events"] /
        behaviour["active_days"].replace(0, pd.NA)
    ).fillna(0)

    behaviour["events_per_week"] = (
        behaviour["total_events"] /
        (behaviour["active_days"] / 7).replace(0, pd.NA)
    ).fillna(0)

    behaviour["weekend_ratio"] = (
        behaviour["weekend_events"] /
        behaviour["total_events"].replace(0, pd.NA)
    ).fillna(0)

    behaviour["after_hours_ratio"] = (
        behaviour["after_hours_events"] /
        behaviour["total_events"].replace(0, pd.NA)
    ).fillna(0)

    return behaviour

# create academic features based on results, assessments and grades
def create_academic_features(
    fact_result,
    dim_assessment,
    dim_grade
):
    result = fact_result.copy()

    result = result.merge(
        dim_assessment[["assessment_key", "assessment_name"]],
        on="assessment_key",
        how="left"
    )
    result = result.merge(
        dim_grade[["grade_key", "grade_code", "pass_status"]],
        on="grade_key",
        how="left"
    )

    result["assessment_score"] = pd.to_numeric(result["assessment_score"], errors="coerce")
    result["final_mark"] = pd.to_numeric(result["final_mark"], errors="coerce")
    result["is_pass_assessment"] = (result["assessment_score"] >= 50).astype(int)

    grouped = result.groupby(["student_key", "course_key"], as_index=False)
    academic = grouped.agg(
        assessments_attempted=("assessment_score", lambda s: s.notna().sum()),
        avg_assessment_score=("assessment_score", "mean"),
        max_assessment_score=("assessment_score", "max"),
        final_mark=("final_mark", "first"),
        pass_assessment_count=("is_pass_assessment", "sum")
    )

    academic["fail_assessment_count"] = (
        academic["assessments_attempted"] - academic["pass_assessment_count"]
    )

    grade_mode = (
        result.groupby(["student_key", "course_key", "grade_code"]).size().reset_index(name="grade_events")
        .sort_values(["student_key", "course_key", "grade_events"], ascending=[True, True, False])
        .drop_duplicates(["student_key", "course_key"])
        [["student_key", "course_key", "grade_code"]]
        .rename(columns={"grade_code": "grade_code_mode"})
    )

    academic = academic.merge(grade_mode, on=["student_key", "course_key"], how="left")

    return academic

# merge all features together to create a student snapshot
def build_student_snapshot(
    behaviour_features,
    academic_features
):  
    snapshot = behaviour_features.merge(
        academic_features,
        on=["student_key", "course_key"],
        how="outer"
    )
    snapshot["snapshot_date"] = pd.Timestamp.today().date()

    # Fill categorical columns
    snapshot["top_material_type"] = snapshot["top_material_type"].fillna("No Activity")
    snapshot["grade_code_mode"] = snapshot["grade_code_mode"].fillna("No Result")

    numeric_cols = snapshot.select_dtypes(include=["number"]).columns
    snapshot[numeric_cols] = snapshot[numeric_cols].fillna(0)

    count_cols = [
        "total_events",
        "active_days",
        "unique_materials",
        "after_hours_events",
        "weekend_events",

        "lecture_material_views",
        "assignment_views",
        "course_page_views",
        "forum_views",
        "quiz_views",

        "assessments_attempted",
        "pass_assessment_count",
        "fail_assessment_count"
    ]

    snapshot[count_cols] = snapshot[count_cols].astype(int)

    """
    # Create engagement level based on total events - 0-50 low, 51-200 medium, 201+ high
    # but removed for now
    if "total_events" in snapshot.columns:
        snapshot["engagement_level"] = pd.cut(
            snapshot["total_events"],
            bins=[-1, 50, 200, float("inf")],
            labels=["Low", "Medium", "High"]
        )
        
        """
    
    return snapshot

# build behavour feature snapshot
def build_behaviour_model_snapshot(student_snapshot):
    """
    Build model-specific snapshot for engagement / behaviour risk model.
    Uses behaviour-only features.
    """

    snapshot = student_snapshot.copy()

    risk_grades = ["N", "S", "SA", "DNS"]

    numeric_cols = snapshot.select_dtypes(include=["number"]).columns
    snapshot[numeric_cols] = snapshot[numeric_cols].fillna(0)


    snapshot = snapshot[
        snapshot["grade_code_mode"] != "No Result"
    ].copy()

    snapshot = snapshot[
        snapshot["grade_code_mode"] != "DX"
    ].copy()

    snapshot["risk_label"] = (
        snapshot["grade_code_mode"]
        .isin(risk_grades)
        .astype(int)
    )
    
    snapshot["no_activity_flag"] = (
        snapshot["total_events"] == 0
    ).astype(int)

    behaviour_cols = [
        "student_key",
        "course_key",
        "snapshot_date",

        "total_events",
        "active_days",
        "unique_materials",
        "after_hours_events",
        "weekend_events",

        "avg_events_per_active_day",
        "events_per_week",
        "weekend_ratio",
        "after_hours_ratio",

        "lecture_material_views",
        "assignment_views",
        "course_page_views",
        "forum_views",
        "quiz_views",

        "top_material_type",
        "no_activity_flag",

        "risk_label"
    ]

    return snapshot[behaviour_cols]

# build academic feature snapshot
def build_academic_model_snapshot(
    student_snapshot,
    fact_result,
    dim_assessment
):
    """
    Build model-specific snapshot for academic risk model.
    Uses behaviour features + individual assessment scores.
    """

    snapshot = student_snapshot.copy()

    risk_grades = ["N", "S", "SA", "DNS"]

    snapshot = snapshot[
        snapshot["grade_code_mode"] != "No Result"
    ].copy()

    snapshot = snapshot[
        snapshot["grade_code_mode"] != "DX"
    ].copy()

    snapshot["risk_label"] = (
        snapshot["grade_code_mode"]
        .isin(risk_grades)
        .astype(int)
    )

    results = fact_result.copy()

    results = results.merge(
        dim_assessment[["assessment_key", "assessment_name"]],
        on="assessment_key",
        how="left"
    )

    results["assessment_score"] = pd.to_numeric(
        results["assessment_score"],
        errors="coerce"
    )

    assessment_features = results.pivot_table(
        index=["student_key", "course_key"],
        columns="assessment_name",
        values="assessment_score",
        aggfunc="first"
    ).reset_index()

    assessment_features.columns.name = None

    academic_snapshot = snapshot.merge(
        assessment_features,
        on=["student_key", "course_key"],
        how="left"
    )

    drop_cols = [
        "avg_assessment_score",
        "max_assessment_score",
        "final_mark",
        "pass_assessment_count",
        "fail_assessment_count",
        "assessments_attempted",
        "grade_code_mode"
    ]

    academic_snapshot = academic_snapshot.drop(
        columns=[col for col in drop_cols if col in academic_snapshot.columns]
    )

    academic_snapshot = academic_snapshot.fillna(0)

    return academic_snapshot