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

### Windows (Docker Desktop) — install and run

1. Install [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) and start it. Wait until the whale icon shows **Engine running**.
2. Open **PowerShell** or **Windows Terminal**.
3. Clone this repo (after the GitHub remote exists):

   ```powershell
   git clone https://github.com/OWNER/elp-studios-platform.git
   cd elp-studios-platform\apps\gallery
   ```

4. Create env file:

   ```powershell
   copy .env.example .env
   notepad .env
   ```

   Set `ADMIN_PASSWORD` to a strong demo password (upper + lower + number, 8+ chars).

5. Start:

   ```powershell
   docker compose up -d
   ```

6. Open admin: http://localhost:3000/admin  
   Login with `ADMIN_USERNAME` / `ADMIN_PASSWORD` from `.env`.

7. Create a gallery (event), set a **guest password**, upload files from `demo-media\`, copy the client link, open it in a private window and verify favourites + download.

8. Stop:

   ```powershell
   docker compose down
   ```

   Data stays in the Docker volume `elp-picpeak-data` until you remove the volume.

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

### Brand separation (demo approach)

One PicPeak instance (saves RAM). Differentiate brands **per gallery** (logo / colours / custom styling in Admin), not three full stacks — unless you later choose multi-instance for isolation.

Optional hostnames (Cloudflare Tunnel later): `gallery.minimomentz…`, `gallery.kathafilms…`, `gallery.tattvaweddings…` → same container.

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
