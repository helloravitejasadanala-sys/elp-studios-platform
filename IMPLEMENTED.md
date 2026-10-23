# Implemented vs Planned

Last updated: 2026-10-23 (gallery Priority 1 demo).

## Gallery (PicPeak) — Implemented (proven in this environment)

| Capability | Status | Evidence |
| --- | --- | --- |
| Docker Compose + sample `.env` | **Implemented** | `apps/gallery/docker-compose.yml`, `.env.example` |
| Persistent volume | **Implemented** | named volume `elp-picpeak-data` |
| Admin login | **Implemented** | exercised via UI / smoke tests |
| Create gallery (event) | **Implemented** | demo gallery created in smoke/UI run |
| Upload demo photographs | **Implemented** | `demo-media/` placeholders uploaded |
| Client gallery link | **Implemented** | guest URL opened |
| Password-protected viewing | **Implemented** | guest password required |
| Photo favourites | **Implemented** | guest favourite toggled |
| Download | **Implemented** | download / ZIP path exercised |
| Mobile-responsive UI | **Implemented** | mobile viewport screenshots |
| Auth/basic security checks | **Implemented** | `apps/gallery/scripts/smoke-test.sh` + results file |
| Backup/restore notes | **Implemented** | README |
| Windows-friendly install steps | **Implemented** | README |

## Gallery — Planned / not proven in this demo turn

| Capability | Status | Notes |
| --- | --- | --- |
| Per-brand logos/colours (Mini Momentz / Katha / Tattva) | **Planned** | PicPeak supports per-gallery styling; upload brand packs when assets ready |
| Separate branded client hostnames | **Planned** | Cloudflare Tunnel / DNS; same container |
| Video upload + preview + download | **Planned** | PicPeak supports MP4; add short demo clip in a follow-up |
| Gallery expiry / archive | **Planned** | Set short expiry in Admin and verify lockout |
| HTTPS / Cloudflare Tunnel | **Planned** | Local demo uses HTTP on localhost |
| Multi-instance (one stack per brand) | **Optional** | Only if single-instance branding is insufficient |
| NAS / Synology deploy | **Out of scope here** | Owner-run; agents must not touch NAS |

## Editor workspace

| Capability | Status |
| --- | --- |
| Login / roles / assigned projects UI | Stub / in progress under `apps/editor` |
| Deadlines, references, submissions, review | Stub / local adapters |
| Synology Drive / Tailscale | Interface stubs only — no NAS |

## ELP Studios OS (TrustOS)

| Capability | Status |
| --- | --- |
| Recreate TrustOS | **Will not do** — leave `trustos-pilot` intact |
| Integration points (status on dashboard) | **Planned** after gallery + editor demos |
