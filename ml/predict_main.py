
# ml/predict_main.py

from pathlib import Path
import pandas as pd

from ml.db import get_ml_engine
from ml.load import load_prediction_result
from ml.preprocessing import split_metadata
from ml.predict import predict_ensemble


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

    metadata, behaviour_features = split_metadata(
        behaviour_snapshot,
        metadata_cols
    )

    _, academic_features = split_metadata(
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

    load_prediction_result(
        prediction_result,
        ml_engine
    )

    print("Prediction pipeline completed.")
    print(prediction_result.head())


if __name__ == "__main__":
    main()