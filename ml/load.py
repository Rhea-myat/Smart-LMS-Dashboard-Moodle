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