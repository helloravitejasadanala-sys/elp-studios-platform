# NAS, storage, and backup architecture

Planning only. The live gallery stays on Windows Docker volume **`elp-picpeak-data`**. The Synology is **unhealthy until you verify it**. Do not copy galleries, initialise volumes, or open Container Manager as part of this PR.

Official PicPeak references used here:

- [Single-container install](https://docs.picpeak.app/deployment/single-container)
- [External Media (Reference Mode)](https://docs.picpeak.app/features/external-media)
- [Backup and Restore](https://docs.picpeak.app/guides/backup-restore)
- [Example: NAS at home](https://docs.picpeak.app/deployment/nas-example)

This document replaces `docs/synology-deployment-plan.md` for new work. Leave that file as the earlier Phase 2 note.

---

## Hard rules

1. Never delete, reset, replace, reformat, or initialise NAS volumes or storage pools.
2. Never run `docker compose down -v`.
3. Never delete or recreate `elp-picpeak-data`.
4. Never mount PicPeak `/data` (the SQLite database volume) on an SMB/CIFS share. SQLite corrupts over network filesystems.
5. Never bind-mount the studio master archive as PicPeak `/data`.
6. Never treat a copy on the same disk, or `/data/backup` on the same volume, as a real backup.
7. Agents must not access the NAS. You (or an approved local session) do NAS work.

---

## What exists today

```
Windows PC (Docker Desktop / WSL2)
  └── container elp-picpeak  (picpeak/aio:stable, host :3000)
        └── volume elp-picpeak-data → /data
              ├── /data/db          picpeak.db, jwt.secret, backup-manifest.key
              ├── /data/storage     uploads, thumbnails, archives
              ├── /data/logs
              └── /data/backup      unused (same volume)

Synology NAS
  └── storage pool previously degraded or missing
  └── not in compose — no bind-mount
```

PicPeak’s ~763 GB “capacity” is the WSL2 virtual disk, not the NAS.

---

## Target shape (only after the pool is Healthy)

Three **separate** stores:

| Store | Role | Who writes |
| --- | --- | --- |
| **Local working** | Editor scratch, Lightroom catalogs, video caches | That editor’s PC |
| **NAS studio library** | Event folders, masters, selects, footage, approved JPEGs/MP4s | Studio + assigned editors via Drive |
| **PicPeak `/data`** | SQLite + thumbnails + any files PicPeak manages | PicPeak container only, on **local** disk (Windows volume now; later a NAS *local* folder, never SMB) |

Approved stills that clients should see can be **referenced** (not copied as masters) through PicPeak External Media:

```
NAS  …/events/…/07-approved   ──ro mount──►  container /external-media
PicPeak /data                 ── named volume or local bind ──►  /data
```

`EXTERNAL_MEDIA_ROOT=/external-media` and the mount **must** be `:ro`. PicPeak then stores references + thumbnails. Masters stay on the NAS and need their **own** backup.

### External Media limits (stable)

From PicPeak docs (as of 2026-10-18):

- Import accepts `.jpg`, `.jpeg`, `.png`, `.webp` only. **RAW is not imported.**
- **`aio:stable` imports photos only.** Video import from a watched folder is a **beta** feature.
- Deleting a file on the share does **not** delete the gallery row on stable.
- SuperAdmin assigns which account may browse which folder.

So: put **approved web JPEGs** (and, for now, upload finished films through PicPeak Admin) in `07-approved`. Keep RAW and camera footage **out** of the External Media root.

---

## Event folder structure

Create this on the NAS **only after** Stage 2 health gates pass. Use a dedicated share, for example `elp-studio`, on the healthy volume. Do not put it inside the PicPeak `/data` folder.

```
elp-studio/
  00-templates/
    event-template/                 # copied for each new job
  brands/
    mini-momentz/
    katha-films/
    tattva-weddings/
  events/
    2026/
      2026-10-24_mini-momentz_client-slug/
        00-brief/                   # brief, refs, shot list (admin writes)
        01-selects/                 # photo RAW / JPEG selects
        02-footage/                 # video originals
        03-proxies/                 # ffmpeg proxies (disposable)
        04-working/                 # optional; prefer local disk
        05-edited/                  # editor uploads
        06-review/                  # notes, revision lists
        07-approved/                # finals for the gallery (External Media)
        08-delivery/                # client packages if needed
        PROJECT.md                  # assignee, due, priority, status
  picpeak-volume-backups/           # tar copies of elp-picpeak-data — not the live volume
  secrets-copies/                   # jwt.secret + backup-manifest.key (restricted ACL)
```

Slug: `YYYY-MM-DD_<brand>_<short-client>`. One event = one folder. Photo editors get `01-selects`, `05-edited`, `06-review` on **their** jobs. Video editors get `02-footage`, `03-proxies`, `05-edited`, `06-review`. Only studio admin writes `07-approved` and `08-delivery`.

---

## Local working storage

| Machine | Keep local | Sync with Drive |
| --- | --- | --- |
| Windows gallery host | Docker VHD + `elp-picpeak-data` | Backup tars **out** to another disk, then to NAS `picpeak-volume-backups` |
| Photo editor PC | Lightroom catalog, Smart Previews, cache | Assigned event `01-selects` + `05-edited` |
| Video editor PC | Proxy timeline, cache, project file | Assigned `02-footage` (or proxies only) + `05-edited` |

Do not ask PicPeak to read RAW, Lightroom catalogs, or Premiere/DaVinci projects.

---

## Automated copy and integrity (design, not built)

After folders exist:

1. Card dump → `00-inbox` or straight into the event `01-selects` / `02-footage`.
2. `robocopy` / `rsync` with logging. No silent overwrite of `07-approved`.
3. Checksums: `Get-FileHash` (SHA-256) written to `06-review/checksums.sha256` for anything that enters `07-approved`.
4. Spot-check: open three files, confirm byte size + hash before PicPeak import.
5. PicPeak: either **upload** approved files in Admin, or (later) Rescan External Media on that event.

A disconnected mount must not delete gallery photos. PicPeak stable already keeps rows if the file vanishes; still treat a missing mount as an incident, not a cleanup.

---

## PicPeak `/data` backups (separate from the NAS library)

PicPeak docs: back up the **whole volume**, not only `picpeak.db`. Built-in backup **does not include** `jwt.secret`. Lose that file and sessions and gallery links break. `backup-manifest.key` is required to authenticate a PicPeak-format backup on a new host.

| Path | Must copy |
| --- | --- |
| `/data/db/picpeak.db` (+ `-wal`/`-shm` if present) | Yes |
| `/data/db/jwt.secret` | Yes — also keep a second copy in `secrets-copies/` |
| `/data/db/backup-manifest.key` | Yes, once it exists |
| `/data/storage` | Yes |
| `/data/logs` | Optional |
| `/data/backup` | Only if you later enable in-app backup to a **different** disk |

**Layer A — Windows (do this first, Stage 1)**  
Read-only helper container, tar to another local disk (not the Docker VHD):

```powershell
docker run --rm -v elp-picpeak-data:/data:ro -v "D:\elp-backups:/backup" alpine `
  tar czf /backup/picpeak-data-backup.tgz -C /data .
```

Then restore that tar into a **throwaway** volume and start a second PicPeak on another port. Open one known gallery. Never restore onto the live volume first.

**Layer B — NAS (only when Healthy)**  
Copy the proven tar into `elp-studio/picpeak-volume-backups/`. Same-NAS copy is still not off-site.

**Layer C — independent NAS backup**  
Hyper Backup (or equivalent) of `elp-studio` **and** the volume-backup share to USB / a second NAS / Synology C2 — **your choice, after you price it**. Same-NAS replication is not this layer.

**Layer D — off-site**  
At least one copy that survives fire/theft of the studio.

Leave PicPeak **Admin → Backup** off until the destination is a **separate** writable mount, not `/data/backup`.

---

## Recovery (must be practised)

1. Confirm the tar opens and contains `db/jwt.secret` and `db/picpeak.db`.
2. `docker volume create elp-picpeak-restore-test` (never reuse the live name).
3. Extract the tar into that volume.
4. Start `picpeak/aio:stable` with that volume on e.g. host port `3001`.
5. Log in, open one existing client gallery, download one original, confirm the share link.
6. Stop and remove **only** the test container and test volume.

If the live container dies: recreate the **container** against the **same** `elp-picpeak-data` volume. Recreating the container is safe. Recreating the volume is not.

After a power cut: check Docker Desktop is running, `docker volume ls` still shows `elp-picpeak-data`, then `docker compose up -d picpeak`. Never `-v`.

---

## Capacity and alerts

| Where | What to watch |
| --- | --- |
| Windows now | `verify-storage.ps1`, `storage-report.py`, PicPeak System Status. ELP 70 / 85 / 95% of *reported* disk. |
| NAS later | DSM Storage Manager (pool / volume health and free TB). Plan **3–5×** current gallery size once video is routine. |
| Backup targets | Each full `/data` tar is about the size of `/data`. Keep room for several copies. |

Do not set `STORAGE_CAPACITY_OVERRIDE_GB` until `verify-storage.ps1` matches the disk you mean.

---

## Network (later, not now)

- Client galleries: HTTPS via DSM reverse proxy or Cloudflare Tunnel. Set `FRONTEND_URL`, `TRUST_PROXY=1`.
- Admin: not on the open internet. Tailscale / VPN / Cloudflare Access.
- Editors: Synology Drive over Tailscale (or LAN). Do not port-forward `:3000/admin`.
- UPS on the NAS before it hosts anything you care about.

---

## What this document does **not** do

- It does not migrate PicPeak.
- It does not create NAS folders.
- It does not enable External Media on the live container.
- It does not turn on paid C2, S3, or SMTP.

Answer `QUESTIONS.md`, then see `SAFE-MIGRATION-PLAN.md` Stage 1.
