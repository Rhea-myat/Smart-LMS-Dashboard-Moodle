import os
import pandas as pd
from pathlib import Path

from etl.extract import BASE_DIR, extract_data
from etl.transform import (
    create_dim_student,
    create_dim_time,
    create_dim_academic_period,
    lookup_academic_period_key,
    parse_academic_period_from_label,
    create_dim_course_from_historical_logs,
    create_dim_event,
    create_dim_material,
    create_dim_assessment,
    create_dim_grade,
    create_fact_activity_log_from_historical,
    create_fact_result,
    create_fact_enrolment,
)
from etl.db import get_engine, get_source_engine
from etl.load import load_warehouse_incremental
from etl.data_quality_rules_v2 import (
    standardise_column_names,
    rename_result_columns,
    extract_student_id_from_username,
    filter_valid_student_records,
    handle_missing_values,
    remove_duplicates,
)
from etl.data_quality_rules import validate_academic_period_integrity
from etl.logging_utils import write_log, append_etl_run_summary
from etl.reconcile_datasets import check_student_matching, generate_matching_log


DATA_SOURCE = os.getenv("DATA_SOURCE", "moodle").strip().lower()  # "moodle" or "historical"

CSV_UPSERT_KEYS = {
    "dim_student": ["student_id"],
    "dim_time": ["time"],
    "dim_academic_period": ["semester", "academic_year"],
    "dim_course": ["course_id"],
    "dim_event": ["event_name"],
    "dim_material": ["context", "component"],
    "dim_assessment": ["assessment_name"],
    "dim_grade": ["grade_code"],
    "fact_activity_log": [
        "source_system",
        "activity_fact_id",
    ],
    "fact_result": [
        "source_system",
        "result_fact_id",
    ],
    "fact_enrolment": [
        "enrolment_source",
        "enrolment_fact_id",
    ],
}

DIMENSION_CONFIG = {
    "dim_student": {"sk": "student_key", "bk": ["student_id"]},
    "dim_time": {"sk": "time_key", "bk": ["time"]},
    "dim_academic_period": {"sk": "academic_period_key", "bk": ["semester", "academic_year"]},
    "dim_course": {"sk": "course_key", "bk": ["course_id"]},
    "dim_event": {"sk": "event_key", "bk": ["event_name"]},
    "dim_material": {"sk": "material_key", "bk": ["context", "component"]},
    "dim_assessment": {"sk": "assessment_key", "bk": ["assessment_name"]},
    "dim_grade": {"sk": "grade_key", "bk": ["grade_code"]},
}

FACT_FK_MAP = {
    "fact_activity_log": {
        "student_key": "dim_student",
        "course_key": "dim_course",
        "time_key": "dim_time",
        "academic_period_key": "dim_academic_period",
        "event_key": "dim_event",
        "material_key": "dim_material",
    },
    "fact_result": {
        "student_key": "dim_student",
        "course_key": "dim_course",
        "academic_period_key": "dim_academic_period",
        "assessment_key": "dim_assessment",
        "grade_key": "dim_grade",
    },
    "fact_enrolment": {
        "student_key": "dim_student",
        "course_key": "dim_course",
        "academic_period_key": "dim_academic_period",
        "time_key": "dim_time",
    },
}

STAGING_TABLE_FILES = {
    "courses": "courses.csv",
    "students": "students.csv",
    "enrolments": "enrolments.csv",
    "logs": "activity_logs.csv",
    "grades": "grades.csv",
}


def derive_murdoch_period_from_logs(logs):
    if "timecreated" in logs.columns:
        timestamps = pd.to_datetime(logs["timecreated"], unit="s", errors="coerce")
    elif "timemodified" in logs.columns:
        timestamps = pd.to_datetime(logs["timemodified"], unit="s", errors="coerce")
    else:
        timestamps = pd.Series(dtype="datetime64[ns]")

    latest_ts = timestamps.dropna().max()
    if pd.isna(latest_ts):
        latest_ts = pd.Timestamp.today()

    semester = "S1" if int(latest_ts.month) <= 6 else "S2"
    academic_year = int(latest_ts.year)
    return semester, academic_year


def load_moodle_sources(moodle_engine):
    from etl.extract import (
        STAGING_DIR,
        extract_moodle_courses,
        extract_moodle_students,
        extract_moodle_enrolments,
        extract_moodle_logs,
        extract_moodle_grades,
        load_to_staging,
    )

    extractors = {
        "courses": extract_moodle_courses,
        "students": extract_moodle_students,
        "enrolments": extract_moodle_enrolments,
        "logs": extract_moodle_logs,
        "grades": extract_moodle_grades,
    }

    refresh_staging = os.getenv("REFRESH_STAGING", "0").strip().lower() in {"1", "true", "yes", "y"}

    datasets = {}
    for dataset_name, file_name in STAGING_TABLE_FILES.items():
        staging_path = Path(STAGING_DIR) / file_name
        if staging_path.exists() and not refresh_staging:
            datasets[dataset_name] = pd.read_csv(staging_path, keep_default_na=False)
            write_log(f"Loaded {dataset_name} from staging: {staging_path}")
        else:
            extracted_df = extractors[dataset_name](moodle_engine)
            load_to_staging(extracted_df, staging_path)
            datasets[dataset_name] = extracted_df
            write_log(f"Extracted {dataset_name} from Moodle DB and staged to: {staging_path}")

    return datasets


def _norm_key_series(series):
    return series.astype(str).str.strip()


def _normalize_murdoch_semester(value):
    raw = str(value).strip().upper()
    if raw in {"S1", "SEMESTER 1", "SEM 1", "SPRING"}:
        return "S1"
    if raw in {"S2", "SEMESTER 2", "SEM 2", "FALL", "AUTUMN"}:
        return "S2"
    return raw


def _ensure_nullable_int_keys(df):
    out_df = df.copy()
    for col in out_df.columns:
        if col.endswith("_key") or col.endswith("_fact_id"):
            out_df[col] = pd.to_numeric(out_df[col], errors="coerce").astype("Int64")
    return out_df


def _upsert_csv_file(csv_path, incoming_df, upsert_keys):
    incoming_df = incoming_df.copy()

    if csv_path.exists():
        existing_df = pd.read_csv(csv_path, keep_default_na=False)

        for col in existing_df.columns:
            if col not in incoming_df.columns:
                incoming_df[col] = pd.NA
        for col in incoming_df.columns:
            if col not in existing_df.columns:
                existing_df[col] = pd.NA

        incoming_df = incoming_df[existing_df.columns]
        if existing_df.empty:
            combined_df = incoming_df.copy()
        elif incoming_df.empty:
            combined_df = existing_df.copy()
        else:
            combined_df = pd.concat([existing_df, incoming_df], ignore_index=True)
    else:
        existing_df = pd.DataFrame(columns=incoming_df.columns)
        combined_df = incoming_df

    valid_keys = [col for col in upsert_keys if col in combined_df.columns]

    if valid_keys:
        helper_cols = []
        work_df = combined_df.copy()
        for idx, key_col in enumerate(valid_keys):
            helper_col = f"__upsert_key_{idx}"
            helper_cols.append(helper_col)
            work_df[helper_col] = _norm_key_series(work_df[key_col])
        merged_df = work_df.drop_duplicates(subset=helper_cols, keep="last").drop(columns=helper_cols)
    else:
        merged_df = combined_df.drop_duplicates(keep="last")

    added_rows = int(max(len(merged_df) - len(existing_df), 0))
    skipped_duplicates = int(max(len(incoming_df) - added_rows, 0))

    if csv_path.name == "fact_activity_log.csv" and "source_system" in merged_df.columns:
        moodle_mask = merged_df["source_system"].astype(str).str.strip().str.lower() == "moodle"
        if "student_key" in merged_df.columns:
            valid_student = pd.to_numeric(merged_df["student_key"], errors="coerce").notna()
            merged_df = merged_df[~moodle_mask | valid_student]

    if csv_path.name == "fact_enrolment.csv" and "enrolment_source" in merged_df.columns:
        moodle_mask = merged_df["enrolment_source"].astype(str).str.strip().str.lower() == "moodle"
        if "student_key" in merged_df.columns:
            valid_student = pd.to_numeric(merged_df["student_key"], errors="coerce").notna()
            merged_df = merged_df[~moodle_mask | valid_student]

    merged_df = _ensure_nullable_int_keys(merged_df)
    merged_df.to_csv(csv_path, index=False)

    return merged_df, added_rows, skipped_duplicates, incoming_df


def _reconcile_dimension_keys(tables, warehouse_root):
    key_maps = {}

    for dim_table, cfg in DIMENSION_CONFIG.items():
        sk_col = cfg["sk"]
        bk_cols = cfg["bk"]

        incoming_df = tables[dim_table].copy()
        incoming_df[sk_col] = pd.to_numeric(incoming_df[sk_col], errors="coerce").astype("Int64")

        csv_path = warehouse_root / f"{dim_table}.csv"
        if csv_path.exists():
            existing_df = pd.read_csv(csv_path, keep_default_na=False)
        else:
            existing_df = pd.DataFrame(columns=incoming_df.columns)

        for col in incoming_df.columns:
            if col not in existing_df.columns:
                existing_df[col] = pd.NA
        for col in existing_df.columns:
            if col not in incoming_df.columns:
                incoming_df[col] = pd.NA

        incoming_df = incoming_df[existing_df.columns]

        if dim_table == "dim_academic_period" and "semester" in incoming_df.columns:
            incoming_df["semester"] = incoming_df["semester"].apply(_normalize_murdoch_semester)
            existing_df["semester"] = existing_df["semester"].apply(_normalize_murdoch_semester)

        existing_df[sk_col] = pd.to_numeric(existing_df[sk_col], errors="coerce").astype("Int64")

        helper_cols = []
        for idx, bk_col in enumerate(bk_cols):
            helper_col = f"__bk_{idx}"
            helper_cols.append(helper_col)
            existing_df[helper_col] = _norm_key_series(existing_df[bk_col])
            incoming_df[helper_col] = _norm_key_series(incoming_df[bk_col])

        existing_dedup = existing_df.drop_duplicates(subset=helper_cols, keep="first").copy()

        max_existing_key = int(existing_dedup[sk_col].dropna().max()) if existing_dedup[sk_col].notna().any() else 0
        next_key = max_existing_key + 1

        # Repair legacy conflicts where different business keys share one surrogate key.
        used_keys = set()
        repaired_keys = []
        for _, row in existing_dedup.iterrows():
            current_key = None
            if pd.notna(row[sk_col]):
                current_key = int(row[sk_col])

            if current_key is None or current_key in used_keys:
                current_key = next_key
                next_key += 1

            used_keys.add(current_key)
            repaired_keys.append(current_key)

        existing_dedup[sk_col] = pd.Series(repaired_keys, index=existing_dedup.index, dtype="Int64")

        key_lookup = {
            tuple(row[helper_col] for helper_col in helper_cols): int(row[sk_col])
            for _, row in existing_dedup.iterrows()
            if pd.notna(row[sk_col])
        }

        incoming_dedup = incoming_df.drop_duplicates(subset=helper_cols, keep="last").copy()

        assigned_keys = []
        for _, row in incoming_dedup.iterrows():
            business_key = tuple(row[helper_col] for helper_col in helper_cols)
            current_key = key_lookup.get(business_key)
            if current_key is None:
                current_key = next_key
                key_lookup[business_key] = current_key
                next_key += 1
            assigned_keys.append(current_key)

        incoming_dedup[sk_col] = pd.Series(assigned_keys, index=incoming_dedup.index, dtype="Int64")

        original_sk = incoming_df[[sk_col] + helper_cols].drop_duplicates(subset=helper_cols, keep="last")
        incoming_to_global = original_sk.merge(
            incoming_dedup[[sk_col] + helper_cols].rename(columns={sk_col: "__global_sk"}),
            on=helper_cols,
            how="left",
        )

        key_maps[dim_table] = {
            int(row[sk_col]): int(row["__global_sk"])
            for _, row in incoming_to_global.iterrows()
            if pd.notna(row[sk_col]) and pd.notna(row["__global_sk"])
        }

        combined_df = pd.concat([existing_dedup, incoming_dedup], ignore_index=True)
        merged_df = combined_df.drop_duplicates(subset=helper_cols, keep="last").drop(columns=helper_cols)
        merged_df[sk_col] = pd.to_numeric(merged_df[sk_col], errors="coerce").astype("Int64")

        merged_df = _ensure_nullable_int_keys(merged_df)
        merged_df.to_csv(csv_path, index=False)

        tables[dim_table] = incoming_dedup.drop(columns=helper_cols)

    return tables, key_maps


def _remap_fact_foreign_keys(tables, key_maps):
    for fact_table, fk_map in FACT_FK_MAP.items():
        fact_df = tables[fact_table].copy()
        for fk_col, dim_table in fk_map.items():
            mapper = key_maps.get(dim_table, {})
            if fk_col in fact_df.columns and mapper:
                fact_df[fk_col] = pd.to_numeric(fact_df[fk_col], errors="coerce").map(mapper).astype("Int64")
        tables[fact_table] = _ensure_nullable_int_keys(fact_df)
    return tables


def save_tables_to_local_csv(tables, source_name):
    """
    Upsert ETL output into shared data/warehouse CSVs without duplicate rows.
    """
    warehouse_root = BASE_DIR / "data" / "warehouse"
    warehouse_root.mkdir(parents=True, exist_ok=True)

    tables, key_maps = _reconcile_dimension_keys(tables, warehouse_root)
    tables = _remap_fact_foreign_keys(tables, key_maps)

    for table_name, df in tables.items():
        if table_name in DIMENSION_CONFIG:
            continue

        csv_path = warehouse_root / f"{table_name}.csv"

        merged_df, added_rows, skipped_duplicates, prepared_incoming_df = _upsert_csv_file(
            csv_path,
            df,
            CSV_UPSERT_KEYS.get(table_name, []),
        )
        tables[table_name] = merged_df
        write_log(
            f"Upserted {table_name} from {source_name} | "
            f"incoming={len(prepared_incoming_df)} added={added_rows} "
            f"skipped_duplicates={skipped_duplicates} total={len(merged_df)}"
        )

    # Write aligned run-level dimension snapshots after global key assignment.
    for dim_table in DIMENSION_CONFIG:
        dim_df = tables[dim_table]
        write_log(
            f"Aligned keys for {dim_table} from {source_name} | "
            f"incoming={len(dim_df)}"
        )

    return tables


def build_historical_tables():
    logs_path = BASE_DIR / "data" / "raw" / "ICT001 S1 2025 Logs RELEASED V1.0.xlsx"
    results_path = BASE_DIR / "data" / "raw" / "cleaned_standard_results.xlsx"
    source_label = logs_path.stem

    logs = extract_data(logs_path)
    results = extract_data(results_path)

    logs = standardise_column_names(logs)
    results = standardise_column_names(results)

    results = rename_result_columns(results)

    logs["studentid_clean"] = extract_student_id_from_username(logs["username"])
    results = filter_valid_student_records(results)
    results["studentid_clean"] = results["person_id"].astype(str).str.strip()

    logs, results = handle_missing_values(logs, results)

    logs = remove_duplicates(logs, "logs")
    results = remove_duplicates(results, "results")

    check_student_matching(logs, results)
    _ = generate_matching_log(logs, results)

    source_semester, source_academic_year = parse_academic_period_from_label(source_label)

    dim_student = create_dim_student(logs, results)
    dim_time = create_dim_time(logs)
    dim_academic_period = create_dim_academic_period(source_semester, source_academic_year)

    historical_academic_period_key = lookup_academic_period_key(
        dim_academic_period,
        source_semester,
        source_academic_year,
    )

    dim_course, course_lookup = create_dim_course_from_historical_logs(logs)
    dim_event = create_dim_event(logs)
    dim_material = create_dim_material(logs)
    dim_assessment = create_dim_assessment(results)
    dim_grade = create_dim_grade(results)

    fact_activity_log = create_fact_activity_log_from_historical(
        logs,
        dim_student,
        dim_time,
        historical_academic_period_key,
        dim_course,
        dim_event,
        dim_material,
        course_lookup,
    )

    fact_result = create_fact_result(
        results,
        dim_student,
        dim_course,
        dim_assessment,
        dim_grade,
        historical_academic_period_key,
    )
    fact_result["source_system"] = "Historical"

    fact_enrolment = create_fact_enrolment(
        logs,
        results,
        dim_student,
        dim_course,
        dim_time,
        historical_academic_period_key,
    )

    validate_academic_period_integrity(
        dim_academic_period,
        fact_activity_log,
        fact_result,
        fact_enrolment,
    )

    tables = {
        "dim_student": dim_student,
        "dim_time": dim_time,
        "dim_academic_period": dim_academic_period,
        "dim_course": dim_course,
        "dim_event": dim_event,
        "dim_material": dim_material,
        "dim_assessment": dim_assessment,
        "dim_grade": dim_grade,
        "fact_activity_log": fact_activity_log,
        "fact_result": fact_result,
        "fact_enrolment": fact_enrolment,
    }

    source_counts = {
        "logs": int(len(logs)),
        "results": int(len(results)),
    }

    return tables, source_counts


def run_historical_etl():
    tables, source_counts = build_historical_tables()

    tables = save_tables_to_local_csv(tables, "historical")

    analytics_engine = get_engine(os.getenv("DB_NAME"))
    load_counts = load_warehouse_incremental(tables, analytics_engine)

    transformed_counts = {table_name: int(len(df)) for table_name, df in tables.items()}

    for table_name, stats in load_counts.items():
        write_log(
            "Loaded "
            f"{table_name} | incoming={stats['incoming_rows']} "
            f"inserted={stats['rows_added']} "
            f"skipped_existing={stats['skipped_existing']} "
            f"skipped_batch_duplicates={stats['skipped_batch_duplicates']}"
        )

    append_etl_run_summary(
        run_type="historical_incremental",
        summary_payload={
            "source_counts": source_counts,
            "transformed_counts": transformed_counts,
            "dropped_unresolved_fk": {},
            "load_counts": load_counts,
        },
    )


def run_moodle_etl():
    from etl.transform_moodle import transform_moodle_data
    from etl.load import cleanup_non_student_moodle_records

    moodle_engine = get_source_engine()
    analytics_engine = get_engine(os.getenv("DB_NAME"))

    datasets = load_moodle_sources(moodle_engine)
    courses = datasets["courses"]
    students = datasets["students"]
    enrolments = datasets["enrolments"]
    logs = datasets["logs"]
    grades = datasets["grades"]

    semester, academic_year = derive_murdoch_period_from_logs(logs)

    print("Courses:", courses.shape)
    print("Students:", students.shape)
    print("Enrolments:", enrolments.shape)
    print("Logs:", logs.shape)
    print("Grades:", grades.shape)

    source_counts = {
        "courses": int(len(courses)),
        "students": int(len(students)),
        "enrolments": int(len(enrolments)),
        "logs": int(len(logs)),
        "grades": int(len(grades)),
    }

    tables = transform_moodle_data(
        courses=courses,
        students=students,
        enrolments=enrolments,
        logs=logs,
        grades=grades,
        semester=semester,
        academic_year=academic_year,
    )

    transformed_counts = {table_name: int(len(df)) for table_name, df in tables.items()}

    dropped_unresolved_fk = {
        table_name: int(df.attrs.get("dropped_unresolved_fk", 0))
        for table_name, df in tables.items()
        if table_name.startswith("fact_")
    }

    tables = save_tables_to_local_csv(tables, "moodle")

    cleanup_non_student_moodle_records(analytics_engine)

    load_counts = load_warehouse_incremental(tables, analytics_engine)

    for table_name, stats in load_counts.items():
        write_log(
            "Loaded "
            f"{table_name} | incoming={stats['incoming_rows']} "
            f"inserted={stats['rows_added']} "
            f"skipped_existing={stats['skipped_existing']} "
            f"skipped_batch_duplicates={stats['skipped_batch_duplicates']}"
        )

    append_etl_run_summary(
        run_type="moodle_incremental",
        summary_payload={
            "source_counts": source_counts,
            "transformed_counts": transformed_counts,
            "dropped_unresolved_fk": dropped_unresolved_fk,
            "load_counts": load_counts,
        },
    )


if __name__ == "__main__":
    if DATA_SOURCE == "historical":
        run_historical_etl()
    elif DATA_SOURCE == "moodle":
        run_moodle_etl()
    else:
        raise ValueError("DATA_SOURCE must be either 'historical' or 'moodle'")
