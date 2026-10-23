# Original download integrity — Style A + Style B demos (SHA-256)

- Origin: `http://127.0.0.1:3000`
- Settings: `download_standard_resolution=original`, watermarks off, original filenames on
- Result: **12 PASS / 0 FAIL** of 12 files

## Tattva Weddings — Wedding Editorial (`id=5`)
- Client path: `/gallery/other-tattva-weddings-ananya-rohan-wedding-day-2026-10-05/855445a3588571e906baf3a8109c4431`
- Sets: Getting Ready, Ceremony, Portraits, Reception Film
- Download-all ZIP: PASS

| Set | Source file | Bytes | SHA-256 match |
| --- | --- | ---: | --- |
| Getting Ready | `tattva-weddings-01.jpg` | 49847 | PASS |
| Getting Ready | `tattva-weddings-02.jpg` | 54313 | PASS |
| Ceremony | `tattva-weddings-03.jpg` | 50197 | PASS |
| Ceremony | `tattva-weddings-cover.jpg` | 84943 | PASS |
| Portraits | `tattva-weddings-04.jpg` | 54230 | PASS |
| Reception Film | `katha-demo-clip.mp4` | 13238 | PASS |

## Mini Momentz — Modern Story (`id=6`)
- Client path: `/gallery/other-mini-momentz-divya-ravi-seemantham-2026-10-12/41ce4a1960bf38bb14773e1e05b86d49`
- Sets: Outdoor Portraits, Ceremony, Family, Highlights Film
- Download-all ZIP: PASS

| Set | Source file | Bytes | SHA-256 match |
| --- | --- | ---: | --- |
| Outdoor Portraits | `mini-momentz-01.jpg` | 49855 | PASS |
| Outdoor Portraits | `mini-momentz-02.jpg` | 54055 | PASS |
| Ceremony | `mini-momentz-03.jpg` | 47965 | PASS |
| Ceremony | `mini-momentz-cover.jpg` | 83465 | PASS |
| Family | `mini-momentz-04.jpg` | 53273 | PASS |
| Highlights Film | `katha-demo-clip.mp4` | 13238 | PASS |

Raw: `apps/gallery/test-results/styles-original-integrity-raw.json`
Meta: `apps/gallery/test-results/styles-demo-galleries.json`

Guest download endpoints return **exact uploaded bytes** when original resolution is standard and watermarks are off.
