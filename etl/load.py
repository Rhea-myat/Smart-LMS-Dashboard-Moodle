from etl.logging_utils import write_log
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

"""
def get_connection(): 
    return mysql.connector.connect(
        host="localhost",
        port=8889, 
        user="root",
        password="password",
        database="analytics_db"
    )
"""

def build_dimensions(transformed_df):
    dim_course = transformed_df[["courseid"]].drop_duplicates()
    dim_course["course_name"] = "Course " + dim_course["courseid"].astype(str)

    dim_user = transformed_df[["userid"]].drop_duplicates()
    dim_user["username"] = "User " + dim_user["userid"].astype(str)

    dim_activity = transformed_df[
        ["component", "event_context", "event_name"]
    ].drop_duplicates()

    return {
    "dim_course": dim_course,
    "dim_user": dim_user,
    "dim_activity": dim_activity
}

def build_facts(transformed_df):
    fact_engagement = (
        transformed_df
        .groupby(["courseid", "userid", "component", "event_context", "event_name"])
        .size()
        .reset_index(name="event_count")
    )

    return fact_engagement

def load(transformed_df, engine, mode="initial"):
    dimensions = build_dimensions(transformed_df)
    for name, df in dimensions.items():
        write_log(f"Dimension {name} built with {len(df)} records.")
    fact_engagement = build_facts(transformed_df)
    write_log(f"Fact table built with {len(fact_engagement)} records.")

    if mode == "initial":
        load_to_mysql_initial(dimensions["dim_course"], "mdl_local_smartlms_dim_course", engine)
        load_to_mysql_initial(dimensions["dim_user"], "mdl_local_smartlms_dim_user", engine)
        load_to_mysql_initial(dimensions["dim_activity"], "mdl_local_smartlms_dim_activity", engine)
        load_to_mysql_initial(fact_engagement, "mdl_local_smartlms_fact_engagement", engine)

    elif mode == "incremental":
        load_to_mysql_incremental(dimensions["dim_course"], "mdl_local_smartlms_dim_course", engine, ["courseid"])
        load_to_mysql_incremental(dimensions["dim_user"], "mdl_local_smartlms_dim_user", engine, ["userid"])
        load_to_mysql_incremental(
            dimensions["dim_activity"],
            "mdl_local_smartlms_dim_activity",
            engine,
            ["component", "event_context", "event_name"]
        )
        load_to_mysql_incremental(
            fact_engagement,
            "mdl_local_smartlms_fact_engagement",
            engine,
            ["courseid", "userid", "component", "event_context", "event_name"]
        )

