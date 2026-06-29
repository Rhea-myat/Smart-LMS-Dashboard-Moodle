import pandas as pd
import os
from pathlib import Path
from ml import feature_engineering as fe_v1
from ml import feature_engineering_v2 as fe_v2
from ml import feature_engineering_v2_1 as fe_v2_1

from ml.db import get_ml_engine
from ml.load import load_snapshot, load_model_registry, load_model_feature_stats, load_model_feature_baseline
from ml.monitoring.drift_utils import save_model_baselines
from datetime import datetime   


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
    test_feature_engineering_v2_1()
    test_behaviour_model_registry()
    test_academic_model_registry()

    