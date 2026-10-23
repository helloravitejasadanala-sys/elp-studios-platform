# Implemented vs Planned

Last updated: 2026-10-23 (Style A/B + owner brand specs applied).

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
| **Style A — Wedding Editorial** | `styles/wedding-editorial/` → PicPeak CSS slot 1 | Tattva demo + screenshots `20-tattva-editorial-*` |
| **Style B — Modern Story** | `styles/modern-story/` → PicPeak CSS slot 2 | Mini Momentz demo + screenshots `21-mini-modern-*` |
| Owner brand colours (config) | Tattva Soft Ivory/Deep Crimson/Plum; Mini Teal/Terracotta/… | `brands/*/brand.json`, `styles/*/style.json` |
| Brand → Client → Gallery (convention) | Event naming + customer fields + per-event logo | Seed scripts |
| Unlimited Sets | PicPeak `photo_categories` `is_folder=true` | Both style demos |
| Upload into sets | Upload with `category_id` | Seed + integrity |
| Cover / password / expiry / publish / link | PicPeak native | Seed |
| Favourites / comments | PicPeak feedback | Prior smoke |
| Video in a set | PicPeak + MIME allow-list + curl `type=video/mp4` | Reception Film / Highlights Film |
| **Exact original downloads** | `download_standard_resolution=original`, watermarks off | **`STYLES_ORIGINAL_INTEGRITY.md` — 12/12 SHA-256 PASS** |
| Download-all ZIP | Guest API | Both galleries PASS |
| Original filenames on download | Setting enabled | Configured |
| Client one-link all sets | Share URL; folders in gallery UI | Screenshots |
| Docker Compose + Windows README | **Our config** | `apps/gallery/` |
| Brand/style config (no app rebuild) | **Our config** | `brands/`, `styles/` |
| Capability matrix | **Our docs** | `GAPS.md` |

## Font / logo status (owner specs 2026-10-23)

| Asset | Status |
| --- | --- |
| Mini Momentz colours | **Applied** from brand specs image |
| Tattva colours | **Applied** (crimson/plum/ivory — not gold/bronze) |
| Futura Now / Peach Blossom | **Not shipped** — documented geometric fallbacks; Peach Blossom skipped |
| Bizantheum / Canela Trial | **Not shipped** — no PDF extraction; Georgia/system serif fallback |
| Poppins Light | Prefer when self-hosted; PicPeak CSS sanitizer blocks external font `@import` |
| Official logos | **Placeholders only** — no separate genuine logo files in store |

## Unfinished / planned

| Item | Notes |
| --- | --- |
| Licensed brand fonts embedded | Owner must supply files; sanitizer-safe delivery path |
| Real brand logos | Placeholders until owner assets |
| First-class Brand entity (vs naming convention) | Optional thin wrapper — see `GAPS.md` |
| Admin “Select Brand → Style” guided wizard | Convention + seed today; dedicated UI polish planned |
| Per-set one-click ZIP UX polish | Selected/download-all native |
| Synology storage adapter (read masters) | Interface/docs only — no NAS now |
| Independent backup automation | Documented; owner Hyper Backup / offsite |
| Branded hostnames + HTTPS / Tunnel | Cloudflare Tunnel planned |
| Editor workspace UI | Stub |
| TrustOS integration | Later |
| Katha Films dual-style demos | Config ready; not seeded this pass |

## Not production-ready

Demo credentials, placeholder logos/fonts, no Tunnel/HTTPS, no Synology, no real client media. Use for local / Dell Docker Desktop demos only.
