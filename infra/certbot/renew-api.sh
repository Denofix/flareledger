#!/usr/bin/env bash
# Host-side maintenance candidate; install only after existing renewal jobs are inspected.
set -euo pipefail

repository_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repository_root"

# Prevent overlapping invocations of this wrapper. Certbot also manages its locks.
exec 9>/run/lock/flareledger-certbot.lock
flock -n 9 || exit 0

renew_options=()
if [[ $# -gt 0 ]]; then
    if [[ $# -ne 1 || "$1" != "--dry-run" ]]; then
        echo 'Usage: renew-api.sh [--dry-run]' >&2
        exit 2
    fi
    renew_options+=(--dry-run)
fi

docker exec qresto-production-nginx-1 nginx -t
docker compose -f compose.certbot.yaml run --rm certbot renew \
    --cert-name api.flareledger.fun "${renew_options[@]}"

# A failed renewal or config check exits before any reload. A successful no-op
# renewal may reload the same certificate, which is harmless but not a new issuance.
if [[ ${#renew_options[@]} -eq 0 ]]; then
    docker exec qresto-production-nginx-1 nginx -t
    docker exec qresto-production-nginx-1 nginx -s reload
fi
