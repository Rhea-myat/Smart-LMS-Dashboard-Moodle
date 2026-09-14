from pathlib import Path

import pandas as pd


def _build_model_feature_stats(model_version, snapshot_df):
    feature_cols = [
        col for col in snapshot_df.columns
        if col not in {"student_key", "course_key", "snapshot_date", "risk_label"}
    ]

    stats_rows = []
    for feature_name in feature_cols:
        feature_series = pd.to_numeric(snapshot_df[feature_name], errors="coerce")
        if feature_series.notna().sum() == 0:
            continue

        stats_rows.append({
            "model_version": model_version,
            "feature_name": feature_name,
            "mean": feature_series.mean(),
            "std": feature_series.std(),
            "min": feature_series.min(),
            "q1": feature_series.quantile(0.25),
            "median": feature_series.median(),
            "q3": feature_series.quantile(0.75),
            "max": feature_series.max()
        })

    return pd.DataFrame(stats_rows)


def _build_model_feature_baseline(model_version, snapshot_df):
    baseline_cols = [
        col for col in snapshot_df.columns
        if col not in {"student_key", "course_key", "snapshot_date", "risk_label"}
    ]

    baseline_df = snapshot_df.melt(
        id_vars=["student_key", "course_key", "snapshot_date"],
        value_vars=baseline_cols,
        var_name="feature_name",
        value_name="feature_value"
    )

    baseline_df.insert(0, "model_version", model_version)

    return baseline_df[[
        "model_version",
        "student_key",
        "course_key",
        "feature_name",
        "feature_value",
        "snapshot_date"
    ]]


def save_model_baselines(behaviour_model_snapshot, academic_model_snapshot):
    baselines_path = Path("ml/baselines")
    baselines_path.mkdir(parents=True, exist_ok=True)

    behaviour_version = "behaviour_v1"
    academic_version = "academic_v1"

    behaviour_stats = _build_model_feature_stats(
        behaviour_version,
        behaviour_model_snapshot
    )
    academic_stats = _build_model_feature_stats(
        academic_version,
        academic_model_snapshot
    )
    model_feature_stats = pd.concat(
        [behaviour_stats, academic_stats],
        ignore_index=True
    )

    behaviour_baseline = _build_model_feature_baseline(
        behaviour_version,
        behaviour_model_snapshot
    )
    academic_baseline = _build_model_feature_baseline(
        academic_version,
        academic_model_snapshot
    )
    model_feature_baseline = pd.concat(
        [behaviour_baseline, academic_baseline],
        ignore_index=True
    )

    model_feature_stats.to_csv(
        baselines_path / "model_feature_stats.csv",
        index=False
    )
    model_feature_baseline.to_csv(
        baselines_path / "model_feature_baseline.csv",
        index=False
    )

    print("Saved:", baselines_path / "model_feature_stats.csv")
    print("Saved:", baselines_path / "model_feature_baseline.csv")
