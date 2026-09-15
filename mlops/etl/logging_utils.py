import datetime
import json
import pandas as pd
from pathlib import Path
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)


def write_log(message): 
    with open(LOG_DIR / "etl_test_log.txt", "a") as f: 
        f.write(f"{datetime.datetime.now()}: {message}\n")


def append_etl_run_summary(run_type, summary_payload):
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")

    summary_path = LOG_DIR / "etl_run_summary.csv"
    debug_path = LOG_DIR / "etl_pipeline_debug.log"

    row = {
        "run_timestamp": timestamp,
        "run_type": run_type,
        "source_counts": json.dumps(summary_payload.get("source_counts", {}), sort_keys=True),
        "transformed_counts": json.dumps(summary_payload.get("transformed_counts", {}), sort_keys=True),
        "dropped_unresolved_fk": json.dumps(summary_payload.get("dropped_unresolved_fk", {}), sort_keys=True),
        "load_counts": json.dumps(summary_payload.get("load_counts", {}), sort_keys=True),
    }

    df = pd.DataFrame([row])
    df.to_csv(summary_path, mode="a", header=not summary_path.exists(), index=False)

    with open(debug_path, "a") as f:
        f.write(f"[{timestamp}] run_type={run_type} summary={json.dumps(summary_payload, sort_keys=True)}\n")