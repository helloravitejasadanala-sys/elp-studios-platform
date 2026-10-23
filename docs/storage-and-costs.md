# Storage & cost monitoring

Use this when running PicPeak heavily (photos **and** video) so disk fills and bills do not surprise you.

Nothing in this document, the Studio Console Storage page, or `scripts/storage-report.py` deletes galleries, removes the Docker volume, enables PicPeak backup, or signs you up to a paid service.

## What PicPeak already does (we did not replace this)

| Need | Native PicPeak | ELP extra |
| --- | --- | --- |
| Bytes used + disk total/free | `GET /api/admin/settings/storage/info` (`total_used` from a disk walk on local backends, `disk_total` / `disk_available` from `fs.statfs`) | Same numbers on Studio Console → **Storage** |
| Top events by original size | `storage_by_event` (catalogued `photos.size_bytes`, top 10) | Per-event **photo vs video** split from each event’s media list |
| One advisory cap | Settings → System Status → **Storage soft limit (GB)**. Warns only; does **not** delete galleries | Three alerts at **70% / 85% / 95%** of reported capacity |
| Archive | Admin → Archive Gallery: zip, then **active originals are deleted**. Restore from Events → Archives | Type-the-name safeguard, then a **link** into Admin. Console never calls archive/delete APIs |
| Trash | Deleted photos stay ~30 days (still using disk) | Documented only |
| Backup | Admin → Backup & Restore. Default **`backup_enabled=false`**. aio writes `/data/backup` on the **same** volume | Status + restore-test checklist. We do **not** turn backup on or add S3 |

Admin UI: http://localhost:3000/admin (System Status, Backup, Events → Archives).

## Actual Docker usage vs the huge “capacity” number

Photos live in named volume **`elp-picpeak-data`** → container `/data`.

| Check | Command / place |
| --- | --- |
| Volume still named correctly | `docker volume inspect elp-picpeak-data` |
| Capacity the container can see | `docker exec elp-picpeak df -h /data` (same family of numbers as PicPeak’s disk_total) |
| Gallery tree size | `docker exec elp-picpeak du -sh /data /data/storage /data/db /data/backup` |
| Packaged report | `python apps/gallery/scripts/storage-report.py` |
| PowerShell wrapper | `apps/gallery/scripts/verify-storage.ps1` |

On Docker Desktop for Windows, `df` / PicPeak `disk_total` is usually the **WSL2 virtual disk**, not Synology and not a gallery quota. A figure near hundreds of GB (for example ~763 GB) is that virtual disk. Used space (`total_used`) is what PicPeak actually wrote (originals, thumbnails, archives, caches).

Do **not** set `STORAGE_CAPACITY_OVERRIDE_GB` until `verify-storage.ps1` matches what you intend to treat as capacity.

**Never:** `docker compose down -v`, `docker volume rm elp-picpeak-data`.

## Alerts (70 / 85 / 95)

ELP computes `percent_used = total_used / disk_total` (or PicPeak’s single soft limit if disk total is missing).

| Fill | Level | What to do |
| --- | --- | --- |
| &lt; 70% | OK | Keep an off-disk backup anyway |
| ≥ 70% | Watch | Plan archives; confirm a copy exists off this disk |
| ≥ 85% | Warning | Pause large video batches; archive finished events **in PicPeak Admin** |
| ≥ 95% | Critical | Uploads may fail; free space or enlarge the disk. Still never `-v` |

PicPeak’s own banner uses **one** soft limit (docs recommend ~80% of available). Leave that as the native warning; ELP adds the three-tier view. Setting the PicPeak limit is optional and advisory — it does not delete data.

## Remaining capacity estimate

Studio Console / `storage-report.py` sums catalogued file sizes uploaded in the last **14 days** and divides reported **free** bytes by that daily rate.

- Idle (no recent uploads): free space is unchanged; there is no burn-rate.
- Low sample counts are labelled low confidence.
- The estimate is “until this Docker/WSL2 disk fills”, not a billed cloud quota.

## Per-event photo and video

PicPeak `storage_by_event` is **originals only**, all types together, top events. ELP also lists each gallery’s media and classifies:

- Photos: jpg/jpeg/png/webp/gif/heic/…
- Videos: mp4/m4v/mov/webm/avi

Thumbnails and download zips sit in PicPeak’s `storage_breakdown` when the disk walk succeeded; they are extra bytes on the same volume.

## Archive and deletion (confirmation)

Archive **is not** a backup.

1. Type the exact gallery name on Studio Console → Storage to unlock the Admin link (no API delete).
2. In PicPeak, Archive Gallery writes `events/archived/{slug}-….zip`, then removes active originals, thumbnails, hero files, and cached watermarks. The public URL stops working.
3. Restore from **Events → Archives** (extract + thumbnail rebuild).
4. **Delete** on the Archives page removes the zip and the database row — permanent.
5. Event expiry can auto-archive. Photo trash (default 30 days) is separate and still uses disk.

This console does not archive, restore, or delete.

## Backup status and restore testing

Default: **off**. The all-in-one image would write local backups under `/data/backup` — **same volume as the photos**, so it is not an independent copy.

Safe copy (does not wipe anything):

```powershell
docker run --rm -v elp-picpeak-data:/data -v "${PWD}:/backup" alpine tar czf /backup/picpeak-data-backup.tgz -C /data .
```

Keep that archive on another disk. Include `/data/db/jwt.secret` so share links still verify after restore.

**Restore test (required before you trust a backup):** restore the tar into a **spare** folder or a throwaway volume; start a second PicPeak on another port; open one known gallery. Do **not** restore over the live volume first. PicPeak’s UI Restore overwrites the live database — practise on a spare instance. Tick the checklist on the Storage page (saved only in that browser).

Do not enable S3/rsync destinations from this repo. Those are optional paid or extra-infra choices you make later in Admin.

## Cost categories (no commitments)

| Category | This install | When it might cost money |
| --- | --- | --- |
| **Software** | PicPeak is open-source; no monthly licence. Studio Console is local. | Never, unless you later buy unrelated apps |
| **Hosting** | Windows PC + Docker Desktop disk/electricity. Synology is **plan only**. | NAS electricity later; or a VPS if you ever leave the studio |
| **Backup** | Off. A local tar is free. Same-disk `/data/backup` is not a second copy. | Extra disk, Synology Hyper Backup/C2, or object storage **if you choose them** |
| **Optional third-party** | Not enabled: SMTP, Cloudflare Tunnel/domain, S3/R2/B2, paid analytics, WhatsApp Business API. `wa.me` share links are free. | Only if you create those accounts yourself |

## Technical limits (upload, video, performance)

From PicPeak `aio:stable` + this compose file (not extra ELP caps):

| Limit | Default / behaviour |
| --- | --- |
| Photo size | 50 MB (Admin range 1–500 MB) |
| Video size | 500 MB (raise in Admin; docs mention up to 10 GB; reverse-proxy body size must match) |
| Files per batch | 500 (1–2000) |
| Batch request | 95 MB (Cloudflare is ~100 MB — use chunked upload for larger files) |
| Chunked upload | 10 MB chunks; Studio Console uses this above ~40 MB |
| Simultaneous uploads | SQLite in aio: **one writer**; extra uploads queue. Several staff uploading at once needs PostgreSQL compose, not this image |
| Admin in-flight | ~16 requests/account, 64/deployment; staged bytes vs free disk (`ADMIN_UPLOAD_LIMITS_JSON`) |
| Video processing | Poster frame ~1s. Browser-playable copies / HLS are **beta and off** so originals are not recompressed |
| RAM / CPU | 4 GB+ recommended with regular video; 2 GB hosts should set `UPLOAD_PROCESSOR_CONCURRENCY=1` |
| Trash | 30 days; still occupies disk |

Prefer H.264 MP4. MOV may not play in every browser until you opt into beta transcode (extra CPU **and** disk).

## Synology

Not connected. Do not migrate until the NAS pool is healthy — `docs/synology-deployment-plan.md`.
