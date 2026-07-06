import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def append_csv_row(csv_path: Path, row: dict):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    headers = list(row.keys())

    if not csv_path.exists():
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(",".join(headers) + "\n")
    else:
        with open(csv_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
        if first_line:
            headers = [h.strip() for h in first_line.split(",")]

    values = []
    for key in headers:
        value = str(row.get(key, ""))
        value = value.replace("\n", " ").replace("\r", " ").replace(",", ";")
        values.append(value)

    with open(csv_path, "a", encoding="utf-8") as f:
        f.write(",".join(values) + "\n")


def append_debug_line(debug_path: Path, line: str):
    debug_path.parent.mkdir(parents=True, exist_ok=True)
    with open(debug_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_stage(stage_name: str, command: list[str], env: dict, cwd: Path, debug_log: Path):
    started_at = utc_now_iso()
    start_ts = time.time()

    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        exit_code = int(proc.returncode)
        status = "completed" if exit_code == 0 else "failed"
        stdout_tail = "\n".join(proc.stdout.strip().splitlines()[-20:]) if proc.stdout else ""
        stderr_tail = "\n".join(proc.stderr.strip().splitlines()[-20:]) if proc.stderr else ""
    except Exception as exc:  # pragma: no cover
        exit_code = 1
        status = "failed"
        stdout_tail = ""
        stderr_tail = f"runner_exception: {type(exc).__name__}: {exc}"

    finished_at = utc_now_iso()
    duration_sec = round(time.time() - start_ts, 3)

    append_debug_line(
        debug_log,
        (
            f"{finished_at} | stage={stage_name} | status={status} | exit_code={exit_code} | "
            f"duration_sec={duration_sec}"
        ),
    )
    if stdout_tail:
        append_debug_line(debug_log, f"{finished_at} | stage={stage_name} | stdout_tail=\n{stdout_tail}")
    if stderr_tail:
        append_debug_line(debug_log, f"{finished_at} | stage={stage_name} | stderr_tail=\n{stderr_tail}")

    return {
        "stage_name": stage_name,
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_sec": duration_sec,
        "exit_code": exit_code,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
    }


def main():
    parser = argparse.ArgumentParser(description="Production pipeline runner for ETL + feature engineering + online prediction.")
    parser.add_argument("--data-source", default="moodle", choices=["moodle", "historical"], help="DATA_SOURCE value for ETL stage.")
    parser.add_argument("--skip-etl", action="store_true", help="Skip ETL stage.")
    parser.add_argument("--skip-feature", action="store_true", help="Skip feature engineering stage.")
    parser.add_argument("--skip-predict", action="store_true", help="Skip prediction stage.")
    parser.add_argument("--continue-on-error", action="store_true", default=True, help="Continue remaining stages if one stage fails.")
    parser.add_argument("--strict-exit", action="store_true", help="Exit non-zero when any stage fails.")
    parser.add_argument("--conda-env", default="", help="Run stages via conda environment name, for example dataviz305.")
    parser.add_argument("--reuse-staging", action="store_true", help="For moodle data source, reuse staged files instead of forcing refresh.")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    logs_dir = project_root / "logs"
    run_id = f"pipe_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}_{uuid.uuid4().hex[:8]}"
    debug_log = logs_dir / "pipeline_runner_debug.log"
    summary_csv = logs_dir / "pipeline_runner_runs.csv"
    stage_csv = logs_dir / "pipeline_runner_stage_logs.csv"

    env = os.environ.copy()
    env["DATA_SOURCE"] = args.data_source

    refresh_staging_effective = False
    if args.data_source == "moodle" and not args.reuse_staging:
        env["REFRESH_STAGING"] = "1"
        refresh_staging_effective = True
    elif args.data_source == "moodle" and args.reuse_staging:
        env["REFRESH_STAGING"] = "0"

    py = sys.executable

    def build_cmd(module_name: str):
        if args.conda_env:
            return ["conda", "run", "-n", args.conda_env, "python", "-m", module_name]
        return [py, "-m", module_name]

    stages = []
    if not args.skip_etl:
        stages.append(("etl", build_cmd("etl.main")))
    if not args.skip_feature:
        stages.append(("feature_engineering", build_cmd("ml.main")))
    if not args.skip_predict:
        stages.append(("online_prediction", build_cmd("ml.predict_main")))

    run_started = utc_now_iso()
    run_start_ts = time.time()
    append_debug_line(debug_log, f"{run_started} | run_id={run_id} | status=started | stages={','.join([s[0] for s in stages])}")

    failed = False
    stage_results = []

    for stage_name, command in stages:
        result = run_stage(stage_name, command, env, project_root, debug_log)
        stage_results.append(result)
        append_csv_row(
            stage_csv,
            {
                "run_id": run_id,
                "run_timestamp_utc": run_started,
                "stage_name": result["stage_name"],
                "status": result["status"],
                "started_at": result["started_at"],
                "finished_at": result["finished_at"],
                "duration_sec": result["duration_sec"],
                "exit_code": result["exit_code"],
                "stdout_tail": result["stdout_tail"],
                "stderr_tail": result["stderr_tail"],
            },
        )

        if result["status"] != "completed":
            failed = True
            if not args.continue_on_error:
                break

    run_finished = utc_now_iso()
    run_duration = round(time.time() - run_start_ts, 3)
    final_status = "failed" if failed else "completed"
    append_csv_row(
        summary_csv,
        {
            "run_id": run_id,
            "run_timestamp_utc": run_started,
            "finished_at": run_finished,
            "duration_sec": run_duration,
            "data_source": args.data_source,
            "stages_requested": ",".join([s[0] for s in stages]),
            "stages_executed": len(stage_results),
            "stages_failed": sum(1 for s in stage_results if s["status"] != "completed"),
            "status": final_status,
            "strict_exit": args.strict_exit,
            "conda_env": args.conda_env,
            "reuse_staging": args.reuse_staging,
            "refresh_staging_effective": refresh_staging_effective,
        },
    )

    append_debug_line(
        debug_log,
        f"{run_finished} | run_id={run_id} | status={final_status} | duration_sec={run_duration}",
    )

    print(json.dumps({
        "run_id": run_id,
        "status": final_status,
        "data_source": args.data_source,
        "conda_env": args.conda_env,
        "reuse_staging": args.reuse_staging,
        "refresh_staging_effective": refresh_staging_effective,
        "stages": [s["stage_name"] for s in stage_results],
        "failed_stages": [s["stage_name"] for s in stage_results if s["status"] != "completed"],
        "duration_sec": run_duration,
        "logs": {
            "run_summary": str(summary_csv),
            "stage_logs": str(stage_csv),
            "debug_log": str(debug_log),
        },
    }, indent=2))

    if failed and args.strict_exit:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
