# ml/preprocessing.py

import pandas as pd
from pathlib import Path

from sqlalchemy.orm import Load

"""
# load feature baseline values from the deployed artifact
def load_feature_baseline(model_dir: Path):
    baseline = pd.read_csv(
        model_dir / "feature_baseline_v1.csv"
    )

    baseline_dict = dict(
        zip(
            baseline["feature"],
            baseline["baseline_value"]
        )
    )

    return baseline_dict
"""


def split_metadata(
    snapshot: pd.DataFrame,
    metadata_cols: list
):
    """
    Separate metadata from model features.
    """

    metadata = snapshot[metadata_cols].copy()

    features = snapshot.drop(
        columns=metadata_cols,
        errors="ignore"
    ).copy()

    return metadata, features


def prepare_features(
    X: pd.DataFrame,
    feature_list: list
):
    """
    Ensure prediction features match the training schema.

    1. Create missing columns.
    2. Reorder columns.
    """

    X = X.copy()

    for feature in feature_list:

        if feature not in X.columns:

            # Feature absent in current snapshot
            X[feature] = 0

    X = X[feature_list]

    return X


def apply_feature_baseline(
    X: pd.DataFrame,
    baseline_dict: dict
):
    """
    Replace missing values using the
    training feature baselines.
    """

    X = X.copy()

    for feature in X.columns:

        if feature in baseline_dict:

            X[feature] = X[feature].fillna(
                baseline_dict[feature]
            )

    return X


def scale_behaviour_features(
    X: pd.DataFrame,
    scaler
):
    """
    Apply saved StandardScaler
    for behaviour model.
    """

    return scaler.transform(X)


def validate_feature_schema(
    X: pd.DataFrame,
    feature_list: list
):
    """
    Verify feature order before prediction.
    """

    missing = [
        feature
        for feature in feature_list
        if feature not in X.columns
    ]

    extra = [
        feature
        for feature in X.columns
        if feature not in feature_list
    ]

    return {
        "missing_features": missing,
        "extra_features": extra
    }