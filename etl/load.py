import logging
import pandas as pd

from etl.logging_utils import write_log

WAREHOUSE_LOAD_ORDER = [
    "dim_student",
    "dim_time",
    "dim_academic_period",
    "dim_course",
    "dim_event",
    "dim_material",
    "dim_assessment",
    "dim_grade",
    "fact_activity_log",
    "fact_result",
    "fact_enrolment"
]


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
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if not inspector.has_table(table_name):
        bootstrap_df = df.copy()
        load_to_mysql_initial(bootstrap_df, table_name, engine)
        created_rows = int(len(bootstrap_df))
        return {
            "incoming_rows": created_rows,
            "rows_to_insert": created_rows,
            "rows_after_load": created_rows,
            "rows_added": created_rows,
            "skipped_existing": 0,
            "skipped_batch_duplicates": 0,
        }

    table_columns = [col["name"] for col in inspector.get_columns(table_name)]

    aligned_df = df.copy()
    for col in table_columns:
        if col not in aligned_df.columns:
            aligned_df[col] = None
    aligned_df = aligned_df[table_columns]

    valid_key_columns = [col for col in key_columns if col in table_columns]

    incoming_rows = int(len(aligned_df))
    if valid_key_columns:
        aligned_df = aligned_df.drop_duplicates(subset=valid_key_columns, keep="last")
    deduped_rows = int(len(aligned_df))
    skipped_batch_duplicates = int(incoming_rows - deduped_rows)

    existing_key_matches = 0
    if valid_key_columns and not aligned_df.empty:
        key_query = text(f"SELECT {', '.join(valid_key_columns)} FROM {table_name}")
        existing_keys_df = pd.read_sql(key_query, engine)

        if not existing_keys_df.empty:
            existing_keys_df = existing_keys_df.drop_duplicates(subset=valid_key_columns)

            incoming_keys = aligned_df[valid_key_columns].copy()
            existing_keys = existing_keys_df[valid_key_columns].copy()

            normalized_key_cols = []
            for idx, key_col in enumerate(valid_key_columns):
                norm_col = f"__norm_key_{idx}"
                normalized_key_cols.append(norm_col)

                incoming_keys[norm_col] = incoming_keys[key_col].astype(str).str.strip()
                existing_keys[norm_col] = existing_keys[key_col].astype(str).str.strip()

            incoming_keys = incoming_keys[normalized_key_cols]
            existing_keys = existing_keys[normalized_key_cols].drop_duplicates()

            aligned_with_keys = aligned_df.reset_index(drop=True).copy()
            aligned_with_keys = pd.concat([aligned_with_keys, incoming_keys.reset_index(drop=True)], axis=1)

            aligned_with_keys = aligned_with_keys.merge(
                existing_keys,
                on=normalized_key_cols,
                how="left",
                indicator=True
            )

            existing_key_matches = int((aligned_with_keys["_merge"] == "both").sum())
            aligned_df = aligned_with_keys[aligned_with_keys["_merge"] == "left_only"].drop(
                columns=normalized_key_cols + ["_merge"]
            )

    rows_to_insert = int(len(aligned_df))

    count_query = text(f"SELECT COUNT(*) AS row_count FROM {table_name}")
    before_count = int(pd.read_sql(count_query, engine).iloc[0]["row_count"])

    if rows_to_insert == 0:
        return {
            "incoming_rows": incoming_rows,
            "rows_to_insert": 0,
            "rows_after_load": before_count,
            "rows_added": 0,
            "skipped_existing": existing_key_matches,
            "skipped_batch_duplicates": skipped_batch_duplicates
        }

    update_columns = [col for col in table_columns if col not in valid_key_columns]
    if update_columns:
        update_clause = ", ".join([f"{col} = VALUES({col})" for col in update_columns])
    else:
        update_clause = f"{table_columns[0]} = {table_columns[0]}"

    with engine.begin() as conn:
        for _, row in aligned_df.iterrows():
            query = text(f"""
                INSERT INTO {table_name} ({', '.join(table_columns)})
                VALUES ({', '.join([f":{col}" for col in table_columns])})
                ON DUPLICATE KEY UPDATE
                {update_clause}
            """)
            clean_row = row.where(pd.notna(row), None).to_dict()
            conn.execute(query, clean_row)

    after_count = int(pd.read_sql(count_query, engine).iloc[0]["row_count"])

    return {
        "incoming_rows": incoming_rows,
        "rows_to_insert": rows_to_insert,
        "rows_after_load": after_count,
        "rows_added": int(max(after_count - before_count, 0)),
        "skipped_existing": existing_key_matches,
        "skipped_batch_duplicates": skipped_batch_duplicates
    }

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


def load_warehouse_initial(tables, engine):
    load_stats = {}
    for table_name in WAREHOUSE_LOAD_ORDER:
        df = tables[table_name]
        load_to_mysql_initial(df, table_name, engine)
        write_log(f"Loaded {table_name}: {len(df)} rows")
        load_stats[table_name] = {
            "incoming_rows": int(len(df)),
            "rows_to_insert": int(len(df)),
            "rows_after_load": int(len(df)),
            "rows_added": int(len(df)),
            "skipped_existing": 0,
            "skipped_batch_duplicates": 0
        }
    return load_stats


def load_warehouse_incremental(tables, engine):
    from sqlalchemy import inspect

    load_stats = {}

    load_stats["dim_student"] = load_to_mysql_incremental(tables["dim_student"], "dim_student", engine, ["student_id"])
    load_stats["dim_time"] = load_to_mysql_incremental(tables["dim_time"], "dim_time", engine, ["time"])
    load_stats["dim_academic_period"] = load_to_mysql_incremental(
        tables["dim_academic_period"],
        "dim_academic_period",
        engine,
        ["semester", "academic_year"]
    )
    load_stats["dim_course"] = load_to_mysql_incremental(tables["dim_course"], "dim_course", engine, ["course_id"])
    load_stats["dim_event"] = load_to_mysql_incremental(tables["dim_event"], "dim_event", engine, ["event_name"])
    load_stats["dim_material"] = load_to_mysql_incremental(
        tables["dim_material"],
        "dim_material",
        engine,
        ["context", "component"]
    )
    load_stats["dim_assessment"] = load_to_mysql_incremental(
        tables["dim_assessment"],
        "dim_assessment",
        engine,
        ["assessment_name"]
    )
    load_stats["dim_grade"] = load_to_mysql_incremental(tables["dim_grade"], "dim_grade", engine, ["grade_code"])

    inspector = inspect(engine)
    table_columns = {}
    for table_name in ["fact_activity_log", "fact_result", "fact_enrolment"]:
        if inspector.has_table(table_name):
            table_columns[table_name] = [col["name"] for col in inspector.get_columns(table_name)]
        else:
            table_columns[table_name] = []

    # One-time schema migration support for new source-based upsert keys.
    if (
        table_columns["fact_result"]
        and "source_system" not in table_columns["fact_result"]
        and "source_system" in tables["fact_result"].columns
    ):
        load_to_mysql_initial(tables["fact_result"], "fact_result", engine)

    load_stats["fact_activity_log"] = load_to_mysql_incremental(
        tables["fact_activity_log"],
        "fact_activity_log",
        engine,
        ["source_system", "activity_fact_id"]
    )
    load_stats["fact_result"] = load_to_mysql_incremental(
        tables["fact_result"],
        "fact_result",
        engine,
        ["source_system", "result_fact_id"]
    )
    load_stats["fact_enrolment"] = load_to_mysql_incremental(
        tables["fact_enrolment"],
        "fact_enrolment",
        engine,
        ["enrolment_source", "enrolment_fact_id"]
    )

    logging.info("Incremental load completed for all tables.")
    return load_stats


def cleanup_non_student_moodle_records(engine):
    """
    Remove legacy Moodle records that are not linked to student keys.
    """
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text("""
            DELETE FROM fact_activity_log
            WHERE source_system = 'Moodle'
              AND (student_key IS NULL OR student_key NOT IN (SELECT student_key FROM dim_student))
        """))

        conn.execute(text("""
            DELETE FROM fact_enrolment
            WHERE enrolment_source = 'Moodle'
              AND (student_key IS NULL OR student_key NOT IN (SELECT student_key FROM dim_student))
        """))