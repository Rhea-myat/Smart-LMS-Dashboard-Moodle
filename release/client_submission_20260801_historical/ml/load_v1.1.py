from sqlalchemy import text
import pandas as pd

def load_snapshot(df, table_name, engine):
    df.to_sql(
        table_name,
        engine,
        if_exists="replace",
        index=False
    )

def append_snapshot(df, table_name, engine):
    df.to_sql(
        table_name,
        engine,
        if_exists="append",
        index=False
    )

def upsert_table(df, table_name, engine, key_columns):
    if df.empty:
        print(f"No rows to upsert into {table_name}")
        return

    columns = list(df.columns)

    update_cols = [
        col for col in columns
        if col not in key_columns
    ]

    insert_cols = ", ".join(columns)
    value_cols = ", ".join([f":{col}" for col in columns])
    update_clause = ", ".join([
        f"{col} = VALUES({col})"
        for col in update_cols
    ])

    query = text(f"""
        INSERT INTO {table_name} ({insert_cols})
        VALUES ({value_cols})
        ON DUPLICATE KEY UPDATE
        {update_clause}
    """)

    with engine.begin() as conn:
        for _, row in df.iterrows():
            payload = {
                key: (None if pd.isna(value) else value)
                for key, value in row.to_dict().items()
            }
            conn.execute(query, payload)

def load_model_registry(df, table_name, engine):
    df.to_sql(
        table_name,
        engine,
        if_exists="append",
        index=False
    )

def load_model_feature_stats(df, table_name, engine):
    df.to_sql(
        table_name,
        engine,
        if_exists="replace",
        index=False
    )

def load_model_feature_baseline(df, table_name, engine):
    df.to_sql(
        table_name,
        engine,
        if_exists="replace",
        index=False
    )


def load_prediction_result(df, engine):
    upsert_table(
        df,
        "prediction_result",
        engine,
        [
            "student_key",
            "course_key",
            "academic_period_key",
            "snapshot_date",
            "ensemble_model_version"
        ]
    )


def prune_stale_prediction_result(engine, target_snapshot_date, active_course_keys):
    target_snapshot_date = str(target_snapshot_date).strip()
    if target_snapshot_date == "":
        return 0

    with engine.begin() as conn:
        if active_course_keys:
            placeholders = []
            params = {"target_snapshot_date": target_snapshot_date}
            for idx, key in enumerate(active_course_keys):
                param_name = f"course_key_{idx}"
                placeholders.append(f":{param_name}")
                params[param_name] = str(key)

            query = text(
                """
                DELETE FROM prediction_result
                 WHERE snapshot_date < :target_snapshot_date
                   AND CAST(course_key AS CHAR) NOT IN (""" + ", ".join(placeholders) + ")"
            )
            result = conn.execute(query, params)
            return int(result.rowcount or 0)

        query = text(
            """
            DELETE FROM prediction_result
             WHERE snapshot_date < :target_snapshot_date
            """
        )
        result = conn.execute(query, {"target_snapshot_date": target_snapshot_date})
        return int(result.rowcount or 0)

def load_prediction_run(df, engine): 
    df.to_sql(
        "prediction_runs",
        engine,
        if_exists="append",
        index=False
    )
