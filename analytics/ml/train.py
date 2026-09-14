from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


DATASET_DIR = Path(__file__).parent / "datasets"


def load_split_datasets(dataset_dir: Path | None = None) -> dict:
    dataset_dir = dataset_dir or DATASET_DIR

    return {
        "X_beh_train": pd.read_csv(dataset_dir / "X_beh_train.csv"),
        "X_beh_val": pd.read_csv(dataset_dir / "X_beh_val.csv"),
        "X_beh_test": pd.read_csv(dataset_dir / "X_beh_test.csv"),
        "y_beh_train": pd.read_csv(dataset_dir / "y_beh_train.csv").squeeze("columns"),
        "y_beh_val": pd.read_csv(dataset_dir / "y_beh_val.csv").squeeze("columns"),
        "y_beh_test": pd.read_csv(dataset_dir / "y_beh_test.csv").squeeze("columns"),
        "X_aca_train": pd.read_csv(dataset_dir / "X_aca_train.csv"),
        "X_aca_val": pd.read_csv(dataset_dir / "X_aca_val.csv"),
        "X_aca_test": pd.read_csv(dataset_dir / "X_aca_test.csv"),
        "y_aca_train": pd.read_csv(dataset_dir / "y_aca_train.csv").squeeze("columns"),
        "y_aca_val": pd.read_csv(dataset_dir / "y_aca_val.csv").squeeze("columns"),
        "y_aca_test": pd.read_csv(dataset_dir / "y_aca_test.csv").squeeze("columns")
    }


def combine_train_validation(X_train, X_val, y_train, y_val):
    X_trainval = pd.concat([X_train, X_val], ignore_index=True)
    y_trainval = pd.concat([y_train, y_val], ignore_index=True)
    return X_trainval, y_trainval


def train_behaviour_model(X_beh_train, X_beh_val, y_beh_train, y_beh_val) -> dict:
    X_beh_trainval, y_beh_trainval = combine_train_validation(
        X_beh_train,
        X_beh_val,
        y_beh_train,
        y_beh_val
    )

    behaviour_scaler = StandardScaler()
    X_beh_trainval_scaled = behaviour_scaler.fit_transform(X_beh_trainval)

    behaviour_model = LogisticRegression(
        C=0.1,
        penalty="l2",
        solver="lbfgs",
        max_iter=1000,
        random_state=42
    )
    behaviour_model.fit(X_beh_trainval_scaled, y_beh_trainval)

    return {
        "model": behaviour_model,
        "scaler": behaviour_scaler,
        "X_trainval": X_beh_trainval,
        "X_trainval_scaled": X_beh_trainval_scaled,
        "y_trainval": y_beh_trainval
    }


def train_academic_model(X_aca_train, X_aca_val, y_aca_train, y_aca_val) -> dict:
    X_aca_trainval, y_aca_trainval = combine_train_validation(
        X_aca_train,
        X_aca_val,
        y_aca_train,
        y_aca_val
    )

    academic_model = RandomForestClassifier(random_state=42)
    academic_model.fit(X_aca_trainval, y_aca_trainval)

    return {
        "model": academic_model,
        "X_trainval": X_aca_trainval,
        "y_trainval": y_aca_trainval
    }