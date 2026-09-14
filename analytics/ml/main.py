import pandas as pd
import os
import importlib.util
from pathlib import Path
from ml import feature_engineering as fe_v1
from ml import feature_engineering_v2 as fe_v2
from ml import feature_engineering_v2_1 as fe_v2_1

from ml.db import get_ml_engine
from ml.load import load_snapshot, load_model_registry, load_model_feature_stats, load_model_feature_baseline
from ml.monitoring.drift_utils import save_model_baselines
from datetime import datetime, timezone


def _load_v2_2_module():
    module_path = Path(__file__).resolve().parent / "feature_engineering_v2.2.py"
    spec = importlib.util.spec_from_file_location("ml_feature_engineering_v2_2", module_path)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module from {module_path}")
    spec.loader.exec_module(module)
    return module


fe_v2_2 = _load_v2_2_module()


def _norm_key_series(series):
    return series.astype(str).str.strip()


def _valid_course_period_pairs(*fact_dfs: pd.DataFrame):
    pairs = set()
    for df in fact_dfs:
        if df is None or df.empty:
            continue
        if "course_key" not in df.columns or "academic_period_key" not in df.columns:
            continue
        work = df[["course_key", "academic_period_key"]].copy()
        work["course_key"] = pd.to_numeric(work["course_key"], errors="coerce")
        work["academic_period_key"] = pd.to_numeric(work["academic_period_key"], errors="coerce")
        work = work.dropna().drop_duplicates()
        for row in work.itertuples(index=False):
            pairs.add((int(row.course_key), int(row.academic_period_key)))
    return pairs


def _filter_valid_course_period_rows(df: pd.DataFrame, valid_pairs):
    if df.empty or not valid_pairs:
        return df.copy()
    if "course_key" not in df.columns or "academic_period_key" not in df.columns:
        return df.copy()

    work = df.copy()
    work["course_key"] = pd.to_numeric(work["course_key"], errors="coerce")
    work["academic_period_key"] = pd.to_numeric(work["academic_period_key"], errors="coerce")

    keep_mask = [
        (int(course), int(period)) in valid_pairs if pd.notna(course) and pd.notna(period) else False
        for course, period in zip(work["course_key"], work["academic_period_key"])
    ]

    return work.loc[keep_mask].copy()


def _upsert_snapshot_csv(csv_path: Path, incoming_df: pd.DataFrame, key_columns):
    incoming_df = incoming_df.copy()

    if csv_path.exists():
        existing_df = pd.read_csv(csv_path, keep_default_na=False)
    else:
        existing_df = pd.DataFrame(columns=incoming_df.columns)

    for col in existing_df.columns:
        if col not in incoming_df.columns:
            incoming_df[col] = pd.NA
    for col in incoming_df.columns:
        if col not in existing_df.columns:
            existing_df[col] = pd.NA

    incoming_df = incoming_df[existing_df.columns] if not existing_df.empty else incoming_df
    existing_df = existing_df[incoming_df.columns]

    combined_df = pd.concat([existing_df, incoming_df], ignore_index=True)

    valid_keys = [col for col in key_columns if col in combined_df.columns]
    if valid_keys:
        helper_cols = []
        work_df = combined_df.copy()
        for idx, key_col in enumerate(valid_keys):
            helper_col = f"__upsert_key_{idx}"
            helper_cols.append(helper_col)
            work_df[helper_col] = _norm_key_series(work_df[key_col])
        merged_df = work_df.drop_duplicates(subset=helper_cols, keep="last").drop(columns=helper_cols)
    else:
        merged_df = combined_df.drop_duplicates(keep="last")

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    merged_df.to_csv(csv_path, index=False)
    added_rows = int(max(len(merged_df) - len(existing_df), 0))
    return merged_df, added_rows


def _append_feature_engineering_run_log(logs_dir: Path, run_payload: dict):
    logs_dir.mkdir(parents=True, exist_ok=True)

    csv_path = logs_dir / "feature_engineering_run_logs.csv"
    debug_path = logs_dir / "feature_engineering_run_debug.log"

    row_df = pd.DataFrame([run_payload])
    if csv_path.exists():
        row_df.to_csv(csv_path, mode="a", header=False, index=False)
    else:
        row_df.to_csv(csv_path, index=False)

    debug_line = (
        f"{run_payload['run_timestamp_utc']} | run_id={run_payload['run_id']} | "
        f"status={run_payload['status']} | snapshot_date={run_payload['snapshot_date']} | "
        f"academic_period_key={run_payload['academic_period_key']} | "
        f"rows_student={run_payload['student_snapshot_rows']} | "
        f"rows_behaviour_pred={run_payload['behaviour_prediction_snapshot_rows']} | "
        f"rows_academic_pred={run_payload['academic_prediction_snapshot_rows']}"
    )
    with open(debug_path, "a", encoding="utf-8") as f:
        f.write(debug_line + "\n")


def _latest_snapshot_alias(df: pd.DataFrame):
    if "snapshot_date" not in df.columns or df.empty:
        return df.copy()

    latest_snapshot_date = pd.to_datetime(df["snapshot_date"], errors="coerce").max()
    if pd.isna(latest_snapshot_date):
        return df.copy()

    latest_date_str = latest_snapshot_date.date().isoformat()
    return df[
        pd.to_datetime(df["snapshot_date"], errors="coerce").dt.date.astype(str) == latest_date_str
    ].copy()


def run_feature_engineering_v2_2_incremental():
    run_timestamp = datetime.now(timezone.utc)
    run_id = run_timestamp.strftime("feat_%Y%m%dT%H%M%S%fZ")

    fact_activity_log = pd.read_csv("data/warehouse/fact_activity_log.csv")
    fact_enrolment = pd.read_csv("data/warehouse/fact_enrolment.csv")
    dim_material = pd.read_csv("data/warehouse/dim_material.csv")
    fact_result = pd.read_csv("data/warehouse/fact_result.csv")
    dim_time = pd.read_csv("data/warehouse/dim_time.csv")
    dim_assessment = pd.read_csv("data/warehouse/dim_assessment.csv")
    dim_grade = pd.read_csv("data/warehouse/dim_grade.csv")

    behaviour = fe_v2_2.create_behaviour_features(
        fact_activity_log,
        dim_material,
        dim_time
    )

    academic = fe_v2_2.create_academic_features(
        fact_result,
        dim_assessment,
        dim_grade
    )

    moodle_activity = fact_activity_log[
        fact_activity_log.get("source_system", pd.Series("", index=fact_activity_log.index)).astype(str).str.lower() == "moodle"
    ].copy()

    # Use all activity rows for course-period mapping.
    # Restricting to moodle-only rows can exclude historical units (e.g., ICT001)
    # and incorrectly fall back to another period.
    source_activity = fact_activity_log.copy()

    period_values = pd.to_numeric(source_activity.get("academic_period_key"), errors="coerce").dropna()
    if period_values.empty:
        raise ValueError("Cannot determine academic_period_key from activity facts.")
    default_academic_period_key = int(period_values.max())

    source_activity = source_activity.copy()
    source_activity["course_key"] = pd.to_numeric(source_activity.get("course_key"), errors="coerce")
    source_activity["academic_period_key"] = pd.to_numeric(
        source_activity.get("academic_period_key"), errors="coerce"
    )

    # Preserve period integrity per course_key instead of stamping one global period.
    # Use the most frequent observed period per course as the default for that course.
    course_period_map = (
        source_activity[["course_key", "academic_period_key"]]
        .dropna()
        .groupby("course_key", as_index=False)["academic_period_key"]
        .agg(lambda values: int(pd.Series(values).astype(int).mode().iloc[0]))
        .rename(columns={"academic_period_key": "derived_academic_period_key"})
    )

    source_activity["time_key"] = pd.to_numeric(source_activity["time_key"], errors="coerce")
    dim_time_work = dim_time.copy()
    dim_time_work["time_key"] = pd.to_numeric(dim_time_work["time_key"], errors="coerce")
    if "date" in dim_time_work.columns:
        dim_time_work["date"] = pd.to_datetime(dim_time_work["date"], errors="coerce")

    activity_with_date = source_activity.merge(
        dim_time_work[["time_key", "date"]],
        on="time_key",
        how="left"
    )
    latest_activity_date = pd.to_datetime(activity_with_date["date"], errors="coerce").max()
    if pd.isna(latest_activity_date):
        latest_activity_date = pd.Timestamp.today()

    run_snapshot_date = pd.Timestamp.today().date().isoformat()

    valid_pairs = _valid_course_period_pairs(fact_activity_log, fact_result, fact_enrolment)

    snapshot = fe_v2_2.build_student_snapshot(
        behaviour,
        academic,
        academic_period_key=default_academic_period_key,
        snapshot_date=run_snapshot_date
    )

    snapshot["course_key"] = pd.to_numeric(snapshot.get("course_key"), errors="coerce")
    snapshot = snapshot.merge(course_period_map, on="course_key", how="left")
    snapshot["academic_period_key"] = (
        pd.to_numeric(snapshot["derived_academic_period_key"], errors="coerce")
        .fillna(default_academic_period_key)
        .astype(int)
    )
    snapshot = snapshot.drop(columns=["derived_academic_period_key"])
    snapshot = _filter_valid_course_period_rows(snapshot, valid_pairs)

    behaviour_model_snapshot = fe_v2_2.build_behaviour_model_snapshot(snapshot)
    academic_model_snapshot = fe_v2_2.build_academic_model_snapshot(snapshot)

    behaviour_prediction_snapshot = fe_v2_2.build_behaviour_prediction_snapshot(snapshot)
    academic_prediction_snapshot = fe_v2_2.build_academic_prediction_snapshot(snapshot)

    feature_store_path = Path("ml/feature_store")
    feature_store_path.mkdir(parents=True, exist_ok=True)

    key_cols = ["student_key", "course_key", "academic_period_key", "snapshot_date"]

    student_snapshot_all, student_added = _upsert_snapshot_csv(
        feature_store_path / "student_snapshot.csv",
        snapshot,
        key_cols,
    )
    behaviour_model_snapshot_all, behaviour_model_added = _upsert_snapshot_csv(
        feature_store_path / "behaviour_model_snapshot.csv",
        behaviour_model_snapshot,
        key_cols,
    )
    academic_model_snapshot_all, academic_model_added = _upsert_snapshot_csv(
        feature_store_path / "academic_model_snapshot_v2.csv",
        academic_model_snapshot,
        key_cols,
    )
    behaviour_prediction_snapshot_all, behaviour_prediction_added = _upsert_snapshot_csv(
        feature_store_path / "behaviour_prediction_snapshot.csv",
        behaviour_prediction_snapshot,
        key_cols,
    )
    academic_prediction_snapshot_all, academic_prediction_added = _upsert_snapshot_csv(
        feature_store_path / "academic_prediction_snapshot.csv",
        academic_prediction_snapshot,
        key_cols,
    )

    # Keep persisted snapshot CSVs clean: remove stale invalid course-period rows.
    student_snapshot_all = _filter_valid_course_period_rows(student_snapshot_all, valid_pairs)
    behaviour_model_snapshot_all = _filter_valid_course_period_rows(behaviour_model_snapshot_all, valid_pairs)
    academic_model_snapshot_all = _filter_valid_course_period_rows(academic_model_snapshot_all, valid_pairs)
    behaviour_prediction_snapshot_all = _filter_valid_course_period_rows(behaviour_prediction_snapshot_all, valid_pairs)
    academic_prediction_snapshot_all = _filter_valid_course_period_rows(academic_prediction_snapshot_all, valid_pairs)

    student_snapshot_all.to_csv(feature_store_path / "student_snapshot.csv", index=False)
    behaviour_model_snapshot_all.to_csv(feature_store_path / "behaviour_model_snapshot.csv", index=False)
    academic_model_snapshot_all.to_csv(feature_store_path / "academic_model_snapshot_v2.csv", index=False)
    behaviour_prediction_snapshot_all.to_csv(feature_store_path / "behaviour_prediction_snapshot.csv", index=False)
    academic_prediction_snapshot_all.to_csv(feature_store_path / "academic_prediction_snapshot.csv", index=False)

    # Keep latest aliases from the current engineered run.
    _latest_snapshot_alias(snapshot).to_csv(
        feature_store_path / "student_snapshot_latest.csv",
        index=False
    )
    _latest_snapshot_alias(behaviour_model_snapshot).to_csv(
        feature_store_path / "behaviour_model_snapshot_latest.csv",
        index=False
    )
    _latest_snapshot_alias(academic_model_snapshot).to_csv(
        feature_store_path / "academic_model_snapshot_v2_latest.csv",
        index=False
    )
    _latest_snapshot_alias(behaviour_prediction_snapshot).to_csv(
        feature_store_path / "behaviour_prediction_snapshot_latest.csv",
        index=False
    )
    _latest_snapshot_alias(academic_prediction_snapshot).to_csv(
        feature_store_path / "academic_prediction_snapshot_latest.csv",
        index=False
    )

    save_model_baselines(
        _latest_snapshot_alias(behaviour_model_snapshot_all),
        _latest_snapshot_alias(academic_model_snapshot_all)
    )

    # Keep DB tables as latest serving snapshots.
    engine = get_ml_engine()
    load_snapshot(_latest_snapshot_alias(student_snapshot_all), "student_snapshot", engine)
    load_snapshot(_latest_snapshot_alias(behaviour_model_snapshot_all), "behaviour_model_snapshot", engine)
    load_snapshot(_latest_snapshot_alias(academic_model_snapshot_all), "academic_model_snapshot_v2", engine)
    load_snapshot(_latest_snapshot_alias(behaviour_prediction_snapshot_all), "behaviour_prediction_snapshot", engine)
    load_snapshot(_latest_snapshot_alias(academic_prediction_snapshot_all), "academic_prediction_snapshot", engine)

    load_model_feature_stats(
        _latest_snapshot_alias(behaviour_model_snapshot_all),
        "model_feature_stats",
        engine
    )

    load_model_feature_baseline(
        _latest_snapshot_alias(behaviour_model_snapshot_all),
        "model_feature_baseline",
        engine
    )

    moodle_activity_rows = int(len(moodle_activity))
    moodle_result_rows = 0
    if "source_system" in fact_result.columns:
        moodle_result_rows = int(
            fact_result["source_system"].astype(str).str.lower().eq("moodle").sum()
        )
    else:
        moodle_result_rows = int(len(fact_result))

    _append_feature_engineering_run_log(
        Path("logs"),
        {
            "run_id": run_id,
            "run_timestamp_utc": run_timestamp.isoformat(),
            "pipeline": "feature_engineering_v2.2_incremental",
            "status": "completed",
            "snapshot_date": run_snapshot_date,
            "latest_activity_date": latest_activity_date.date().isoformat(),
            "academic_period_key": default_academic_period_key,
            "input_fact_activity_rows": int(len(fact_activity_log)),
            "input_fact_result_rows": int(len(fact_result)),
            "input_moodle_activity_rows": moodle_activity_rows,
            "input_moodle_result_rows": moodle_result_rows,
            "student_snapshot_rows": int(len(snapshot)),
            "behaviour_model_snapshot_rows": int(len(behaviour_model_snapshot)),
            "academic_model_snapshot_rows": int(len(academic_model_snapshot)),
            "behaviour_prediction_snapshot_rows": int(len(behaviour_prediction_snapshot)),
            "academic_prediction_snapshot_rows": int(len(academic_prediction_snapshot)),
            "student_snapshot_added": student_added,
            "behaviour_model_snapshot_added": behaviour_model_added,
            "academic_model_snapshot_added": academic_model_added,
            "behaviour_prediction_snapshot_added": behaviour_prediction_added,
            "academic_prediction_snapshot_added": academic_prediction_added,
            "student_snapshot_total": int(len(student_snapshot_all)),
            "behaviour_model_snapshot_total": int(len(behaviour_model_snapshot_all)),
            "academic_model_snapshot_total": int(len(academic_model_snapshot_all)),
            "behaviour_prediction_snapshot_total": int(len(behaviour_prediction_snapshot_all)),
            "academic_prediction_snapshot_total": int(len(academic_prediction_snapshot_all)),
            "message": "Feature engineering snapshots upserted and latest aliases refreshed.",
        },
    )

    print(
        "v2.2 snapshot upsert complete | "
        f"student_snapshot_total={len(student_snapshot_all)} "
        f"latest_snapshot_date={run_snapshot_date} "
        f"latest_activity_date={latest_activity_date.date().isoformat()} "
        f"academic_period_key_default={default_academic_period_key}"
    )


def test_feature_engineering():
    # load warehouse csvs
    fact_activity_log = pd.read_csv("data/warehouse/fact_activity_log.csv")
    dim_material = pd.read_csv("data/warehouse/dim_material.csv")
    fact_result = pd.read_csv("data/warehouse/fact_result.csv")
    dim_time = pd.read_csv("data/warehouse/dim_time.csv")
    dim_assessment = pd.read_csv("data/warehouse/dim_assessment.csv")
    dim_grade = pd.read_csv("data/warehouse/dim_grade.csv")
    
    behaviour = fe_v1.create_behaviour_features(
        fact_activity_log,
        dim_material,
        dim_time
    )
    print(behaviour.head())
    print(behaviour.columns)
    print(behaviour.shape)

    academic = fe_v1.create_academic_features(
        fact_result,
        dim_assessment,
        dim_grade
    )
    print(academic.head())
    print(academic.columns)
    print(academic.shape)

    snapshot = fe_v1.build_student_snapshot(
        behaviour,
        academic
    )

    print(snapshot.head())
    print(snapshot.shape)

    behaviour_model_snapshot = fe_v1.build_behaviour_model_snapshot(snapshot)
    print(behaviour_model_snapshot.head())
    print(behaviour_model_snapshot.shape)

    academic_model_snapshot = fe_v1.build_academic_model_snapshot(
        snapshot,
        fact_result,
        dim_assessment
    )

    print(academic_model_snapshot.head())
    print(academic_model_snapshot.shape)


    feature_store_path = Path("ml/feature_store")
    feature_store_path.mkdir(parents=True, exist_ok=True)

    snapshot.to_csv(
        feature_store_path / "student_snapshot.csv",
        index=False
    )

    behaviour_model_snapshot.to_csv(
        feature_store_path / "behaviour_model_snapshot.csv",
        index=False
    )

    academic_model_snapshot.to_csv(
        feature_store_path / "academic_model_snapshot.csv",
        index=False
    )

    # Load snapshots to database
    engine = get_ml_engine()
    load_snapshot(
        snapshot,
        "student_snapshot",
        engine
    )

    load_snapshot(
        behaviour_model_snapshot,
        "behaviour_model_snapshot",
        engine
    )

    load_snapshot(
        academic_model_snapshot,
        "academic_model_snapshot",
        engine
    )

    # verify which students disappeared from the snapshot
    all_students = set(snapshot["student_key"])
    behaviour_students = set(
        behaviour_model_snapshot["student_key"]
    )
    missing = sorted(
        all_students - behaviour_students
    )
    print(missing)

    missing_students = snapshot[
        snapshot["student_key"].isin(missing)
    ][
        ["student_key",
         "grade_code_mode",
         "total_events",
         "active_days",
         "top_material_type"]
    ]

    print(missing_students)

def test_feature_engineering_v2():
    # load warehouse csvs
    fact_activity_log = pd.read_csv("data/warehouse/fact_activity_log.csv")
    dim_material = pd.read_csv("data/warehouse/dim_material.csv")
    fact_result = pd.read_csv("data/warehouse/fact_result.csv")
    dim_time = pd.read_csv("data/warehouse/dim_time.csv")
    dim_assessment = pd.read_csv("data/warehouse/dim_assessment.csv")
    dim_grade = pd.read_csv("data/warehouse/dim_grade.csv")
    
    behaviour = fe_v2.create_behaviour_features(
        fact_activity_log,
        dim_material,
        dim_time
    )
    print(behaviour.head())
    print(behaviour.columns)
    print(behaviour.shape)

    academic = fe_v2.create_academic_features(
        fact_result,
        dim_assessment,
        dim_grade
    )
    print(academic.head())
    print(academic.columns)
    print(academic.shape)

    snapshot = fe_v2.build_student_snapshot(
        behaviour,
        academic
    )

    print(snapshot.head())
    print(snapshot.shape)

    behaviour_model_snapshot = fe_v2.build_behaviour_model_snapshot(snapshot)
    print(behaviour_model_snapshot.head())
    print(behaviour_model_snapshot.shape)

    academic_model_snapshot = fe_v2.build_academic_model_snapshot(snapshot)

    print(academic_model_snapshot.head())
    print(academic_model_snapshot.shape)


    feature_store_path = Path("ml/feature_store")
    feature_store_path.mkdir(parents=True, exist_ok=True)

    snapshot.to_csv(
        feature_store_path / "student_snapshot.csv",
        index=False
    )

    behaviour_model_snapshot.to_csv(
        feature_store_path / "behaviour_model_snapshot.csv",
        index=False
    )

    academic_model_snapshot.to_csv(
        feature_store_path / "academic_model_snapshot_v2.csv",
        index=False
    )

    save_model_baselines(
        behaviour_model_snapshot,
        academic_model_snapshot
    )

    # Load snapshots to database
    engine = get_ml_engine()
    load_snapshot(
        snapshot,
        "student_snapshot",
        engine
    )

    load_snapshot(
        behaviour_model_snapshot,
        "behaviour_model_snapshot",
        engine
    )

    load_snapshot(
        academic_model_snapshot,
        "academic_model_snapshot_v2",
        engine
    )

    load_model_feature_stats(
        behaviour_model_snapshot,
        "model_feature_stats",
        engine
    )

    load_model_feature_baseline(
        behaviour_model_snapshot,
        "model_feature_baseline",
        engine
    )   

    # verify which students disappeared from the snapshot
    all_students = set(snapshot["student_key"])
    behaviour_students = set(
        behaviour_model_snapshot["student_key"]
    )
    missing = sorted(
        all_students - behaviour_students
    )
    print(missing)

    missing_students = snapshot[
        snapshot["student_key"].isin(missing)
    ][
        ["student_key",
         "grade_code_mode",
         "total_events",
         "active_days",
         "top_material_type"]
    ]

    print(missing_students)

def test_feature_engineering_v2_1():
    # load warehouse csvs
    fact_activity_log = pd.read_csv("data/warehouse/fact_activity_log.csv")
    dim_material = pd.read_csv("data/warehouse/dim_material.csv")
    fact_result = pd.read_csv("data/warehouse/fact_result.csv")
    dim_time = pd.read_csv("data/warehouse/dim_time.csv")
    dim_assessment = pd.read_csv("data/warehouse/dim_assessment.csv")
    dim_grade = pd.read_csv("data/warehouse/dim_grade.csv")
    
    behaviour = fe_v2_1.create_behaviour_features(
        fact_activity_log,
        dim_material,
        dim_time
    )
    print(behaviour.head())
    print(behaviour.columns)
    print(behaviour.shape)

    academic = fe_v2_1.create_academic_features(
        fact_result,
        dim_assessment,
        dim_grade
    )
    print(academic.head())
    print(academic.columns)
    print(academic.shape)

    academic_period_key = fact_activity_log["academic_period_key"].iloc[0]  # Historical S1 2025 dataset. In production this comes from the ETL lookup.

    snapshot = fe_v2_1.build_student_snapshot(
        behaviour,
        academic,
        academic_period_key=academic_period_key,
        snapshot_date=pd.Timestamp.today().date()
    )

    print(snapshot.head())
    print(snapshot.shape)

    behaviour_model_snapshot = fe_v2_1.build_behaviour_model_snapshot(snapshot)
    print(behaviour_model_snapshot.head())
    print(behaviour_model_snapshot.shape)

    academic_model_snapshot = fe_v2_1.build_academic_model_snapshot(snapshot)

    print(academic_model_snapshot.head())
    print(academic_model_snapshot.shape)


    feature_store_path = Path("ml/feature_store")
    feature_store_path.mkdir(parents=True, exist_ok=True)

    snapshot.to_csv(
        feature_store_path / "student_snapshot.csv",
        index=False
    )

    behaviour_model_snapshot.to_csv(
        feature_store_path / "behaviour_model_snapshot.csv",
        index=False
    )

    academic_model_snapshot.to_csv(
        feature_store_path / "academic_model_snapshot_v2.csv",
        index=False
    )

    save_model_baselines(
        behaviour_model_snapshot,
        academic_model_snapshot
    )

    # Load snapshots to database
    engine = get_ml_engine()
    load_snapshot(
        snapshot,
        "student_snapshot",
        engine
    )

    load_snapshot(
        behaviour_model_snapshot,
        "behaviour_model_snapshot",
        engine
    )

    load_snapshot(
        academic_model_snapshot,
        "academic_model_snapshot_v2",
        engine
    )

    load_model_feature_stats(
        behaviour_model_snapshot,
        "model_feature_stats",
        engine
    )

    load_model_feature_baseline(
        behaviour_model_snapshot,
        "model_feature_baseline",
        engine
    )   

    # verify which students disappeared from the snapshot
    all_students = set(snapshot["student_key"])
    behaviour_students = set(
        behaviour_model_snapshot["student_key"]
    )
    missing = sorted(
        all_students - behaviour_students
    )
    print(missing)

    missing_students = snapshot[
        snapshot["student_key"].isin(missing)
    ][
        ["student_key",
         "grade_code_mode",
         "total_events",
         "active_days",
         "top_material_type"]
    ]

    print(missing_students)

def test_behaviour_model_registry():
    registry_df = pd.DataFrame([{
        "model_name": "behaviour_model",
        "model_version": "v1",
        "algorithm": "Random Forest",
        "accuracy": 0.85,
        "recall": 0.82,
        "f1": 0.83,
        "roc_auc": 0.90,
        "model_path": "ml/models/behaviour_model_v1.pkl",
        "scaler_path": "ml/models/behaviour_scaler_v1.pkl",
        "created_at": datetime.now()
    }])

    load_model_registry(
        registry_df,
        "model_registry",
        get_ml_engine()        
        )

    
def test_academic_model_registry():
    registry_df = pd.DataFrame([{
        "model_name": "academic_model",
        "model_version": "v1",
        "algorithm": "Random Forest",
        "accuracy": 0.78, # later can replace with more robust metrics like precision, recall, f1, roc_auc
        "recall": 0.85,
        "f1": 0.82,
        "roc_auc": 0.88,
        "model_path": "ml/models/academic_model_v1.pkl",
        "scaler_path": "ml/models/academic_scaler_v1.pkl",
        "created_at": datetime.now()
    }])

    load_model_registry(
        registry_df,
        "model_registry",
        get_ml_engine()        
        )



if __name__ == "__main__":
    run_feature_engineering_v2_2_incremental()

    