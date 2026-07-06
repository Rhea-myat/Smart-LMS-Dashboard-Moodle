import json
import importlib.util
from pathlib import Path

import joblib
import pandas as pd

def _load_preprocessing_v1_1():
    module_path = Path(__file__).resolve().parent / "preprocessing_v1.1.py"
    spec = importlib.util.spec_from_file_location("ml_preprocessing_v1_1", module_path)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load preprocessing module from {module_path}")
    spec.loader.exec_module(module)
    return module


_pre_v1_1 = _load_preprocessing_v1_1()

from ml.ensemble import (
    weighted_average,
    apply_threshold,
    build_prediction_result
)


def load_configured_feature_baseline(model_dir: Path, config: dict):
    baseline_name = config.get("feature_baseline", "feature_baseline_v1.csv")

    candidates = [
        model_dir / baseline_name,
        model_dir.parent.parent / "baselines" / baseline_name,
        model_dir.parent.parent / "baselines" / Path(baseline_name).name
    ]

    for path in candidates:
        if path.exists():
            baseline = pd.read_csv(path)

            if {"feature", "baseline_value"}.issubset(baseline.columns):
                return dict(zip(baseline["feature"], baseline["baseline_value"]))

            if {"feature_name", "feature_value"}.issubset(baseline.columns):
                baseline = baseline.copy()
                baseline["feature_value"] = pd.to_numeric(
                    baseline["feature_value"],
                    errors="coerce"
                )

                baseline_values = (
                    baseline.dropna(subset=["feature_value"])
                    .groupby("feature_name", as_index=False)["feature_value"]
                    .mean()
                )
                return dict(
                    zip(
                        baseline_values["feature_name"],
                        baseline_values["feature_value"]
                    )
                )

            raise ValueError(
                f"Unsupported feature baseline schema in {path}."
            )

    return None

def load_ensemble_artifacts(model_dir: Path):
    config_path = model_dir / "ensemble_config_v1.json"

    with open(config_path, "r") as f:
        config = json.load(f)

    config.setdefault("version", "v1")
    config.setdefault("behaviour_scaler", "final_behaviour_scaler_v1.pkl")
    config.setdefault("behaviour_features", "final_behaviour_features_v1.pkl")
    config.setdefault("academic_features", "final_academic_features_v1.pkl")

    return {
        "config": config,
        "behaviour_model": joblib.load(model_dir / config["behaviour_model"]),
        "academic_model": joblib.load(model_dir / config["academic_model"]),
        "behaviour_scaler": joblib.load(model_dir / config["behaviour_scaler"]),
        "behaviour_features": joblib.load(model_dir / config["behaviour_features"]),
        "academic_features": joblib.load(model_dir / config["academic_features"])
    }


def predict_behaviour(behaviour_snapshot, artifacts, baseline_dict=None):
    X_beh = _pre_v1_1.prepare_features(
        behaviour_snapshot,
        artifacts["behaviour_features"]
    )

    if baseline_dict is not None:
        X_beh = _pre_v1_1.apply_feature_baseline(
            X_beh,
            baseline_dict
        )

    X_beh_scaled = artifacts["behaviour_scaler"].transform(X_beh)

    return artifacts["behaviour_model"].predict_proba(X_beh_scaled)[:, 1]


def predict_academic(academic_snapshot, artifacts, baseline_dict=None):
    X_aca = _pre_v1_1.prepare_features(
        academic_snapshot,
        artifacts["academic_features"]
    )

    if baseline_dict is not None:
        X_aca = _pre_v1_1.apply_feature_baseline(
            X_aca,
            baseline_dict
        )

    return artifacts["academic_model"].predict_proba(X_aca)[:, 1]


def predict_ensemble(
    metadata: pd.DataFrame,
    behaviour_snapshot: pd.DataFrame,
    academic_snapshot: pd.DataFrame,
    model_dir: Path
):
    artifacts = load_ensemble_artifacts(model_dir)
    config = artifacts["config"]

    baseline_dict = load_configured_feature_baseline(model_dir, config)

    behaviour_prob = predict_behaviour(
        behaviour_snapshot,
        artifacts,
        baseline_dict
    )

    academic_prob = predict_academic(
        academic_snapshot,
        artifacts,
        baseline_dict
    )

    final_prob = weighted_average(
        behaviour_prob,
        academic_prob,
        config["behaviour_weight"],
        config["academic_weight"]
    )

    final_label = apply_threshold(
        final_prob,
        config["threshold"]
    )

    result = build_prediction_result(
        metadata,
        behaviour_prob,
        academic_prob,
        final_prob,
        final_label,
        config["version"]
    )

    return result