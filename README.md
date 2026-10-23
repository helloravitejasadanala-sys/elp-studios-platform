# ELP Studios Platform

Working demo stack for **client galleries** (PicPeak) and a later **editor workspace**.  
This repository is **separate from** `trustos-pilot` (TrustOS). Do not merge gallery code into TrustOS.

Brands (client-facing identity per gallery): **Mini Momentz**, **Katha Films**, **Tattva Weddings**.

## What’s in this repo

| Path | Purpose |
| --- | --- |
| `apps/gallery/` | PicPeak Docker Compose + sample env + smoke tests |
| `apps/editor/` | Editor workspace (demo UI; Priority 2) |
| `demo-media/` | Royalty-free / generated placeholder photos for demos |
| `IMPLEMENTED.md` | Done vs planned checklist |

**Hard rules:** no Synology NAS access from agents; demo media only; no real client PII or hardcoded production secrets (use `.env` from `.env.example`).

---

## Priority 1 — Client galleries (PicPeak)

We run the official **all-in-one** image (`picpeak/aio:stable`): one container, SQLite, one volume.  
Docs: [Single-container install](https://docs.picpeak.app/deployment/single-container).

### Requirements

- Docker Desktop (Windows / macOS) or Docker Engine + Compose v2 (Linux)
- ~2 GB free RAM for the container
- Ports: host `3000` → container `3000` (configurable)

### Windows (Docker Desktop on Dell) — install and run

1. Install [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) and start it. Wait until the whale icon shows **Engine running**.
2. Open **PowerShell** or **Windows Terminal**.
3. Clone this repo:

   ```powershell
   git clone https://github.com/helloravitejasadanala-sys/elp-studios-platform.git
   cd elp-studios-platform\apps\gallery
   ```

4. Create env file:

   ```powershell
   copy .env.example .env
   notepad .env
   ```

   Set `ADMIN_PASSWORD` to a strong demo password (upper + lower + number, **12+ chars** preferred for PicPeak first-boot change). First login may require changing the password in Admin before APIs unlock.

5. Start:

   ```powershell
   docker compose up -d
   ```

6. Open admin: http://localhost:3000/admin  
   Login with `ADMIN_USERNAME` / `ADMIN_PASSWORD` from `.env`.

7. **Quick Style A/B demo** (after Python 3 is available):

   ```powershell
   python scripts\seed-styles-demo.py
   ```

   Or manually: Select CSS template (Wedding Editorial / Modern Story) → create event → sets → upload from `demo-media\` → publish → copy client link. Guest password from `GUEST_PASSWORD` if seeded.

8. Client: open the share link in a private window — Cover → View Gallery → sets → photo/video → downloads.

9. Stop:

   ```powershell
   docker compose down
   ```

   Data stays in the Docker volume `elp-picpeak-data` until you remove the volume.

**HTTPS preview:** not enabled in this demo (`COOKIE_SECURE=auto`, no Tunnel). For HTTPS later, set `FRONTEND_URL` + Cloudflare Tunnel (or similar) and `TRUST_PROXY=1` — see Planned items in `IMPLEMENTED.md`.

### Linux / macOS

```bash
cd apps/gallery
cp .env.example .env
# edit ADMIN_PASSWORD
docker compose up -d
# Admin: http://localhost:3000/admin
```

### Persistent storage

| Location | Contents |
| --- | --- |
| Docker volume `elp-picpeak-data` → `/data` | DB, JWT secret, photos, thumbnails, built-in backups |

List the volume:

```bash
docker volume inspect elp-picpeak-data
```

**Backup (recommended):** copy the whole volume, not only the DB. The JWT secret lives at `/data/db/jwt.secret` and is required to keep sessions/links valid after restore.

```bash
# Example: tar the volume via a helper container
docker run --rm -v elp-picpeak-data:/data -v "%CD%:/backup" alpine \
  tar czf /backup/picpeak-data-backup.tgz -C /data .
```

**Restore:** stop the stack, empty/replace volume contents from the archive, start again.

PicPeak also has an in-app backup under Admin; still keep a copy of `jwt.secret` / the whole `/data` tree. See [PicPeak Backup & Restore](https://docs.picpeak.app/).

### Brand + style separation (config-driven)

One PicPeak instance (saves RAM). Per gallery:

- **Brand** — `brands/<id>/brand.json` + labelled logo placeholder (`brands/placeholders/`)
- **Style** — `styles/wedding-editorial` (Style A) or `styles/modern-story` (Style B) → PicPeak CSS template slots

Owner brand colours (Tattva crimson/plum/ivory; Mini teal/terracotta/…) live in those config files. Change fonts/colours there and re-apply the CSS template — **no app rebuild**. Official fonts/logos are **not** invented; see `styles/README.md`.

Optional hostnames (Cloudflare Tunnel later): `gallery.minimomentz…`, `gallery.kathafilms…`, `gallery.tattvaweddings…` → same container.

### Style demos (Tattva + Mini Momentz)

```bash
cd apps/gallery
docker compose up -d
python3 scripts/seed-styles-demo.py          # Style A + B galleries, SHA-256 integrity
python3 scripts/capture-styles-screenshots.py # optional Playwright shots
```

Results: `apps/gallery/test-results/STYLES_ORIGINAL_INTEGRITY.md`

### Smoke tests

```bash
cd apps/gallery
./scripts/smoke-test.sh
```

Results are written to `apps/gallery/test-results/SMOKE_TEST_RESULTS.md`.

### Screenshots

Verified demo screenshots live in the Project store:

`/cursor/stores/.../media/gallery-prototype/` (see that folder’s README after a demo run).

---

## Priority 2 — Editor workspace

See `apps/editor/README.md`. Local demo UI with roles, assigned projects, deadlines, references, submissions, review comments. Synology Drive / Tailscale are **stubs only** — no NAS.

---

## Priority 3 — ELP Studios OS (TrustOS)

`trustos-pilot` remains the TrustOS app. Integration is design-only for now: dashboard can later surface gallery/editor/delivery status via links or APIs. Do not recreate TrustOS here.


## Original downloads (critical)

Configure PicPeak so guest downloads are **exact uploaded bytes**:

- `download_standard_resolution=original`
- `download_allow_original=true`
- watermarks off (global + per-gallery)
- `general_use_original_filenames_for_downloads=true`

Prove with: `python3 apps/gallery/scripts/seed-styles-demo.py` → `apps/gallery/test-results/STYLES_ORIGINAL_INTEGRITY.md` (SHA-256), or the earlier `seed-sets-demo.py` / `ORIGINAL_INTEGRITY.md`.

Thumbnails/previews are separate display renditions under `/data/storage/thumbnails`.

## Sets (albums)

PicPeak **event categories** with `is_folder: true` are used as Sets. Seed: `scripts/seed-sets-demo.py`.

## Storage adapter (future Synology)

PicPeak already abstracts storage. Later: point media roots at Synology shared folders via documented storage settings — **read masters; never modify/delete the studio archive from the gallery app**. Same-NAS gallery volume is **not** an independent backup; keep a second copy of `/data` (or Synology Hyper Backup / offsite).

