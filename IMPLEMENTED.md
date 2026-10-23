# Implemented vs Planned

Last updated: 2026-10-23 (Phase 2 — video settings, Studio Console, WhatsApp, optional email).

## Legend

| Tag | Meaning |
| --- | --- |
| **PicPeak native** | Built into `picpeak/aio` — we only configure/use it |
| **Our config** | Scripts, CSS, brand files, Studio Console in this repo |
| **Planned** | Not done yet |

## Working now

| Capability | How | Evidence |
| --- | --- | --- |
| Admin login + dashboard | PicPeak native | Existing local install |
| **Video uploads** | PicPeak native once `general_allowed_file_types` includes `mp4,mov,webm` | Official [Video Support](https://docs.picpeak.app/features/video-support) docs; prior demo SHA-256 of `katha-demo-clip.mp4`; `apply-platform-settings.py` |
| Mixed photo + video galleries | Native player + FFmpeg poster frames | PicPeak docs; CSS `video` rules in styles |
| Original downloads | `download_standard_resolution=original`, watermarks off | `STYLES_ORIGINAL_INTEGRITY.md` 12/12 |
| Optional client email | `event_require_customer_email=false`; create payload omits empty email | `elp_lib.event_create_payload` tests |
| WhatsApp + copy link | Studio Console | `apps/studio-console/` |
| Tabbed event create | Studio Console (PicPeak long form unchanged) | Console wizard |
| Three brands | `brands/*/brand.json` + per-event logo/CSS | Mini/Tattva genuine logos; Katha placeholder |
| Style A/B/C CSS templates | PicPeak CSS slots 1–3 | `styles/` |
| Named volume persistence | `elp-picpeak-data` | Compose file; `docs/storage.md` |

## Font / logo status

| Asset | Status |
| --- | --- |
| Mini Momentz / Tattva genuine logos | Wired in `brands/*/logos/` |
| Katha Films logo | **Placeholder only** — no genuine file in repo |
| Licensed brand fonts | Fallbacks only |

## Unfinished / planned

| Item | Notes |
| --- | --- |
| Native PicPeak create form as tabs | Not customisable without forking PicPeak; use Studio Console |
| Guest-facing Photos/Videos tabs | Admin Media tab + Studio Console filters. PicPeak guest gallery plays mixed media; type tabs on the **client** gallery are not a stable public API |
| Browser-playable video copies / HLS | Beta PicPeak only — off on `aio:stable` so originals are not recompressed |
| Genuine Katha logo | Owner must supply |
| Licensed fonts | Owner must supply; sanitizer blocks `@import` |
| Synology hosting | Plan only — `docs/synology-deployment-plan.md` |
| Independent backup automation | Documented; owner Hyper Backup / offsite |
| Editor workspace / TrustOS | Out of scope here |

## Not production-ready

Demo credentials, Katha placeholder logo, font fallbacks, no Tunnel/HTTPS, no NAS. Use locally until NAS health is verified.
