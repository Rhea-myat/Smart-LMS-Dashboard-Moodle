#!/usr/bin/env bash
set -Eeuo pipefail

# Production nightly runner for Smart-LMS ETL + feature engineering + prediction.
# Safe defaults can be overridden via environment variables in cron.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$SCRIPT_DIR}"
LOG_DIR="${LOG_DIR:-$PROJECT_ROOT/logs}"
LOCK_FILE="${LOCK_FILE:-/tmp/smart_lms_pipeline.lock}"
RUN_LOG="${RUN_LOG:-$LOG_DIR/cron_pipeline.out}"
ENV_FILE="${ENV_FILE:-$PROJECT_ROOT/.env}"
REQ_FILE="${REQ_FILE:-$PROJECT_ROOT/requirements.txt}"

DATA_SOURCE="${DATA_SOURCE:-moodle}"
REUSE_STAGING="${REUSE_STAGING:-0}"
STRICT_EXIT="${STRICT_EXIT:-1}"
INSTALL_DEPS_ON_START="${INSTALL_DEPS_ON_START:-0}"
PYTHON_BIN="${PYTHON_BIN:-}"
DRY_RUN="${DRY_RUN:-0}"
USE_DOCKER="${USE_DOCKER:-1}"
DOCKER_BIN="${DOCKER_BIN:-docker}"
DOCKER_IMAGE="${DOCKER_IMAGE:-smart-lms-ml}"
DOCKER_TAG="${DOCKER_TAG:-nightly}"
DOCKER_BUILD="${DOCKER_BUILD:-auto}"
DB_HOST_DOCKER="${DB_HOST_DOCKER:-}"
DOCKER_NETWORK_MODE="${DOCKER_NETWORK_MODE:-host}"

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

umask 027
mkdir -p "$LOG_DIR"

# If running interactively (terminal attached), tee to screen AND log.
# When run by cron (no tty), output goes only to the log file.
if [[ -t 1 ]]; then
  exec > >(tee -a "$RUN_LOG") 2>&1
else
  exec >>"$RUN_LOG" 2>&1
fi

log() {
  printf '%s %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*"
}

on_error() {
  local code=$?
  log "ERROR: run_nightly failed at line ${BASH_LINENO[0]} with exit code ${code}"
  exit "$code"
}
trap on_error ERR

if ! command -v flock >/dev/null 2>&1; then
  log "ERROR: flock command not found (install util-linux)"
  exit 1
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  log "INFO: lock busy ($LOCK_FILE). Another run is active; skipping this run."
  exit 0
fi

log "INFO: nightly pipeline starting"
log "INFO: project_root=$PROJECT_ROOT data_source=$DATA_SOURCE reuse_staging=$REUSE_STAGING use_docker=$USE_DOCKER"

if [[ "$USE_DOCKER" == "1" ]]; then
  if ! command -v "$DOCKER_BIN" >/dev/null 2>&1; then
    log "ERROR: docker not found (expected command: $DOCKER_BIN)"
    exit 1
  fi

  if [[ ! -f "$PROJECT_ROOT/Dockerfile" ]]; then
    log "ERROR: Dockerfile not found at $PROJECT_ROOT/Dockerfile"
    exit 1
  fi

  IMAGE_REF="$DOCKER_IMAGE:$DOCKER_TAG"
  NEED_BUILD=0

  if [[ "$DOCKER_BUILD" == "1" ]]; then
    NEED_BUILD=1
  elif [[ "$DOCKER_BUILD" == "auto" ]]; then
    if ! "$DOCKER_BIN" image inspect "$IMAGE_REF" >/dev/null 2>&1; then
      NEED_BUILD=1
    fi
  fi

  if [[ "$NEED_BUILD" == "1" ]]; then
    if [[ "$DRY_RUN" == "1" ]]; then
      log "INFO: DRY_RUN=1, skipping image build for $IMAGE_REF"
    else
      log "INFO: building docker image $IMAGE_REF"
      "$DOCKER_BIN" build -t "$IMAGE_REF" -f "$PROJECT_ROOT/Dockerfile" "$PROJECT_ROOT"
    fi
  else
    log "INFO: using existing docker image $IMAGE_REF"
  fi

  cd "$PROJECT_ROOT"
  RUN_TS="$(date +%Y%m%d%H%M%S)"
  ENV_DB_HOST=""

  if [[ -f "$ENV_FILE" ]]; then
    ENV_DB_HOST="$(grep -E '^DB_HOST=' "$ENV_FILE" | tail -n 1 | cut -d '=' -f 2- | tr -d '\r' || true)"
  fi

  if [[ "$DOCKER_NETWORK_MODE" != "host" ]] && [[ -z "$DB_HOST_DOCKER" ]] && [[ "$ENV_DB_HOST" == "127.0.0.1" || "$ENV_DB_HOST" == "localhost" ]]; then
    DB_HOST_DOCKER="host.docker.internal"
  fi

  CMD=(
    "$DOCKER_BIN" run --rm
    --name "smart-lms-nightly-$RUN_TS"
    --network "$DOCKER_NETWORK_MODE"
    -v "$PROJECT_ROOT:/app"
    -v "$LOG_DIR:/app/logs"
    -w /app
  )

  if [[ -f "$ENV_FILE" ]]; then
    CMD+=(--env-file "$ENV_FILE")
    log "INFO: using docker env file $ENV_FILE"
  else
    log "WARN: .env not found at $ENV_FILE"
  fi

  if [[ -n "$DB_HOST_DOCKER" ]]; then
    CMD+=(
      --env "DB_HOST=$DB_HOST_DOCKER"
      --env "MOODLE_DB_HOST=$DB_HOST_DOCKER"
      --env "SOURCE_DB_HOST=$DB_HOST_DOCKER"
      --env "ML_DB_HOST=$DB_HOST_DOCKER"
    )
    log "INFO: overriding DB host env vars for docker to $DB_HOST_DOCKER"
  fi

  CMD+=("$IMAGE_REF" python pipeline_runner.py --data-source "$DATA_SOURCE")

  if [[ "$REUSE_STAGING" == "1" ]]; then
    CMD+=(--reuse-staging)
  fi

  if [[ "$STRICT_EXIT" == "1" ]]; then
    CMD+=(--strict-exit)
  fi

else
  if [[ -f "$ENV_FILE" ]]; then
    # Export .env variables for db connectivity used by ETL/ML modules.
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
    log "INFO: loaded environment from $ENV_FILE"
  else
    log "WARN: .env not found at $ENV_FILE"
  fi

resolve_python() {
  if [[ -n "$PYTHON_BIN" ]]; then
    if [[ -x "$PYTHON_BIN" ]]; then
      printf '%s\n' "$PYTHON_BIN"
      return
    fi
    log "ERROR: configured PYTHON_BIN is not executable: $PYTHON_BIN"
    exit 1
  fi

  if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
    printf '%s\n' "$PROJECT_ROOT/.venv/bin/python"
    return
  fi

  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return
  fi

  log "ERROR: python executable not found (.venv/bin/python or python3)"
  exit 1
}

  PYTHON_BIN="$(resolve_python)"
  log "INFO: python_bin=$PYTHON_BIN"

  if [[ "$INSTALL_DEPS_ON_START" == "1" ]]; then
    log "INFO: installing/updating dependencies from $REQ_FILE"
    "$PYTHON_BIN" -m pip install -r "$REQ_FILE"
  else
    log "INFO: validating required dependencies from $REQ_FILE"
    "$PYTHON_BIN" - "$REQ_FILE" <<'PY'
import importlib.metadata as md
import re
import sys
from pathlib import Path

req_file = Path(sys.argv[1])
if not req_file.exists():
    print(f"ERROR: requirements file not found: {req_file}")
    raise SystemExit(1)

missing = []
for raw in req_file.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#"):
        continue
    match = re.match(r"^([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)$", line)
    if not match:
        continue
    pkg, pinned = match.groups()
    try:
        installed = md.version(pkg)
    except md.PackageNotFoundError:
        missing.append(f"{pkg}=={pinned} (not installed)")
        continue
    if installed != pinned:
        missing.append(f"{pkg}=={pinned} (installed {installed})")

if missing:
    print("ERROR: dependency mismatch:")
    for item in missing:
        print(f" - {item}")
    raise SystemExit(1)

print("OK: dependency pins validated")
PY
  fi

  cd "$PROJECT_ROOT"

  CMD=("$PYTHON_BIN" "$PROJECT_ROOT/pipeline_runner.py" "--data-source" "$DATA_SOURCE")

  if [[ "$REUSE_STAGING" == "1" ]]; then
    CMD+=("--reuse-staging")
  fi

  if [[ "$STRICT_EXIT" == "1" ]]; then
    CMD+=("--strict-exit")
  fi
fi

log "INFO: running command: ${CMD[*]}"
START_TS="$(date +%s)"
if [[ "$DRY_RUN" == "1" ]]; then
  log "INFO: DRY_RUN=1, skipping execution"
else
  "${CMD[@]}"
fi
END_TS="$(date +%s)"

log "INFO: nightly pipeline finished successfully in $((END_TS - START_TS))s"