# PicPeak capabilities vs ELP product model

Short verification (2026-10-23) against running `picpeak/aio:stable`. Prefer configure/extend; custom-build only where blocked.

| Need | PicPeak | Status |
| --- | --- | --- |
| Brand → Client → Gallery | No first-class Brand tree. **Gallery = event**; brand via per-event logo/CSS/name prefix; client via `customer_name` / email | **Configured** (convention + seed). True Brand entity = Planned (thin wrapper later if needed) |
| Unlimited Sets inside a gallery | **Yes** — `photo_categories` with `event_id`, `is_folder: true` | **Native** — proven in sets demo |
| Upload into sets | **Yes** — upload `category_id` | **Native** |
| Cover image | **Yes** — `header_style=hero`, `hero_photo_id`; per-category hero optional | **Native** |
| Password + expiry | **Yes** | **Native** |
| Favourites / comments | **Yes** — feedback settings | **Native** |
| One client link, all sets | **Yes** — single share URL; categories appear in gallery | **Native** |
| Video in gallery | **Yes** — after allowing `mp4` in `general_allowed_file_types` | **Configured** |
| Fullscreen viewer | **Yes** — client UI | **Native** |
| Download single / all / set | Single + ZIP-all **Yes**. Per-set ZIP via filter/selected download | **Native** (set ZIP via selected or category filter) |
| **Exact original bytes** | When `download_standard_resolution=original` and watermarks **off**, `renderPhotoForDownload` returns null → `sendFile` of stored file | **Proven** with SHA-256 (see `test-results/ORIGINAL_INTEGRITY.md`) |
| Use original filenames | `general_use_original_filenames_for_downloads` | **Configured** |
| Storage adapter for Synology later | PicPeak storage abstraction exists; Synology path = interface/docs only | **Stub / Planned** — no NAS in this agent |
| Metadata ≠ original media | DB + `/data/storage` originals separate from thumbs | **Native** |
| Backup | Volume `/data` + in-app backup; same-NAS ≠ independent backup | **Documented** in README |

## Genuine blockers (none for first bar)

Sets + original download integrity work on PicPeak without a rewrite. Remaining work is product UX polish, real brand assets, Tunnel/HTTPS, and a later Synology storage adapter — not a gallery rebuild.
