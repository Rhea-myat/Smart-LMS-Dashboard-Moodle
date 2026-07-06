from sqlalchemy import text

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
            conn.execute(query, row.to_dict())

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

def load_prediction_run(df, engine): 
    df.to_sql(
        "prediction_runs",
        engine,
        if_exists="append",
        index=False
    )
