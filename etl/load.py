
# for initial loading to MySQL
def load_to_mysql_initial(df, table_name, engine):
    df.to_sql(
        table_name,
        engine,
        if_exists="replace",
        index=False
    )

# incremental loading to MySQL - Production use 
def load_to_mysql_incremental(df, table_name, engine, key_columns):
    from sqlalchemy import text

    with engine.connect() as conn:
        for _, row in df.iterrows():
            where_clause = " AND ".join([f"{col} = :{col}" for col in key_columns])
            query = text(f"""
                INSERT INTO {table_name} ({', '.join(df.columns)})
                VALUES ({', '.join([f":{col}" for col in df.columns])})
                ON DUPLICATE KEY UPDATE
                {', '.join([f"{col} = VALUES({col})" for col in df.columns if col not in key_columns])}
            """)
            conn.execute(query, **row.to_dict())

