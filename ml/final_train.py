import json
from datetime import datetime
from pathlib import Path

import joblib

from ml.evaluate import (
    evaluate_academic_model,
    evaluate_behaviour_model,
    evaluate_ensemble,
)
from ml.register_model import register_models
from ml.train import (
    load_split_datasets,
    train_academic_model,
    train_behaviour_model,
)


MODEL_VERSION = "v1"
MODEL_DIR = Path(__file__).parent / "models"


def _write_json(path: Path, payload: dict):
    with open(path, "w") as file_obj:
        json.dump(payload, file_obj, indent=4)


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    datasets = load_split_datasets()

    behaviour_artifacts = train_behaviour_model(
        datasets["X_beh_train"],
        datasets["X_beh_val"],
        datasets["y_beh_train"],
        datasets["y_beh_val"]
    )
    academic_artifacts = train_academic_model(
        datasets["X_aca_train"],
        datasets["X_aca_val"],
        datasets["y_aca_train"],
        datasets["y_aca_val"]
    )

    behaviour_eval = evaluate_behaviour_model(
        behaviour_artifacts["model"],
        behaviour_artifacts["scaler"],
        datasets["X_beh_test"],
        datasets["y_beh_test"]
    )
    academic_eval = evaluate_academic_model(
        academic_artifacts["model"],
        datasets["X_aca_test"],
        datasets["y_aca_test"]
    )
    ensemble_eval = evaluate_ensemble(
        datasets["y_aca_test"],
        behaviour_eval["prob"],
        academic_eval["prob"]
    )

    joblib.dump(
        behaviour_artifacts["model"],
        MODEL_DIR / f"final_behaviour_model_{MODEL_VERSION}.pkl"
    )
    joblib.dump(
        behaviour_artifacts["scaler"],
        MODEL_DIR / f"final_behaviour_scaler_{MODEL_VERSION}.pkl"
    )
    joblib.dump(
        academic_artifacts["model"],
        MODEL_DIR / f"final_academic_model_{MODEL_VERSION}.pkl"
    )
    joblib.dump(
        list(datasets["X_beh_train"].columns),
        MODEL_DIR / f"final_behaviour_features_{MODEL_VERSION}.pkl"
    )
    joblib.dump(
        list(datasets["X_aca_train"].columns),
        MODEL_DIR / f"final_academic_features_{MODEL_VERSION}.pkl"
    )

    metadata_behaviour = {
        "model_name": "behaviour_model",
        "version": MODEL_VERSION,
        "model_type": "Logistic Regression",
        "created_at": datetime.now().isoformat(),
        "training": {
            "dataset": "train + validation",
            "evaluation_dataset": "test"
        },
        "hyperparameters": behaviour_artifacts["model"].get_params(),
        "metrics": behaviour_eval["metrics"],
        "artifacts": {
            "model": f"final_behaviour_model_{MODEL_VERSION}.pkl",
            "scaler": f"final_behaviour_scaler_{MODEL_VERSION}.pkl",
            "features": f"final_behaviour_features_{MODEL_VERSION}.pkl"
        }
    }
    _write_json(MODEL_DIR / f"behaviour_model_metadata_{MODEL_VERSION}.json", metadata_behaviour)

    metadata_academic = {
        "model_name": "academic_model",
        "version": MODEL_VERSION,
        "model_type": "Random Forest",
        "created_at": datetime.now().isoformat(),
        "training": {
            "dataset": "train + validation",
            "evaluation_dataset": "test"
        },
        "hyperparameters": academic_artifacts["model"].get_params(),
        "metrics": academic_eval["metrics"],
        "artifacts": {
            "model": f"final_academic_model_{MODEL_VERSION}.pkl",
            "features": f"final_academic_features_{MODEL_VERSION}.pkl"
        }
    }
    _write_json(MODEL_DIR / f"academic_model_metadata_{MODEL_VERSION}.json", metadata_academic)

    ensemble_metadata = {
        "model_name": "ensemble_risk_model",
        "version": MODEL_VERSION,
        "ensemble_type": "Weighted Average",
        "created_at": datetime.now().isoformat(),
        "components": {
            "behaviour_model": f"final_behaviour_model_{MODEL_VERSION}.pkl",
            "academic_model": f"final_academic_model_{MODEL_VERSION}.pkl",
            "behaviour_weight": 0.5,
            "academic_weight": 0.5,
            "threshold": 0.5
        },
        "metrics": ensemble_eval["metrics"]
    }
    _write_json(MODEL_DIR / f"ensemble_model_metadata_{MODEL_VERSION}.json", ensemble_metadata)

    ensemble_config = {
        "version": MODEL_VERSION,
        "ensemble_type": "weighted_average",
        "behaviour_weight": 0.5,
        "academic_weight": 0.5,
        "threshold": 0.5,
        "behaviour_model": f"final_behaviour_model_{MODEL_VERSION}.pkl",
        "academic_model": f"final_academic_model_{MODEL_VERSION}.pkl",
        "behaviour_scaler": f"final_behaviour_scaler_{MODEL_VERSION}.pkl",
        "behaviour_features": f"final_behaviour_features_{MODEL_VERSION}.pkl",
        "academic_features": f"final_academic_features_{MODEL_VERSION}.pkl",
        "feature_baseline": "model_feature_baseline.csv",
        "feature_stats": "model_feature_stats.csv"
    }
    _write_json(MODEL_DIR / f"ensemble_config_{MODEL_VERSION}.json", ensemble_config)

    registry_df = register_models(MODEL_DIR)
    print(registry_df)


if __name__ == "__main__":
    main()