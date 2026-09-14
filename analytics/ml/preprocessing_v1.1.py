# ml/preprocessing.py
import pandas as pd


def split_metadata(
    snapshot: pd.DataFrame,
    metadata_cols: list
):
    """
    Separate metadata from model features.
    """

    existing_metadata = [
        col for col in metadata_cols
        if col in snapshot.columns
    ]

    metadata = snapshot[existing_metadata].copy()

    features = snapshot.drop(
        columns=existing_metadata,
        errors="ignore"
    ).copy()

    return metadata, features


def prepare_features(X: pd.DataFrame, feature_list: list):
    X = X.copy()

    extra_cols = [
        col for col in X.columns
        if col not in feature_list
    ]

    if extra_cols:
        print(f"Dropping unexpected features: {extra_cols}")

    X = X.reindex(columns=feature_list, fill_value=0)
    X = X.fillna(0)

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

