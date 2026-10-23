# Original download integrity (SHA-256)

- Gallery: **Mini Momentz → Divya & Ravi → Seemantham** (event `7`)
- Client path: `/gallery/other-mini-momentz-divya-ravi-seemantham-2026-10-12/1c325723b8ca26d82e19228c2b6c31cf`
- Config: `download_standard_resolution=original`, watermarks off, original filenames on
- Result: **7 PASS / 0 FAIL**

| Set | File | Source↔Stored | Source↔Download | Bytes |
| --- | --- | --- | --- | ---: |
| Outdoor Portraits | `mini-momentz-01.jpg` | PASS | PASS | 49855 |
| Outdoor Portraits | `mini-momentz-02.jpg` | PASS | PASS | 54055 |
| Ceremony | `mini-momentz-03.jpg` | PASS | PASS | 47965 |
| Ceremony | `mini-momentz-cover.jpg` | PASS | PASS | 83465 |
| Family | `mini-momentz-04.jpg` | PASS | PASS | 53273 |
| Family | `katha-films-01.jpg` | PASS | PASS | 46689 |
| Highlights Film | `katha-demo-clip.mp4` | PASS | PASS | 13238 |

Raw JSON: `apps/gallery/test-results/original-integrity-raw.json`

When resolution is original and watermarking is off, PicPeak returns null from `renderPhotoForDownload` and `sendFile`s the stored object — SHA-256 matches the pre-upload file.
