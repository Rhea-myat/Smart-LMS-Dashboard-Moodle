# Nightly Cron Template (VM)

This template schedules the production pipeline runner nightly and rotates large log files.

## 1) Edit crontab

```bash
crontab -e
```

## 2) Nightly pipeline job

Update `PROJECT_ROOT` and `CONDA_ENV` to match your VM.

```cron
# Run nightly at 01:30 AM server time
30 1 * * * PROJECT_ROOT="/opt/smart-lms/Smart-LMS-Dashboard-Moodle" && \
  cd "$PROJECT_ROOT" && \
  /usr/bin/flock -n /tmp/smart_lms_pipeline.lock \
  /bin/bash -lc "python pipeline_runner.py --conda-env dataviz305 --data-source moodle --strict-exit" \
  >> "$PROJECT_ROOT/logs/cron_pipeline.out" 2>&1
```

Notes:
- `flock` prevents overlapping runs.
- `--strict-exit` makes failures visible to cron/system monitors.
- Output is appended to `logs/cron_pipeline.out`.
- `--data-source moodle` now refreshes staging by default (fresh Moodle extract each run).
- Use `--reuse-staging` only when you intentionally want to reuse staged files.

### Reuse-staging example (optional)

```cron
# Run nightly but reuse staging (faster; not a fresh DB extract)
30 1 * * * PROJECT_ROOT="/opt/smart-lms/Smart-LMS-Dashboard-Moodle" && \
  cd "$PROJECT_ROOT" && \
  /usr/bin/flock -n /tmp/smart_lms_pipeline.lock \
  /bin/bash -lc "python pipeline_runner.py --conda-env dataviz305 --data-source moodle --reuse-staging --strict-exit" \
  >> "$PROJECT_ROOT/logs/cron_pipeline.out" 2>&1
```

## 3) Simple weekly log rotation via cron

This keeps logs small by archiving once per week.

```cron
# Rotate every Sunday at 02:15 AM
15 2 * * 0 PROJECT_ROOT="/opt/smart-lms/Smart-LMS-Dashboard-Moodle" && \
  cd "$PROJECT_ROOT" && \
  /bin/bash -lc '
    TS=$(date +"%Y%m%d_%H%M%S");
    mkdir -p logs/archive;
    for f in \
      logs/cron_pipeline.out \
      logs/pipeline_runner_debug.log \
      logs/pipeline_runner_runs.csv \
      logs/pipeline_runner_stage_logs.csv \
      logs/feature_engineering_run_debug.log \
      logs/feature_engineering_run_logs.csv \
      logs/prediction_run_debug.log \
      logs/prediction_run_logs.csv; do
      if [ -f "$f" ]; then
        cp "$f" "logs/archive/$(basename "$f").$TS";
        : > "$f";
      fi;
    done'
```

## 4) Optional retention cleanup

Delete archived logs older than 30 days.

```cron
# Cleanup daily at 03:00 AM
0 3 * * * PROJECT_ROOT="/opt/smart-lms/Smart-LMS-Dashboard-Moodle" && \
  cd "$PROJECT_ROOT" && \
  /usr/bin/find logs/archive -type f -mtime +30 -delete
```

## 5) Quick checks

```bash
# List cron entries
crontab -l

# Trigger runner manually
cd /opt/smart-lms/Smart-LMS-Dashboard-Moodle
python pipeline_runner.py --conda-env dataviz305 --data-source moodle --strict-exit

# Inspect latest pipeline logs
tail -n 50 logs/pipeline_runner_debug.log
tail -n 50 logs/cron_pipeline.out
```
