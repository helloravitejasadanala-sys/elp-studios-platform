# Read-only storage check for the existing ELP PicPeak volume.
# Does NOT delete, recreate, or prune volumes. Never pass -v to compose down.
#
# Run in PowerShell:
#   cd <repo>\apps\gallery
#   powershell -ExecutionPolicy Bypass -File .\scripts\verify-storage.ps1

$ErrorActionPreference = "Continue"

Write-Host "ELP storage verification (read-only)" -ForegroundColor Cyan
Write-Host "Never run: docker compose down -v"

Write-Host "`n== Docker engine =="
docker info --format "Name={{.Name}} OS={{.OperatingSystem}} Mem={{.MemTotal}}"

Write-Host "`n== PicPeak container (no changes) =="
docker inspect elp-picpeak --format "Status={{.State.Status}} Started={{.State.StartedAt}} Image={{.Config.Image}}"
docker inspect elp-picpeak --format "Binds={{json .HostConfig.Binds}} Mounts={{json .Mounts}}"

Write-Host "`n== Named volume elp-picpeak-data =="
docker volume inspect elp-picpeak-data

Write-Host "`n== Data layout inside the volume (names only) =="
docker exec elp-picpeak sh -c "ls -la /data; echo '--- db ---'; ls -la /data/db 2>/dev/null; echo '--- storage ---'; ls -la /data/storage 2>/dev/null | head"

Write-Host "`n== Usage (df of the container mount) =="
docker exec elp-picpeak df -h /data

Write-Host "`n== Folder sizes inside /data (read-only du) =="
docker exec elp-picpeak sh -c "du -sh /data /data/storage /data/db /data/backup /data/storage/events /data/storage/thumbnails 2>/dev/null"

Write-Host "`n== PicPeak health =="
try {
  Invoke-RestMethod -Uri "http://127.0.0.1:3000/health" -TimeoutSec 5 | ConvertTo-Json -Compress
} catch {
  Write-Host "Health endpoint not reachable on http://127.0.0.1:3000/health"
}

Write-Host "`nInterpretation:"
Write-Host "- Mount source 'elp-picpeak-data' is a Docker named volume on THIS Windows/WSL2 machine, not Synology, unless you later bind-mounted a NAS path."
Write-Host "- Dashboard 'capacity' is usually the virtual disk (WSL2 VHD / drive), not a dedicated gallery quota. See docs/storage.md and docs/storage-and-costs.md."
Write-Host "- Data survives 'docker compose down' (without -v) and container recreation because the volume is named elp-picpeak-data."
Write-Host "- 70/85/95% alerts, per-event photo/video, remaining-capacity estimate: Studio Console → Storage, or python scripts\storage-report.py"
Write-Host "- This script never archives, deletes, or enables paid backup destinations."
