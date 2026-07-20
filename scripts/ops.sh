#!/usr/bin/env bash
# Safe, reproducible maintenance commands for the local Compose deployment.
set -Eeuo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
COMPOSE=(docker compose --project-directory "$ROOT_DIR")
DATA_VOLUME="${JOBSCRAPPER_DATA_VOLUME:-jobscrapper_data}"
OLLAMA_VOLUME="${OLLAMA_DATA_VOLUME:-jobscrapper_ollama}"
BACKUP_DIR="${JOBSCRAPPER_BACKUP_DIR:-$ROOT_DIR/backups}"

die() { echo "ops: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"; }
usage() {
  cat <<'EOF'
Usage: scripts/ops.sh <restart|backup|restore|update|rollback|recover|check> [options]

  restart                         Start services after reboot (no rebuild).
  backup [directory]              Archive SQLite data and Compose volumes.
  restore <archive> --yes         Restore a data-volume archive (stops services).
  update                          Pull fast-forward changes, build, and restart.
  rollback <git-ref> --yes        Check out a known-good ref, build, and restart.
  recover                         Restart unhealthy services and print diagnostics.
  check                           Validate Compose config and service health.
EOF
}

compose() { "${COMPOSE[@]}" "$@"; }

backup() {
  need docker
  local target="${1:-$BACKUP_DIR}"
  mkdir -p -- "$target"
  local stamp archive ollama_archive
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  archive="$target/jobscrapper-data-$stamp.tar.gz"
  ollama_archive="$target/jobscrapper-ollama-$stamp.tar.gz"
  compose up -d backend >/dev/null
  # Stream the SQLite database, WAL, logs, and uploaded CVs from the named volume.
  compose exec -T backend sh -c 'tar czf - -C /app data' >"$archive"
  # Ollama is optional; a missing volume is not a failed application backup.
  if docker volume inspect "$OLLAMA_VOLUME" >/dev/null 2>&1; then
    docker run --rm -v "$OLLAMA_VOLUME:/source:ro" -v "$(cd -- "$target" && pwd):/backup" \
      alpine:3.20 tar czf "/backup/$(basename -- "$ollama_archive")" -C /source .
  fi
  echo "Created: $archive"
  [[ -f "$ollama_archive" ]] && echo "Created: $ollama_archive"
}

restore() {
  need docker
  [[ "${2:-}" == "--yes" ]] || die "restore is destructive; pass --yes"
  local archive="$1"
  [[ -f "$archive" ]] || die "archive not found: $archive"
  compose down
  # Restore only the application data tree into the named volume.
  docker run --rm -i -v "$DATA_VOLUME:/target" alpine:3.20 \
    sh -c 'rm -rf /target/data && tar xzf - -C /target' <"$archive"
  compose up -d
  echo "Restored $archive; run '$0 check' before enabling the scheduler."
}

restart() { need docker; compose up -d; "$0" check; }

update() {
  need git; need docker
  git -C "$ROOT_DIR" diff --quiet || die "working tree is not clean; commit or stash before update"
  git -C "$ROOT_DIR" pull --ff-only
  compose build
  compose up -d
  "$0" check
}

rollback() {
  need git; need docker
  [[ "${2:-}" == "--yes" ]] || die "rollback changes the checkout; pass --yes"
  git -C "$ROOT_DIR" diff --quiet || die "working tree is not clean; commit or stash before rollback"
  git -C "$ROOT_DIR" show-ref --verify --quiet "refs/$1" || git -C "$ROOT_DIR" rev-parse --verify "$1^{commit}" >/dev/null || die "unknown git ref: $1"
  git -C "$ROOT_DIR" switch --detach "$1"
  compose build
  compose up -d
  "$0" check
}

recover() {
  need docker
  compose ps
  compose up -d
  compose ps
  "$0" check || {
    echo "Recovery incomplete; collect: ${COMPOSE[*]} logs --since=30m" >&2
    compose logs --since=30m --tail=200
    return 1
  }
}

check() {
  need docker
  compose config --quiet
  compose ps
  local port="${BACKEND_PORT:-8000}"
  python3 - "$port" <<'PY'
import sys, urllib.request
port = sys.argv[1]
try:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as response:
        if response.status != 200:
            raise SystemExit(f"health status {response.status}")
except Exception as exc:
    raise SystemExit(f"health check failed: {exc}")
print("health: ok")
PY
}

[[ $# -gt 0 ]] || { usage; exit 2; }
case "$1" in
  restart) restart ;;
  backup) shift; backup "${1:-$BACKUP_DIR}" ;;
  restore) [[ $# -ge 2 ]] || die "restore requires archive and --yes"; restore "$2" "${3:-}" ;;
  update) update ;;
  rollback) [[ $# -ge 3 ]] || die "rollback requires git-ref and --yes"; rollback "$2" "$3" ;;
  recover) recover ;;
  check) check ;;
  -h|--help) usage ;;
  *) usage; exit 2 ;;
esac
