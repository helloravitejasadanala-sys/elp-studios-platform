# PicPeak capabilities vs ELP product model

Short verification (2026-10-23) against running `picpeak/aio:stable`. Prefer configure/extend; custom-build only where blocked.

| Need | PicPeak | Status |
| --- | --- | --- |
| Brand → Client → Gallery | No first-class Brand tree. **Gallery = event**; brand via per-event logo/CSS/name prefix; client via `customer_name` / email | **Configured** (`brands/*/brand.json` + seed). True Brand entity = Planned |
| Gallery visual **styles** (A/B) | CSS templates (slots) per event | **Configured** — `styles/wedding-editorial`, `styles/modern-story` |
| Owner brand colours | Via CSS custom properties on `.gallery-page` | **Configured** from brand-specs image (not Macro) |
| Owner brand fonts | CSS templates; **sanitizer blocks external font `@import`** | **Fallback stacks only** until licensed files + sanitizer-safe path |
| Unlimited Sets inside a gallery | **Yes** — `photo_categories` with `event_id`, `is_folder: true` | **Native** |
| Upload into sets | **Yes** — upload `category_id` | **Native** |
| Cover image | **Yes** — `header_style=hero`, `hero_photo_id` | **Native** |
| Password + expiry | **Yes** | **Native** |
| Favourites / comments | **Yes** — feedback settings | **Native** |
| One client link, all sets | **Yes** — single share URL | **Native** |
| Video in gallery | **Yes** — allow `mp4` in `general_allowed_file_types`; curl must send `type=video/mp4` | **Configured** |
| Fullscreen viewer | **Yes** — client UI | **Native** |
| Download single / all / set | Single + ZIP-all **Yes**. Per-set ZIP via filter/selected | **Native** |
| **Exact original bytes** | `download_standard_resolution=original`, watermarks **off** | **Proven** SHA-256 (Style demos 12/12) |
| Use original filenames | `general_use_original_filenames_for_downloads` | **Configured** |
| Storage adapter for Synology later | Storage abstraction exists; Synology = docs only | **Stub / Planned** — no NAS |
| Official logos | Per-event logo upload | **Placeholders** — no genuine logo files in store yet |
| Backup | Volume `/data` + in-app backup; same-NAS ≠ independent backup | **Documented** in README |

## Genuine blockers (none for first bar)

Sets + original download integrity + config-driven Style A/B work on PicPeak without a rewrite. Remaining work is licensed fonts/logos, Tunnel/HTTPS, Synology adapter, and admin wizard polish — not a gallery rebuild.

## Pre-production testing gaps

- Cross-browser font fallback rendering (Windows vs macOS geometric stacks)
- Fullset ZIP contents vs category filter edge cases
- Long-session guest token / password change flows under Tunnel + HTTPS
- Real photography (not solid placeholder demos) for hero contrast QA
- Accessibility contrast audit on every hero colourway
