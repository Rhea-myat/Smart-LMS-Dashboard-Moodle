# Client Submission Pack

Date: 2026-08-01
Project: Smart LMS Dashboard Moodle

## 1) Final Technical Check

- Python runtime found: 3.8.10 in `.venv`.
- Core script syntax check passed:
  - `run_nightly.sh` via `bash -n`
  - `dashboard.py`, `pipeline_runner.py`, `etl/*.py`, `ml/*.py` via `py_compile`
- Test framework gap found:
  - `pytest` is not installed in the current environment.
  - `tests/` scripts run, but `unittest discover` reports `Ran 0 tests`, so there are no assert-based automated tests currently executed.

Release status: Conditionally ready for submission, with test coverage caveat above.

## 2) Include in Client Package (Recommended)

### Root scripts and configs
- `pipeline_runner.py`: Production orchestrator for ETL -> feature engineering -> prediction stages.
- `run_nightly.sh`: Hardened nightly runner (lock file, optional Docker path, logs, env loading).
- `Dockerfile`: Container image build for pipeline execution.
- `requirements.txt`: Python dependency pins for VM/local compatibility.
- `README.md`: Environment and setup summary.

### ETL module
- `etl/main.py`: Main ETL pipeline for moodle/historical sources, transformations, and warehouse writes.
- `etl/extract.py`: Source extraction and staging writers.
- `etl/transform.py`: Dimension/fact builders and transformation routines.
- `etl/transform_moodle.py`: Moodle-specific transform flow.
- `etl/load.py`: Incremental warehouse load operations.
- `etl/db.py`: Database engine/connectivity helpers.
- `etl/data_quality_rules.py`: Core integrity/validation rules.
- `etl/data_quality_rules_v2.py`: Updated data quality and cleanup rules.
- `etl/reconcile_datasets.py`: Student matching/reconciliation checks.
- `etl/logging_utils.py`: ETL run logging helpers.

### ML module
- `ml/main.py`: Feature engineering orchestration and snapshot generation.
- `ml/predict_main.py`: Batch prediction orchestration and prediction-store writes.
- `ml/predict.py`: Ensemble prediction execution logic.
- `ml/ensemble.py`: Ensemble model combination logic.
- `ml/preprocessing.py`: Feature preprocessing routines.
- `ml/preprocessing_v1.1.py`: Versioned preprocessing implementation.
- `ml/load.py`: ML output/data loading helpers.
- `ml/load_v1.1.py`: Versioned model/result loading helpers.
- `ml/db.py`: ML database connectivity.
- `ml/register_model.py`: Model metadata registration.
- `ml/train.py`: Model training entry workflow.
- `ml/final_train.py`: Final training workflow.
- `ml/evaluate.py`: Evaluation metrics/reporting.

### Data directories (required for reproducible run)
- `data/staging/`: Staged extracts used by ETL.
- `data/warehouse/`: Generated dimensional/fact outputs consumed by ML.
- `ml/feature_store/`: Feature snapshots for prediction.
- `ml/models/`: Model artifacts/config required by predictor.
- `ml/prediction_store/`: Output predictions.

### Operations docs
- `docs/Cron_Schedule_Template.md`: Cron templates, rotation, retention.
- `docs/VM_Setup_Guide.md`: VM setup instructions.

## 3) Optional/Dev-Only (Do Not Send Unless Requested)

- `tests/`: Useful internally; currently not assert-driven in CI style.
- `logs/`: Execution logs and debug traces (may include environment-specific details).
- `ml/notebooks/`: Experiment notebooks.
- `ml/datasets/`: Training splits and local experiment assets.

## 4) Exclude from Client Package

- `.env`: Secrets and environment-specific credentials.
- `.git/`, `__pycache__/`, `.venv/`: Development metadata and local virtual environment.
- Placeholder files that are not part of runtime pipeline:
  - `--env-file`
  - `--network`
  - `python`
  - `smart-lms-ml:v1.1`

## 5) Client Run Commands

### VM or local (without Docker)
1. Create and configure `.env` for DB connectivity.
  - Start from `.env.example` and replace placeholder values.
2. Install dependencies:
   - `python -m pip install -r requirements.txt`
3. Execute full pipeline:
   - `python pipeline_runner.py --data-source moodle --strict-exit`

### One-command handover smoke test (validated)
Run from project root:

```bash
./scripts/smoke_handover.sh
```

Expected PASS lines in terminal output:

```text
PASS: ETL
PASS: Feature Engineering
PASS: Prediction
PASS: smoke handover run completed successfully
PASS: ETL -> ML feature engineering -> prediction validated
```

Notes:
- Default smoke data source is `historical`.
- Smoke run writes a timestamped log to `logs/smoke_<timestamp>.log`.

### Nightly schedule
- Use `run_nightly.sh` directly in cron, or use the cron samples in `docs/Cron_Schedule_Template.md`.

## 6) Recommended Pre-Submission Improvements

1. Add `pytest` to dev dependencies and migrate tests to assert-based automated tests.
2. Add `unittest`/`pytest` assertions for end-to-end smoke checks in CI.

## 7) Delivered Handover Extras

1. One-command smoke runner: `scripts/smoke_handover.sh`.
2. Sanitized env template: `.env.example`.