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
| Admin login + dashboard | PicPeak native | Screenshots `01`–`03`, `08` |
| One admin for 3 brands | PicPeak native (single instance) + **our** seed creates Mini Momentz / Katha / Tattva events | Admin events list |
| Create gallery (few clicks / API) | PicPeak native + `seed-premium-demo.py` | Seed + smoke |
| Brand select (per gallery) | PicPeak native per-event logo + **our** placeholder logos | Event logos uploaded |
| Upload photos | PicPeak native | Demo JPGs |
| Upload finished videos | PicPeak native after **our** `general_allowed_file_types` includes `mp4` | Katha gallery has MP4 |
| Cover / hero image | PicPeak native `header_style=hero` + `hero_photo_id` | Client screenshots |
| Password + downloads | PicPeak native | Smoke 15/15 |
| Copy client link | PicPeak native share URL | Seed JSON paths |
| Favourites / comments | PicPeak native feedback (+ ensure `feedback_enabled`) | Smoke favourites |
| Archive / expire | PicPeak native (extend/archive UI); expiry proven | Extend + expired UI earlier |
| Client password gate | PicPeak native | `04`, `06` |
| Full-screen cover + title + date | PicPeak native hero header | `05` |
| Responsive grid + mobile | PicPeak native + **our** photography-first CSS | `07` |
| Download individual + all | PicPeak native | Smoke downloads |
| Video in gallery | PicPeak native (after MIME allow) | Katha event media_type=video |
| Auth / hashed passwords / private galleries | PicPeak native — **not weakened** | Smoke auth negatives |
| Docker Compose + Windows README | **Our config** | `apps/gallery/` |
| Brand placeholder logos | **Our config** | `brands/placeholders/` (labelled) |
| Photography-first CSS template | **Our config** | `apps/gallery/config/css/photography-first.css` |

## Unfinished / planned

| Item | Notes |
| --- | --- |
| Real brand logos & exact brand colours | Placeholders only until owner supplies assets |
| Branded client hostnames (Tunnel) | Planned — Cloudflare Tunnel |
| HTTPS for public clients | Planned |
| Family sharing polish beyond PicPeak share | PicPeak share links exist; no custom share app |
| Selection-submit workflow UX polish | Favourites/comments work; dedicated “submit selection” packaging planned |
| Editor workspace UI | Stub only (`apps/editor`) |
| TrustOS / ELP OS dashboard integration | Design later — do not recreate TrustOS |
| GitHub push from this agent | Blocked: `cursor[bot]` 403 on `elp-studios-platform` until Cursor GitHub App repo access includes it |

## UX research (public pages only)

Patterns used as inspiration (not copied assets/code): Pixieset / Pic-Time / ShootProof public marketing — photography-first covers, minimal chrome, favourites proofing, password delivery, mobile ease, video alongside photos. No e-commerce/payments/CRM in our scope.
