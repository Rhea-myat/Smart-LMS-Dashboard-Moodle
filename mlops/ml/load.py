from sqlalchemy import engine


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
    # insert new records
    # update existing records based on key_columns
    pass

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
    df.to_sql(
        "prediction_result",
        engine,
        if_exists="append",
        index=False
    )

def load_prediction_run(df, engine): 
    df.to_sql(
        "prediction_runs",
        engine,
        if_exists="append",
        index=False
    )
