#!/usr/bin/env bash
# Read-only storage check. Does not delete or recreate volumes.
set -euo pipefail
echo "ELP storage verification (read-only)"
echo "Never run: docker compose down -v"
docker inspect elp-picpeak --format 'Status={{.State.Status}} Image={{.Config.Image}}'
docker inspect elp-picpeak --format '{{json .Mounts}}'
docker volume inspect elp-picpeak-data
docker exec elp-picpeak sh -c 'ls -la /data; df -h /data'
curl -sS "http://127.0.0.1:${PICPEAK_PORT:-3000}/health" || true
echo
echo "Named volume elp-picpeak-data lives on this Docker host (Windows/WSL2), not Synology, unless you bind-mounted a NAS path."
