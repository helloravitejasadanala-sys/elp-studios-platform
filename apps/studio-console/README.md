# ELP Studio Console

A small companion for PicPeak: tabbed gallery creation, three-brand picker, optional email, WhatsApp sharing, and a simpler dashboard.

It does **not** replace PicPeak, store photos, or touch the `elp-picpeak-data` volume.

- PicPeak Admin remains at http://localhost:3000/admin
- Studio Console is at http://localhost:3080

## Start (existing install)

From `apps/gallery`, with Docker already running PicPeak:

```powershell
docker compose up -d studio-console
```

Do **not** use `docker compose down -v`.

Then apply video + optional-email settings (does not delete galleries):

```powershell
python scripts\apply-platform-settings.py --dry-run
python scripts\apply-platform-settings.py
```

## Without Compose

```powershell
cd apps\studio-console
$env:PICPEAK_ORIGIN="http://127.0.0.1:3000"
python server.py
```
