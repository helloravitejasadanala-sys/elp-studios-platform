# ELP Studio Console

A small companion for PicPeak: tabbed gallery creation, three-brand picker, optional email, WhatsApp sharing, a simpler dashboard, and **Storage & cost monitoring**.

It does **not** replace PicPeak, store photos, or touch the `elp-picpeak-data` volume.

- PicPeak Admin remains at http://localhost:3000/admin
- Studio Console is at http://localhost:3080
- Storage page reads PicPeak `storage/info` only. It does not archive, delete, or enable paid backup destinations.

## Start (existing install)

From `apps/gallery`, with Docker already running PicPeak:

```powershell
docker compose up -d --no-deps --force-recreate studio-console
```

`--no-deps` leaves the `picpeak` container and `elp-picpeak-data` volume untouched. Do **not** use `docker compose down -v`.

The console proxies PicPeak at **one** `/api` prefix (`POST /api/auth/admin/login`, `GET /api/auth/session`, `POST /api/auth/logout`). If PicPeak logs `HTTP 429` after earlier bad `/api/api/...` attempts, wait for that limit to lift and try sign-in **once**.

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
