import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from ml.db import get_ml_engine
from ml.load import load_model_registry


MODEL_DIR = Path(__file__).parent / "models"


def _load_json(path: Path) -> dict:
    with open(path, "r") as file_obj:
        return json.load(file_obj)


def _registry_row_from_metadata(metadata: dict, model_dir: Path, metadata_file: Path) -> dict:
    model_name = metadata["model_name"]
    metrics = metadata.get("metrics", {})

    if model_name == "ensemble_risk_model":
        algorithm = metadata.get("ensemble_type", "Ensemble")
        model_path = str(model_dir / "ensemble_config_v1.json")
        scaler_path = None
    else:
        algorithm = metadata.get("model_type", "Unknown")
        artifacts = metadata.get("artifacts", {})
        model_path = str(model_dir / artifacts.get("model", metadata_file.name))
        scaler_name = artifacts.get("scaler")
        scaler_path = str(model_dir / scaler_name) if scaler_name else None

    created_at = metadata.get("created_at", datetime.now().isoformat())

    return {
        "model_name": model_name,
        "model_version": metadata.get("version", "v1"),
        "algorithm": algorithm,
        "accuracy": metrics.get("accuracy"),
        "recall": metrics.get("recall"),
        "f1": metrics.get("f1_score"),
        "roc_auc": metrics.get("roc_auc"),
        "model_path": model_path,
        "scaler_path": scaler_path,
        "created_at": created_at
    }


def build_registry_records(model_dir: Path | None = None) -> pd.DataFrame:
    model_dir = model_dir or MODEL_DIR
    metadata_files = [
        model_dir / "behaviour_model_metadata_v1.json",
        model_dir / "academic_model_metadata_v1.json",
        model_dir / "ensemble_model_metadata_v1.json"
    ]

    rows = []
    for metadata_file in metadata_files:
        metadata = _load_json(metadata_file)
        rows.append(_registry_row_from_metadata(metadata, model_dir, metadata_file))

    return pd.DataFrame(rows)


def register_models(model_dir: Path | None = None):
    registry_df = build_registry_records(model_dir)
    load_model_registry(registry_df, "model_registry", get_ml_engine())
    return registry_df


if __name__ == "__main__":
    result = register_models()
    print(result)