#!/usr/bin/env bash
set -Eeuo pipefail

# One-command handover smoke run:
# 1) ETL only
# 2) Feature engineering only
# 3) Prediction only

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="${LOG_DIR:-$PROJECT_ROOT/logs}"
DATA_SOURCE="${DATA_SOURCE:-historical}"
ENV_FILE="${ENV_FILE:-$PROJECT_ROOT/.env}"

mkdir -p "$LOG_DIR"
RUN_ID="smoke_$(date -u +%Y%m%dT%H%M%SZ)"
LOG_FILE="$LOG_DIR/${RUN_ID}.log"

if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
else
  echo "ERROR: No Python executable found (.venv/bin/python or python3)."
  exit 1
fi

cd "$PROJECT_ROOT"
exec > >(tee -a "$LOG_FILE") 2>&1

log() {
  printf '%s %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*"
}

on_error() {
  local code=$?
  log "FAIL: smoke handover run failed at line ${BASH_LINENO[0]} (exit=${code})"
  log "FAIL: see log file $LOG_FILE"
  exit "$code"
}
trap on_error ERR

if [[ ! -f "$ENV_FILE" ]]; then
  log "ERROR: missing environment file: $ENV_FILE"
  log "ERROR: copy .env.example to .env and fill DB credentials before smoke run"
  exit 1
fi

if [[ "$DATA_SOURCE" == "historical" ]]; then
  if [[ ! -f "$PROJECT_ROOT/data/raw/ICT001 S1 2025 Logs RELEASED V1.0.xlsx" ]]; then
    log "ERROR: missing historical logs workbook in data/raw"
    exit 1
  fi
  if [[ ! -f "$PROJECT_ROOT/data/raw/cleaned_standard_results.xlsx" ]]; then
    log "ERROR: missing historical results workbook in data/raw"
    exit 1
  fi
fi

run_stage() {
  local stage_name="$1"
  shift
  log "START: $stage_name"
  if "$@"; then
    log "PASS: $stage_name"
  else
    log "FAIL: $stage_name"
    return 1
  fi
}

log "INFO: smoke handover run starting"
log "INFO: run_id=$RUN_ID data_source=$DATA_SOURCE python=$PYTHON_BIN"
log "INFO: log_file=$LOG_FILE"

run_stage "ETL" \
  "$PYTHON_BIN" pipeline_runner.py --data-source "$DATA_SOURCE" --skip-feature --skip-predict --strict-exit

run_stage "Feature Engineering" \
  "$PYTHON_BIN" pipeline_runner.py --data-source "$DATA_SOURCE" --skip-etl --skip-predict --strict-exit

run_stage "Prediction" \
  "$PYTHON_BIN" pipeline_runner.py --data-source "$DATA_SOURCE" --skip-etl --skip-feature --strict-exit

log "PASS: smoke handover run completed successfully"
log "PASS: ETL -> ML feature engineering -> prediction validated"
