# Implemented vs Planned

Last updated: 2026-10-23 (premium multi-brand PicPeak config pass).

## Legend

| Tag | Meaning |
| --- | --- |
| **PicPeak native** | Built into `picpeak/aio` — we only configure/use it |
| **Our config** | Scripts, CSS, brand placeholders, docs in this repo |
| **Planned** | Not done yet |

## Working now (proven)

| Capability | How | Evidence |
| --- | --- | --- |
| Admin login + dashboard | PicPeak native | Screenshots |
| Brand → Client → Gallery (convention) | Event naming + customer fields + per-event logo | Sets demo: Mini Momentz → Divya & Ravi → Seemantham |
| Unlimited Sets | PicPeak `photo_categories` `is_folder=true` | Outdoor Portraits / Ceremony / Family / Highlights Film |
| Upload into sets | Upload with `category_id` | Seed + integrity |
| Cover / password / expiry / publish / link | PicPeak native | Seed |
| Favourites / comments | PicPeak feedback | Smoke |
| Video in a set | PicPeak + MIME allow-list | Highlights Film MP4 |
| **Exact original downloads** | `download_standard_resolution=original`, watermarks off | **`ORIGINAL_INTEGRITY.md` — 7/7 SHA-256 PASS** |
| Original filenames on download | Setting enabled | Configured |
| Client one-link all sets | Share URL; folders in gallery UI | Screenshots `12`/`13` |
| Auth / private galleries | PicPeak native — not weakened | Smoke |
| Docker Compose + Windows README | **Our config** | `apps/gallery/` |
| Brand placeholders + photography CSS | **Our config** | `brands/`, `config/css/` |
| Capability matrix | **Our docs** | `GAPS.md` |

## Unfinished / planned

| Item | Notes |
| --- | --- |
| First-class Brand entity (vs naming convention) | Optional thin wrapper later — see `GAPS.md` |
| Real brand logos & colours | Placeholders until owner assets |
| Per-set one-click ZIP in UI polish | Selected/download-all native; UX packaging planned |
| Synology storage adapter (read masters) | Interface/docs only — no NAS now |
| Independent backup automation | Documented; owner Hyper Backup / offsite |
| Branded hostnames + HTTPS | Cloudflare Tunnel planned |
| Editor workspace UI | Stub |
| TrustOS integration | Later |
| GitHub push | Blocked: Cursor App write on `elp-studios-platform` |

## UX research (public pages only)

Patterns used as inspiration (not copied assets/code): Pixieset / Pic-Time / ShootProof public marketing — photography-first covers, minimal chrome, favourites proofing, password delivery, mobile ease, video alongside photos. No e-commerce/payments/CRM in our scope.
