# Storage (read-only notes)

The live install uses the Docker named volume **`elp-picpeak-data`**, mounted at `/data` inside `elp-picpeak`.

## What that means

| Question | Answer |
| --- | --- |
| Where are uploaded photos? | Inside the volume: `/data/storage` (and related folders) in the `elp-picpeak` container |
| Windows path? | Docker Desktop stores named volumes in the WSL2 virtual disk, not as a normal `C:\` folder you should edit by hand |
| Synology NAS? | **Not connected** by this compose file. There is no bind-mount to a NAS share |
| Survive restart? | **Yes**, as long as you do not remove the volume |
| Survive `docker compose down`? | **Yes**, without `-v` |
| Destroyed by `docker compose down -v`? | **Yes — never run that** |

## Why the dashboard shows ~763 GB

PicPeak’s System Status reports `fs.statfs()` on the container’s storage path (`disk_total` / `disk_available`). On Docker Desktop for Windows that is usually the **WSL2 virtual disk or host drive capacity**, not “gallery quota” and not NAS capacity.

Used space (`total_used`) is the size of gallery files, thumbnails and uploads. Capacity is the disk the container can see.

If the number looks wrong, PicPeak documents capacity overrides — optional, not required:

```
STORAGE_CAPACITY_OVERRIDE_GB=...
STORAGE_AVAILABLE_OVERRIDE_GB=...
```

Do not set these until you have measured real free space with `verify-storage.ps1`.

## Safe checks (PowerShell)

From `apps\gallery`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify-storage.ps1
```

That script only inspects. It never deletes.

## Backups

PicPeak stores DB, JWT secret, photos and thumbnails together under `/data`. Copy the **whole volume**, not only the SQLite file.

Example (creates a tar in the current folder; does not wipe anything):

```powershell
docker run --rm -v elp-picpeak-data:/data -v "${PWD}:/backup" alpine tar czf /backup/picpeak-data-backup.tgz -C /data .
```

Keep that archive off the same disk as Docker Desktop.
