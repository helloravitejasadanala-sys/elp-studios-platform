# Future Synology hosting (plan only — do not migrate yet)

This is a deployment **plan**. Do not move galleries, volumes, or DNS until NAS health is verified.

The current live gallery is on the Windows PC Docker volume `elp-picpeak-data`. The NAS previously showed a degraded or missing storage pool. **No copy, rsync, or Container Manager deploy until that is healthy and backed up.**

## 1. NAS health gates (must all pass)

- Storage pool is Healthy (not degraded, crashed, or missing)
- Volumes have headroom (plan 3–5× current gallery size for video)
- SHR/RAID status clean; no uninitiated disks
- Hyper Backup (or equivalent) has a recent successful job to a **second** target
- DSM is current enough for Container Manager
- You can restore a test folder from backup

If any gate fails: stay on the Windows Docker volume.

## 2. Synology requirements

- Container Manager (Docker) with Compose
- A dedicated shared folder, e.g. `docker/elp-picpeak`, on the **healthy** volume
- 4 GB+ RAM recommended once video is in regular use
- Do **not** bind-mount the studio photo archive as PicPeak’s `/data` in a way that lets the gallery app modify or delete masters

Recommended layout:

- `/volumeX/docker/elp-picpeak/data` → container `/data` (gallery DB + delivered copies)
- Studio masters stay in a **separate** share, read-only later if you add a storage adapter

## 3. Backup and restore

- Independent backup of `/data` (Hyper Backup + offsite)
- JWT secret lives under `/data/db/jwt.secret` — required to keep links valid
- Test restore on a spare folder before going live
- Same-NAS copy is not an independent backup

## 4. HTTPS, domain, remote access

- Reverse proxy in DSM (or Cloudflare Tunnel) with a real certificate
- Set `FRONTEND_URL` to the public HTTPS origin
- `TRUST_PROXY=1` and `COOKIE_SECURE` appropriate for HTTPS
- **Never publish `/admin` on the open internet without:**
  - HTTPS
  - strong unique admin password
  - IP allow-list / VPN / Tailscale for admin, or Cloudflare Access
- Client gallery links can be public HTTPS; admin should not be

## 5. Remote laptop access

Preferred: Tailscale (or similar VPN) to the NAS, then browse `https://gallery…` or the LAN IP. Do not port-forward 3000/admin to the world.

## 6. Upload performance

- Local NAS uploads are LAN-limited; remote uploads are upload-bandwidth limited
- Keep PicPeak `Max Video Size` and the reverse-proxy body limit aligned (docs: `client_max_body_size` up to several GB)
- Chunked upload is already used by the Studio Console for files over 40 MB

## 7. Power / internet failure

- UPS on the NAS
- Docker restart policy `unless-stopped` (already in compose)
- After outage: confirm volume healthy, then `docker compose up -d` — **never** `-v`
- Clients keep working when the NAS is up; links do not need the Windows PC once hosted on the NAS

## 8. Migration when ready (later)

1. Backup Windows `elp-picpeak-data`
2. Restore that archive into the NAS data folder
3. Start PicPeak with the **same** image tag `picpeak/aio:stable`
4. Test one draft gallery and one existing client gallery
5. Only then change DNS / Tunnel

Do not run this migration as part of Phase 2.
