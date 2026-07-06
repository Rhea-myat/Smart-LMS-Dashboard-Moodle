
from pathlib import Path
import importlib.util
import pandas as pd
from datetime import datetime, timezone

from ml.db import get_ml_engine
from ml.predict import predict_ensemble


def _load_versioned_module(module_name: str, relative_path: str):
    module_path = Path(__file__).resolve().parent / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module from {module_path}")
    spec.loader.exec_module(module)
    return module


fe_v2_2 = _load_versioned_module("ml_feature_engineering_v2_2", "feature_engineering_v2.2.py")
pre_v1_1 = _load_versioned_module("ml_preprocessing_v1_1", "preprocessing_v1.1.py")
load_v1_1 = _load_versioned_module("ml_load_v1_1", "load_v1.1.py")


def _append_prediction_run_log(logs_dir: Path, run_payload: dict):
    logs_dir.mkdir(parents=True, exist_ok=True)

    csv_path = logs_dir / "prediction_run_logs.csv"
    debug_path = logs_dir / "prediction_run_debug.log"

    row_df = pd.DataFrame([run_payload])
    if csv_path.exists():
        row_df.to_csv(csv_path, mode="a", header=False, index=False)
    else:
        row_df.to_csv(csv_path, index=False)

    debug_line = (
        f"{run_payload['run_timestamp_utc']} | run_id={run_payload['run_id']} | "
        f"status={run_payload['status']} | target_snapshot_date={run_payload['target_snapshot_date']} | "
        f"rows_scored={run_payload['rows_scored']} | rows_inserted={run_payload['rows_inserted']} | "
        f"message={run_payload['message']}"
    )
    with open(debug_path, "a", encoding="utf-8") as f:
        f.write(debug_line + "\n")


def _latest_snapshot_only(behaviour_snapshot: pd.DataFrame, academic_snapshot: pd.DataFrame):
    latest_snapshot_date = pd.to_datetime(
        behaviour_snapshot["snapshot_date"],
        errors="coerce"
    ).max()

    if pd.isna(latest_snapshot_date):
        raise ValueError("No valid snapshot_date found in behaviour prediction snapshot.")

    latest_date_str = latest_snapshot_date.date().isoformat()
    behaviour_latest = behaviour_snapshot[
        pd.to_datetime(behaviour_snapshot["snapshot_date"], errors="coerce").dt.date.astype(str) == latest_date_str
    ].copy()
    academic_latest = academic_snapshot[
        pd.to_datetime(academic_snapshot["snapshot_date"], errors="coerce").dt.date.astype(str) == latest_date_str
    ].copy()

    return behaviour_latest, academic_latest, latest_date_str


def _filter_unseen_predictions(prediction_result: pd.DataFrame, ml_engine):
    from sqlalchemy import inspect

    if prediction_result.empty:
        return prediction_result

    inspector = inspect(ml_engine)
    if not inspector.has_table("prediction_result"):
        return prediction_result

    existing_df = pd.read_sql(
        """
        SELECT
            student_key,
            course_key,
            academic_period_key,
            snapshot_date,
            ensemble_model_version
        FROM prediction_result
        """,
        ml_engine
    )

    if existing_df.empty:
        return prediction_result

    key_cols = [
        "student_key",
        "course_key",
        "academic_period_key",
        "snapshot_date",
        "ensemble_model_version",
    ]

    incoming = prediction_result.copy()
    existing = existing_df.copy()

    for col in key_cols:
        incoming[col] = incoming[col].astype(str).str.strip()
        existing[col] = existing[col].astype(str).str.strip()

    merged = incoming.merge(
        existing[key_cols].drop_duplicates(),
        on=key_cols,
        how="left",
        indicator=True,
    )

    return prediction_result.loc[merged["_merge"] == "left_only"].copy()


def _norm_key_series(series):
    return series.astype(str).str.strip()


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
    return merged_df


def resolve_model_dir(project_root: Path) -> Path:
    primary_dir = project_root / "ml" / "models"
    if (primary_dir / "ensemble_config_v1.json").exists():
        return primary_dir

    fallback_dir = primary_dir / "experimental"
    return fallback_dir

def main():
    project_root = Path.cwd()
    model_dir = resolve_model_dir(project_root)
    feature_store_dir = project_root / "ml" / "feature_store"
    prediction_store_dir = project_root / "ml" / "prediction_store"

    prediction_store_dir.mkdir(parents=True, exist_ok=True)

    # Load latest feature snapshots
    behaviour_snapshot = pd.read_csv(
        feature_store_dir / "behaviour_model_snapshot.csv"
    )

    academic_snapshot = pd.read_csv(
        feature_store_dir / "academic_model_snapshot_v2.csv"
    )

    metadata_cols = [
        "student_key",
        "course_key",
        "academic_period_key",
        "snapshot_date"
    ]

    latest_snapshot_date = pd.to_datetime(
        behaviour_snapshot["snapshot_date"],
        errors="coerce"
    ).max()

    if pd.isna(latest_snapshot_date):
        raise ValueError("No valid snapshot_date found in behaviour_model_snapshot.csv")

    latest_date_str = latest_snapshot_date.date().isoformat()
    behaviour_snapshot = behaviour_snapshot[
        pd.to_datetime(behaviour_snapshot["snapshot_date"], errors="coerce").dt.date.astype(str) == latest_date_str
    ].copy()
    academic_snapshot = academic_snapshot[
        pd.to_datetime(academic_snapshot["snapshot_date"], errors="coerce").dt.date.astype(str) == latest_date_str
    ].copy()

    metadata, behaviour_features = pre_v1_1.split_metadata(
        behaviour_snapshot,
        metadata_cols
    )

    _, academic_features = pre_v1_1.split_metadata(
        academic_snapshot,
        metadata_cols
    )

    prediction_result = predict_ensemble(
        metadata=metadata,
        behaviour_snapshot=behaviour_features,
        academic_snapshot=academic_features,
        model_dir=model_dir
    )

    prediction_result.to_csv(
        prediction_store_dir / "prediction_result.csv",
        index=False
    )

    ml_engine = get_ml_engine()

    load_v1_1.load_prediction_result(
        prediction_result,
        ml_engine
    )

    print("Prediction pipeline completed.")
    print(prediction_result.head())

def run_online_prediction():
    project_root = Path.cwd()
    model_dir = resolve_model_dir(project_root)
    feature_store_dir = project_root / "ml" / "feature_store"
    prediction_store_dir = project_root / "ml" / "prediction_store"
    logs_dir = project_root / "logs"

    run_timestamp = datetime.now(timezone.utc)
    run_id = run_timestamp.strftime("pred_%Y%m%dT%H%M%S%fZ")

    prediction_store_dir.mkdir(parents=True, exist_ok=True)

    behaviour_snapshot_path = feature_store_dir / "behaviour_prediction_snapshot_latest.csv"
    academic_snapshot_path = feature_store_dir / "academic_prediction_snapshot_latest.csv"

    if not behaviour_snapshot_path.exists() or not academic_snapshot_path.exists():
        behaviour_snapshot_path = feature_store_dir / "behaviour_prediction_snapshot.csv"
        academic_snapshot_path = feature_store_dir / "academic_prediction_snapshot.csv"

    if not behaviour_snapshot_path.exists() or not academic_snapshot_path.exists():
        raise FileNotFoundError(
            "Engineered prediction snapshots are missing. "
            "Generate feature snapshots first before running online prediction."
        )

    behaviour_snapshot = pd.read_csv(behaviour_snapshot_path)
    academic_snapshot = pd.read_csv(academic_snapshot_path)

    behaviour_snapshot, academic_snapshot, latest_date_str = _latest_snapshot_only(
        behaviour_snapshot,
        academic_snapshot,
    )

    run_snapshot_date = pd.Timestamp.today().date().isoformat()
    behaviour_snapshot["snapshot_date"] = run_snapshot_date
    academic_snapshot["snapshot_date"] = run_snapshot_date

    # Keep latest aliases aligned to online prediction run date.
    behaviour_latest_alias = feature_store_dir / "behaviour_prediction_snapshot_latest.csv"
    academic_latest_alias = feature_store_dir / "academic_prediction_snapshot_latest.csv"
    behaviour_snapshot.to_csv(behaviour_latest_alias, index=False)
    academic_snapshot.to_csv(academic_latest_alias, index=False)

    key_cols = ["student_key", "course_key", "academic_period_key", "snapshot_date"]
    _upsert_snapshot_csv(feature_store_dir / "behaviour_prediction_snapshot.csv", behaviour_snapshot, key_cols)
    _upsert_snapshot_csv(feature_store_dir / "academic_prediction_snapshot.csv", academic_snapshot, key_cols)

    ml_engine = get_ml_engine()

    metadata_cols = [
        "student_key",
        "course_key",
        "academic_period_key",
        "snapshot_date"
    ]

    metadata, behaviour_features = pre_v1_1.split_metadata(
        behaviour_snapshot,
        metadata_cols
    )

    _, academic_features = pre_v1_1.split_metadata(
        academic_snapshot,
        metadata_cols
    )

    prediction_result = predict_ensemble(
        metadata=metadata,
        behaviour_snapshot=behaviour_features,
        academic_snapshot=academic_features,
        model_dir=model_dir
    )

    prediction_result = _filter_unseen_predictions(prediction_result, ml_engine)

    if prediction_result.empty:
        existing_today = pd.read_sql(
            """
            SELECT
                student_key,
                course_key,
                academic_period_key,
                snapshot_date,
                behaviour_probability,
                academic_probability,
                final_risk_probability,
                final_risk_label,
                ensemble_model_version
            FROM prediction_result
            WHERE snapshot_date = %(snapshot_date)s
            """,
            ml_engine,
            params={"snapshot_date": run_snapshot_date},
        )

        if not existing_today.empty:
            existing_today.to_csv(
                prediction_store_dir / "prediction_result.csv",
                index=False
            )

        _append_prediction_run_log(
            logs_dir,
            {
                "run_id": run_id,
                "run_timestamp_utc": run_timestamp.isoformat(),
                "pipeline": "online_prediction",
                "status": "skipped_no_new_rows",
                "target_snapshot_date": run_snapshot_date,
                "target_academic_period_keys": ",".join(
                    sorted(
                        behaviour_snapshot["academic_period_key"]
                        .dropna()
                        .astype(int)
                        .astype(str)
                        .unique()
                        .tolist()
                    )
                ) if "academic_period_key" in behaviour_snapshot.columns else "",
                "input_behaviour_rows": int(len(behaviour_snapshot)),
                "input_academic_rows": int(len(academic_snapshot)),
                "rows_scored": 0,
                "rows_inserted": 0,
                "prediction_store_path": str(prediction_store_dir / "prediction_result.csv"),
                "model_dir": str(model_dir),
                "message": "No unseen Moodle rows for target snapshot date; reused existing prediction_result rows.",
            },
        )

        print(
            "Online prediction skipped. "
            f"No new Moodle rows to score for snapshot_date={run_snapshot_date}."
        )
        return

    prediction_result.to_csv(
        prediction_store_dir / "prediction_result.csv",
        index=False
    )

    load_v1_1.load_prediction_result(prediction_result, ml_engine)

    _append_prediction_run_log(
        logs_dir,
        {
            "run_id": run_id,
            "run_timestamp_utc": run_timestamp.isoformat(),
            "pipeline": "online_prediction",
            "status": "completed",
            "target_snapshot_date": run_snapshot_date,
            "target_academic_period_keys": ",".join(
                sorted(
                    behaviour_snapshot["academic_period_key"]
                    .dropna()
                    .astype(int)
                    .astype(str)
                    .unique()
                    .tolist()
                )
            ) if "academic_period_key" in behaviour_snapshot.columns else "",
            "input_behaviour_rows": int(len(behaviour_snapshot)),
            "input_academic_rows": int(len(academic_snapshot)),
            "rows_scored": int(len(prediction_result)),
            "rows_inserted": int(len(prediction_result)),
            "prediction_store_path": str(prediction_store_dir / "prediction_result.csv"),
            "model_dir": str(model_dir),
            "message": "Prediction scored and upserted successfully.",
        },
    )

    print("Online prediction pipeline completed.")
    print(prediction_result.head())

if __name__ == "__main__":
    #main()
    run_online_prediction() 
